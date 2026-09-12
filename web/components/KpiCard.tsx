export function KpiCard({
  label,
  value,
  hint,
  accent = "text-emerald-400",
}: {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  accent?: string;
}) {
  return (
    <div className="card card-pad">
      <p className="label-muted">{label}</p>
      <p className={`mt-2 value-hero ${accent}`}>{value}</p>
      {hint ? <p className="mt-1 text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}