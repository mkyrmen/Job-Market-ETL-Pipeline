import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, ExternalLink, MapPin } from "lucide-react";
import { getJob } from "@/lib/data-source";
import { Card } from "@/components/Card";
import { formatSalary } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const job = await getJob(id);
  if (!job) notFound();

  const salary = formatSalary(job);

  return (
    <div className="mx-auto max-w-4xl">
      <Link href="/jobs" className="mb-6 inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-200">
        <ArrowLeft className="h-4 w-4" /> Back to all jobs
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-50">{job.title}</h1>
          <p className="mt-1 text-sm text-slate-400">{job.company}</p>
        </div>
        <div className="flex items-center gap-2">
          {job.apply_url ? (
            <a href={job.apply_url} target="_blank" rel="noreferrer" className="btn btn-primary">
              Apply <ExternalLink className="h-4 w-4" />
            </a>
          ) : null}
          {job.job_url ? (
            <a href={job.job_url} target="_blank" rel="noreferrer" className="btn btn-outline">
              Source
            </a>
          ) : null}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-1.5">
        {job.seniority && job.seniority !== "Unknown" ? <span className="chip">{job.seniority}</span> : null}
        {job.remote_type && job.remote_type !== "Unknown" ? <span className="chip">{job.remote_type}</span> : null}
        {job.employment_type && job.employment_type !== "Unknown" ? <span className="chip">{job.employment_type}</span> : null}
        {salary ? <span className="chip text-emerald-400">{salary}</span> : null}
      </div>

      {job.original_title && job.original_title !== job.title ? (
        <p className="mt-3 text-xs text-slate-500">
          Original title: <span className="font-mono">{job.original_title}</span>
        </p>
      ) : null}

      <div className="mt-8 grid gap-4 md:grid-cols-3">
        <Card title="Locations">
          {job.locations.length > 0 ? (
            <ul className="space-y-2">
              {job.locations.map((loc) => (
                <li key={loc} className="flex items-start gap-2 text-sm text-slate-300">
                  <MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-500" />
                  {loc}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">No location specified.</p>
          )}
        </Card>
        <Card title="Skills extracted" className="md:col-span-2">
          {job.skills.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {job.skills.map((skill) => (
                <Link
                  key={skill}
                  href={`/jobs?skill=${encodeURIComponent(skill)}`}
                  className="rounded-md bg-emerald-500/10 px-2 py-1 text-xs font-medium text-emerald-400 ring-1 ring-emerald-500/20 transition-colors hover:bg-emerald-500/20"
                >
                  {skill}
                </Link>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">No skills detected.</p>
          )}
        </Card>
      </div>

      <Card title="Description" className="mt-4" subtitle="as captured and cleaned by the pipeline">
        <div className="prose-invert max-w-none space-y-3 text-sm leading-relaxed text-slate-300">
          {job.description.split(/\n+/).filter(Boolean).map((paragraph, i) => (
            <p key={i}>{paragraph}</p>
          ))}
        </div>
      </Card>

      <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-xs text-slate-500">
        <span>External ID: <code className="font-mono">{job.external_job_id}</code></span>
        {job.posted_at ? (
          <span>
            Posted: <code className="font-mono">{job.posted_at.replace("T", " ")} UTC</code>
          </span>
        ) : null}
      </div>
    </div>
  );
}