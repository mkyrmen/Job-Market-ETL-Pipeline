import type {
  AnalyticsBundle,
  AnalyticsOverview,
  CompanyStat,
  EmploymentStat,
  Insight,
  Job,
  JobsOverTimePoint,
  LocationStat,
  RemoteStat,
  SeniorityStat,
  SkillBySeniority,
  SkillCombination,
  SkillTrendPoint,
  TopSkill,
} from "@/lib/types";
import { monthKey } from "@/lib/types";

function sortDescription(rows: { label: string; count: number }[]) {
  return rows.sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
}

export function computeOverview(jobs: Job[]): AnalyticsOverview {
  const companies = new Set(jobs.map((j) => j.company).filter(Boolean));
  const locations = new Set(jobs.flatMap((j) => j.locations).filter(Boolean));
  const skills = new Set(jobs.flatMap((j) => j.skills).filter(Boolean));
  const salaried = jobs.filter((j) => j.salary_min != null && j.salary_max != null);
  const min = salaried.length ? Math.min(...salaried.map((j) => j.salary_min as number)) : null;
  const max = salaried.length ? Math.max(...salaried.map((j) => j.salary_max as number)) : null;
  const currency = salaried[0]?.salary_currency ?? null;
  return {
    total_jobs: jobs.length,
    total_companies: companies.size,
    total_locations: locations.size,
    total_skills: skills.size,
    salary_disclosed_postings: salaried.length,
    salary_min: min,
    salary_max: max,
    salary_currency: currency,
  };
}

export function computeTopSkills(jobs: Job[]): TopSkill[] {
  const total = Math.max(1, jobs.length);
  const skills = new Map<string, number>();
  for (const job of jobs) {
    for (const skill of new Set(job.skills)) {
      skills.set(skill, (skills.get(skill) ?? 0) + 1);
    }
  }
  return sortDescription(
    [...skills.entries()].map(([name, count], i) => ({
      label: name,
      count,
    })),
  )
    .map((row, i) => ({
      name: row.label,
      category: "",
      job_count: row.count,
      percentage: Math.round((row.count / total) * 1000) / 10,
      rank: i + 1,
    }))
    .slice(0, 60);
}

function labelled<T>(jobs: Job[], pick: (j: Job) => string): Map<string, number> {
  const counts = new Map<string, number>();
  for (const job of jobs) {
    const label = pick(job);
    if (!label || label === "Unknown") continue;
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }
  return counts;
}

export function computeJobsBySeniority(jobs: Job[]): SeniorityStat[] {
  return sortDescription(
    [...labelled(jobs, (j) => j.seniority)].map(([label, count]) => ({ label, count })),
  );
}

export function computeJobsByCompany(jobs: Job[]): CompanyStat[] {
  return sortDescription(
    [...labelled(jobs, (j) => j.company)].map(([label, count]) => ({ label, count })),
  );
}

export function computeJobsByLocation(jobs: Job[]): LocationStat[] {
  const counts = new Map<string, number>();
  for (const job of jobs) {
    for (const loc of job.locations) {
      counts.set(loc, (counts.get(loc) ?? 0) + 1);
    }
  }
  return sortDescription([...counts].map(([label, count]) => ({ label, count })));
}

export function computeJobsByRemoteType(jobs: Job[]): RemoteStat[] {
  return sortDescription(
    [...labelled(jobs, (j) => j.remote_type)].map(([label, count]) => ({ label, count })),
  );
}

export function computeJobsByEmploymentType(jobs: Job[]): EmploymentStat[] {
  return sortDescription(
    [...labelled(jobs, (j) => j.employment_type)].map(([label, count]) => ({ label, count })),
  );
}

export function computeJobsOverTime(jobs: Job[]): JobsOverTimePoint[] {
  const counts = new Map<string, number>();
  for (const job of jobs) {
    const key = monthKey(job.posted_at);
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([month, job_count]) => ({ month, job_count }))
    .sort((a, b) => a.month.localeCompare(b.month));
}

const TREND_TOP_N = 8;

