const STYLES = {
  verified: "bg-emerald-100 text-emerald-800 border-emerald-400",
  approved: "bg-emerald-100 text-emerald-800 border-emerald-400",
  "flagged: duplicate": "bg-amber-100 text-amber-800 border-amber-400",
  "flagged: area mismatch": "bg-red-100 text-red-700 border-red-400",
  "flagged: no GIS match": "bg-red-100 text-red-700 border-red-400",
  rejected: "bg-zinc-200 text-zinc-600 border-zinc-400",
  pending: "bg-zinc-100 text-zinc-600 border-zinc-300",
};

export const StatusBadge = ({ status }) => (
  <span
    data-testid="status-badge"
    className={`inline-block px-2 py-0.5 text-xs font-medium border rounded ${STYLES[status] || STYLES.pending}`}
  >
    {status}
  </span>
);
