import { readFileSync } from "node:fs";
import path from "node:path";
import type { Job } from "@/lib/types";

type SeatRecord = {
  id: number;
  external_job_id: string;
  title: string;
  original_title: string;
  description: string;
  employment_type: string | null;
  seniority: string | null;
  remote_type: string | null;
  job_url: string;
  apply_url: string | null;
  posted_at: string | null;
  scraped_at: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  source_id: string;
  company: { name: string } | null;
  locations: { display_name: string; rank?: number | null }[];
  skills: { name: string; category?: string | null }[];
};

function resolveSeedFile(): string {
  const candidates = [
    path.join(process.cwd(), "..", "data", "web_seed.json"),
    path.join(process.cwd(), "data", "web_seed.json"),
  ];
  for (const candidate of candidates) {
    if (readFileSync(candidate, "utf-8").length > 0) return candidate;
  }
  throw new Error("web_seed.json not found (data/web_seed.json)");
}

let bundleCache: { records: SeatRecord[] } | null = null;
let seedPath: string | null = null;

function loadBundle(): { records: SeatRecord[] } {
  if (bundleCache) return bundleCache;
  seedPath ??= resolveSeedFile();
  bundleCache = JSON.parse(readFileSync(seedPath, "utf-8")) as { records: SeatRecord[] };
  return bundleCache;
}

let jobCache: Job[] | null = null;

export function loadSeedJobs(): Job[] {
  if (jobCache) return jobCache;
  jobCache = loadBundle()
    .records.filter((r) => r && r.external_job_id && r.title)
    .map((r) => ({
      id: String(r.id),
      external_job_id: r.external_job_id,
      title: r.title,
      original_title: r.original_title,
      company: r.company?.name ?? "Unknown",
      description: r.description ?? "",
      job_url: r.job_url,
      apply_url: r.apply_url ?? "",
      employment_type: r.employment_type ?? "Unknown",
      seniority: r.seniority ?? "Unknown",
      remote_type: r.remote_type ?? "Unknown",
      posted_at: r.posted_at,
      scraped_at: r.scraped_at,
      salary_min: r.salary_min,
      salary_max: r.salary_max,
      salary_currency: r.salary_currency,
      primary_location: r.locations[0]?.display_name ?? null,
      locations: r.locations.map((l) => l.display_name),
      skills: r.skills.map((s) => s.name),
    }));
  return jobCache;
}

/** Skill name -> category, e.g. {"Python": "Language", "Docker": "DevOps & Infrastructure"}. */
export function loadSeedSkillCategories(): Record<string, string> {
  const categories: Record<string, string> = {};
  for (const record of loadBundle().records) {
    for (const skill of record.skills ?? []) {
      if (skill.name && skill.category) categories[skill.name] = skill.category;
    }
  }
  return categories;
}