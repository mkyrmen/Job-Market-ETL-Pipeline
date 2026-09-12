import Link from "next/link";
import { getAnalyticsBundle, getSkillCategories } from "@/lib/data-source";
import { PageHeader } from "@/components/Card";
import { Card } from "@/components/Card";
import { BarList } from "@/components/BarList";

export const dynamic = "force-dynamic";

export default async function SkillsPage() {
  const bundle = await getAnalyticsBundle();
  const categories = await getSkillCategories();

  const byCategory = new Map<string, number>();
  for (const skill of bundle.topSkills) {
    const category = skill.category || categories[skill.name] || "Other";
    byCategory.set(category, (byCategory.get(category) ?? 0) + skill.job_count);
  }
  const categoryRows = [...byCategory.entries()]
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count);

  return (
    <>
      <PageHeader
        title="Skills intelligence"
        subtitle="The most demanded technologies and how they combine in Google Careers postings."
      />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card
          title="Demand by category"
          subtitle="postings referencing skills in each bucket"
        >
          <BarList rows={categoryRows.slice(0, 12)} />
        </Card>
        <Card
          title="Top skill pairings"
          subtitle="skills frequently mentioned together"
          className="lg:col-span-2"
        >
          <div className="space-y-2">
            {bundle.skillCombinations.map((combo, i) => {
              const percent = bundle.overview.total_jobs
                ? Math.round((combo.job_count / bundle.overview.total_jobs) * 100)
                : 0;
              return (
                <div
                  key={`${combo.skill_a}-${combo.skill_b}`}
                  className="flex items-center justify-between gap-4 rounded-lg border border-ink-700 bg-ink-850/60 px-4 py-2.5"
                >
                  <div className="flex items-center gap-2 text-sm">
                    <span className="font-mono text-xs text-slate-500">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <Link
                      href={`/jobs?skill=${encodeURIComponent(combo.skill_a)}`}
                      className="font-medium text-emerald-400 hover:text-emerald-300"
                    >
                      {combo.skill_a}
                    </Link>
                    <span className="text-slate-600">+</span>
                    <Link
                      href={`/jobs?skill=${encodeURIComponent(combo.skill_b)}`}
                      className="font-medium text-teal-400 hover:text-teal-300"
                    >
                      {combo.skill_b}
                    </Link>
                  </div>
                  <span className="shrink-0 font-mono text-xs text-slate-500">
                    {combo.job_count} jobs · {percent}%
                  </span>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      <Card
        title="Full skill ranking"
        subtitle="every skill the extractor can identify, ranked by posting share"
        className="mt-4"
      >
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-ink-700 text-left text-xs uppercase tracking-wider text-slate-500">
                <th className="py-2 pr-4 font-medium">Rank</th>
                <th className="py-2 pr-4 font-medium">Skill</th>
                <th className="py-2 pr-4 font-medium">Category</th>
                <th className="py-2 pr-4 text-right font-medium">Postings</th>
                <th className="py-2 text-right font-medium">Share</th>
              </tr>
            </thead>
            <tbody>
              {bundle.topSkills.map((skill) => (
                <tr key={skill.name} className="border-b border-ink-800/60 last:border-0 hover:bg-ink-800/30">
                  <td className="py-2 pr-4 font-mono text-xs text-slate-500">{skill.rank}</td>
                  <td className="max-w-[16rem] truncate py-2 pr-4">
                    <Link
                      href={`/jobs?skill=${encodeURIComponent(skill.name)}`}
                      className="font-medium text-slate-200 hover:text-emerald-300"
                    >
                      {skill.name}
                    </Link>
                  </td>
                  <td className="py-2 pr-4 text-xs text-slate-500">
                    {skill.category || categories[skill.name] || "—"}
                  </td>
                  <td className="py-2 pr-4 text-right font-mono text-xs text-slate-400">
                    {skill.job_count.toLocaleString()}
                  </td>
                  <td className="py-2 text-right font-mono text-xs text-emerald-400">
                    {skill.percentage}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}