import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const statusColor = (status) => {
  if (!status) return "#9ca3af";
  if (status === "verified" || status === "approved") return "#059669";
  if (status === "flagged: duplicate") return "#d97706";
  if (status === "rejected") return "#52525b";
  return "#dc2626";
};

export const ParcelMap = ({ parcels, records = [], highlightSurvey, onSelect, height = "500px" }) => {
  const divRef = useRef(null);
  const mapRef = useRef(null);
  const layerRef = useRef(null);

  useEffect(() => {
    if (!divRef.current || mapRef.current) return;
    mapRef.current = L.map(divRef.current, { zoomControl: true });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap",
    }).addTo(mapRef.current);
    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !parcels) return;
    if (layerRef.current) layerRef.current.remove();

    const bySurvey = {};
    records.forEach((r) => {
      if (r.survey_number && !bySurvey[r.survey_number]) bySurvey[r.survey_number] = r;
    });

    layerRef.current = L.geoJSON(parcels, {
      style: (f) => {
        const sn = f.properties.survey_number;
        const rec = bySurvey[sn];
        const isHl = highlightSurvey && sn === highlightSurvey;
        return {
          color: isHl ? "#18181b" : statusColor(rec?.status),
          weight: isHl ? 3 : 2,
          fillColor: statusColor(rec?.status),
          fillOpacity: isHl ? 0.55 : 0.3,
        };
      },
      onEachFeature: (f, layer) => {
        const p = f.properties;
        const rec = bySurvey[p.survey_number];
        layer.bindTooltip(
          `Khasra ${p.survey_number} · ${p.computed_area_ha} ha${rec ? ` · ${rec.owner_name}` : " · no record"}`,
          { sticky: true }
        );
        layer.on("click", () => onSelect && onSelect(f));
      },
    }).addTo(map);
    map.fitBounds(layerRef.current.getBounds(), { padding: [24, 24] });
  }, [parcels, records, highlightSurvey, onSelect]);

  return (
    <div
      ref={divRef}
      data-testid="parcel-map"
      className="rounded-md border border-zinc-200 w-full"
      style={{ height }}
    />
  );
};
