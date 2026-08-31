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

TMP_DIR = Path("/tmp/adhikar_samples")

app = FastAPI(title="Adhikar API")
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("adhikar")

PARCEL_INDEX = {f["properties"]["survey_number"]: f for f in PARCELS_GEOJSON["features"]}

# ---------- OCR ----------
_readers = {}


def get_reader(lang: str = "en"):
    if lang not in _readers:
        import easyocr
        langs = ['hi', 'en'] if lang == "hi" else ['en']
        _readers[lang] = easyocr.Reader(langs, gpu=False, verbose=False)
    return _readers[lang]


def run_ocr(path: Path, lang: str = "en") -> str:
    if path.suffix.lower() == ".pdf":
        import fitz
        doc = fitz.open(str(path))
        pix = doc[0].get_pixmap(dpi=200)
        png_path = path.with_suffix(".page1.png")
        pix.save(str(png_path))
        doc.close()
        path = png_path
    lines = get_reader(lang).readtext(str(path), detail=0, paragraph=False)
    return "\n".join(lines)


# ---------- Field extraction (regex first pass) ----------
def _clean(s):
    return re.sub(r"[^A-Za-z0-9/ .\u0900-\u097F]", "", s).strip(" ः.") if s else None


DEVA_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def extract_fields(text: str) -> dict:
    t = text.translate(DEVA_DIGITS)
    fields = {}
    m = re.search(r"(?:owner\s*name|name\s*of\s*owner|owner|(?:भूमि)?स्?वामी(?:\s*का)?(?:\s*नाम)?)\s*[:;ः\-]?\s*(.+)", t, re.I)
    fields["owner_name"] = _clean(m.group(1)) if m else None
    m = re.search(r"(?:khasra|survey|खसरा)[^\d]{0,25}(\d+\s*/?\s*\d*)", t, re.I | re.S)
    fields["survey_number"] = m.group(1).replace(" ", "").rstrip("/") if m else None
    m = re.search(r"(?:village|ग्?राम)\s*[:;ः\-]?\s*([A-Za-z\u0900-\u097F ]+)", t, re.I)
    fields["village"] = _clean(m.group(1)) if m else None
    m = re.search(r"(?:tehsil|तहसील)\s*[:;ः\-]?\s*([A-Za-z\u0900-\u097F ]+)", t, re.I)
    fields["tehsil"] = _clean(m.group(1)) if m else None
    m = re.search(r"(?:area|क्?षेत्?रफल)\s*[:;ः\-]?\s*(\d+[.,]?\d*)\s*(?:ha|hect|हे)", t, re.I)
    if not m:
        m = re.search(r"(?:area|क्?षेत्?रफल)\s*[:;ः\-]?\s*(\d+[.,]?\d*)", t, re.I)
    fields["area_ha"] = float(m.group(1).replace(",", ".")) if m else None
    m = re.search(r"(?:land\s*type|(?:भूमि\s*(?:का)?\s*)?प्?रकार)\s*[:;ः\-]?\s*([A-Za-z\u0900-\u097F ]+)", t, re.I)
    fields["land_type"] = _clean(m.group(1)) if m else None
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
        logger.exception("Object storage upload failed")
        storage_path = None

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


@api_router.get("/files/{path:path}")
async def serve_file(path: str):
    try:
        data, content_type = await asyncio.to_thread(get_object, path)
    except Exception:
        raise HTTPException(404, "File not found")
    return Response(content=data, media_type=content_type)


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
    init_storage()
    for p in paths:
        put_object(f"{APP_NAME}/samples/{p.name}", p.read_bytes(), "image/png")


@app.on_event("startup")
async def startup():
    try:
        await asyncio.to_thread(_prepare_samples)
        logger.info("Samples ready in object storage")
    except Exception:
        logger.exception("Sample preparation failed")
    if await db.records.count_documents({}) == 0:
        await _seed_records()
        logger.info("Seeded demo records")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
