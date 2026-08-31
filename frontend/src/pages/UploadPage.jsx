import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { FileUp, Loader2, ScanText } from "lucide-react";
import { uploadDocument, fetchSamples, processSample, BACKEND_URL } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";

const FieldRow = ({ label, value }) => (
  <div className="flex justify-between border-b border-zinc-100 py-1.5 text-sm">
    <span className="text-zinc-500">{label}</span>
    <span className="font-medium text-right">{value ?? <span className="text-red-500">not extracted</span>}</span>
  </div>
);

export default function UploadPage() {
  const [samples, setSamples] = useState([]);
  const [busy, setBusy] = useState(null);
  const [result, setResult] = useState(null);
  const [hindi, setHindi] = useState(false);
  const fileRef = useRef(null);

  useEffect(() => {
    fetchSamples().then(setSamples).catch(() => {});
  }, []);

  const run = async (fn, label) => {
    setBusy(label);
    setResult(null);
    try {
      const rec = await fn();
      setResult(rec);
      toast.success(`OCR complete — status: ${rec.status}`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Processing failed");
    } finally {
      setBusy(null);
    }
  };

  const onFile = (e) => {
    const f = e.target.files?.[0];
    if (f) run(() => uploadDocument(f, hindi ? "hi" : "en"), "upload");
    e.target.value = "";
  };

  return (
    <div data-testid="upload-page" className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <div className="lg:col-span-4 space-y-6">
        <div>
          <h2 className="font-heading text-2xl font-bold tracking-tight">Upload &amp; OCR</h2>
          <p className="text-sm text-zinc-500">Scan a land record (JPG / PNG / PDF). EasyOCR extracts the text, then regex rules pull structured fields and validation runs automatically.</p>
        </div>

        <div
          className="border-2 border-dashed border-zinc-300 rounded-md p-8 text-center hover:border-zinc-500 transition-colors cursor-pointer bg-zinc-50"
          onClick={() => fileRef.current?.click()}
          data-testid="upload-dropzone"
        >
          <FileUp className="mx-auto mb-2 text-zinc-400" size={28} />
          <p className="text-sm font-medium">Click to upload a scanned record</p>
          <p className="text-xs text-zinc-400 mt-1">JPG, PNG or PDF · first OCR run may take ~30s</p>
          <input ref={fileRef} type="file" accept=".jpg,.jpeg,.png,.pdf" className="hidden" onChange={onFile} data-testid="file-input" />
        </div>

        <label className="flex items-center gap-2 text-sm text-zinc-700 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={hindi}
            onChange={(e) => setHindi(e.target.checked)}
            data-testid="hindi-toggle"
            className="accent-zinc-900 w-4 h-4"
          />
          Document is in Hindi (Devanagari) — uses the Hindi OCR model
        </label>

        <div>
          <h3 className="text-xs uppercase tracking-[0.1em] text-zinc-500 mb-2">Or try a sample document</h3>
          <div className="grid grid-cols-2 gap-3">
            {samples.map((s) => (
              <button
                key={s.name}
                onClick={() => run(() => processSample(s.name), s.name)}
                disabled={!!busy}
                data-testid={`sample-${s.name}`}
                className="border border-zinc-200 rounded-md overflow-hidden text-left hover:border-zinc-900 transition-colors disabled:opacity-50"
              >
                <img src={`${BACKEND_URL}${s.url}`} alt={s.name} className="w-full h-24 object-cover object-top" />
                <p className="text-[11px] px-2 py-1.5 truncate font-medium">
                  {busy === s.name ? "Processing…" : s.name.replace("sample_", "").replace(".png", "").replaceAll("_", " ")}
                </p>
              </button>
            ))}
          </div>
        </div>

        {busy && (
          <div className="flex items-center gap-2 text-sm text-zinc-600" data-testid="ocr-loading">
            <Loader2 className="animate-spin" size={16} /> Running EasyOCR… this can take up to a minute on first load
          </div>
        )}
      </div>

      <div className="lg:col-span-8">
        {!result ? (
          <div className="border border-zinc-200 rounded-md h-full min-h-[300px] flex flex-col items-center justify-center text-zinc-400 bg-zinc-50">
            <ScanText size={32} className="mb-2" />
            <p className="text-sm">OCR output will appear here</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="ocr-result">
            <div className="border border-zinc-200 rounded-md bg-white">
              <div className="px-4 py-2 border-b border-zinc-200 text-xs uppercase tracking-[0.1em] text-zinc-500">Raw OCR text</div>
              <pre data-testid="raw-ocr-text" className="p-4 text-xs whitespace-pre-wrap max-h-[420px] overflow-y-auto font-mono">{result.ocr_text}</pre>
            </div>
            <div className="space-y-4">
              <div className="border border-zinc-200 rounded-md bg-white p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs uppercase tracking-[0.1em] text-zinc-500">Extracted fields</span>
                  <StatusBadge status={result.status} />
                </div>
                <FieldRow label="Owner name" value={result.owner_name} />
                <FieldRow label="Khasra / Survey no" value={result.survey_number} />
                <FieldRow label="Village" value={result.village} />
                <FieldRow label="Tehsil" value={result.tehsil} />
                <FieldRow label="Area (ha)" value={result.area_ha} />
                <FieldRow label="Land type" value={result.land_type} />
              </div>
              {result.flags?.length > 0 && (
                <div className="border border-amber-300 bg-amber-50 rounded-md p-4">
                  <p className="text-xs uppercase tracking-[0.1em] text-amber-700 mb-2">Validation flags</p>
                  <ul className="text-sm text-amber-900 list-disc pl-4 space-y-1">
                    {result.flags.map((f, i) => <li key={i}>{f}</li>)}
                  </ul>
                </div>
              )}
              <Button asChild className="w-full" data-testid="view-record-link">
                <Link to={`/records/${result.id}`}>Open record in review view</Link>
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
