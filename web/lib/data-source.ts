import type { SupabaseClient } from "@supabase/supabase-js";
import {
  computeAnalyticsBundle,
  computeInsights,
  computeJobsBySeniority,
  computeTopSkills,
  computeOverview,
  queryJobs,
} from "@/lib/analytics";
import { loadSeedJobs, loadSeedSkillCategories } from "@/lib/seed";
import { getSupabase } from "@/lib/supabase";
import type {
  AnalyticsBundle,
  AnalyticsOverview,
  CompanyStat,
  EmploymentStat,
  Insight,
  Job,
  JobsOverTimePoint,
  JobsResponse,
  LocationStat,
  RemoteStat,
  SeniorityStat,
  SkillBySeniority,
  SkillCombination,
  SkillTrendPoint,
  TopSkill,
} from "@/lib/types";

/**
 * Unified data-source adapter.
 *
 * - Supabase is used when SUPABASE_URL + SUPABASE_ANON_KEY are configured
 *   (server-side; anon key + RLS/GRANTs via the migration file).
 * - Otherwise the committed local seed snapshot (data/web_seed.json) is used
 *   so the app is fully functional with zero external configuration.
 */
type Row = Record<string, unknown>;

function toJob(row: Row, idx: number): Job {
  const raw = (key: string) => row[key];
  const str = (key: string, fallback: string | null = "") => {
    const v = raw(key);
    return v == null ? (fallback ?? "") : String(v);
  };
  const num = (key: string): number | null => {
    const v = raw(key);
    return v == null ? null : Number(v);
  };
  const arr = (key: string): string[] => {
    const v = raw(key);
    if (Array.isArray(v)) return v.map(String);
    if (typeof v === "string") {
      const trimmed = v.trim();
      if (trimmed.startsWith("{")) {
        return trimmed
          .replace(/[{}]/g, "")
          .split(",")
          .filter(Boolean);
      }
      return trimmed ? [trimmed] : [];
    }
    return [];
  };
  return {
    id: str("id", String(idx)),
    external_job_id: str("external_job_id", str("id")),
    title: str("title"),
    original_title: str("original_title", str("title")),
    company: str("company", "Unknown"),
    description: str("description"),
    job_url: str("job_url"),
    apply_url: str("apply_url"),
    employment_type: str("employment_type", "Unknown"),
    seniority: str("seniority", "Unknown"),
    remote_type: str("remote_type", "Unknown"),
    posted_at: str("posted_at", null),
    scraped_at: str("scraped_at", null),
    salary_min: num("salary_min"),
    salary_max: num("salary_max"),
    salary_currency: str("salary_currency", null),
    primary_location: str("primary_location", null),
    locations: arr("locations"),
    skills: arr("skills"),
  };
}

function analyse(filters: Record<string, string | undefined>): JobsResponse {
  const jobs = loadSeedJobs();
  const { jobs: page, total, page: current, pageSize } = queryJobs(jobs, filters);
  return {
    jobs: page,
    total,
    page: current,
    pageSize,
    filters: { ...filters },
    source: "local-seed",
  };
}

function seedJob(id: string): Job | null {
  return loadSeedJobs().find((j) => j.id === id) ?? null;
}

export function getSourceLabel(): string {
  return getSupabase() ? "supabase-postgres" : "local-seed";
}

export async function listJobs(
  filters: Record<string, string | undefined>,
): Promise<JobsResponse> {
  const supabase = getSupabase();
  if (!supabase) return analyse(filters);

  const page = Math.max(1, Number(filters.page ?? 1) || 1);
  const pageSize = Math.min(100, Math.max(1, Number(filters.pageSize ?? 25) || 25));
  const q = (filters.q ?? "").trim();

  let query = (supabase as unknown as SupabaseClient).from("analytics_jobs").select("*", { count: "exact" });
  const filtersOut: { [k: string]: string } = {};
  if (q) {
    query = query.or(`title.ilike.%${q}%,original_title.ilike.%${q}%,company.ilike.%${q}%`);
    filtersOut.q = q;
  }
  for (const [key, col] of [
    ["seniority", "seniority"],
    ["remote", "remote_type"],
    ["employment", "employment_type"],
    ["company", "company"],
    ["location", "primary_location"],
    ["skill", "skills"],
  ] as const) {
    const value = filters[key];
    if (value) {
      if (col === "skills") {
        query = query.contains("skills", [value]);
      } else {
        query = query.eq(col, value);
      }
      filtersOut[key] = value;
    }
  }
  const order = filters.sort === "title" ? "title" : filters.sort === "salary" ? "salary_max" : "posted_at";
  query = query.order(order, { ascending: order === "title" });

  const { data, error, count } = await query.range((page - 1) * pageSize, page * pageSize - 1);
  if (error) throw new Error(`supabase list jobs: ${error.message}`);

  return {
    jobs: (data ?? []).map((row, i) => toJob(row, i)),
    total: count ?? (data ?? []).length,
    page,
    pageSize,
    filters: filtersOut,
    source: "supabase-postgres",
  };
}

