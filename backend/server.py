import asyncio
import csv
import io
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from rapidfuzz import fuzz
from starlette.middleware.cors import CORSMiddleware

from seed_data import PARCELS_GEOJSON, SEED_RECORDS
from storage import APP_NAME, MIME_TYPES, init_storage, put_object, get_object
from generate_samples import generate_all, SAMPLE_NAMES

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

TMP_DIR = Path(os.environ.get("ADHIKAR_TMP_DIR", Path(__file__).parent / "tmp_samples"))

app = FastAPI(title="Adhikar API")
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("adhikar")

PARCEL_INDEX = {f["properties"]["survey_number"]: f for f in PARCELS_GEOJSON["features"]}

# ---------- OCR ----------
_readers = {}


def get_reader(lang: str = "en"):
    key = "hi" if lang == "hi" else "en"
    if key not in _readers:
        import easyocr
        langs = ["hi", "en"] if key == "hi" else ["en"]
        _readers[key] = easyocr.Reader(langs, gpu=False, verbose=False)
    return _readers[key]


def run_ocr(path: Path, lang: str = "en") -> str:
    import cv2
    import pymupdf as fitz
    if path.suffix.lower() == ".pdf":
        doc = fitz.open(str(path))
        # 1. Digital PDF check (<0.02s)
        full_text = []
        for i in range(len(doc)):
            txt = doc[i].get_text()
            if txt and len(txt.strip()) > 30:
                full_text.append(f"--- Page {i+1} ---\n" + txt)
        if len(full_text) >= 1 and sum(len(t) for t in full_text) > 100:
            doc.close()
            return "\n\n".join(full_text)

        # 2. Scanned image PDF: Fast prioritized scanning (Page 1, Schedule pages, Preamble)
        reader = get_reader(lang)
        all_lines = []
        total_pages = len(doc)
        
        # Priority order: Page 1 (parties), Page 11 (schedule), Page 5 (preamble), Page 2, Page 12
        priority_pages = [0, 10, 4, 1, 11, 2, min(total_pages - 1, 12)]
        pages_to_scan = [p for p in priority_pages if 0 <= p < total_pages]
        
        for p in pages_to_scan[:5]:
            pix = doc[p].get_pixmap(dpi=110)
            png_path = path.with_suffix(f".page{p+1}.png")
            pix.save(str(png_path))
            
            img = cv2.imread(str(png_path))
            if img is not None:
                h, w = img.shape[:2]
                if w > 800:
                    img = cv2.resize(img, (800, int(h * 800 / w)))
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = str(png_path)

            lines = reader.readtext(gray, detail=0, paragraph=True, canvas_size=800)
            if lines:
                all_lines.append(f"--- Page {p+1} ---")
                all_lines.extend(lines)
            
            # Check if all primary fields have been discovered
            curr_text = "\n".join(all_lines)
            fields = extract_fields(curr_text)
            if fields.get("survey_number") and fields.get("owner_name") and fields.get("area_ha"):
                break

        doc.close()
        return "\n".join(all_lines)

    # For image files (JPG/PNG), fast grayscale OCR
    img_path = str(path)
    img = cv2.imread(img_path)
    if img is not None:
        h, w = img.shape[:2]
        if w > 800:
            img = cv2.resize(img, (800, int(h * 800 / w)))
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img_path

    lines = get_reader(lang).readtext(gray, detail=0, paragraph=True, canvas_size=800)
    return "\n".join(lines)


# ---------- Field extraction (pan-India multi-regional logic) ----------
def _clean(s):
    return re.sub(r"[^A-Za-z0-9/ .\u0900-\u097F]", "", s).strip(" ः.-") if s else None


