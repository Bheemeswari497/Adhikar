"""Adhikar backend API tests"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://adhikar-demo.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def seeded():
    r = requests.post(f"{API}/seed", timeout=60)
    assert r.status_code == 200
    assert r.json()["seeded"] >= 10
    return True


# ---------- Basic health ----------
def test_root():
    r = requests.get(f"{API}/", timeout=15)
    assert r.status_code == 200
    assert "Adhikar" in r.json().get("message", "")


# ---------- Records ----------
def test_records_seeded(seeded):
    r = requests.get(f"{API}/records", timeout=20)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 10
    # no mongo _id
    assert all("_id" not in rec for rec in data)

    by_owner = {rec["owner_name"]: rec for rec in data}
    assert by_owner["Ram Prasad Sharma"]["status"] == "verified"
    assert by_owner["Ramprasad Sharma"]["status"] == "flagged: duplicate"
    assert by_owner["Mohan Lal Verma"]["status"] == "flagged: area mismatch"
    assert by_owner["Devendra Singh Thakur"]["status"] == "flagged: no GIS match"


def test_records_filter_by_status(seeded):
    r = requests.get(f"{API}/records", params={"status": "verified"}, timeout=20)
    assert r.status_code == 200
    for rec in r.json():
        assert rec["status"] == "verified"


def test_get_single_record(seeded):
    recs = requests.get(f"{API}/records", timeout=20).json()
    rid = recs[0]["id"]
    r = requests.get(f"{API}/records/{rid}", timeout=15)
    assert r.status_code == 200
    assert r.json()["id"] == rid


def test_get_record_404():
    r = requests.get(f"{API}/records/nonexistent-id", timeout=15)
    assert r.status_code == 404


# ---------- Parcels ----------
def test_parcels():
    r = requests.get(f"{API}/parcels", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 8
    for f in data["features"]:
        assert "survey_number" in f["properties"]
        assert "computed_area_ha" in f["properties"]
        assert f["geometry"]["type"] == "Polygon"


# ---------- Samples ----------
def test_list_samples():
    r = requests.get(f"{API}/samples", timeout=15)
    assert r.status_code == 200
    samples = r.json()
    assert len(samples) >= 4
    names = [s["name"] for s in samples]
    assert "sample_1_clean_record.png" in names


def test_serve_sample_file():
    r = requests.get(f"{API}/files/adhikar/samples/sample_1_clean_record.png", timeout=30)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("image/")
    assert len(r.content) > 100


def test_serve_missing_file():
    r = requests.get(f"{API}/files/adhikar/samples/nope.png", timeout=15)
    assert r.status_code == 404


# ---------- Decision ----------
def test_decision_approve_and_reject(seeded):
    recs = requests.get(f"{API}/records", timeout=20).json()
    # find a verified record to approve
    verified = next(r for r in recs if r["status"] == "verified")
    r = requests.post(f"{API}/records/{verified['id']}/decision", json={"action": "approve"}, timeout=15)
    assert r.status_code == 200
    assert r.json()["status"] == "approved"

    # verify via GET
    got = requests.get(f"{API}/records/{verified['id']}", timeout=15).json()
    assert got["status"] == "approved"

    # reject another
    other = next(r for r in recs if r["status"].startswith("flagged"))
    r = requests.post(f"{API}/records/{other['id']}/decision", json={"action": "reject"}, timeout=15)
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


def test_decision_invalid_action(seeded):
    recs = requests.get(f"{API}/records", timeout=20).json()
    rid = recs[0]["id"]
    r = requests.post(f"{API}/records/{rid}/decision", json={"action": "bogus"}, timeout=15)
    assert r.status_code == 400


def test_decision_not_found():
    r = requests.post(f"{API}/records/does-not-exist/decision", json={"action": "approve"}, timeout=15)
    assert r.status_code == 404


# ---------- Sample processing (slow OCR) ----------
def test_process_sample_no_gis_match(seeded):
    r = requests.post(f"{API}/samples/sample_3_unknown_khasra.png/process", timeout=180)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert data["status"] == "flagged: no GIS match"


def test_process_sample_area_mismatch(seeded):
    r = requests.post(f"{API}/samples/sample_4_area_mismatch.png/process", timeout=180)
    assert r.status_code == 200
    data = r.json()
    # could be flagged: duplicate OR area mismatch depending on prior state; test seeded first
    assert data["status"] in ("flagged: area mismatch", "flagged: duplicate")


def test_process_sample_not_found():
    r = requests.post(f"{API}/samples/notasample.png/process", timeout=15)
    assert r.status_code == 404


# ---------- Upload ----------
def test_upload_flow(seeded):
    # download sample then upload
    img = requests.get(f"{API}/files/adhikar/samples/sample_1_clean_record.png", timeout=30).content
    files = {"file": ("sample_1_clean_record.png", img, "image/png")}
    r = requests.post(f"{API}/upload", files=files, timeout=180)
    assert r.status_code == 200
    data = r.json()
    assert "ocr_text" in data
    assert "status" in data
    assert "id" in data


def test_upload_invalid_ext():
    files = {"file": ("bad.txt", b"hello", "text/plain")}
    r = requests.post(f"{API}/upload", files=files, timeout=15)
    assert r.status_code == 400


# ---------- Final: reset seed for demo cleanliness ----------
def test_zz_final_seed_reset():
    r = requests.post(f"{API}/seed", timeout=60)
    assert r.status_code == 200
    assert r.json()["seeded"] == 10