export function computeSkillTrends(jobs: Job[], topN = TREND_TOP_N): SkillTrendPoint[] {
  const bySkill = new Map<string, Map<string, number>>();
  for (const job of jobs) {
    const key = monthKey(job.posted_at);
    for (const skill of new Set(job.skills)) {
      if (!bySkill.has(skill)) bySkill.set(skill, new Map());
      const m = bySkill.get(skill)!;
      m.set(key, (m.get(key) ?? 0) + 1);
    }
  }
  const popularity = [...bySkill.entries()]
    .map(([skill, m]) => [skill, [...m.values()].reduce((a, b) => a + b, 0)] as const)
    .sort((a, b) => b[1] - a[1]);
  const selected = new Set(popularity.slice(0, topN).map(([skill]) => skill));
  const points: SkillTrendPoint[] = [];
  for (const [skill, months] of bySkill) {
    if (!selected.has(skill)) continue;
    for (const [month, job_count] of months) {
      points.push({ month, skill, job_count });
    }
  }
  return points.sort((a, b) => a.month.localeCompare(b.month));
}

export function computeSkillsBySeniority(jobs: Job[], topSkills = 12): SkillBySeniority[] {
  const skills = computeTopSkills(jobs).slice(0, topSkills).map((s) => s.name);
  const set = new Set(skills);
  const rows: SkillBySeniority[] = [];
  for (const job of jobs) {
    for (const skill of new Set(job.skills)) {
      if (!set.has(skill) || job.seniority === "Unknown") continue;
      rows.push({ skill, seniority: job.seniority, job_count: 1 });
    }
  }
  return rows;
}

export function computeSkillCombinations(jobs: Job[], topN = 10): SkillCombination[] {
  const pairs = new Map<string, number>();
  const popularity = new Map<string, number>();
  for (const job of jobs) {
    const buckets = new Map<string, number>();
    for (const skill of new Set(job.skills)) {
      buckets.set(skill, 1);
      popularity.set(skill, (popularity.get(skill) ?? 0) + 1);
    }
    const names = [...buckets.keys()].sort();
    for (let i = 0; i < names.length; i++) {
      for (let j = i + 1; j < names.length; j++) {
        const key = `${names[i]}\u0000${names[j]}`;
        pairs.set(key, (pairs.get(key) ?? 0) + 1);
      }
    }
  }
  return [...pairs.entries()]
    .map(([key, job_count]) => {
      const [skill_a, skill_b] = key.split("\u0000");
      return { skill_a, skill_b, job_count };
    })
    .sort((a, b) => b.job_count - a.job_count)
    .slice(0, topN);
}

export function computeInsights(jobs: Job[]): Insight[] {
  const insights: Insight[] = [];
  if (jobs.length === 0) {
    return [
      {
        title: "Awaiting data",
        detail:
          "Run the ETL pipeline (python -m src.main run) to start populating the jobs database.",
        category: "Pipeline",
        basis: "Empty dataset",
        severity: "info",
      },
    ];
  }
  const overview = computeOverview(jobs);
  const topSkills = computeTopSkills(jobs);
  const byCompany = computeJobsByCompany(jobs);
  const bySeniority = computeJobsBySeniority(jobs);
  const byLocation = computeJobsByLocation(jobs);
  const combos = computeSkillCombinations(jobs);

  if (topSkills.length > 0) {
    const first = topSkills[0];
    insights.push({
      title: `${first.name} is the most demanded skill`,
      detail: `${first.name} appears in ${first.job_count} of ${overview.total_jobs} postings (${first.percentage}%).`,
      category: "Skills",
      basis: "top-skills",
      severity: first.percentage >= 0.4 ? "action" : "positive",
    });
  }

  const single = byCompany.find((c) => c.count === overview.total_jobs);
  if (single) {
    insights.push({
      title: `${single.label} dominates the feed`,
      detail: `All ${overview.total_jobs} tracked postings are from ${single.label}, so company comparisons are not possible yet.`,
      category: "Companies",
      basis: "jobs-by-company",
      severity: "warning",
    });
  }

  const salaried = overview.salary_disclosed_postings;
  if (salaried > 0 && overview.salary_max != null && overview.salary_min != null) {
    insights.push({
      title: `Salary range spans ${overview.salary_currency ?? "USD"} ${overview.salary_min.toLocaleString()} - ${overview.salary_max.toLocaleString()}`,
      detail: `${salaried} postings (${Math.round((salaried / overview.total_jobs) * 100)}%) disclose a US base salary band.`,
      category: "Compensation",
      basis: "overview",
      severity: "positive",
    });
  } else if (overview.total_jobs > 0) {
    insights.push({
      title: "No salary bands disclosed",
      detail: `None of the ${overview.total_jobs} postings carry a parsable US base salary range.`,
      category: "Compensation",
      basis: "overview",
      severity: "warning",
    });
  }

  const unknownSeniority = bySeniority.find((s) => s.label === "Unknown")?.count ?? 0;
  if (unknownSeniority / overview.total_jobs > 0.3) {
    insights.push({
      title: "Many postings have unknown seniority",
      detail: `${unknownSeniority} of ${overview.total_jobs} postings (${Math.round((unknownSeniority / overview.total_jobs) * 100)}%) carry no seniority signal; titles use Google's neutral wording.`,
      category: "Classification",
      basis: "jobs-by-seniority",
      severity: "info",
    });
  }

  if (combos.length > 0) {
    const top = combos[0];
    insights.push({
      title: `${top.skill_a} + ${top.skill_b} is the top pairing`,
      detail: `${top.job_count} postings mention both skills together, indicating an in-demand combination.`,
      category: "Skills",
      basis: "skill-combinations",
      severity: "positive",
    });
  }

  const topLocation = byLocation[0];
  if (topLocation) {
    insights.push({
      title: `${topLocation.label} is the top hiring hub`,
      detail: `${topLocation.count} postings list this location (${Math.round((topLocation.count / overview.total_jobs) * 100)}%).`,
      category: "Geography",
      basis: "jobs-by-location",
      severity: "info",
    });
  }

  return insights;
}