DEVA_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def extract_fields(text: str) -> dict:
    t = text.translate(DEVA_DIGITS)
    fields = {}

    # 1. Land Type / Classification
    lt_m = re.search(
        r"(?:Agriculture\s*(?:Dry|Wet|Dry\/Wet|DrylWet)?\s*Land|Agricultural\s*(?:Dry|Wet)?\s*Land|कृषि\s*भूमि|निजी\s*भूमि|Residential\s*(?:Plot|Land|Layout)?|Commercial\s*Land|Freehold|Sale Deed|Non[\s-]Judicial\s*Stamp|Government\s*Land|Inam\s*Land|Khatauni)",
        t,
        re.I,
    )
    if lt_m:
        fields["land_type"] = lt_m.group(0).strip().replace("DrylWet", "Dry/Wet")
    elif "agricultural" in t.lower() or "agriculture" in t.lower() or "कृषि" in t:
        fields["land_type"] = "Agricultural Land (कृषि भूमि)"
    elif "residential" in t.lower() or "आवासीय" in t:
        fields["land_type"] = "Residential"
    elif "sale deed" in t.lower():
        fields["land_type"] = "Freehold (Sale Deed)"
    elif "stamp paper" in t.lower() or "non judicial" in t.lower():
        fields["land_type"] = "Registered Land (Stamp Paper)"
    else:
        fields["land_type"] = "Agricultural Land"

    # 2. Area / Extent
    # Total ha / Extent in hectares or Ac-Gts
    tot_m = re.search(r"Total\s*\n?(?:[0-9]+-[0-9]+\s*\n?)?([0-9]+\.[0-9]+)", t, re.I)
    ac_gts_m = re.search(r"(?:Ac\.?|Acres?)\s*([0-9]+)[\s\-]+([0-9]+)\s*(?:gt[s8]|guntas?)?", t, re.I)
    ha_m = re.search(r"(?:area|extent|total\s*area|रकबा|कुल\s*रकबा|क्षेत्रफल)\s*[:;ः\-]?\s*([0-9]+[.,]?[0-9]*)\s*(?:ha|hect|हे|हेक्टेयर)?", t, re.I)
    acres_only = re.search(r"([0-9]+[.,]?[0-9]*)\s*(?:acres?|acre|एकर|एकड़)", t, re.I)
    sq_yards_m = re.search(r"([0-9]+[.,]?[0-9]*)\s*(?:sq\.?\s*yards?|square\s*yards?|वर्ग\s*गज)", t, re.I)

    if tot_m and float(tot_m.group(1)) > 0:
        fields["area_ha"] = float(tot_m.group(1))
    elif ac_gts_m:
        ac = float(ac_gts_m.group(1))
        gts = float(ac_gts_m.group(2))
        fields["area_ha"] = round((ac + gts / 40.0) * 0.404686, 2)
    elif ha_m:
        try:
            fields["area_ha"] = float(ha_m.group(1).replace(",", "."))
        except Exception:
            fields["area_ha"] = None
    elif acres_only:
        try:
            fields["area_ha"] = round(float(acres_only.group(1).replace(",", ".")) * 0.404686, 2)
        except Exception:
            fields["area_ha"] = None
    elif sq_yards_m:
        try:
            fields["area_ha"] = round(float(sq_yards_m.group(1).replace(",", ".")) * 0.0000836127, 3)
        except Exception:
            fields["area_ha"] = None
    else:
        fields["area_ha"] = None

    # 3. Survey Number / Sy No / Khasra No / Gata No / Plot No
    # A. Inline patterns
    sn_matches = re.findall(
        r"(?:Sy[\s\-_.]*Nos?\.?|Survey\s*(?:No|Number)\.?|Khasra\s*(?:No)?\.?|खसरा\s*(?:नं)?\.?|गाटा\s*(?:नं)?\.?|सर्वे\s*(?:नं)?\.?)\s*[:;ः\-,\.]?\s*([0-9]+[\s/.-]*[0-9A-Za-z]*)",
        t,
        re.I,
    )
    valid_sns = []
    for s in sn_matches:
        cleaned = re.sub(r"[^0-9/A-Za-z]", "", s.replace("-", "/").replace(".", "/")).rstrip("/")
        if any(c.isdigit() for c in cleaned) and len(cleaned) >= 1 and cleaned not in ["199", "200", "201", "202", "2005", "2007", "2010", "2020", "2024", "2025", "2026"]:
            valid_sns.append(cleaned)

    # B. Tabular Schedule Survey Numbers
    if not valid_sns:
        tab_m = re.findall(r"\b([0-9]{1,4}\s*[/.]\s*[0-9]{1,4}[A-Za-z]?)\b", t)
        for cand in tab_m:
            c = re.sub(r"[^0-9/A-Za-z]", "", cand.replace(".", "/")).strip("/")
            if c not in ["199", "200", "201", "202", "2005", "2007", "2010", "2020", "2024", "2025", "2026", "2010/2011"] and any(x.isdigit() for x in c):
                valid_sns.append(c)

    fields["survey_number"] = valid_sns[0] if valid_sns else None

    # 4. Village
    vm_sit = re.search(r"situated\s+(?:at|in)\s*\n?\s*([A-Za-z\s]{3,30}?)(?:\s*\n?\s*(?:Village|VIllage|Villlace|Mandal|Tehsil|District|,|\n))", t, re.I)
    if vm_sit:
        v_clean = _clean(vm_sit.group(1).replace("\n", " ").strip())
        v_clean = re.sub(r"^(?:above|said|land|property|the|at|in|Rlo|R/o|Laaruun|Garcen|Garden)\s*", "", v_clean, flags=re.I).strip(" ,.-")
        if v_clean and len(v_clean) >= 3 and v_clean.lower() not in ["above", "land", "property", "contd", "village"]:
            fields["village"] = v_clean
        else:
            fields["village"] = None
    else:
        fields["village"] = None

    if not fields.get("village"):
        vm = re.search(r"([A-Za-z\u0900-\u097F\s]{3,30}?)\s+(?:Village|VIllage|Villlace|Villlage|Vlg|Vill|ग्?राम|गाँव|मौजा)", t, re.I)
        if vm:
            v = vm.group(1).replace("\n", " ").strip()
            v = re.sub(r".*?(?:above\s*said\s*land\s*situated\s*at|situated\s*at|situated\s*in|the|at|in|R/o|Rlo|Laaruun|Garcen|Garden)\s*", "", v, flags=re.I).strip(" ,.-")
            v_cand = _clean(v)
            if v_cand and len(v_cand) >= 3 and v_cand.lower() not in ["age", "wratt", "contd", "village", "sale", "deed", "this"]:
                fields["village"] = v_cand
            else:
                fields["village"] = None
        else:
            fields["village"] = None

    # 5. Tehsil / Mandal / Taluk
    mm = re.search(r"([A-Za-z\u0900-\u097F\s]{3,25}?)\s+(?:Mandal|1landal|Mandai|Tehsil|tehsil|Taluk|taluk|तहसील|तालुका|मंडल)", t, re.I)
    if mm:
        m_cand = _clean(mm.group(1).replace("\n", " ").strip())
        m_cand = re.sub(r".*?(?:Village|VIllage|Villlace|Villlage|Vlg|Vill)\s*", "", m_cand, flags=re.I).strip(" ,.-")
        if m_cand and len(m_cand) >= 3 and m_cand.lower() not in ["this", "sale", "deed", "mandal", "contd"]:
            fields["tehsil"] = m_cand
        else:
            fields["tehsil"] = None
    else:
        mm2 = re.search(r"(?:tehsil|mandal|taluk|तहसील|तालुका|मंडल)\s*[:;ः\-]?\s*([A-Za-z\u0900-\u097F]+)", t, re.I)
        fields["tehsil"] = _clean(mm2.group(1)) if mm2 else None

    # 6. Owner / Vendor / Purchaser / Pattadar / Khatedar
    owner_patterns = [
        r"(?:Shri|Smt|Sri|Mr|Mrs|Smt\.|Shri\.|Sri\.|Mr\.|Mrs\.)\s*[:;.,\-]?\s*([A-Za-z\u0900-\u097F\s.]{3,45}?)(?:\s+(?:W[/l1|o]?o|S[/l1|o]?o|Snri|D[/l1|o]?o|C[/l1|o]?o|aged|resident|having|R[/l1|o]?o|\n|\r|,))",
        r"(?:owner\s*name|name\s*of\s*owner|applicant\s*name|applicant|pattedar|pattadar|khatedar|खातेदार|आवेदक|पट्टेदार|काश्तकार|(?:भूमि)?स्?वामी(?:\s*का)?(?:\s*नाम)?)\s*[:;ः\-,\.]?\s*([A-Za-z\u0900-\u097F. ]+)",
        r"(?:M/s|M/s\.)\s*([A-Za-z\u0900-\u097F. ]+?(?:Pvt|Ltd|Limited|Private|LLP|Corp|Corporation|Enterprises|Builders|Avenues))",
        r"(?:प्रति|पति|प्रत्ति|सेवा\s*में|सेवा\s*मे|मेसर्स|M/s|श्री|श्रीमती)\s*[:;ः\-,\.]?\s*\n?\s*([A-Za-z\u0900-\u097F. ]+)",
    ]
    owner_name = None
    stop_words = ["as", "is", "to", "by", "the", "this", "sale", "deed", "whereas", "herein", "having", "which", "and", "sro", "day of", "november", "peaceful", "possessor", "possession", "admeasuring", "situated", "registered", "विषय", "संदर्भ"]
    for pat in owner_patterns:
        m = re.search(pat, t, re.I)
        if m:
            cand = _clean(m.group(1))
            cand = re.sub(r"\s+(?:निवासी|ड्रीम|अपार्टमेंट|थाटीपुर|ग्वालियर|W[/l1|o]?o|S[/l1|o]?o|Snri|D[/l1|o]?o|C[/l1|o]?o|aged|resident|having|R[/l1|o]?o).*", "", cand, flags=re.I).strip(" ,.")
            if cand and len(cand) >= 3 and cand.lower() not in stop_words and not any(sw == cand.lower() for sw in stop_words):
                owner_name = cand
                break
    fields["owner_name"] = owner_name

    return fields



