import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchParcels, fetchRecords } from "@/lib/api";
import { ParcelMap } from "@/components/ParcelMap";
import { StatusBadge } from "@/components/StatusBadge";

const LEGEND = [
  ["#059669", "Verified / Approved"],
  ["#d97706", "Flagged: duplicate"],
  ["#dc2626", "Flagged: mismatch"],
  ["#9ca3af", "No linked record"],
];

export default function MapPage() {
  const [parcels, setParcels] = useState(null);
  const [records, setRecords] = useState([]);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    fetchParcels().then(setParcels);
    fetchRecords().then(setRecords);
  }, []);

  const linked = selected
    ? records.filter((r) => r.survey_number === selected.properties.survey_number)
    : [];

  return (
    <div data-testid="map-page">
      <div className="mb-4">
        <h2 className="font-heading text-2xl font-bold tracking-tight">Parcel Map (Sample GIS Layer)</h2>
        <p className="text-sm text-zinc-500">8 sample parcel boundaries for Rampur Kalan. Click a polygon to see the linked digitized record.</p>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-8">
          {parcels && <ParcelMap parcels={parcels} records={records} onSelect={setSelected} height="560px" highlightSurvey={selected?.properties.survey_number} />}
          <div className="flex flex-wrap gap-4 mt-3">
            {LEGEND.map(([c, label]) => (
              <span key={label} className="flex items-center gap-1.5 text-xs text-zinc-600">
                <span className="w-3 h-3 rounded-sm inline-block" style={{ background: c }} /> {label}
              </span>
            ))}
          </div>
        </div>
        <div className="lg:col-span-4">
          <div className="border border-zinc-200 rounded-md bg-white p-4 min-h-[300px]" data-testid="parcel-detail-panel">
            {!selected ? (
              <p className="text-sm text-zinc-400 mt-8 text-center">Click a parcel polygon to view its linked record</p>
            ) : (
              <>
                <h3 className="font-heading font-semibold text-lg mb-1">Khasra {selected.properties.survey_number}</h3>
                <p className="text-sm text-zinc-500 mb-3">
                  {selected.properties.village}, {selected.properties.tehsil} · GIS area {selected.properties.computed_area_ha} ha
                </p>
                {linked.length === 0 ? (
                  <p className="text-sm text-zinc-400">No digitized record linked to this parcel yet.</p>
                ) : (
                  <div className="space-y-3">
                    {linked.map((r) => (
                      <Link
                        key={r.id}
                        to={`/records/${r.id}`}
                        data-testid={`linked-record-${r.id}`}
                        className="block border border-zinc-200 rounded-md p-3 hover:border-zinc-900 transition-colors"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-sm">{r.owner_name}</span>
                          <StatusBadge status={r.status} />
                        </div>
                        <p className="text-xs text-zinc-500">Recorded area: {r.area_ha ?? "—"} ha · {r.land_type || "—"}</p>
                      </Link>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
