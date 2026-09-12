import { AlertTriangle, CheckCircle2, Info, TrendingUp } from "lucide-react";
import type { Insight } from "@/lib/types";

const severityStyle: Record<Insight["severity"], string> = {
  info: "text-sky-400",
  positive: "text-emerald-400",
  warning: "text-amber-400",
  action: "text-rose-400",
};

const SeverityIcon = {
  info: Info,
  positive: CheckCircle2,
  warning: AlertTriangle,
  action: TrendingUp,
};

export function InsightCard({
  insight,
  index,
}: {
  insight: Insight;
  index: number;
}) {
  const Icon = SeverityIcon[insight.severity];
  return (
    <article className="card card-pad flex flex-col gap-3">
      <div className="flex items-start gap-3">
        <span
          className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ring-1 ${severityStyle[insight.severity]} bg-ink-850 ring-ink-600`}
        >
          <Icon className="h-4 w-4" />
        </span>
        <div>
          <h3 className="text-sm font-semibold leading-snug text-slate-100">
            <span className="mr-1.5 font-mono text-xs text-slate-500">{String(index + 1).padStart(2, "0")}</span>
            {insight.title}
          </h3>
          <p className="mt-1 text-xs leading-relaxed text-slate-400">{insight.detail}</p>
        </div>
      </div>
      <footer className="mt-auto flex items-center gap-2 text-[11px] text-slate-500">
        <span className="chip">{insight.category}</span>
        <code className="font-mono">basis: {insight.basis}</code>
      </footer>
    </article>
  );
}