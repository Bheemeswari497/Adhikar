import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { FileUp, Loader2, ScanText, CheckCircle2, AlertCircle, FileText, ArrowRight, Edit3, Save, X } from "lucide-react";
import { uploadDocument, fetchSamples, processSample, updateRecord, BACKEND_URL } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";

const FieldRow = ({ label, value }) => (
  <div className="flex justify-between items-center border-b border-zinc-100 py-2 text-sm">
    <span className="text-zinc-500">{label}</span>
    <span className="font-medium text-right text-zinc-900">
      {value ?? <span className="text-red-500 font-normal italic">not extracted</span>}
    </span>
  </div>
);

export default function UploadPage() {
  const [samples, setSamples] = useState([]);
  const [busy, setBusy] = useState(null);
  const [result, setResult] = useState(null);
  const [hindi, setHindi] = useState(true);
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [savingEdit, setSavingEdit] = useState(false);
  const [editForm, setEditForm] = useState({
    owner_name: "",
    survey_number: "",
    village: "",
    tehsil: "",
    area_ha: "",
    land_type: "",
  });
  const fileRef = useRef(null);

  useEffect(() => {
    fetchSamples().then(setSamples).catch(() => {});
  }, []);

  const startEdit = () => {
    if (!result) return;
    setEditForm({
      owner_name: result.owner_name || "",
      survey_number: result.survey_number || "",
      village: result.village || "",
      tehsil: result.tehsil || "",
      area_ha: result.area_ha != null ? String(result.area_ha) : "",
      land_type: result.land_type || "",
    });
    setIsEditing(true);
  };

  const handleSaveEdit = async (e) => {
    e.preventDefault();
    if (!result?.id) return;
    setSavingEdit(true);
    try {
      const payload = {
        owner_name: editForm.owner_name.trim() || null,
        survey_number: editForm.survey_number.trim() || null,
        village: editForm.village.trim() || null,
        tehsil: editForm.tehsil.trim() || null,
        area_ha: editForm.area_ha ? parseFloat(editForm.area_ha) : null,
        land_type: editForm.land_type.trim() || null,
      };
      const updated = await updateRecord(result.id, payload);
      setResult(updated);
      setIsEditing(false);
      toast.success("Fields updated & re-validated successfully!");
    } catch (err) {
      toast.error(err?.response?.data?.detail || err.message || "Failed to update record");
    } finally {
      setSavingEdit(false);
    }
  };

  const handleProcessFile = async (file) => {
    if (!file) return;
    const validExts = [".jpg", ".jpeg", ".png", ".pdf", ".webp", ".bmp", ".tiff", ".tif"];
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
    if (!validExts.includes(ext)) {
      toast.error(`Unsupported file type (${ext}). Please upload JPG, PNG, or PDF.`);
      return;
    }

    setSelectedFile(file);
    setBusy("upload");
    setResult(null);
    setIsEditing(false);
    try {
      const rec = await uploadDocument(file, hindi ? "hi" : "en");
      setResult(rec);
      toast.success(`OCR complete — record ${rec.status}`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message || "Document processing failed");
    } finally {
      setBusy(null);
    }
  };

  const handleSampleClick = async (sampleName) => {
    setSelectedFile(null);
    setBusy(sampleName);
    setResult(null);
    setIsEditing(false);
    try {
      const rec = await processSample(sampleName);
      setResult(rec);
      toast.success(`OCR complete — status: ${rec.status}`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message || "Sample processing failed");
    } finally {
      setBusy(null);
    }
  };

  const onDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const onDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const onDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      handleProcessFile(files[0]);
    }
  };

  const onFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      handleProcessFile(file);
    }
    e.target.value = "";
  };

  return (
    <div data-testid="upload-page" className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <div className="lg:col-span-4 space-y-6">
        <div>
          <h2 className="font-heading text-2xl font-bold tracking-tight text-zinc-900">Upload &amp; OCR</h2>
          <p className="text-sm text-zinc-500 mt-1">
            Upload or drop a scanned land record (JPG / PNG / PDF). EasyOCR will extract text, parse survey &amp; owner details, and validate against cadastral GIS maps.
          </p>
        </div>

        {/* Dropzone with Drag & Drop + Click to Upload */}
        <div
          onDragOver={onDragOver}
          onDragEnter={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={() => fileRef.current?.click()}
          data-testid="upload-dropzone"
          className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-all ${
            isDragging
              ? "border-blue-600 bg-blue-50 scale-[1.01]"
              : "border-zinc-300 bg-zinc-50 hover:border-zinc-500 hover:bg-zinc-100/70"
          }`}
        >
          <input
            ref={fileRef}
            type="file"
            accept=".jpg,.jpeg,.png,.pdf,.webp,.bmp"
            className="hidden"
            onChange={onFileChange}
            data-testid="file-input"
          />

          <div className="flex flex-col items-center justify-center space-y-2">
            <div className="p-3 bg-white rounded-full shadow-sm border border-zinc-200">
              <FileUp className={`w-6 h-6 ${isDragging ? "text-blue-600" : "text-zinc-600"}`} />
            </div>
            <div>
              <p className="text-sm font-semibold text-zinc-800">
                {isDragging ? "Drop your file here" : "Drag & drop or click to upload"}
              </p>
              <p className="text-xs text-zinc-500 mt-0.5">Supports JPG, PNG, WebP, PDF (up to 20MB)</p>
            </div>

            <Button
              type="button"
              variant="outline"
              size="sm"
              className="mt-2 text-xs bg-white pointer-events-none"
            >
              Select File from Device
            </Button>
          </div>

          {selectedFile && (
            <div className="mt-4 pt-3 border-t border-zinc-200 flex items-center justify-center gap-2 text-xs text-zinc-700 font-medium">
              <FileText size={14} className="text-zinc-500" />
              <span className="truncate max-w-[200px]">{selectedFile.name}</span>
              <span className="text-zinc-400">({(selectedFile.size / 1024).toFixed(0)} KB)</span>
            </div>
          )}
        </div>

        {/* Hindi Toggle */}
        <label className="flex items-center gap-2.5 p-3 rounded-md border border-zinc-200 bg-white text-sm text-zinc-700 cursor-pointer select-none hover:bg-zinc-50 transition-colors">
          <input
            type="checkbox"
            checked={hindi}
            onChange={(e) => setHindi(e.target.checked)}
            data-testid="hindi-toggle"
            className="accent-zinc-900 w-4 h-4 rounded cursor-pointer"
          />
          <span className="leading-tight">
            Document in Hindi (Devanagari) — <span className="text-xs text-zinc-500">uses Hindi OCR model</span>
          </span>
        </label>

        {/* Sample Documents */}
        <div>
          <h3 className="text-xs uppercase tracking-wider font-semibold text-zinc-500 mb-2.5">
            Or try a demo sample
          </h3>
          <div className="grid grid-cols-2 gap-3">
            {samples.map((s) => {
              const isSampleBusy = busy === s.name;
              return (
                <button
                  key={s.name}
                  type="button"
                  onClick={() => handleSampleClick(s.name)}
                  disabled={!!busy}
                  data-testid={`sample-${s.name}`}
                  className="border border-zinc-200 bg-white rounded-lg overflow-hidden text-left hover:border-zinc-900 hover:shadow-sm transition-all disabled:opacity-50 group relative"
                >
                  <img
                    src={`${BACKEND_URL}${s.url}`}
                    alt={s.name}
                    className="w-full h-24 object-cover object-top border-b border-zinc-100 group-hover:opacity-90"
                  />
                  <div className="p-2">
                    <p className="text-[11px] truncate font-medium text-zinc-800 capitalize">
                      {s.name.replace("sample_", "").replace(".png", "").replaceAll("_", " ")}
                    </p>
                    <span className="text-[10px] text-blue-600 font-medium">Click to run OCR →</span>
                  </div>
                  {isSampleBusy && (
                    <div className="absolute inset-0 bg-white/80 backdrop-blur-[1px] flex items-center justify-center">
                      <Loader2 className="animate-spin text-zinc-800" size={20} />
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {busy && (
          <div
            className="flex items-center gap-2.5 p-3 rounded-lg border border-blue-200 bg-blue-50 text-xs text-blue-800 font-medium"
            data-testid="ocr-loading"
          >
            <Loader2 className="animate-spin text-blue-600 shrink-0" size={16} />
            <span>Running EasyOCR recognition and GIS parcel validation…</span>
          </div>
        )}
      </div>

      {/* OCR Result View */}
      <div className="lg:col-span-8">
        {busy ? (
          <div className="border border-blue-200 rounded-lg h-full min-h-[380px] flex flex-col items-center justify-center text-zinc-600 bg-blue-50/40 p-8 text-center animate-pulse">
            <div className="w-14 h-14 rounded-full bg-blue-100 flex items-center justify-center mb-4 text-blue-600 shadow-sm">
              <Loader2 className="animate-spin" size={28} />
            </div>
            <p className="text-base font-semibold text-zinc-900">Processing Land Document...</p>
            <p className="text-xs text-zinc-500 mt-1 max-w-md leading-relaxed">
              Performing multi-page optical character recognition (OCR), extracting Khasra / Survey numbers, owner names, and area extents, then validating against Cadastral GIS parcels.
            </p>
            <div className="mt-4 flex items-center gap-2 text-[11px] text-blue-700 bg-white/80 px-3 py-1.5 rounded-full border border-blue-200 shadow-xs">
              <span className="w-2 h-2 rounded-full bg-blue-500 animate-ping" />
              <span>Analyzing Document Pages…</span>
            </div>
          </div>
        ) : !result ? (
          <div className="border border-zinc-200 rounded-lg h-full min-h-[350px] flex flex-col items-center justify-center text-zinc-400 bg-zinc-50/70 p-6 text-center">
            <div className="w-12 h-12 rounded-full bg-zinc-100 flex items-center justify-center mb-3 text-zinc-400">
              <ScanText size={24} />
            </div>
            <p className="text-sm font-medium text-zinc-600">No document processed yet</p>
            <p className="text-xs text-zinc-400 mt-1 max-w-sm">
              Upload a scanned khasra / khatauni file or click one of the demo samples on the left to extract text and validate.
            </p>
          </div>
        ) : (
          <div className="space-y-4" data-testid="ocr-result">
            <div className="flex items-center justify-between p-3 rounded-lg border border-zinc-200 bg-white">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                <span className="text-sm font-semibold text-zinc-900">Document Processed Successfully</span>
              </div>
              <StatusBadge status={result.status} />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Raw OCR Text */}
              <div className="border border-zinc-200 rounded-lg bg-white overflow-hidden flex flex-col">
                <div className="px-4 py-2.5 border-b border-zinc-200 bg-zinc-50 text-xs uppercase tracking-wider font-semibold text-zinc-600 flex justify-between items-center">
                  <span>Raw OCR Output</span>
                  <span className="text-[10px] text-zinc-400 lowercase font-mono">easyocr</span>
                </div>
                <pre
                  data-testid="raw-ocr-text"
                  className="p-4 text-xs whitespace-pre-wrap max-h-[440px] overflow-y-auto font-mono text-zinc-800 bg-zinc-50/40 flex-1 leading-relaxed"
                >
                  {result.ocr_text || "(No text recognized)"}
                </pre>
              </div>

              {/* Extracted Fields */}
              <div className="space-y-4">
                <div className="border border-zinc-200 rounded-lg bg-white p-4 shadow-sm">
                  <div className="flex items-center justify-between mb-3 pb-2 border-b border-zinc-100">
                    <span className="text-xs uppercase tracking-wider font-semibold text-zinc-600">
                      Structured Fields
                    </span>
                    {!isEditing ? (
                      <button
                        type="button"
                        onClick={startEdit}
                        className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
                      >
                        <Edit3 size={13} /> Edit / Refine
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setIsEditing(false)}
                        className="text-xs text-zinc-500 hover:text-zinc-700 font-medium flex items-center gap-1"
                      >
                        <X size={13} /> Cancel
                      </button>
                    )}
                  </div>

                  {isEditing ? (
                    <form onSubmit={handleSaveEdit} className="space-y-3 text-xs">
                      <div>
                        <label className="block text-zinc-500 font-medium mb-1">Owner Name</label>
                        <input
                          type="text"
                          value={editForm.owner_name}
                          onChange={(e) => setEditForm({ ...editForm, owner_name: e.target.value })}
                          className="w-full p-2 border border-zinc-300 rounded text-xs focus:ring-1 focus:ring-zinc-900 outline-none"
                          placeholder="e.g. Involu Sumathi"
                        />
                      </div>
                      <div>
                        <label className="block text-zinc-500 font-medium mb-1">Khasra / Survey No</label>
                        <input
                          type="text"
                          value={editForm.survey_number}
                          onChange={(e) => setEditForm({ ...editForm, survey_number: e.target.value })}
                          className="w-full p-2 border border-zinc-300 rounded text-xs focus:ring-1 focus:ring-zinc-900 outline-none"
                          placeholder="e.g. 106/2 or 31/8"
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="block text-zinc-500 font-medium mb-1">Village</label>
                          <input
                            type="text"
                            value={editForm.village}
                            onChange={(e) => setEditForm({ ...editForm, village: e.target.value })}
                            className="w-full p-2 border border-zinc-300 rounded text-xs focus:ring-1 focus:ring-zinc-900 outline-none"
                            placeholder="e.g. Rampur Kalan"
                          />
                        </div>
                        <div>
                          <label className="block text-zinc-500 font-medium mb-1">Tehsil / Mandal</label>
                          <input
                            type="text"
                            value={editForm.tehsil}
                            onChange={(e) => setEditForm({ ...editForm, tehsil: e.target.value })}
                            className="w-full p-2 border border-zinc-300 rounded text-xs focus:ring-1 focus:ring-zinc-900 outline-none"
                            placeholder="e.g. Huzur or Kandukur"
                          />
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="block text-zinc-500 font-medium mb-1">Area (ha)</label>
                          <input
                            type="number"
                            step="any"
                            value={editForm.area_ha}
                            onChange={(e) => setEditForm({ ...editForm, area_ha: e.target.value })}
                            className="w-full p-2 border border-zinc-300 rounded text-xs focus:ring-1 focus:ring-zinc-900 outline-none"
                            placeholder="e.g. 1.18"
                          />
                        </div>
                        <div>
                          <label className="block text-zinc-500 font-medium mb-1">Land Type</label>
                          <input
                            type="text"
                            value={editForm.land_type}
                            onChange={(e) => setEditForm({ ...editForm, land_type: e.target.value })}
                            className="w-full p-2 border border-zinc-300 rounded text-xs focus:ring-1 focus:ring-zinc-900 outline-none"
                            placeholder="e.g. Agricultural Land"
                          />
                        </div>
                      </div>

                      <div className="pt-2 flex items-center gap-2">
                        <Button type="submit" size="sm" disabled={savingEdit} className="w-full gap-1.5 text-xs">
                          {savingEdit ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
                          Save &amp; Re-validate GIS
                        </Button>
                      </div>
                    </form>
                  ) : (
                    <div>
                      {result.parcel_area_ha && (
                        <div className="mb-2 text-right text-[11px] text-zinc-500">
                          GIS Polygon Area: <strong className="text-zinc-800">{result.parcel_area_ha} ha</strong>
                        </div>
                      )}
                      <FieldRow label="Owner Name" value={result.owner_name} />
                      <FieldRow label="Khasra / Survey No" value={result.survey_number} />
                      <FieldRow label="Village" value={result.village} />
                      <FieldRow label="Tehsil / Mandal" value={result.tehsil} />
                      <FieldRow label="Recorded Area (ha)" value={result.area_ha ? `${result.area_ha} ha` : null} />
                      <FieldRow label="Land Type" value={result.land_type} />
                    </div>
                  )}
                </div>

                {/* Validation Warnings / Flags */}
                {result.flags?.length > 0 ? (
                  <div className="border border-amber-300 bg-amber-50 rounded-lg p-4">
                    <div className="flex items-center gap-1.5 mb-2 text-amber-800 font-semibold text-xs uppercase tracking-wide">
                      <AlertCircle size={14} />
                      <span>Validation Flags ({result.flags.length})</span>
                    </div>
                    <ul className="text-xs text-amber-900 list-disc pl-4 space-y-1">
                      {result.flags.map((f, i) => (
                        <li key={i}>{f}</li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <div className="border border-emerald-200 bg-emerald-50 rounded-lg p-3 text-xs text-emerald-800 flex items-center gap-2">
                    <CheckCircle2 size={16} className="text-emerald-600" />
                    <span>All validation checks passed with 100% cadastral match!</span>
                  </div>
                )}

                <Button asChild className="w-full gap-2" data-testid="view-record-link">
                  <Link to={`/records/${result.id}`}>
                    Review in Cadastral Map View <ArrowRight size={14} />
                  </Link>
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
