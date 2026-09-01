import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HINDI_SAMPLE = "sample_5_hindi_khatauni.png"

def _load_font(bold: bool = False, deva: bool = False, size: int = 24):
    candidates = []
    if deva:
        if bold:
            candidates = [
                "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
                "C:/Windows/Fonts/NirmalaB.ttc", "NirmalaB.ttc", "NirmalaB.ttf",
                "C:/Windows/Fonts/Nirmala.ttc", "Nirmala.ttc", "Nirmala.ttf",
                "C:/Windows/Fonts/mangal.ttf", "mangal.ttf",
                "C:/Windows/Fonts/aparajb.ttf", "aparajb.ttf"
            ]
        else:
            candidates = [
                "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
                "C:/Windows/Fonts/Nirmala.ttc", "Nirmala.ttc", "Nirmala.ttf",
                "C:/Windows/Fonts/mangal.ttf", "mangal.ttf",
                "C:/Windows/Fonts/aparaj.ttf", "aparaj.ttf"
            ]
    else:
        if bold:
            candidates = [
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "C:/Windows/Fonts/arialbd.ttf", "arialbd.ttf",
                "C:/Windows/Fonts/calibrib.ttf", "calibrib.ttf",
                "C:/Windows/Fonts/segoeuib.ttf", "segoeuib.ttf"
            ]
        else:
            candidates = [
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "C:/Windows/Fonts/arial.ttf", "arial.ttf",
                "C:/Windows/Fonts/calibri.ttf", "calibri.ttf",
                "C:/Windows/Fonts/segoeui.ttf", "segoeui.ttf"
            ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            continue
    return ImageFont.load_default()

SAMPLES = [
    ("sample_1_clean_record.png", "Rajesh Kumar Yadav", "106/2", "2.00", "Agricultural"),
    ("sample_2_duplicate_owner.png", "Ram Prashad Sharma", "101/1", "2.00", "Agricultural"),
    ("sample_3_unknown_khasra.png", "Vinod Kumar Sen", "777/2", "1.50", "Agricultural"),
    ("sample_4_area_mismatch.png", "Meera Bai Ahirwar", "103/2", "4.50", "Residential"),
]


def _make(out_dir: Path, fname, owner, khasra, area, land_type):
    img = Image.new("RGB", (920, 700), "#f5f1e8")
    d = ImageDraw.Draw(img)
    h1 = _load_font(bold=True, size=30)
    h2 = _load_font(bold=True, size=24)
    body = _load_font(size=26)
    d.rectangle([20, 20, 900, 680], outline="#555", width=3)
    d.text((460, 50), "GOVERNMENT OF MADHYA PRADESH", font=h1, anchor="mm", fill="#222")
    d.text((460, 95), "REVENUE DEPARTMENT", font=h2, anchor="mm", fill="#222")
    d.text((460, 135), "RECORD OF RIGHTS (KHATAUNI)", font=h2, anchor="mm", fill="#222")
    d.line([60, 170, 860, 170], fill="#555", width=2)
    lines = [
        f"Owner Name: {owner}",
        f"Khasra No: {khasra}",
        "Village: Rampur Kalan",
        "Tehsil: Huzur",
        "District: Bhopal",
        f"Area: {area} Hectare",
        f"Land Type: {land_type}",
    ]
    y = 210
    for line in lines:
        d.text((80, y), line, font=body, fill="#1a1a1a")
        y += 52
    d.line([60, y + 10, 860, y + 10], fill="#555", width=2)
    d.text((80, y + 40), "Patwari Halka No: 42", font=body, fill="#1a1a1a")
    d.text((80, y + 90), "Entry verified by Revenue Inspector", font=body, fill="#1a1a1a")
    path = out_dir / fname
    img.save(path)
    return path


def _make_hindi(out_dir: Path):
    img = Image.new("RGB", (920, 700), "#f5efe0")
    d = ImageDraw.Draw(img)
    h1 = _load_font(bold=True, deva=True, size=32)
    h2 = _load_font(bold=True, deva=True, size=26)
    body = _load_font(deva=True, size=28)
    d.rectangle([20, 20, 900, 680], outline="#555", width=3)
    d.text((460, 55), "मध्य प्रदेश शासन", font=h1, anchor="mm", fill="#222")
    d.text((460, 100), "राजस्व विभाग", font=h2, anchor="mm", fill="#222")
    d.text((460, 140), "अधिकार अभिलेख (खतौनी)", font=h2, anchor="mm", fill="#222")
    d.line([60, 175, 860, 175], fill="#555", width=2)
    lines = [
        "स्वामी का नाम: रामलाल पाटीदार",
        "खसरा क्रमांक: 104/1",
        "ग्राम: रामपुर कलां",
        "तहसील: हुजूर",
        "जिला: भोपाल",
        "क्षेत्रफल: 2.95 हेक्टेयर",
        "भूमि प्रकार: कृषि",
    ]
    y = 215
    for line in lines:
        d.text((80, y), line, font=body, fill="#1a1a1a")
        y += 54
    d.line([60, y + 10, 860, y + 10], fill="#555", width=2)
    d.text((80, y + 40), "पटवारी हल्का: 42", font=body, fill="#1a1a1a")
    path = out_dir / HINDI_SAMPLE
    img.save(path)
    return path


SAMPLE_NAMES = [s[0] for s in SAMPLES] + [HINDI_SAMPLE]


def generate_all(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    return [_make(out_dir, *s) for s in SAMPLES] + [_make_hindi(out_dir)]


if __name__ == "__main__":
    for p in generate_all(Path("/tmp/adhikar_samples")):
        print("wrote", p)
