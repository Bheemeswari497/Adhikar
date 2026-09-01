import math

VILLAGE = "Rampur Kalan"
TEHSIL = "Huzur"
DISTRICT = "Bhopal"
BASE_LAT, BASE_LON = 23.3021, 77.5522


def _quad(lat, lon, w_m, h_m, jitter=0.15):
    dlat = h_m / 110540.0
    dlon = w_m / (111320.0 * math.cos(math.radians(lat)))
    jx, jy = dlon * jitter, dlat * jitter
    return [[
        [lon, lat],
        [lon + dlon, lat + jy * 0.3],
        [lon + dlon + jx * 0.2, lat + dlat],
        [lon - jx * 0.1, lat + dlat - jy * 0.2],
        [lon, lat],
    ]]


def polygon_area_ha(coords):
    ring = coords[0]
    lat0 = ring[0][1]
    kx = 111320.0 * math.cos(math.radians(lat0))
    ky = 110540.0
    pts = [(p[0] * kx, p[1] * ky) for p in ring]
    s = 0.0
    for i in range(len(pts) - 1):
        s += pts[i][0] * pts[i + 1][1] - pts[i + 1][0] * pts[i][1]
    return abs(s) / 2.0 / 10000.0


_PARCEL_DEFS = [
    ("101/1", 0, 0, 200, 100),
    ("102/3", 220, 0, 150, 80),
    ("103/2", 390, 0, 120, 100),
    ("104/1", 0, 130, 250, 120),
    ("105", 270, 130, 100, 90),
    ("106/2", 390, 130, 180, 110),
    ("107/1", 0, 270, 140, 140),
    ("108/4", 160, 270, 160, 100),
    ("16/2", 330, 270, 130, 125),
    ("16", 330, 270, 130, 125),
    ("502/1", 470, 270, 130, 124),
]


def _build_parcels():
    features = []
    for sn, dx, dy, w, h in _PARCEL_DEFS:
        lat = BASE_LAT + dy / 110540.0
        lon = BASE_LON + dx / (111320.0 * math.cos(math.radians(BASE_LAT)))
        coords = _quad(lat, lon, w, h)
        features.append({
            "type": "Feature",
            "properties": {
                "survey_number": sn,
                "village": VILLAGE,
                "tehsil": TEHSIL,
                "district": DISTRICT,
                "computed_area_ha": round(polygon_area_ha(coords), 2),
            },
            "geometry": {"type": "Polygon", "coordinates": coords},
        })
    return {"type": "FeatureCollection", "features": features}


PARCELS_GEOJSON = _build_parcels()


def make_ocr_text(owner, sn, area, land_type):
    return (
        "GOVERNMENT OF MADHYA PRADESH\n"
        "REVENUE DEPARTMENT\n"
        "RECORD OF RIGHTS (KHATAUNI)\n"
        "-----------------------------------\n"
        f"Owner Name: {owner}\n"
        f"Khasra No: {sn}\n"
        f"Village: {VILLAGE}\n"
        f"Tehsil: {TEHSIL}\n"
        f"District: {DISTRICT}\n"
        f"Area: {area:.2f} Hectare\n"
        f"Land Type: {land_type}\n"
        "-----------------------------------\n"
        "Patwari Halka No: 42\n"
        "Entry verified by Revenue Inspector"
    )


SEED_RECORDS = [
    {"owner_name": "Ram Prasad Sharma", "survey_number": "101/1", "area_ha": 2.02, "land_type": "Agricultural"},
    {"owner_name": "Ramprasad Sharma", "survey_number": "101/1", "area_ha": 2.00, "land_type": "Agricultural"},
    {"owner_name": "Sunita Devi", "survey_number": "102/3", "area_ha": 1.18, "land_type": "Agricultural"},
    {"owner_name": "Mohan Lal Verma", "survey_number": "103/2", "area_ha": 5.00, "land_type": "Agricultural"},
    {"owner_name": "Abdul Rashid Khan", "survey_number": "104/1", "area_ha": 2.95, "land_type": "Agricultural"},
    {"owner_name": "Kamla Bai", "survey_number": "105", "area_ha": 0.88, "land_type": "Residential"},
    {"owner_name": "Devendra Singh Thakur", "survey_number": "999/9", "area_ha": 1.50, "land_type": "Agricultural"},
    {"owner_name": "Geeta Kushwaha", "survey_number": "106/2", "area_ha": 2.00, "land_type": "Agricultural"},
    {"owner_name": "Prakash Patel", "survey_number": "107/1", "area_ha": 1.90, "land_type": "Orchard"},
    {"owner_name": "Shyam Sunder Mishra", "survey_number": "108/4", "area_ha": 1.55, "land_type": "Agricultural"},
]

for r in SEED_RECORDS:
    r["village"] = VILLAGE
    r["tehsil"] = TEHSIL
    r["ocr_text"] = make_ocr_text(r["owner_name"], r["survey_number"], r["area_ha"], r["land_type"])
