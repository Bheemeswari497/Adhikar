from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

SAMPLES = [
    ("sample_1_clean_record.png", "Rajesh Kumar Yadav", "106/2", "2.00", "Agricultural"),
    ("sample_2_duplicate_owner.png", "Ram Prashad Sharma", "101/1", "2.00", "Agricultural"),
    ("sample_3_unknown_khasra.png", "Vinod Kumar Sen", "777/2", "1.50", "Agricultural"),
    ("sample_4_area_mismatch.png", "Meera Bai Ahirwar", "103/2", "4.50", "Residential"),
]


def _make(out_dir: Path, fname, owner, khasra, area, land_type):
    img = Image.new("RGB", (920, 700), "#f5f1e8")
    d = ImageDraw.Draw(img)
    h1 = ImageFont.truetype(FONT_BOLD, 30)
    h2 = ImageFont.truetype(FONT_BOLD, 24)
    body = ImageFont.truetype(FONT, 26)
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


def generate_all(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    return [_make(out_dir, *s) for s in SAMPLES]


if __name__ == "__main__":
    for p in generate_all(Path("/tmp/adhikar_samples")):
        print("wrote", p)