export async function getJob(id: string): Promise<Job | null> {
  const supabase = getSupabase();
  if (!supabase) return seedJob(id);
  const { data, error } = await (supabase as unknown as SupabaseClient)
    .from("analytics_jobs")
    .select("*")
    .eq("id", id)
    .limit(1);
  if (error) throw new Error(`supabase get job: ${error.message}`);
  if (!data || data.length === 0) return null;
  return toJob(data[0], 0);
}

export async function getAnalyticsBundle(): Promise<AnalyticsBundle> {
  const supabase = getSupabase();
  if (!supabase) {
    const jobs = loadSeedJobs();
    const bundle = computeAnalyticsBundle(jobs, "local-seed");
    bundle.topSkills = await enrichTopSkills(bundle.topSkills);
    return bundle;
  }

  const callers: Array<Promise<{ key: string; rows: Row[] }>> = [];
  const sections = [
    ["overview", "analytics_overview"],
    ["topSkills", "analytics_top_skills"],
    ["jobsBySeniority", "analytics_jobs_by_seniority"],
    ["jobsByEmploymentType", "analytics_jobs_by_employment_type"],
    ["jobsByRemoteType", "analytics_jobs_by_remote_type"],
    ["jobsByCompany", "analytics_jobs_by_company"],
    ["jobsByLocation", "analytics_jobs_by_location"],
    ["jobsOverTime", "analytics_jobs_over_time"],
    ["skillTrends", "analytics_skill_trends"],
    ["skillsBySeniority", "analytics_skills_by_seniority"],
    ["skillCombinations", "analytics_skill_combinations"],
  ] as const;
  for (const [key, view] of sections) {
    callers.push(
      (async () => {
        const { data, error } = await (supabase as unknown as SupabaseClient)
          .from(view)
          .select("*")
          .order("job_count", { ascending: false, nullsFirst: false });
        if (error && error.code !== "42P01") throw new Error(`${view}: ${error.message}`);
        return { key, rows: (data ?? []) as Row[] };
      })(),
    );
  }
  const results = await Promise.all(callers);
  const map = new Map(results.map((r) => [r.key, r.rows]));

  const first = (rows: Row[] | undefined): Row | undefined => rows?.[0];
  const overviewRow = first(map.get("overview"));
  const overview: AnalyticsOverview = {
    total_jobs: Number(overviewRow?.total_jobs ?? 0),
    total_companies: Number(overviewRow?.total_companies ?? 0),
    total_locations: Number(overviewRow?.total_locations ?? 0),
    total_skills: Number(overviewRow?.total_skills ?? 0),
    salary_disclosed_postings: Number(overviewRow?.salary_disclosed_postings ?? 0),
    salary_min: overviewRow?.salary_min == null ? null : Number(overviewRow.salary_min),
    salary_max: overviewRow?.salary_max == null ? null : Number(overviewRow.salary_max),
    salary_currency: overviewRow?.salary_currency == null ? null : String(overviewRow.salary_currency),
  };

  const kv = (rows: Row[] | undefined): { label: string; count: number }[] =>
    (rows ?? []).map((r) => ({
      label: String(r.label ?? r.key ?? r.name ?? r.company ?? r.seniority ?? r.location ?? r.remote_type ?? r.employment_type ?? r.month),
      count: Number(r.job_count ?? r.count ?? r.postings ?? 0),
    }));

  const topSkills: TopSkill[] = (map.get("topSkills") ?? []).map((r, i) => ({
    name: String(r.name ?? r.skill ?? ""),
    category: String(r.category ?? ""),
    job_count: Number(r.job_count ?? 0),
    percentage: Number(r.percentage ?? 0),
    rank: Number(r.rank ?? i + 1),
  }));

  const skillTrends: SkillTrendPoint[] = (map.get("skillTrends") ?? []).map((r) => ({
    month: String((r.month as string).slice(0, 7)),
    skill: String(r.skill ?? r.name ?? ""),
    job_count: Number(r.job_count ?? 0),
  }));

  const jobsOverTime: JobsOverTimePoint[] = (map.get("jobsOverTime") ?? []).map((r) => ({
    month: String((r.month as string).slice(0, 7)),
    job_count: Number(r.job_count ?? 0),
  }));

  const skillsBySeniority: SkillBySeniority[] = (map.get("skillsBySeniority") ?? []).map((r) => ({
    skill: String(r.skill ?? r.name ?? ""),
    seniority: String(r.seniority ?? ""),
    job_count: Number(r.job_count ?? 0),
  }));

  const skillCombinations: SkillCombination[] = (map.get("skillCombinations") ?? []).map((r) => ({
    skill_a: String(r.skill_a ?? ""),
    skill_b: String(r.skill_b ?? ""),
    job_count: Number(r.job_count ?? 0),
  }));

  const allJobs = await listJobs({ pageSize: "1000", sort: "posted_at" });
  const insights: Insight[] = computeInsights(allJobs.jobs);

  return {
    overview,
    topSkills,
    jobsBySeniority: kv(map.get("jobsBySeniority")) as SeniorityStat[],
    jobsByEmploymentType: kv(map.get("jobsByEmploymentType")) as EmploymentStat[],
    jobsByRemoteType: kv(map.get("jobsByRemoteType")) as RemoteStat[],
    jobsByCompany: kv(map.get("jobsByCompany")) as CompanyStat[],
    jobsByLocation: kv(map.get("jobsByLocation")) as LocationStat[],
    jobsOverTime,
    skillTrends,
    skillsBySeniority,
    skillCombinations,
    insights,
    generatedAt: new Date().toISOString(),
    source: "supabase-postgres",
  };
}

