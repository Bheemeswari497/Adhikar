import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Check, X, AlertTriangle, FileText } from "lucide-react";
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

  const handleDecision = async (action) => {
    try {
      const updated = await decideRecord(id, action);
      setRecord(updated);
      toast.success(`Record ${action}d`);
    } catch {
      toast.error("Failed to update status");
    }
  };

  if (!record) return <div className="p-8 text-center text-zinc-500">Loading record…</div>;

  const matchedFeatures = parcels?.features?.filter(
    (f) =>
      record.survey_number &&
      (String(f.properties.survey_number) === String(record.survey_number) ||
        String(f.properties.khasra_no) === String(record.survey_number))
  ) || [];

  const parcelOnly =
    matchedFeatures.length > 0
      ? {
          ...parcels,
          features: matchedFeatures,
        }
      : null;

  return (
    <div data-testid="record-detail-page" className="space-y-4">
      <div className="flex items-center justify-between">
        <Link to="/records" className="inline-flex items-center text-sm text-zinc-600 hover:text-zinc-900">
          <ArrowLeft size={16} className="mr-1" /> Back to records
        </Link>
        <div className="flex items-center gap-2">
          <StatusBadge status={record.status} />
          <Button size="sm" variant="outline" className="text-emerald-700 hover:bg-emerald-50" onClick={() => handleDecision("approve")}>
            <Check size={14} className="mr-1" /> Approve
          </Button>
          <Button size="sm" variant="outline" className="text-rose-700 hover:bg-rose-50" onClick={() => handleDecision("reject")}>
            <X size={14} className="mr-1" /> Reject
          </Button>
        </div>
      </div>

      {record.flags?.length > 0 && (
        <div className="border border-amber-300 bg-amber-50 p-4 rounded-md" data-testid="record-flags-panel">
          <div className="flex items-center gap-1.5 text-amber-900 font-semibold text-xs uppercase tracking-[0.1em] mb-1">
            <AlertTriangle size={14} /> Why this record was flagged
          </div>
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
              {record.source_image.toLowerCase().endsWith(".pdf") ? (
                <div className="rounded border border-zinc-200 bg-zinc-50 p-3 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs text-zinc-700 font-medium truncate">
                    <FileText size={16} className="text-red-500 shrink-0" />
                    <span className="truncate">{record.source_image.split("/").pop()}</span>
                  </div>
                  <a
                    href={`${BACKEND_URL}/api/files/${record.source_image}`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-blue-600 hover:text-blue-800 font-semibold shrink-0 ml-2"
                  >
                    View PDF ↗
                  </a>
                </div>
              ) : (
                <img src={`${BACKEND_URL}/api/files/${record.source_image}`} alt="source" className="rounded border border-zinc-200 max-h-48 w-full object-cover object-top" />
              )}
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
            <div className="h-[380px] flex items-center justify-center text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-4 text-center" data-testid="no-gis-panel">
              No matching parcel polygon found in GIS cadastral map for khasra {record.survey_number || "?"}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