# ---------- Validation ----------
def validate_record(fields: dict, existing: list) -> tuple:
    flags = []
    status = "verified"
    sn = fields.get("survey_number")
    owner = (fields.get("owner_name") or "").lower()

    if not sn or not owner:
        flags.append("Could not extract owner name or khasra number from OCR text")
        return "pending", flags, None

    for r in existing:
        if r.get("survey_number") == sn and r.get("status") != "rejected":
            other = (r.get("owner_name") or "").lower()
            ratio = max(fuzz.ratio(owner, other), fuzz.token_sort_ratio(owner, other))
            if ratio >= 80:
                status = "flagged: duplicate"
                flags.append(
                    f"Possible duplicate: owner '{fields.get('owner_name')}' is {ratio:.0f}% similar to "
                    f"'{r.get('owner_name')}' on the same khasra {sn} (existing record {r['id'][:8]})"
                )
                break

    parcel = PARCEL_INDEX.get(sn)
    if not parcel and sn:
        clean_sn = sn.replace("-", "/").replace(".", "/").strip()
        if clean_sn in PARCEL_INDEX:
            sn = clean_sn
            fields["survey_number"] = sn
            parcel = PARCEL_INDEX.get(sn)
        else:
            for p_sn in PARCEL_INDEX.keys():
                if p_sn.replace("/", "") == sn.replace("/", ""):
                    sn = p_sn
                    fields["survey_number"] = sn
                    parcel = PARCEL_INDEX.get(sn)
                    break

    parcel_area = None
    if not parcel:
        if status == "verified":
            status = "flagged: no GIS match"
        flags.append(f"Khasra {sn} has no matching parcel polygon in the GIS layer")
    else:
        parcel_area = parcel["properties"]["computed_area_ha"]
        area = fields.get("area_ha")
        if area and parcel_area:
            diff_pct = abs(area - parcel_area) / parcel_area * 100
            if diff_pct > 15:
                if status == "verified":
                    status = "flagged: area mismatch"
                flags.append(
                    f"Recorded area {area:.2f} ha differs from GIS polygon area {parcel_area:.2f} ha "
                    f"by {diff_pct:.0f}% (tolerance 15%)"
                )
    return status, flags, parcel_area


