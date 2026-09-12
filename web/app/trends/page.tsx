import { getAnalyticsBundle } from "@/lib/data-source";
import { PageHeader } from "@/components/Card";
import { Card } from "@/components/Card";
import { OverTimeAreaChart, SkillTrendLineChart } from "@/components/Charts";
import { BarList } from "@/components/BarList";

export const dynamic = "force-dynamic";

export default async function TrendsPage() {
  const bundle = await getAnalyticsBundle();
  const seniorityOverTime = bundle.skillsBySeniority;

  return (
    <>
      <PageHeader
        title="Market trends"
        subtitle="How the hiring signal from Google Careers has moved over time."
      />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Postings per month" subtitle="by the first published date in each posting">
          <OverTimeAreaChart data={bundle.jobsOverTime} />
        </Card>
        <Card title="Top skills over time" subtitle="months a top-demand skill appeared in postings">
          <SkillTrendLineChart data={bundle.skillTrends} />
        </Card>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card title="Work mode mix" subtitle="remote / hybrid / onsite labels">
          <BarList rows={bundle.jobsByRemoteType} />
        </Card>
        <Card title="Employment type" subtitle="how the roles are offered">
          <BarList rows={bundle.jobsByEmploymentType} />
        </Card>
        <Card title="Most active hubs" subtitle="locations with the most postings">
          <BarList rows={bundle.jobsByLocation.slice(0, 10)} />
        </Card>
      </div>

      <Card
        title="Skills by seniority"
        subtitle="where each top skill appears across seniority bands (hint on where demand concentrates)"
        className="mt-4"
      >
        {seniorityOverTime.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-500">No seniority-labelled skill data yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-ink-700 text-left text-xs uppercase tracking-wider text-slate-500">
                  <th className="py-2 pr-4 font-medium">Skill</th>
                  {Array.from(new Set(seniorityOverTime.map((row) => row.seniority)))
                    .sort()
                    .map((band) => (
                      <th key={band} className="py-2 pr-4 text-right font-medium">{band}</th>
                    ))}
                </tr>
              </thead>
              <tbody>
                {Array.from(
                  new Map(seniorityOverTime.map((row) => [row.skill, row])).keys(),
                )
                  .slice(0, 20)
                  .map((skill) => {
                    const cells = seniorityOverTime.filter((row) => row.skill === skill);
                    return (
                      <tr key={skill} className="border-b border-ink-800/60 last:border-0 hover:bg-ink-800/30">
                        <td className="py-2 pr-4 font-medium text-slate-200">{skill}</td>
                        {Array.from(new Set(seniorityOverTime.map((row) => row.seniority)))
                          .sort()
                          .map((band) => {
                            const match = cells.find((row) => row.seniority === band);
                            return (
                              <td key={band} className="py-2 pr-4 text-right font-mono text-xs text-slate-400">
                                {match?.job_count ?? 0}
                              </td>
                            );
                          })}
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}