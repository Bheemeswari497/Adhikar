import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Check, X, AlertTriangle } from "lucide-react";
import { fetchRecord, fetchParcels, decideRecord, BACKEND_URL } from "@/lib/api";
import { ParcelMap } from "@/components/ParcelMap";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";

const FieldRow = ({ label, value }) => (
  <div className="flex justify-between border-b border-zinc-100 py-1.5 text-sm">
    <span className="text-zinc-500">{label}</span>
    <span className="font-medium text-right">{value ?? "—"}</span>
  </div>
);

export default function RecordDetailPage() {
  const { id } = useParams();
  const [record, setRecord] = useState(null);
  const [parcels, setParcels] = useState(null);

  useEffect(() => {
    fetchRecord(id).then(setRecord).catch(() => toast.error("Record not found"));
    fetchParcels().then(setParcels);
  }, [id]);

  if (!record) return <p className="text-zinc-400 text-sm">Loading…</p>;

  const parcel = parcels?.features.find((f) => f.properties.survey_number === record.survey_number);
  const parcelOnly = parcel ? { type: "FeatureCollection", features: [parcel] } : null;

  const decide = async (action) => {
    const updated = await decideRecord(id, action);
    setRecord(updated);
    toast.success(`Record ${action}d`);
  };

  return (
    <div data-testid="record-detail-page">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-3">
          <Link to="/" className="text-zinc-500 hover:text-zinc-900 transition-colors" data-testid="back-to-dashboard">
            <ArrowLeft size={20} />
          </Link>
          <div>
            <h2 className="font-heading text-2xl font-bold tracking-tight">
              {record.owner_name || "Unknown owner"} · Khasra {record.survey_number || "?"}
            </h2>
            <div className="flex items-center gap-2 mt-1">
              <StatusBadge status={record.status} />
              <span className="text-xs text-zinc-400">Record {record.id.slice(0, 8)}</span>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => decide("approve")} data-testid="approve-button" className="bg-emerald-700 hover:bg-emerald-800">
            <Check size={16} className="mr-1" /> Approve
          </Button>
          <Button onClick={() => decide("reject")} variant="destructive" data-testid="reject-button">
            <X size={16} className="mr-1" /> Reject
          </Button>
        </div>
      </div>

      {record.flags?.length > 0 && (
        <div className="border border-amber-300 bg-amber-50 rounded-md p-4 mb-4" data-testid="flag-reasons">
          <p className="text-xs uppercase tracking-[0.1em] text-amber-700 mb-2 flex items-center gap-1">
            <AlertTriangle size={14} /> Why this record was flagged
          </p>
          <ul className="text-sm text-amber-900 list-disc pl-4 space-y-1">
            {record.flags.map((f, i) => <li key={i}>{f}</li>)}
          </ul>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-4 border border-zinc-200 rounded-md bg-white flex flex-col">
          <div className="px-4 py-2 border-b border-zinc-200 text-xs uppercase tracking-[0.1em] text-zinc-500">Raw OCR text</div>
          <pre data-testid="detail-ocr-text" className="p-4 text-xs whitespace-pre-wrap font-mono overflow-y-auto max-h-[440px] flex-1">{record.ocr_text || "No OCR text (seeded record)"}</pre>
          {record.source_image && (
            <div className="border-t border-zinc-200 p-3">
              <p className="text-xs text-zinc-500 mb-2">Source document</p>
              <img src={`${BACKEND_URL}/api/files/${record.source_image}`} alt="source" className="rounded border border-zinc-200 max-h-48 w-full object-cover object-top" />
            </div>
          )}
        </div>

        <div className="lg:col-span-4 border border-zinc-200 rounded-md bg-white p-4">
          <p className="text-xs uppercase tracking-[0.1em] text-zinc-500 mb-3">Extracted fields</p>
          <FieldRow label="Owner name" value={record.owner_name} />
          <FieldRow label="Khasra / Survey no" value={record.survey_number} />
          <FieldRow label="Village" value={record.village} />
          <FieldRow label="Tehsil" value={record.tehsil} />
          <FieldRow label="Recorded area (ha)" value={record.area_ha} />
          <FieldRow label="GIS polygon area (ha)" value={record.parcel_area_ha} />
          <FieldRow label="Land type" value={record.land_type} />
          <FieldRow label="Digitized on" value={record.created_at?.slice(0, 10)} />
        </div>

        <div className="lg:col-span-4 border border-zinc-200 rounded-md bg-white p-4">
          <p className="text-xs uppercase tracking-[0.1em] text-zinc-500 mb-3">Matched GIS parcel</p>
          {parcelOnly ? (
            <ParcelMap parcels={parcelOnly} records={[record]} highlightSurvey={record.survey_number} height="380px" />
          ) : (
            <div className="h-[380px] flex items-center justify-center text-sm text-red-600 bg-red-50 border border-red-200 rounded-md" data-testid="no-gis-panel">
              No parcel with khasra {record.survey_number || "?"} exists in the GIS layer
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