export function computeAnalyticsBundle(jobs: Job[], source: string): AnalyticsBundle {
  return {
    overview: computeOverview(jobs),
    topSkills: computeTopSkills(jobs),
    jobsBySeniority: computeJobsBySeniority(jobs),
    jobsByCompany: computeJobsByCompany(jobs),
    jobsByLocation: computeJobsByLocation(jobs),
    jobsByRemoteType: computeJobsByRemoteType(jobs),
    jobsByEmploymentType: computeJobsByEmploymentType(jobs),
    jobsOverTime: computeJobsOverTime(jobs),
    skillTrends: computeSkillTrends(jobs),
    skillsBySeniority: computeSkillsBySeniority(jobs),
    skillCombinations: computeSkillCombinations(jobs),
    insights: computeInsights(jobs),
    generatedAt: new Date().toISOString(),
    source,
  };
}

function filterJobs(jobs: Job[], filters: Record<string, string | undefined>): Job[] {
  const q = (filters.q ?? "").trim().toLowerCase();
  const seniority = filters.seniority ?? "";
  const remote = filters.remote ?? "";
  const employment = filters.employment ?? "";
  const company = filters.company ?? "";
  const location = filters.location ?? "";
  const skill = filters.skill ?? "";

  return jobs.filter((j) => {
    if (q && ![j.title, j.original_title, j.company, j.description].some((f) => (f ?? "").toLowerCase().includes(q))) {
      return false;
    }
    if (seniority && j.seniority !== seniority) return false;
    if (remote && j.remote_type !== remote) return false;
    if (employment && j.employment_type !== employment) return false;
    if (company && j.company !== company) return false;
    if (location && !j.locations.some((l) => l.toLowerCase().includes(location.toLowerCase()))) return false;
    if (skill && !j.skills.includes(skill)) return false;
    return true;
  });
}

export function queryJobs(jobs: Job[], filters: Record<string, string | undefined>) {
  const page = Math.max(1, Number(filters.page ?? 1) || 1);
  const pageSize = Math.min(100, Math.max(1, Number(filters.pageSize ?? 25) || 25));
  const sort = filters.sort ?? "posted_at";

  const filtered = filterJobs(jobs, filters);
  const sorted = [...filtered].sort((a, b) => {
    if (sort === "title") return a.title.localeCompare(b.title);
    if (sort === "salary") {
      const am = a.salary_max ?? a.salary_min ?? 0;
      const bm = b.salary_max ?? b.salary_min ?? 0;
      return bm - am;
    }
    return (b.posted_at ?? "").localeCompare(a.posted_at ?? "");
  });
  const start = (page - 1) * pageSize;
  return {
    jobs: sorted.slice(start, start + pageSize),
    total: filtered.length,
    page,
    pageSize,
  };
}