export async function getOverview(): Promise<AnalyticsOverview> {
  const supabase = getSupabase();
  if (!supabase) {
    const jobs = loadSeedJobs();
    return computeOverview(jobs);
  }
  const { data, error } = await (supabase as unknown as SupabaseClient)
    .from("analytics_overview")
    .select("*")
    .limit(1);
  if (error) return computeOverview(loadSeedJobs());
  const row = (data?.[0] ?? {}) as Row;
  return {
    total_jobs: Number(row.total_jobs ?? 0),
    total_companies: Number(row.total_companies ?? 0),
    total_locations: Number(row.total_locations ?? 0),
    total_skills: Number(row.total_skills ?? 0),
    salary_disclosed_postings: Number(row.salary_disclosed_postings ?? 0),
    salary_min: row.salary_min == null ? null : Number(row.salary_min),
    salary_max: row.salary_max == null ? null : Number(row.salary_max),
    salary_currency: row.salary_currency == null ? null : String(row.salary_currency),
  };
}

export async function getSkillCategories(): Promise<Record<string, string>> {
  const supabase = getSupabase();
  if (!supabase) return loadSeedSkillCategories();
  const { data, error } = await (supabase as unknown as SupabaseClient)
    .from("analytics_top_skills")
    .select("name, category");
  if (error || !data) return loadSeedSkillCategories();
  const categories: Record<string, string> = {};
  for (const row of data as Row[]) {
    if (row.name && row.category) categories[String(row.name)] = String(row.category);
  }
  return categories;
}

async function enrichTopSkills(skills: TopSkill[]): Promise<TopSkill[]> {
  const categories = await getSkillCategories();
  return skills.map((s) => ({
    ...s,
    category: categories[s.name] ?? s.category ?? "",
  }));
}

export async function getTopSkills(): Promise<TopSkill[]> {
  const supabase = getSupabase();
  const source: "seed" | "supabase" = supabase ? "supabase" : "seed";
  if (source === "seed") return enrichTopSkills(computeTopSkills(loadSeedJobs()));
  const { data, error } = await (supabase as unknown as SupabaseClient)
    .from("analytics_top_skills")
    .select("*")
    .order("rank");
  if (error) return enrichTopSkills(computeTopSkills(loadSeedJobs()));
  return (data ?? []).map((r, i) => ({
    name: String((r as Row).name ?? (r as Row).skill ?? ""),
    category: String((r as Row).category ?? ""),
    job_count: Number((r as Row).job_count ?? 0),
    percentage: Number((r as Row).percentage ?? 0),
    rank: Number((r as Row).rank ?? i + 1),
  }));
}

