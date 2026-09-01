# 🏛️ Adhikar — Land Record Digitization & Cadastral GIS Validation

**Adhikar** is an AI-powered land governance and record verification platform designed to digitize scanned land records (Khatauni, Registry deeds, Stamp Papers, and Sale Deeds), extract key cadastral entities using OCR and regex heuristics, and validate them against spatial GIS cadastral parcel maps in real-time.

---

## 🌟 Key Features

* **⚡ Ultra-Fast Multi-Page OCR Pipeline**:
  * **Digital PDFs**: Instant direct stream extraction ($< 0.05\text{s}$).
  * **Scanned Deeds & Stamp Papers**: Smart page prioritization (Preamble / Parties + Schedule of Property pages) with early termination — processes 20+ page deeds in **$\approx 30$ seconds** (down from 15 minutes).
* **🇮🇳 Pan-India Document Support**:
  * Multilingual extraction (English & Hindi Devanagari).
  * Auto-normalizes units: **Acres & Guntas** (e.g., `Ac. 2-37 gts` $\rightarrow$ `1.18 ha`), **Square Yards**, **Bigha/Biswa**, and **Hectares**.
  * Parses complex multi-line party names (`Shri`, `Smt`, `Sri`, `M/s`), Villages (`Kongara Kalan`, `Devara Yamzal`), Mandals/Tehsils (`Ibrahimpatan`, `Shameerpet`), and Survey numbers (`31/8`, `106/2`, etc.).
* **🗺️ Interactive Cadastral GIS Map**:
  * Built with Leaflet & GeoJSON overlays.
  * Visual status coding: **Verified** (Emerald), **Duplicate Flag** (Amber), **Area Mismatch / No GIS Match** (Red).
* **🔍 Automated Land Integrity & Fraud Detection**:
  * **Duplicate Ownership Flag**: Detects conflicting claims on the same Khasra/Survey number.
  * **Area Mismatch Flag**: Identifies discrepancy between deed recorded area and GIS polygon area ($> 5\%$).
  * **Cadastral Existence Flag**: Flags unmapped or non-existent survey numbers.
* **✏️ Real-Time Inline Field Editor & GIS Re-Validation**:
  * Allows operators to refine noisy OCR characters or survey numbers directly in the UI and click **Save & Re-validate GIS** to update validation states instantly.

---

## 🛠️ Tech Stack

* **Backend**:
  * [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+) & [Uvicorn](https://www.uvicorn.org/)
  * [PyMuPDF](https://pymupdf.readthedocs.io/) (`pymupdf`) for lightning-fast digital text extraction and rasterization
  * [EasyOCR](https://github.com/JaidedAI/EasyOCR) & [OpenCV](https://opencv.org/) for deep learning text recognition
  * [MongoDB](https://www.mongodb.com/) with [Motor](https://motor.readthedocs.io/) (Async driver)
* **Frontend**:
  * [React 19](https://react.dev/) & [Craco](https://craco.js.org/)
  * [Tailwind CSS](https://tailwindcss.com/) & [Radix UI](https://www.radix-ui.com/)
  * [Leaflet](https://leafletjs.com/) for GIS map rendering
  * [Lucide React](https://lucide.dev/) for iconography & [Sonner](https://sonner.emilkowal.ski/) for toast notifications

---

## 🚀 Getting Started

### Prerequisites
* **Python 3.10+**
* **Node.js 18+** & **npm**
* **MongoDB** (running locally on port `27017` or via MongoDB Atlas)

---

### 1. Clone the Repository
```bash
git clone https://github.com/Hasini2706/Adhikar.git
cd Adhikar
```

---

### 2. Backend Setup & Run

1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```
3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Verify `backend/.env`:
   ```env
   MONGO_URL=mongodb://localhost:27017
   DB_NAME=adhikar_db
   CORS_ORIGINS=http://localhost:3000
   ```
5. Start the backend development server:
   ```bash
   python -m uvicorn server:app --host 127.0.0.1 --port 8001 --reload
   ```
   * Backend running at: `http://localhost:8001`
   * Interactive API Docs (Swagger UI): `http://localhost:8001/docs`

---

### 3. Frontend Setup & Run

1. In a new terminal, navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Verify `frontend/.env`:
   ```env
   REACT_APP_BACKEND_URL=http://localhost:8001
   PORT=3000
   ```
4. Start the React development server:
   ```bash
   npm start
   ```
   * App opens at: `http://localhost:3000`

---

## 📡 API Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/upload` | Upload document (PDF/PNG/JPG), run OCR, extract fields, and validate with GIS |
| `GET` | `/api/records` | List all digitized land records and their validation statuses |
| `GET` | `/api/records/{id}` | Retrieve details, raw OCR text, flags, and matched parcel for a specific record |
| `PATCH` | `/api/records/{id}` | Update extracted fields and immediately re-calculate GIS validation flags |
| `POST` | `/api/records/{id}/decision` | Approve or Reject a digitized record |
| `GET` | `/api/parcels` | Retrieve GeoJSON cadastral parcel boundaries |
| `GET` | `/api/samples` | Get pre-packaged demo sample documents |
| `POST` | `/api/seed` | Reset database and seed default cadastral demo records |

---

## 📂 Project Structure

```
Adhikar/
├── backend/
│   ├── server.py             # FastAPI backend, OCR engine, validation logic & API routes
│   ├── seed_data.py          # GeoJSON cadastral layers & demo seed records
│   ├── generate_samples.py   # Synthesizer for demo certificate images
│   ├── download_models.py    # EasyOCR model pre-downloader
│   ├── requirements.txt      # Python dependencies
│   └── .env                  # Backend environment configuration
├── frontend/
│   ├── src/
│   │   ├── components/       # ParcelMap (Leaflet), StatusBadge, UI widgets
│   │   ├── pages/            # Dashboard, UploadPage, RecordDetailPage, CadastralMapPage
│   │   ├── lib/api.js        # Axios API client functions
│   │   └── App.js            # App routes and layout
│   ├── package.json          # Node dependencies and scripts
│   └── .env                  # Frontend environment configuration
├── .gitignore
└── README.md
```

---

## 📄 License
This project is open source and available under the [MIT License](LICENSE).
