# Adhikar — AI-powered Land Record Digitization & Validation (SIH Prototype)

## Original Problem Statement
Build a ~50% functional hackathon prototype that digitizes scanned Indian land records (khasra/khatauni), extracts structured fields, links them to a parcel map, runs validation checks, and gives a revenue officer a review dashboard. Demo over polish.

## User Choices
- Build end-to-end in one go (no stage-by-stage confirmation)
- OCR: EasyOCR (English, CPU)
- Frontend: React (minimal, no-frills) + Leaflet
- DB: MongoDB (instead of SQLite)
- Seed data flavor: Madhya Pradesh (Village Rampur Kalan, Tehsil Huzur, Bhopal)

## Architecture
- FastAPI backend (port 8001, /api prefix) + MongoDB (records collection, uuid ids)
- EasyOCR (lazy-loaded reader, runs in thread) with PDF support via PyMuPDF (first page)
- Regex-based field extraction: owner_name, survey_number, village, tehsil, area_ha, land_type
- Validation (server.py validate_record): rapidfuzz duplicate (same khasra + owner similarity ≥80), area mismatch vs GeoJSON polygon computed area (15% tolerance), missing GIS link
- Sample GIS layer: 8 fabricated parcels in seed_data.py (PARCELS_GEOJSON, shoelace area in ha)
- Uploads + generated sample documents stored in Emergent Object Storage (storage.py), served via GET /api/files/{path}
- 4 demo sample documents generated with PIL at startup (generate_samples.py)
- React frontend: DashboardPage (filter/sort table), UploadPage (file upload + sample docs → OCR result), MapPage (Leaflet parcels, click → linked record), RecordDetailPage (side-by-side OCR/fields/parcel map, Approve/Reject)

## Key Endpoints
- POST /api/upload, GET /api/samples, POST /api/samples/{name}/process
- GET /api/records[?status], GET /api/records/{id}, POST /api/records/{id}/decision {action: approve|reject}
- GET /api/parcels, POST /api/seed (reset demo data), GET /api/files/{path}

## Implemented (June 2026)
- Full 5-stage pipeline working end-to-end; tested by testing agent (iteration_1: 17/18 backend, 100% frontend; the 1 failure — sample_4 OCR misread — fixed by regenerating sample with khasra 103/2 and re-verified)
- Auto-seed 10 MP records on startup: 2 near-duplicates (101/1), 1 area mismatch (103/2), 1 no-GIS (999/9), 6 verified
- CSV export: GET /api/export/csv (UTF-8 BOM, flags joined), "Export CSV" button on dashboard
- Hindi/Devanagari OCR: sample_5_hindi_khatauni.png (PIL + FreeSans with raqm shaping), easyocr Reader(['hi','en']) cached per-lang, Hindi upload toggle (Form lang=hi), bilingual extraction regex (स्वामी/खसरा/ग्राम/तहसील/क्षेत्रफल/प्रकार labels, Devanagari digit transliteration, ः-as-colon and lost-conjunct tolerance) — verified: extracts रामलाल पाटीदार / 104/1 / 2.95 ha → "verified"
- Ops note: EasyOCR hi model download once hit disk-full which crashed mongodb (restarted via supervisorctl); models cached at ~/.EasyOCR/model

## Explicitly Skipped (future work, per user)
- Auth / role-based access, real satellite boundary extraction, production security/scaling

## Backlog
- P1: Fuzzy khasra matching against parcel index to tolerate OCR noise
- P2: Aggregate multiple flags per record (currently first duplicate flag short-circuits)
- P2: Audit trail of officer decisions
