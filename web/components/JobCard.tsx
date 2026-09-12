import Link from "next/link";
import { MapPin } from "lucide-react";
import type { Job } from "@/lib/types";
import { formatSalary } from "@/lib/types";

function dateLabel(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso.slice(0, 10);
  return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

export function JobCard({ job }: { job: Job }) {
  const salary = formatSalary(job);
  return (
    <Link
      href={`/jobs/${job.id}`}
      className="card card-pad group block transition-colors hover:border-emerald-500/40"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold text-slate-100 group-hover:text-emerald-300">
            {job.title}
          </h3>
          <p className="mt-0.5 text-xs text-slate-400">{job.company}</p>
        </div>
        <span className="shrink-0 text-[11px] text-slate-500">{dateLabel(job.posted_at)}</span>
      </div>

      {job.primary_location ? (
        <p className="mt-2 flex items-center gap-1.5 text-xs text-slate-400">
          <MapPin className="h-3 w-3 shrink-0" />
          <span className="truncate">{job.primary_location}</span>
        </p>
      ) : null}

      <div className="mt-3 flex flex-wrap gap-1.5">
        {job.seniority && job.seniority !== "Unknown" ? <span className="chip">{job.seniority}</span> : null}
        {job.remote_type && job.remote_type !== "Unknown" ? <span className="chip">{job.remote_type}</span> : null}
        {job.employment_type && job.employment_type !== "Unknown" ? (
          <span className="chip">{job.employment_type}</span>
        ) : null}
        {salary ? <span className="chip text-emerald-400">{salary}</span> : null}
      </div>

      {job.skills.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-1">
          {job.skills.slice(0, 5).map((skill) => (
            <span
              key={skill}
              className="rounded-md bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-400 ring-1 ring-emerald-500/20"
            >
              {skill}
            </span>
          ))}
          {job.skills.length > 5 ? (
            <span className="px-1.5 py-0.5 text-[10px] text-slate-500">
              +{job.skills.length - 5} more
            </span>
          ) : null}
        </div>
      ) : null}
    </Link>
  );
}