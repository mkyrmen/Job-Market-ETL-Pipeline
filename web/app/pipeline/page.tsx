import { PageHeader } from "@/components/Card";
import { Card } from "@/components/Card";

const steps = [
  {
    phase: "Extract",
    label: "src/extract/google_careers.py",
    blurb:
      "HTTPS requests to the Google Careers search page. The structured AF_initDataCallback JSON payload is parsed directly - no browser required. Pagination follows page_number; retries back off on failures.",
  },
  {
    phase: "Validate",
    label: "src/validation/validators.py",
    blurb:
      "Raw records are checked for stable identity fields (title, external job id). Invalid rows are dropped and counted, never silently merged.",
  },
  {
    phase: "Transform",
    label: "src/transform/",
    blurb:
      "Titles are normalised (Sr. -> Senior), companies and locations are standardised, skills are extracted from a curated dictionary (Python, PostgreSQL, Kubernetes, ...), salary bands parsed when disclosed, and seniority/remote/employment classified conservatively.",
  },
  {
    phase: "Deduplicate",
    label: "src/transform/dedupe.py",
    blurb:
      "A SHA-256 fingerprint over stable fields (source, url, title, company, locations) - timestamps are excluded so the same posting never creates a duplicate on re-runs.",
  },
  {
    phase: "Load",
    label: "src/load/sqlite_loader.py · supabase_loader.py",
    blurb:
      "Upserts into a normalised relational schema (jobs, companies, locations, skills, job_locations, job_skills, extraction_runs). The same pipeline writes to Supabase PostgreSQL through the REST API.",
  },
  {
    phase: "Analyse & serve",
    label: "src/analytics/ · web/app/api",
    blurb:
      "SQLite analytics views + a Python report, or Supabase analytics views served by the Next.js API routes - the same shapes either way, so the web app is agnostic to where data lives.",
  },
];

const commands = [
  { cmd: "python -m src.main run", note: "Run one full ETL pass against Google Careers" },
  { cmd: "python -m src.main run --query \"Data Analyst\" --limit 50 --dry-run", note: "Extract and transform without writing to the database" },
  { cmd: "python -m src.main analyze", note: "Print the analytics report from the local database" },
  { cmd: "python -m src.main migrate", note: "Import the legacy job database and preserve the archive" },
  { cmd: "python scripts/seed_database.py", note: "Seed the local database from data/raw/google_careers_sample.json (idempotent)" },
  { cmd: "python scripts/export_web_seed.py", note: "Re-generate data/web_seed.json for the web app" },
  { cmd: "npm run dev --prefix web", note: "Launch the Next.js dashboard locally" },
];

export default function PipelinePage() {
  return (
    <>
      <PageHeader
        title="The data pipeline"
        subtitle="How raw job postings become market intelligence - and how to operate it."
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {steps.map((step, i) => (
          <Card
            key={step.phase}
            title={`${i + 1}. ${step.phase}`}
            subtitle={step.label}
          >
            <p className="text-sm leading-relaxed text-slate-400">{step.blurb}</p>
          </Card>
        ))}
      </div>

      <Card title="Operator commands" className="mt-4" subtitle="run from the repository root">
        <div className="space-y-2">
          {commands.map(({ cmd, note }) => (
            <div
              key={cmd}
              className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 rounded-lg border border-ink-700 bg-ink-850/60 px-4 py-2.5"
            >
              <code className="font-mono text-sm text-emerald-400">{cmd}</code>
              <span className="text-xs text-slate-500">{note}</span>
            </div>
          ))}
        </div>
      </Card>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card title="Schema" subtitle="normalised relational core">
          <pre className="scrollbar-thin overflow-x-auto rounded-lg bg-ink-950/70 p-4 font-mono text-xs leading-relaxed text-slate-400">
{`jobs            (id, source_id, external_job_id, title,
                 original_title, description, seniority,
                 remote_type, employment_type, salary_min/max,
                 salary_currency, job_url, apply_url,
                 posted_at, scraped_at, dedupe_key [unique])
companies       (id, name, normalized_name, external_id)
locations       (id, display_name, city, state, country_code,
                 normalized_key [unique])
skills          (id, name [unique], category)
job_locations   (job_id, location_id, rank)
job_skills      (job_id, skill_id, matched_text)
extraction_runs (id, source_id, query, status,
                 extracted/inserted/skipped, started/finished)`}
          </pre>
        </Card>
        <Card title="Deployment notes" subtitle="where the pieces run">
          <ul className="space-y-3 text-sm leading-relaxed text-slate-400">
            <li>
              <span className="label-muted block">ETL</span>
              Run on a schedule (cron / GitHub Actions) or manually. Writes to the local
              SQLite database or to Supabase PostgreSQL via the REST loader.
            </li>
            <li>
              <span className="label-muted block">Database</span>
              Supabase: apply <code className="font-mono text-xs text-emerald-400">supabase/migrations/0001_init.sql</code> once. It creates the schema plus the analytics views the API reads.
            </li>
            <li>
              <span className="label-muted block">Web</span>
              Next.js in <code className="font-mono text-xs text-emerald-400">web/</code>. With
              <code className="font-mono text-xs text-emerald-400"> SUPABASE_URL </code> and
              <code className="font-mono text-xs text-emerald-400"> SUPABASE_ANON_KEY </code> set it
              queries the analytics views; otherwise it serves the committed seed snapshot so it
              always works.
            </li>
          </ul>
        </Card>
      </div>
    </>
  );
}