export async function getSeniority(): Promise<SeniorityStat[]> {
  const supabase = getSupabase();
  if (!supabase) return computeJobsBySeniority(loadSeedJobs());
  const { data, error } = await (supabase as unknown as SupabaseClient)
    .from("analytics_jobs_by_seniority")
    .select("*")
    .order("job_count", { ascending: false });
  if (error) return computeJobsBySeniority(loadSeedJobs());
  return (data ?? []).map((r) => ({
    label: String((r as Row).seniority ?? ""),
    count: Number((r as Row).job_count ?? 0),
  }));
}

function toRanked(
  rows: Row[] | undefined | null,
  labelKey: string,
): { label: string; count: number }[] {
  return (rows ?? []).map((r) => ({
    label: String(r[labelKey] ?? ""),
    count: Number(r.job_count ?? 0),
  }));
}

export async function getJobsByCompany(): Promise<CompanyStat[]> {
  const supabase = getSupabase();
  if (!supabase) {
    const { computeJobsByCompany } = await import("@/lib/analytics");
    return computeJobsByCompany(loadSeedJobs());
  }
  const { data, error } = await (supabase as unknown as SupabaseClient)
    .from("analytics_jobs_by_company")
    .select("*")
    .order("job_count", { ascending: false });
  if (error) return (await import("@/lib/analytics")).computeJobsByCompany(loadSeedJobs());
  return toRanked(data as Row[], "company");
}

export async function getJobsByLocation(): Promise<LocationStat[]> {
  const supabase = getSupabase();
  if (!supabase) {
    const { computeJobsByLocation } = await import("@/lib/analytics");
    return computeJobsByLocation(loadSeedJobs());
  }
  const { data, error } = await (supabase as unknown as SupabaseClient)
    .from("analytics_jobs_by_location")
    .select("*")
    .order("job_count", { ascending: false });
  if (error) return (await import("@/lib/analytics")).computeJobsByLocation(loadSeedJobs());
  return toRanked(data as Row[], "location");
}

function monthSeries(rows: Row[] | undefined | null, monthKey: string) {
  return (rows ?? []).map((r) => ({
    month: String(String(r[monthKey]).slice(0, 7)),
    job_count: Number(r.job_count ?? 0),
  }));
}

export async function getJobsOverTime(): Promise<JobsOverTimePoint[]> {
  const supabase = getSupabase();
  if (!supabase) {
    const { computeJobsOverTime } = await import("@/lib/analytics");
    return computeJobsOverTime(loadSeedJobs());
  }
  const { data, error } = await (supabase as unknown as SupabaseClient)
    .from("analytics_jobs_over_time")
    .select("*")
    .order("month");
  if (error) return (await import("@/lib/analytics")).computeJobsOverTime(loadSeedJobs());
  return monthSeries(data as Row[], "month");
}

export async function getSkillTrends(): Promise<SkillTrendPoint[]> {
  const supabase = getSupabase();
  if (!supabase) {
    const { computeSkillTrends } = await import("@/lib/analytics");
    return computeSkillTrends(loadSeedJobs());
  }
  const { data, error } = await (supabase as unknown as SupabaseClient)
    .from("analytics_skill_trends")
    .select("*")
    .order("month");
  if (error) return (await import("@/lib/analytics")).computeSkillTrends(loadSeedJobs());
  return (data ?? []).map((r) => ({
    month: String(String((r as Row).month).slice(0, 7)),
    skill: String((r as Row).skill ?? ""),
    job_count: Number((r as Row).job_count ?? 0),
  }));
}

export async function getSkillCombinations(): Promise<SkillCombination[]> {
  const supabase = getSupabase();
  if (!supabase) {
    const { computeSkillCombinations } = await import("@/lib/analytics");
    return computeSkillCombinations(loadSeedJobs());
  }
  const { data, error } = await (supabase as unknown as SupabaseClient)
    .from("analytics_skill_combinations")
    .select("*")
    .order("job_count", { ascending: false });
  if (error) return (await import("@/lib/analytics")).computeSkillCombinations(loadSeedJobs());
  return (data ?? []).map((r) => ({
    skill_a: String((r as Row).skill_a ?? ""),
    skill_b: String((r as Row).skill_b ?? ""),
    job_count: Number((r as Row).job_count ?? 0),
  }));
}

export async function getInsights(): Promise<Insight[]> {
  const supabase = getSupabase();
  if (!supabase) return computeInsights(loadSeedJobs());
  return computeInsights((await listJobs({ pageSize: "1000" })).jobs);
}

export { getSourceLabel as getSourceName };