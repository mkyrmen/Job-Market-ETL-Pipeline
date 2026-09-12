export function BarList({
  rows,
  max,
  formatCount,
}: {
  rows: { label: string; count: number }[];
  max?: number;
  formatCount?: (n: number) => string;
}) {
  const peak = max ?? Math.max(1, ...rows.map((r) => r.count));
  const fmt = formatCount ?? ((n: number) => n.toLocaleString());
  return (
    <ul className="space-y-2.5">
      {rows.map((row) => (
        <li key={row.label} className="group">
          <div className="mb-1 flex items-baseline justify-between gap-3 text-sm">
            <span className="truncate text-slate-300 group-hover:text-slate-100">{row.label}</span>
            <span className="shrink-0 font-mono text-xs text-slate-500">{fmt(row.count)}</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-ink-800">
            <div
              className="h-full rounded-full bg-gradient-to-r from-emerald-500/80 to-teal-400/80 transition-all"
              style={{ width: `${Math.max(2, (row.count / peak) * 100)}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}

export function RankedTable({
  rows,
  total,
  formatCount,
  emptyMessage = "No data yet",
}: {
  rows: { label: string; count: number }[];
  total?: number;
  formatCount?: (n: number) => string;
  emptyMessage?: string;
}) {
  const fmt = formatCount ?? ((n: number) => n.toLocaleString());
  if (rows.length === 0) {
    return <p className="py-8 text-center text-sm text-slate-500">{emptyMessage}</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-ink-700 text-left text-xs uppercase tracking-wider text-slate-500">
            <th className="py-2 pr-4 font-medium">Rank</th>
            <th className="py-2 pr-4 font-medium">Name</th>
            <th className="py-2 text-right font-medium">Postings</th>
            <th className="py-2 pl-4 text-right font-medium">Share</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={row.label} className="border-b border-ink-800/60 last:border-0 hover:bg-ink-800/30">
              <td className="py-2 pr-4 font-mono text-xs text-slate-500">{i + 1}</td>
              <td className="max-w-[18rem] truncate py-2 pr-4 text-slate-200">{row.label}</td>
              <td className="py-2 text-right font-mono text-xs text-slate-400">{fmt(row.count)}</td>
              <td className="py-2 pl-4 text-right font-mono text-xs text-emerald-400">
                {total ? Math.round((row.count / Math.max(1, total)) * 100) : 0}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}