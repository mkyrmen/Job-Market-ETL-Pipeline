import Link from "next/link";
import { ArrowRight, DatabaseZap } from "lucide-react";
import { getAnalyticsBundle, getSourceLabel } from "@/lib/data-source";
import { Card } from "@/components/Card";
import { KpiCard } from "@/components/KpiCard";
import { DonutChart, OverTimeAreaChart, HorizontalBarListChart } from "@/components/Charts";
import { BarList } from "@/components/BarList";
import { InsightCard } from "@/components/InsightCard";
import { SourceBadge } from "@/components/SourceBadge";

export const dynamic = "force-dynamic";

export default async function OverviewPage() {
  const bundle = await getAnalyticsBundle();
  const { overview } = bundle;
  const recent = bundle.overview.total_jobs;

  return (
    <>
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight text-slate-50">
              Job Market Overview
            </h1>
            <SourceBadge source={getSourceLabel()} />
          </div>
          <p className="mt-1 max-w-2xl text-sm text-slate-400">
            An ETL pipeline that watches Google Careers postings and turns them into market
            intelligence on skills, seniority, geography and compensation.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/jobs" className="btn btn-outline">
            Browse jobs <ArrowRight className="h-4 w-4" />
          </Link>
          <Link href="/pipeline" className="btn btn-primary">
            <DatabaseZap className="h-4 w-4" /> View pipeline
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <KpiCard label="Jobs tracked" value={overview.total_jobs.toLocaleString()} hint="postings in the database" />
        <KpiCard label="Skills demanded" value={overview.total_skills.toLocaleString()} hint="distinct skills extracted" accent="text-teal-400" />
        <KpiCard label="Hiring hubs" value={overview.total_locations.toLocaleString()} hint="distinct locations" accent="text-sky-400" />
        <KpiCard label="Companies" value={overview.total_companies.toLocaleString()} hint="employers in the feed" accent="text-violet-400" />
      </div>

      {overview.salary_disclosed_postings > 0 && (
        <div className="card card-pad mt-4 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="label-muted">Compensation disclosed</p>
            <p className="mt-1 text-sm text-slate-300">
              {overview.salary_disclosed_postings} postings carry a US base salary band
            </p>
          </div>
          <p className="font-mono text-xl font-semibold text-emerald-400">
            {overview.salary_currency ?? "USD"}{" "}
            {overview.salary_min?.toLocaleString()} - {overview.salary_max?.toLocaleString()}
          </p>
        </div>
      )}

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card
          title="Top skills"
          subtitle="share of postings mentioning each skill"
          className="lg:col-span-2"
          action={
            <Link href="/skills" className="text-xs font-medium text-emerald-400 hover:text-emerald-300">
              Explore →
            </Link>
          }
        >
          <HorizontalBarListChart
            data={bundle.topSkills
              .slice(0, 10)
              .map((s) => ({ label: s.name, count: s.job_count }))}
          />
        </Card>
        <Card title="Seniority mix" subtitle="how postings are level-tagged">
          <DonutChart data={bundle.jobsBySeniority} centerLabel="postings" />
        </Card>

        <Card title="Postings over time" subtitle="by first published month">
          <OverTimeAreaChart data={bundle.jobsOverTime} />
        </Card>
        <Card
          title="Hiring hubs"
          subtitle="locations appearing most often"
          className="lg:col-span-2"
        >
          <BarList rows={bundle.jobsByLocation.slice(0, 12)} />
        </Card>
      </div>

      <div className="mt-6">
        <div className="mb-4 flex items-end justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-50">Auto-generated insights</h2>
            <p className="text-xs text-slate-500">Every insight carries the data slice it is based on</p>
          </div>
          <Link href="/insights" className="text-xs font-medium text-emerald-400 hover:text-emerald-300">
            All insights →
          </Link>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {bundle.insights.slice(0, 6).map((insight, i) => (
            <InsightCard key={insight.title} insight={insight} index={i} />
          ))}
        </div>
      </div>

      {recent > 0 && (
        <div className="mt-6 flex items-center justify-between gap-4 rounded-xl border border-ink-700 bg-ink-900/60 px-5 py-4">
          <p className="text-sm text-slate-400">
            Data freshness: every run of <code className="font-mono text-emerald-400">python -m src.main run</code>{" "}
            appends new postings and skips ones already seen.
          </p>
          <Link href="/jobs" className="btn btn-outline shrink-0">
            Open job explorer <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      )}
    </>
  );
}