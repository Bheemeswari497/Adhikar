import os
import sys
import zipfile
from pathlib import Path
import urllib.request

MODEL_DIR = Path.home() / ".EasyOCR" / "model"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODELS = {
    "craft_mlt_25k.pth": "https://github.com/JaidedAI/EasyOCR/releases/download/pre-v1.1.6/craft_mlt_25k.zip",
    "english_g2.pth": "https://github.com/JaidedAI/EasyOCR/releases/download/v1.3/english_g2.zip",
    "devanagari.pth": "https://github.com/JaidedAI/EasyOCR/releases/download/pre-v1.1.6/devanagari.zip",
}

def download_and_extract(filename, url):
    target_pth = MODEL_DIR / filename
    if target_pth.exists() and target_pth.stat().st_size > 1000000:
        print(f"Already exists: {filename} ({target_pth.stat().st_size} bytes)")
        return

    zip_path = MODEL_DIR / f"{filename}.zip"
    print(f"Downloading {filename} from {url}...")
    
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    with urllib.request.urlopen(req) as resp, open(zip_path, "wb") as out:
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        while True:
            chunk = resp.read(1024 * 64)
            if not chunk:
                break
            out.write(chunk)
            downloaded += len(chunk)
            if total:
                percent = (downloaded / total) * 100
                sys.stdout.write(f"\r{filename}: {percent:.1f}% ({downloaded // 1024} KB / {total // 1024} KB)")
                sys.stdout.flush()
    print(f"\nExtracting {filename}...")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extract(filename, MODEL_DIR)
    
    if zip_path.exists():
        zip_path.unlink()
    print(f"Successfully installed {filename} ({target_pth.stat().st_size} bytes)!")

if __name__ == "__main__":
    for tmp in MODEL_DIR.glob("temp*"):
        try:
            tmp.unlink()
        except Exception:
            pass

    for fn, url in MODELS.items():
        download_and_extract(fn, url)

    print("\nValidating with EasyOCR...")
    import easyocr
    r_en = easyocr.Reader(['en'], gpu=False, verbose=False)
    print("EasyOCR English reader initialized successfully!")
    r_hi = easyocr.Reader(['hi', 'en'], gpu=False, verbose=False)
    print("EasyOCR Hindi reader initialized successfully!")