async def create_record(fields: dict, ocr_text: str, source_image: Optional[str]) -> dict:
    existing = await db.records.find({}, {"_id": 0}).to_list(1000)
    status, flags, parcel_area = validate_record(fields, existing)
    record = {
        "id": str(uuid.uuid4()),
        "owner_name": fields.get("owner_name"),
        "survey_number": fields.get("survey_number"),
        "village": fields.get("village"),
        "tehsil": fields.get("tehsil"),
        "area_ha": fields.get("area_ha"),
        "land_type": fields.get("land_type"),
        "source_image": source_image,
        "ocr_text": ocr_text,
        "status": status,
        "flags": flags,
        "parcel_area_ha": parcel_area,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.records.insert_one({**record})
    return record


# ---------- Routes ----------
@api_router.get("/")
async def root():
    return {"message": "Adhikar API running"}


@api_router.post("/upload")
async def upload_document(file: UploadFile = File(...), lang: str = Form("en")):
    ext = Path(file.filename or "doc.png").suffix.lower()
    if ext not in MIME_TYPES:
        raise HTTPException(400, "Only JPG, PNG or PDF files are supported")
    data = await file.read()
    fname = f"{uuid.uuid4().hex[:12]}{ext}"
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = TMP_DIR / fname
    tmp_path.write_bytes(data)

    storage_path = f"{APP_NAME}/uploads/{fname}"
    try:
        await asyncio.to_thread(put_object, storage_path, data, MIME_TYPES[ext])
    except Exception:
        logger.warning("Cloud object storage unavailable; using local storage fallback")

    try:
        ocr_text = await asyncio.to_thread(run_ocr, tmp_path, lang if lang == "hi" else "en")
    except Exception as e:
        logger.exception("OCR failed")
        raise HTTPException(500, f"OCR failed: {e}")
    fields = extract_fields(ocr_text)
    return await create_record(fields, ocr_text, storage_path)


@api_router.get("/samples")
async def list_samples():
    return [{"name": n, "url": f"/api/files/{APP_NAME}/samples/{n}"} for n in SAMPLE_NAMES]


@api_router.post("/samples/{name}/process")
async def process_sample(name: str):
    if name not in SAMPLE_NAMES:
        raise HTTPException(404, "Sample not found")
    local = TMP_DIR / name
    if not local.exists():
        generate_all(TMP_DIR)
    lang = "hi" if "hindi" in name else "en"
    ocr_text = await asyncio.to_thread(run_ocr, local, lang)
    fields = extract_fields(ocr_text)
    return await create_record(fields, ocr_text, f"{APP_NAME}/samples/{name}")


class RecordUpdate(BaseModel):
    owner_name: Optional[str] = None
    survey_number: Optional[str] = None
    village: Optional[str] = None
    tehsil: Optional[str] = None
    area_ha: Optional[float] = None
    land_type: Optional[str] = None


@api_router.patch("/records/{record_id}")
async def update_record(record_id: str, update_data: RecordUpdate):
    rec = await db.records.find_one({"id": record_id}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "Record not found")

    updated_fields = {
        "owner_name": update_data.owner_name if update_data.owner_name is not None else rec.get("owner_name"),
        "survey_number": update_data.survey_number if update_data.survey_number is not None else rec.get("survey_number"),
        "village": update_data.village if update_data.village is not None else rec.get("village"),
        "tehsil": update_data.tehsil if update_data.tehsil is not None else rec.get("tehsil"),
        "area_ha": update_data.area_ha if update_data.area_ha is not None else rec.get("area_ha"),
        "land_type": update_data.land_type if update_data.land_type is not None else rec.get("land_type"),
    }

    existing = await db.records.find({"id": {"$ne": record_id}}, {"_id": 0}).to_list(1000)
    status, flags, parcel_area = validate_record(updated_fields, existing)

    to_set = {
        **updated_fields,
        "status": status,
        "flags": flags,
        "parcel_area_ha": parcel_area,
    }

    await db.records.update_one({"id": record_id}, {"$set": to_set})
    return await db.records.find_one({"id": record_id}, {"_id": 0})


@api_router.get("/files/{path:path}")
async def serve_file(path: str):
    try:
        data, content_type = await asyncio.to_thread(get_object, path)
        return Response(content=data, media_type=content_type)
    except Exception:
        pass

    fname = Path(path).name
    local_file = TMP_DIR / fname
    if local_file.exists():
        ext = local_file.suffix.lower()
        content_type = MIME_TYPES.get(ext, "application/octet-stream")
        return Response(content=local_file.read_bytes(), media_type=content_type)

    raise HTTPException(404, "File not found")


@api_router.get("/export/csv")
async def export_csv():
    records = await db.records.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    buf = io.StringIO()
    cols = ["id", "owner_name", "survey_number", "village", "tehsil", "area_ha",
            "land_type", "parcel_area_ha", "status", "flags", "created_at"]
    writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    for r in records:
        r["flags"] = "; ".join(r.get("flags") or [])
        writer.writerow(r)
    return Response(
        content="\ufeff" + buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=adhikar_records.csv"},
    )


@api_router.get("/records")
async def get_records(status: Optional[str] = None):
    query = {"status": status} if status else {}
    return await db.records.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)


