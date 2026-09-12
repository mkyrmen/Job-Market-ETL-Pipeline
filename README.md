# Job Market Intelligence Platform (JMIP)

An end-to-end **job market ETL pipeline and analytics dashboard** that watches
Google Careers postings and turns them into market intelligence on in-demand
skills, seniority levels, geography, remote work, and compensation.

The platform has two halves that share one codebase:

1. **Python ETL core** (`src/`) — scrapes, validates, normalizes, deduplicates,
   and loads structured job data into a relational database (local SQLite
   during development, Supabase/PostgreSQL in production), then computes
   SQL-driven analytics and auto-generated insights.
2. **Web dashboard** (`web/`) — a Next.js server-rendered application with a
   job explorer, skill analytics, market trends, and an insights feed. It runs
   fully offline against a committed data snapshot, or live against Supabase.

---

## Table of contents

- [Features](#features)
- [Architecture](#architecture)
- [Repository layout](#repository-layout)
- [Tech stack](#tech-stack)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [CLI reference](#cli-reference)
- [Data sources & extraction](#data-sources--extraction)
- [The transformation stage](#the-transformation-stage)
- [Deduplication](#deduplication)
- [Persistence & database schema](#persistence--database-schema)
- [Analytics engine & insights](#analytics-engine--insights)
- [Reporting artifacts (pandas)](#reporting-artifacts-pandas)
- [Web dashboard](#web-dashboard)
- [Supabase setup (production persistence)](#supabase-setup-production-persistence)
- [Deploy to Vercel](#deploy-to-vercel)
- [Helper scripts](#helper-scripts)
- [Testing](#testing)
- [Migrating the legacy scraper database](#migrating-the-legacy-scraper-database)
- [Roadmap](#roadmap)

---

## Features

**Extraction**
- Scrapes Google Careers search results **without a browser, CAPTCHAs, or
  anti-bot bypass** — polite HTTPS requests against the public site, parsing
  the server-rendered `AF_initDataCallback` (`ds:1`) JSON payload.
- Structured fields: numeric job id, title, company + company UUID, structured
  locations (city / state / country code), HTML description, overview,
  qualifications, additional qualifications, apply URL, and publish timestamps.
- Automatic pagination across result pages with in-run de-duplication.
- Optional **Selenium** fallback transport for browser-driven extraction.
- File-based sources (`json` / `csv`) so local and offline analysis is possible.

**Validation & transformation**
- Pydantic schema validation that reports and drops malformed records.
- HTML → clean-text cleaning with boilerplate removal.
- Title / company / location / URL normalization (including inferred country
  codes from display names).
- Evidence-based classifiers for **seniority**, **remote type**, and
  **employment type** — every label derived from explicit text signals.
- **Skill extraction** driven by a maintainable dictionary of aliases → canonical
  names → categories (languages, databases, frameworks, cloud, ML, data, DevOps,
  and more), matched case-insensitively with word boundaries.
- **Salary extraction** for disclosed US base-salary bands.

**Data quality**
- Deterministic **dedupe fingerprint** (SHA-256 over stable identity fields)
  that survives re-scraping — timestamps and scrape metadata are excluded.
- Duplicate prevention enforced in-memory *and* by `UNIQUE` database constraints
  (`dedupe_key`, and `(source_id, external_job_id)`).
- `extraction_runs` bookkeeping table records every pipeline run.

**Analytics**
- SQL-aggregated overview, distribution by seniority / employment type /
  remote type, hiring hubs, top skills, skill co-occurrence, skill-by-seniority,
  skill trends, jobs over time, and seniority over time.
- **Auto-generated insights** — every insight is derived from a real query and
  carries the data slice (`basis`) it is based on.

**Presentation**
- A production-grade Next.js **App Router** dashboard with a job explorer,
  per-job pages, skills explorer, market trends, and an insights feed.
- Works with **zero configuration** using a committed data snapshot, or live
  against Supabase when credentials are present.

---

## Architecture

```
                         ┌─────────────────────────────────────────────┐
                         │               DATA SOURCES                  │
                         │   Google Careers (HTTP/Selenium) · JSON/CSV │
                         └──────────────────────┬──────────────────────┘
                                                │
                         ┌──────────────────────▼──────────────────────┐
                         │  EXTRACT   (src/extract/*)                  │
                         │  GoogleCareersExtractor · FileLoader         │
                         └──────────────────────┬──────────────────────┘
                                                │ raw records (dicts)
                         ┌──────────────────────▼──────────────────────┐
                         │  VALIDATE  (src/validation/validators.py)    │
                         │  Pydantic RawRecord; malformed rows dropped  │
                         └──────────────────────┬──────────────────────┘
                                                │ valid RawRecords
                         ┌──────────────────────▼──────────────────────┐
                         │  TRANSFORM (src/transform/*)                 │
                         │  clean → normalize → classify → skills →    │
                         │  salary → dedupe-key                         │
                         └──────────────────────┬──────────────────────┘
                                                │ JobRecord (canonical model)
                         ┌──────────────────────▼──────────────────────┐
                         │  LOAD     (src/load/*)                       │
                         │  SQLiteLoader  ·  SupabaseLoader             │
                         └───────┬──────────────────────────────┬───────┘
                                 │                              │
                 ┌───────────────▼──────────────┐  ┌────────────▼───────────────┐
                 │  SQLite (dev/staging)        │  │  Supabase / PostgreSQL     │
                 │  data/jobs_database.db       │  │  same normalised schema     │
                 └───────────────┬──────────────┘  └────────────┬───────────────┘
                                 │                              │
                         ┌───────▼───────┐            ┌──────────▼──────────┐
                         │  ANALYTICS    │            │  ANALYTICS VIEWS     │
                         │  AnalyticsEngine              (Postgres)          │
                         │  + insights    │            └──────────┬──────────┘
                         └───────┬───────┘                       │
                                 └───────┬───────────────────────┘
                                         │
                        ┌────────────────▼────────────────────────┐
                        │  WEB DASHBOARD (web/ — Next.js 15)      │
                        │  Server routes → data-source adapter     │
                        │  Supabase if configured, else seed file  │
                        └─────────────────────────────────────────┘
```

The pipeline runs as a single orchestrated unit (`src/pipeline.py::run_etl`):
`extract → validate → transform → dedupe → load`, with the scraper executing
exactly once per invocation and followed by optional reporting-artifact export.

---

## Repository layout

```
.
├── .env.example                 # All configuration, documented, with defaults
├── requirements.txt             # Core ETL dependencies
├── requirements-dev.txt         # Optional: selenium, psycopg, pytest
├── README.md
│
├── src/                         # Python ETL core (package "jmip", v2.0.0)
│   ├── cli.py                   # argparse CLI (`python -m src.main`)
│   ├── main.py                  # entry point
│   ├── config.py                # pydantic-settings, repo-root-relative paths
│   ├── models.py                # Pydantic v2 data models (RawRecord, JobRecord…)
│   ├── pipeline.py              # end-to-end ETL orchestration
│   ├── reporting.py             # pandas tidy CSV artifacts
│   ├── logging_config.py        # console+file logging setup
│   ├── analyze_db.py            # standalone DB-summary helper
│   ├── extract/
│   │   ├── base.py              # ExtractionResult contract
│   │   ├── google_careers.py    # HTTP extractor + ds:1 payload parser
│   │   ├── selenium_collector.py# browser fallback (optional)
│   │   └── file_loader.py       # JSON / CSV ingest
│   ├── validation/
│   │   └── validators.py        # RawRecord validation, error reporting
│   ├── transform/
│   │   ├── pipeline.py          # transform_record / transform_all
│   │   ├── cleaners.py          # HTML→text, whitespace, boilerplate
│   │   ├── normalizers.py       # title/company/location/URL normalization
│   │   ├── classifiers.py       # seniority, remote, employment type
│   │   ├── skill_extractor.py   # alias→canonical skill dictionary
│   │   ├── salary.py            # US base-salary band extraction
│   │   └── dedupe.py            # deterministic identity fingerprints
│   ├── load/
│   │   ├── base.py              # LoadResult contract
│   │   ├── sqlite_loader.py     # normalised-schema SQLite backend
│   │   └── supabase_loader.py   # PostgREST backend (service-role key)
│   ├── migration/
│   │   └── migrate.py           # legacy flat-schema DB → new schema
│   └── analytics/
│       ├── engine.py            # SQL aggregations (SQLite)
│       ├── queries.py           # the aggregation SQL
│       └── insights.py          # insight generation with verifiable basis
│
├── scripts/                     # Runnable dev/ops helpers
│   ├── export_sample_dataset.py    # → data/raw/google_careers_sample.json
│   ├── export_web_seed.py          # → data/web_seed.json (web snapshot)
│   ├── seed_database.py            # load bundled data into a target
│   └── migrate_sqlite_to_postgres.py
│
├── supabase/
│   └── migrations/0001_init.sql # Full PG schema + analytics views + grants
│
├── data/
│   ├── README.md
│   ├── web_seed.json            # Committed snapshot the web app uses
│   └── raw/google_careers_sample.json  # Real raw postings (sample dataset)
│
├── web/                         # Next.js 15 dashboard (App Router)
│   ├── app/                     # pages + API route handlers
│   ├── components/              # UI components (charts, cards, explorer)
│   ├── lib/                     # data-source adapter, analytics, types
│   ├── package.json
│   └── tsconfig.json
│
└── tests/                       # pytest suite (82 tests)
```

---

## Tech stack

**Python ETL**
- Python 3.10+ (pydantic v2, pydantic-settings, pandas, requests, beautifulsoup4)
- Supabase client (PostgREST) for production persistence
- Optional: selenium + webdriver-manager, psycopg (binary), pytest

**Web dashboard**
- Next.js 15 (App Router, server components), React 19
- Tailwind CSS, recharts, lucide-react
- `@supabase/supabase-js` (server-side only)

**Persistence**
- SQLite (development / staging, same normalised schema as Postgres)
- Supabase (PostgreSQL + PostgREST) for production

---

## Quick start

### Prerequisites
- Python 3.10+
- Node.js 18+ (20+ recommended) and npm
- (Optional) A Supabase project for production persistence

### 1. Set up the Python ETL

```bash
# from the repository root
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

python -m pip install -r requirements.txt
# optional extras
python -m pip install -r requirements-dev.txt
```

Run a real extraction from Google Careers (default query: "Data Analyst"):

```bash
python -m src.main run --query "Data Analyst" --limit 50
```

Load the bundled sample dataset instead of hitting the network:

```bash
python -m src.main seed
# or dry-run first
python -m src.main seed --dry-run
```

Generate an analytics report from the database:

```bash
python -m src.main analyze
python -m src.main analyze --json    # machine-readable bundle
```

### 2. Run the web dashboard

```bash
cd web
npm install
npm run dev          # http://localhost:3000
```

Production build + serve:

```bash
npm run build
npm run start
```

The dashboard **works out of the box** — no Supabase needed — because
`web/lib/data-source.ts` falls back to the committed snapshot
(`data/web_seed.json`) when `SUPABASE_URL`/`SUPABASE_ANON_KEY` are not set.

Other web scripts: `npm run lint`, `npm run typecheck`.

### 3. Run the tests

```bash
python -m pytest tests -q        # 82 tests
```

---

## Configuration

All configuration is environment-driven via a `.env` file at the repo root
(copy `.env.example`). None of the settings are required to start; defaults
make the platform runnable immediately.

| Variable | Default | Purpose |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Root log level |
| `ETL_LIMIT` | `100` | Default records per extraction |
| `REQUEST_TIMEOUT_SECONDS` | `25` | HTTP timeout for the Google Careers fetcher |
| `MAX_HTTP_RETRIES` | `3` | Retries with backoff before failing a fetch |
| `USER_AGENT` | Chrome UA | Sent with extraction requests |
| `DATABASE_PATH` | `data/jobs_database.db` | SQLite file path |
| `SUPABASE_URL` | — | Supabase project URL (production persistence) |
| `SUPABASE_ANON_KEY` | — | Public read-only key (web app / analytics) |
| `SUPABASE_SERVICE_ROLE_KEY` | — | Write key for the ETL — **never in a browser** |
| `DATABASE_URL` | — | Optional direct Postgres connection string |

Special variable: `ETL_NO_DB_DIR=1` skips creating the SQLite directory.

> The web app reads only `SUPABASE_URL` and `SUPABASE_ANON_KEY` (server-side
> routes). The service-role key is confined to the Python ETL and must never be
> shipped to the browser.

---

## CLI reference

`python -m src.main <command> [options]`

| Command | Description | Example |
|---|---|---|
| `run` | One ETL pass: extract → validate → transform → load | `python -m src.main run --query "Software Engineer" --limit 100 --target sqlite` |
| `analyze` | Analytics report vs the local DB (text or `--json`) | `python -m src.main analyze` |
| `seed` | Load the bundled sample dataset into a target | `python -m src.main seed --target sqlite` |
| `migrate` | Migrate the legacy scraper DB into the new schema | `python -m src.main migrate` |
| `export-sample` | Extract raw records into a JSON sample file | `python -m src.main export-sample --query "Data Analyst" --limit 300` |
| `--version` | Print version | `python -m src.main --version` |

### `run` options

- `--query` — search query (default `Data Analyst`)
- `--source {google,json,csv}` — extraction source
- `--input PATH` — input file for `json`/`csv` sources
- `--limit N` — maximum records
- `--target {sqlite,supabase}` — persistence backend
- `--driver {http,selenium}` — Google transport; `--headless` for Chrome
- `--dry-run` — extract/transform but do not persist
- `--export PATH` — also write raw records to a JSON file

### `run` summary output

```
ETL DONE extract=213 insert=213 duplicates_db=0 duplicates_run=0 target=sqlite
```

---

## Data sources & extraction

### Google Careers (HTTP, default)

`src/extract/google_careers.py` fetches the public search-results page:

```
https://www.google.com/about/careers/applications/jobs/results/?q=<query>&hl=en_US&page_number=<page>
```

The HTML embeds the site data as an `AF_initDataCallback` block keyed `ds:1`.
The parser:

1. Locates `key: 'ds:1'` and extracts its `data:[...]` payload with a
   bracket-depth scan.
2. Normalizes JavaScript literals (`undefined` → `null`, `NaN` → `null`).
3. Recursively locates the list of 21-field job records.
4. Maps each record onto the platform's raw-record schema (positional fields
   are versioned via `_PAYLOAD_VERSION`).

If the payload shape ever changes, parsing **fails loudly** with
`ExtractionError` instead of silently returning garbage.

### Selenium (optional fallback)

`selenium_collector.py` drives a real Chrome browser (headless supported) when
the HTTP path is unavailable. Its output is written to a temp JSON file and fed
through the same file-based `json` source.

### File sources (json / csv)

`file_loader.py` ingests previously exported records. This powers the bundled
sample dataset, `seed`, offline work, and the test suite.

---

## The transformation stage

Every raw record flows through `transform_record` (`src/transform/pipeline.py`):

1. **Clean** (`cleaners.py`) — HTML → plain text, collapse whitespace, strip
   navigation/boilerplate lines, merge descriptions.
2. **Normalize** (`normalizers.py`) — canonical title casing, company name
   normalization (e.g. `Alphabet Inc.` vs `Google`), deterministic location
   keys with inferred country codes, URL scheme/format cleanup.
3. **Classify** (`classifiers.py`) — evidence-based:
   - *Seniority*: Intern → Director using title/level suffixes and
     roman/arabic numeral levels (`SWE III`, `L5`, `Principal`).
   - *Remote type*: Remote / Hybrid / Onsite from explicit text signals.
   - *Employment type*: Internship, Part-time, Contract, Full-time, Temporary.
4. **Extract skills** (`skill_extractor.py`) — dictionary-driven
   (`SKILL_DICTIONARY`) mapping aliases to canonical skills grouped into
   categories such as *Language*, *Database & Data Store*, *Framework*,
   *Cloud*, *Data Science & ML*, *DevOps & Infrastructure*, *Data Engineering*,
   *Dev Tools*, *Automation*, *Product & Operations*. Matching is
   case-insensitive and word-bounded with canonical alias patterns.
5. **Extract salary** (`salary.py`) — detects disclosed US base-salary ranges
   (`$110,000 – $170,000`), storing min, max, and currency.
6. **Compute dedupe key** (`dedupe.py`) — see below.

See `src/models.py::JobRecord` for the canonical transformed model, which is
the contract between the transform and load layers.

---

## Deduplication

`dedupe.py` builds a deterministic identity fingerprint:

```python
compute_dedupe_key(source, job_url, title, company, location_keys, external_job_id)
```

A SHA-256 is computed over those **stable** fields with locations sorted.
Timestamps and scrape metadata are deliberately excluded, so re-running the
pipeline never fabricates a new identity for the same posting.

Protection happens at three layers:
1. In-run: `deduplicate()` keeps the first occurrence within the same batch.
2. Database: `UNIQUE (dedupe_key)` on the `jobs` table.
3. Uniqueness of a delivered job: `UNIQUE (source_id, external_job_id)`.

---

## Persistence & database schema

Both backends implement the **same normalised relational schema**, so analytics
behave identically on SQLite and Postgres.

### Core tables

| Table | Purpose |
|---|---|
| `sources` | Data sources (e.g. `google_careers`) |
| `companies` | Employers; unique by `external_id` and `name`, with `normalized_name` |
| `locations` | Structured locations keyed by `normalized_key` (city/state/country) |
| `skills` | Canonical skill names with category |
| `jobs` | The posting facts: title, company, description, employment/seniority/remote type, URLs, dates, salary band, raw payload (JSON) |
| `job_locations` | Many-to-many job ↔ location with ordering `rank` |
| `job_skills` | Many-to-many job ↔ skill with `matched_text` evidence |
| `extraction_runs` | Bookkeeping: query, status, counts, timestamps, error |

### Analytics views (PostgreSQL / Supabase)

The web application reads analytics exclusively through views, never raw
tables. All aggregation happens server-side via SQL.

| View | Contents |
|---|---|
| `analytics_jobs` | Job explorer rows with aggregated company, primary/all locations, skills |
| `analytics_overview` | Totals: jobs, companies, locations, skills, sources, most-demanded skill, salary disclosure stats |
| `analytics_jobs_by_seniority` | Posting counts per seniority level |
| `analytics_jobs_by_employment_type` | Counts per employment type |
| `analytics_jobs_by_remote_type` | Counts per remote type |
| `analytics_jobs_by_company` | Posting counts per company |
| `analytics_jobs_by_location` | Posting counts per display location |
| `analytics_jobs_over_time` | Monthly posting counts |
| `analytics_jobs_by_country` | Posting counts per country |
| `analytics_top_skills` | Ranked skills with `percentage` of postings |
| `analytics_skills_by_seniority` | Skill × seniority demand matrix |
| `analytics_skills_by_location` | Skill × location demand (top 200) |
| `analytics_skill_combinations` | Top 12 co-occurring skill pairs |
| `analytics_skill_trends` | Monthly skill demand series |
| `analytics_seniority_over_time` | Monthly seniority mix |

Schema and grants live in `supabase/migrations/0001_init.sql`.

---

## Analytics engine & insights

`src/analytics/engine.py::AnalyticsEngine` runs the aggregation SQL
(`analytics/queries.py`) against a connection and assembles an analytics
bundle: overview, seniority, employment type, remote type, companies,
locations, jobs over time, country breakdown, top skills, skill
combinations, skills-by-seniority, skill trends, and seniority over time.

`src/analytics/insights.py::compute_insights` derives human-readable findings
from the bundle. Every insight is grounded in a real query and carries the
slice it is based on (`basis`), e.g.:

- *"Python is the most demanded skill"* — basis `analytics/skills?limit=1`
- *"Remote positions represent X% of postings"* — basis `analytics/remote?type=Remote`
- *"C++ + Python co-occur frequently"* — basis `analytics/skills/combinations?limit=1`
- *"Salary disclosed for N postings"* — basis `analytics/salary`

If no data exists, a single "Awaiting data" insight is returned instead of
fabricated claims.

---

## Reporting artifacts (pandas)

After a local load, `src/reporting.py` writes analyst-friendly CSV files under
`data/processed/` (git-ignored):

- `jobs_tidy.csv` — one tidy row per posting with skills as a list
- `job_skills_long.csv` — one row per (job, skill) pair
- `top_skills.csv` — ranked skill × category × job-count summary

---

## Web dashboard

A server-rendered Next.js **App Router** application in `web/`.

### Data-source adapter

`web/lib/data-source.ts` is the single point of access:

- If `SUPABASE_URL` + `SUPABASE_ANON_KEY` are configured → query the Supabase
  analytics views (PostgREST, server-side).
- Otherwise → compute the same analytics in-process from the committed
  snapshot `data/web_seed.json` (loaded by `web/lib/seed.ts`).

This gives a working dashboard with zero external configuration and an easy
upgrade path to live data.

### Pages

| Route | Description |
|---|---|
| `/` | Overview: KPI cards, top skills, seniority donut, hiring hubs, postings over time, auto-generated insights |
| `/jobs` | Job explorer with search, filters (seniority, remote, employment, company, location, skill), sorting, pagination |
| `/jobs/[id]` | Full job detail (description, skills, locations, salary, apply link) |
| `/skills` | Skill demand explorer (ranked skills with categories) |
| `/trends` | Market trends: postings over time and skill trends |
| `/insights` | Full auto-generated insights feed |
| `/pipeline` | Documentation of the data pipeline |

### API routes

- `GET /api/jobs` — paginated, filterable job list
- `GET /api/jobs/[id]` — single job
- `GET /api/analytics` — the complete analytics bundle
- `GET /api/analytics/{overview,skills,insights,trends,combinations,locations,companies,seniority}` — individual slices

---

## Supabase setup (production persistence)

1. Create a project at https://supabase.com.
2. Open the **SQL editor** and run `supabase/migrations/0001_init.sql`
   (creates tables, analytics views, and grants read access to the `anon` role
   — the dashboard is intentionally public read-only; writes use `service_role`).
3. Configure credentials in the Python environment (`.env`):
   ```ini
   SUPABASE_URL=https://<project>.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=<service role key>
   ```
4. Load or migrate data:
   ```bash
   python -m src.main seed --target supabase
   # or
   python -m src.main migrate --target supabase
   ```
5. For the web app, set the public env vars (Vercel project, or local `.env`):
   ```
   SUPABASE_URL=https://<project>.supabase.co
   SUPABASE_ANON_KEY=<anon key>
   ```

Security notes:

- `SUPABASE_SERVICE_ROLE_KEY` bypasses RLS — it is used only by the Python ETL
  and must never be exposed to the browser.
- Dashboard reads use the anon key from Next.js server-side routes; grants in
  the migration limit anon to `SELECT` on tables/views.

---

## Deploy to Vercel

The dashboard is a standard Next.js app living in the `web/` subfolder.

1. Push this repository to GitHub.
2. In Vercel: **Add New → Project → Import** the repository.
3. Framework preset: **Next.js** (auto-detected).
4. **Root Directory: `web/`** (important — the app is not at the repo root).
5. Environment variables (optional):
   - `SUPABASE_URL` and `SUPABASE_ANON_KEY` if you want live Supabase data.
   - Without them the dashboard runs on the committed snapshot — it will
     deploy and work immediately.
6. **Deploy.** Pushes to `main` trigger automatic redeployments.

> Do **not** add `SUPABASE_SERVICE_ROLE_KEY` to the Vercel environment — the
> web app only needs the anon key and must never hold write credentials.

Build/run commands are the standard Next.js ones already in `web/package.json`
(`build` → `start`); Vercel detects these automatically.

---

## Helper scripts

| Script | Purpose | Example |
|---|---|---|
| `scripts/export_sample_dataset.py` | Extract a curated, deduplicated sample of real Google Careers postings into `data/raw/` (committed) | `python scripts/export_sample_dataset.py --limit 300` |
| `scripts/export_web_seed.py` | Export the local SQLite DB into the web snapshot `data/web_seed.json` (committed) | `python scripts/export_web_seed.py --out data/web_seed.json` |
| `scripts/seed_database.py` | Seed a target (SQLite or Supabase) from the bundled data | `python scripts/seed_database.py --target supabase` |
| `scripts/migrate_sqlite_to_postgres.py` | Migrate a legacy DB into the new schema on either target | `python scripts/migrate_sqlite_to_postgres.py --target supabase` |

The two export scripts are what regenerate the committed data snapshots so the
platform is reproducible and demoable offline.

---

## Testing

82 pytest tests across the whole pipeline:

```
tests/test_analytics.py         analytics engine + insight generation
tests/test_classifiers.py       seniority / remote / employment classifiers
tests/test_cleaners.py          HTML→text, whitespace, boilerplate
tests/test_dedupe.py            dedupe keys and in-memory de-dup
tests/test_google_payload.py    ds:1 payload parsing
tests/test_normalizers.py       title / company / location / URL normalization
tests/test_skill_extractor.py   skill dictionary matching
tests/test_sqlite_loader.py     relational loading + constraints
tests/test_transform.py         end-to-end record transformation
```

```bash
python -m pytest tests -q
```

The web app additionally runs `next build` (which type-checks and lints every
page/route) and `npm run typecheck`.

---

## Migrating the legacy scraper database

The original scraper wrote to a flat 4-column table (`query, title,
description, scraped_at`). `src/migration/migrate.py`:

1. **Archives** the legacy DB to `data/processed/legacy_jobs_database_archive.db`
   (data preservation).
2. Reads legacy rows (deduplicated by normalized title — the old code had a
   double-execution bug that minted duplicates).
3. Cleanse and re-runs them through the **same transformation pipeline**.
4. Loads the migrated records into the new normalised schema on SQLite or
   Supabase.

```bash
python -m src.main migrate --legacy-path path/to/legacy.db --target sqlite
```

---

## Roadmap

Possible future directions:

- Expand the source switchboard beyond Google Careers (LinkedIn, Greenhouse,
  Lever, job boards by region).
- Incremental ETL scheduling (cron / GitHub Actions / Airflow) integrated with
  `extraction_runs` bookkeeping.
- Natural-language skill extraction upgrade (NER) layered over the dictionary.
- Password-protected dashboards via Supabase Auth for private feeds.
- Export dashboards as static reports / email digests.

---

*Copyright © 2026 — part of the Job Market Intelligence Platform.*