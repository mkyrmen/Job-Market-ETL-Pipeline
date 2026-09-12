export function SourceBadge({ source }: { source: string }) {
  const remote = source === "supabase-postgres";
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-ink-600 bg-ink-850 px-2.5 py-1 text-[11px] font-medium text-slate-300">
      <span
        className={`h-1.5 w-1.5 rounded-full ${remote ? "bg-teal-400" : "bg-emerald-400"}`}
      />
      {remote ? "Supabase PostgreSQL" : "Local seed snapshot"}
    </span>
  );
}