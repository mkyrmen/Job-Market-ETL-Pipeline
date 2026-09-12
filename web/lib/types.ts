export type Job = {
  id: string;
  external_job_id: string;
  title: string;
  original_title: string;
  company: string;
  description: string;
  job_url: string;
  apply_url: string;
  employment_type: string;
  seniority: string;
  remote_type: string;
  posted_at: string | null;
  scraped_at: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  primary_location: string | null;
  locations: string[];
  skills: string[];
};

export type JobFilters = {
  q?: string;
  seniority?: string;
  remote?: string;
  employment?: string;
  company?: string;
  location?: string;
  skill?: string;
  sort?: "posted_at" | "salary" | "title";
  page?: number;
  pageSize?: number;
};

export type JobsResponse = {
  jobs: Job[];
  total: number;
  page: number;
  pageSize: number;
  filters: JobFilters;
  source: string;
};

export type AnalyticsOverview = {
  total_jobs: number;
  total_companies: number;
  total_locations: number;
  total_skills: number;
  salary_disclosed_postings: number;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
};

export type RankedValue = {
  label: string;
  count: number;
};

export type TopSkill = {
  name: string;
  category: string;
  job_count: number;
  percentage: number;
  rank: number;
};

export type SkillTrendPoint = {
  month: string;
  skill: string;
  job_count: number;
};

export type JobsOverTimePoint = {
  month: string;
  job_count: number;
};

export type SkillBySeniority = {
  skill: string;
  seniority: string;
  job_count: number;
};

export type SkillCombination = {
  skill_a: string;
  skill_b: string;
  job_count: number;
};

export type Insight = {
  title: string;
  detail: string;
  category: string;
  basis: string;
  severity: "info" | "positive" | "warning" | "action";
};

export type CompanyStat = RankedValue;
export type LocationStat = RankedValue;
export type SeniorityStat = RankedValue;
export type RemoteStat = RankedValue;
export type EmploymentStat = RankedValue;

export type AnalyticsBundle = {
  overview: AnalyticsOverview;
  topSkills: TopSkill[];
  jobsBySeniority: SeniorityStat[];
  jobsByCompany: CompanyStat[];
  jobsByLocation: LocationStat[];
  jobsByRemoteType: RemoteStat[];
  jobsByEmploymentType: EmploymentStat[];
  jobsOverTime: JobsOverTimePoint[];
  skillTrends: SkillTrendPoint[];
  skillsBySeniority: SkillBySeniority[];
  skillCombinations: SkillCombination[];
  insights: Insight[];
  generatedAt: string;
  source: string;
};

export type ApiError = {
  error: string;
};

export function formatSalary(job: Pick<Job, "salary_min" | "salary_max" | "salary_currency">): string | null {
  if (job.salary_min == null && job.salary_max == null) return null;
  const currency = job.salary_currency ?? "USD";
  const symbol = currency === "USD" ? "$" : `${currency} `;
  const fmt = (n: number) =>
    symbol + n.toLocaleString("en-US", { maximumFractionDigits: 0 });
  if (job.salary_min != null && job.salary_max != null) {
    return `${fmt(job.salary_min)} - ${fmt(job.salary_max)}`;
  }
  if (job.salary_min != null) return `${fmt(job.salary_min)}+`;
  return fmt(job.salary_max as number);
}

export function monthKey(iso: string | null): string {
  if (!iso) return "Unknown";
  return iso.slice(0, 7);
}

export function monthLabel(key: string): string {
  if (key === "Unknown") return "Unknown";
  const [y, m] = key.split("-").map(Number);
  const names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `${names[(m ?? 1) - 1]} ${y}`;
}