@api_router.get("/records/{record_id}")
async def get_record(record_id: str):
    rec = await db.records.find_one({"id": record_id}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "Record not found")
    return rec


class Decision(BaseModel):
    action: str  # approve | reject


@api_router.post("/records/{record_id}/decision")
async def decide(record_id: str, decision: Decision):
    if decision.action not in ["approve", "reject"]:
        raise HTTPException(400, "action must be approve or reject")
    new_status = "approved" if decision.action == "approve" else "rejected"
    res = await db.records.update_one({"id": record_id}, {"$set": {"status": new_status}})
    if res.matched_count == 0:
        raise HTTPException(404, "Record not found")
    return await db.records.find_one({"id": record_id}, {"_id": 0})


@api_router.get("/parcels")
async def get_parcels():
    return PARCELS_GEOJSON


async def _seed_records():
    for r in SEED_RECORDS:
        fields = {k: r.get(k) for k in ["owner_name", "survey_number", "village", "tehsil", "area_ha", "land_type"]}
        await create_record(fields, r["ocr_text"], None)


@api_router.post("/seed")
async def seed():
    await db.records.delete_many({})
    await _seed_records()
    return {"seeded": await db.records.count_documents({})}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


def _prepare_samples():
    paths = generate_all(TMP_DIR)
    try:
        if init_storage():
            for p in paths:
                put_object(f"{APP_NAME}/samples/{p.name}", p.read_bytes(), "image/png")
            logger.info("Samples uploaded to cloud storage")
        else:
            logger.info("Cloud storage not configured; samples ready locally")
    except Exception as e:
        logger.warning(f"Could not upload samples to cloud storage ({e}); using local files")


@app.on_event("startup")
async def startup():
    try:
        await asyncio.to_thread(_prepare_samples)
        await asyncio.to_thread(get_reader, "en")
    except Exception:
        logger.exception("Sample preparation / OCR model warmup failed")
    if await db.records.count_documents({}) == 0:
        await _seed_records()
        logger.info("Seeded demo records")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
