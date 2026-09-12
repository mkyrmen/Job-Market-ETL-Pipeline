import { getAnalyticsBundle } from "@/lib/data-source";
import { PageHeader } from "@/components/Card";
import { Card } from "@/components/Card";
import { DonutChart } from "@/components/Charts";
import { InsightCard } from "@/components/InsightCard";
import { BarList } from "@/components/BarList";

export const dynamic = "force-dynamic";

export default async function InsightsPage() {
  const bundle = await getAnalyticsBundle();

  return (
    <>
      <PageHeader
        title="Insights"
        subtitle="Automatically generated observations from the analytics views. Every insight shows the data slice it is based on."
      />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {bundle.insights.map((insight, i) => (
          <InsightCard key={`${insight.title}-${i}`} insight={insight} index={i} />
        ))}
      </div>

      <div className="mt-8 grid gap-4 lg:grid-cols-3">
        <Card title="Seniority mix" subtitle="postings by classified level">
          <DonutChart data={bundle.jobsBySeniority} centerLabel="postings" />
        </Card>
        <Card title="Work mode" subtitle="postings by remote classification">
          <DonutChart data={bundle.jobsByRemoteType} centerLabel="postings" />
        </Card>
        <Card title="Employers" subtitle="postings per company in the feed">
          <BarList rows={bundle.jobsByCompany} />
        </Card>
      </div>

      <Card title="How insights are generated" className="mt-4">
        <div className="grid gap-4 text-sm text-slate-400 md:grid-cols-3">
          <div>
            <p className="label-muted mb-1">Evidence-based</p>
            <p>
              Every insight is tied to a concrete analytics slice (e.g. <code className="font-mono text-xs">top-skills</code>) so the claim can be audited against the numbers.
            </p>
          </div>
          <div>
            <p className="label-muted mb-1">Conservative labels</p>
            <p>
              Seniority, remote-work and employment-type values are only assigned when the title or description contains explicit signal; otherwise they stay <span className="font-mono text-xs">Unknown</span>.
            </p>
          </div>
          <div>
            <p className="label-muted mb-1">No fabricated fields</p>
            <p>
              Salary is surfaced only when a posting discloses a US base salary band; the pipeline never invents values.
            </p>
          </div>
        </div>
      </Card>
    </>
  );
}