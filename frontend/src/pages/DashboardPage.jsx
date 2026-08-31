import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { ArrowUpDown, Download, RefreshCw } from "lucide-react";
import { fetchRecords, reseed, API } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";

const FILTERS = [
  "all",
  "verified",
  "flagged: duplicate",
  "flagged: area mismatch",
  "flagged: no GIS match",
  "approved",
  "rejected",
];

export default function DashboardPage() {
  const [records, setRecords] = useState([]);
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState({ key: "created_at", dir: -1 });
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const load = () => {
    setLoading(true);
    fetchRecords().then(setRecords).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const handleReseed = async () => {
    await reseed();
    toast.success("Demo data reset");
    load();
  };

  const filtered = useMemo(() => {
    let out = filter === "all" ? records : records.filter((r) => r.status === filter);
    return [...out].sort((a, b) => {
      const av = a[sort.key] ?? "";
      const bv = b[sort.key] ?? "";
      return (av > bv ? 1 : av < bv ? -1 : 0) * sort.dir;
    });
  }, [records, filter, sort]);

  const counts = useMemo(() => {
    const c = { all: records.length };
    records.forEach((r) => (c[r.status] = (c[r.status] || 0) + 1));
    return c;
  }, [records]);

  const th = (label, key) => (
    <th
      className="text-left px-4 py-2 text-xs uppercase tracking-[0.1em] text-zinc-500 cursor-pointer select-none hover:text-zinc-900"
      onClick={() => setSort((s) => ({ key, dir: s.key === key ? -s.dir : 1 }))}
      data-testid={`sort-${key}`}
    >
      <span className="inline-flex items-center gap-1">{label} <ArrowUpDown size={12} /></span>
    </th>
  );

  return (
    <div data-testid="officer-dashboard">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div>
          <h2 className="font-heading text-2xl font-bold tracking-tight">Officer Review Dashboard</h2>
          <p className="text-sm text-zinc-500">Digitized land records · Village Rampur Kalan, Tehsil Huzur, Bhopal</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" asChild data-testid="export-csv-button">
            <a href={`${API}/export/csv`} download>
              <Download size={14} className="mr-1" /> Export CSV
            </a>
          </Button>
          <Button variant="outline" size="sm" onClick={handleReseed} data-testid="reseed-button">
            <RefreshCw size={14} className="mr-1" /> Reset demo data
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            data-testid={`filter-${f.replace(/[:\s]+/g, "-")}`}
            className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-colors ${
              filter === f
                ? "bg-zinc-900 text-white border-zinc-900"
                : "bg-white text-zinc-600 border-zinc-300 hover:bg-zinc-50"
            }`}
          >
            {f} {counts[f] ? `(${counts[f]})` : "(0)"}
          </button>
        ))}
      </div>

      <div className="border border-zinc-200 rounded-md overflow-x-auto bg-white">
        <table className="w-full text-sm" data-testid="records-table">
          <thead className="bg-zinc-50 border-b border-zinc-200">
            <tr>
              {th("Owner", "owner_name")}
              {th("Khasra No", "survey_number")}
              {th("Village", "village")}
              {th("Area (ha)", "area_ha")}
              {th("Land Type", "land_type")}
              {th("Status", "status")}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-zinc-400">Loading…</td></tr>
            ) : filtered.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-zinc-400">No records</td></tr>
            ) : (
              filtered.map((r) => (
                <tr
                  key={r.id}
                  onClick={() => navigate(`/records/${r.id}`)}
                  data-testid={`record-row-${r.id}`}
                  className="border-b border-zinc-100 hover:bg-zinc-50 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-2 font-medium">{r.owner_name || "—"}</td>
                  <td className="px-4 py-2">{r.survey_number || "—"}</td>
                  <td className="px-4 py-2">{r.village || "—"}</td>
                  <td className="px-4 py-2">{r.area_ha ?? "—"}</td>
                  <td className="px-4 py-2">{r.land_type || "—"}</td>
                  <td className="px-4 py-2"><StatusBadge status={r.status} /></td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
