-- =====================================================================
-- Job Market Intelligence Platform — PostgreSQL / Supabase schema
-- Run this file in the Supabase SQL editor (or via the supabase CLI).
-- =====================================================================

-- ---------------------------------------------------------------------
-- Core tables
-- ---------------------------------------------------------------------

create table if not exists sources (
    id          bigserial primary key,
    name        text not null unique,
    base_url    text,
    created_at  timestamptz not null default now()
);

create table if not exists companies (
    id              bigserial primary key,
    external_id     text unique,
    name            text not null unique,
    normalized_name text not null,
    created_at      timestamptz not null default now()
);

create table if not exists locations (
    id             bigserial primary key,
    normalized_key text not null unique,
    display_name   text not null,
    city           text,
    state          text,
    country_code   text,
    created_at     timestamptz not null default now()
);

create table if not exists skills (
    id         bigserial primary key,
    name       text not null unique,
    category   text,
    created_at timestamptz not null default now()
);

create table if not exists jobs (
    id              bigserial primary key,
    source_id       bigint not null references sources(id),
    external_job_id text,
    dedupe_key      text not null unique,
    title           text not null,
    original_title  text,
    company_id      bigint references companies(id),
    description     text,
    employment_type text,
    seniority       text,
    remote_type     text,
    job_url         text,
    apply_url       text,
    posted_at       timestamptz,
    scraped_at      timestamptz not null default now(),
    salary_min      numeric,
    salary_max      numeric,
    salary_currency text,
    raw_payload     jsonb,
    created_at      timestamptz not null default now(),
    unique (source_id, external_job_id)
);

create index if not exists idx_jobs_title        on jobs (title);
create index if not exists idx_jobs_company      on jobs (company_id);
create index if not exists idx_jobs_seniority    on jobs (seniority);
create index if not exists idx_jobs_remote       on jobs (remote_type);
create index if not exists idx_jobs_posted       on jobs (posted_at);
create index if not exists idx_jobs_scraped      on jobs (scraped_at);

create table if not exists job_locations (
    job_id      bigint not null references jobs(id) on delete cascade,
    location_id bigint not null references locations(id) on delete cascade,
    rank        integer not null default 0,
    primary key (job_id, location_id)
);

create table if not exists job_skills (
    job_id       bigint not null references jobs(id) on delete cascade,
    skill_id     bigint not null references skills(id) on delete cascade,
    matched_text text,
    primary key (job_id, skill_id)
);
create index if not exists idx_job_skills_skill on job_skills (skill_id);

create table if not exists extraction_runs (
    id                 bigserial primary key,
    source_id          bigint references sources(id),
    query              text,
    status             text,
    records_extracted  integer,
    records_inserted   integer,
    duplicates_skipped integer,
    started_at         timestamptz default now(),
    finished_at        timestamptz,
    error              text
);

-- ---------------------------------------------------------------------
-- Analytics views (read by the web application via PostgREST)
-- ---------------------------------------------------------------------

-- Job explorer / detail view with aggregated company, locations and skills.
create or replace view analytics_jobs as
select
    j.id::text                                                as id,
    j.external_job_id,
    j.title,
    j.original_title,
    c.name                                                    as company,
    j.description,
    j.job_url,
    j.apply_url,
    j.employment_type,
    j.seniority,
    j.remote_type,
    j.posted_at,
    j.scraped_at,
    j.salary_min,
    j.salary_max,
    j.salary_currency,
    (select l.display_name
       from job_locations jl
       join locations l on l.id = jl.location_id
      where jl.job_id = j.id
      order by jl.rank
      limit 1)                                                as primary_location,
    coalesce(
        (select array_agg(distinct l.display_name order by l.display_name)
           from job_locations jl0
           join locations l on l.id = jl0.location_id
          where jl0.job_id = j.id),
        '{}'::text[]
    )                                                          as locations,
    coalesce(
        (select array_agg(distinct s.name order by s.name)
           from job_skills jsk0
           join skills s on s.id = jsk0.skill_id
          where jsk0.job_id = j.id),
        '{}'::text[]
    )                                                          as skills
from jobs j
left join companies c on c.id = j.company_id;

create or replace view analytics_overview as
select
    (select count(*) from jobs)                                          as total_jobs,
    (select count(*) from companies)                                     as total_companies,
    (select count(*) from locations)                                     as total_locations,
    (select count(*) from skills)                                        as total_skills,
    (select count(*) from sources)                                       as total_sources,
    (select s.name
       from job_skills js join skills s on s.id = js.skill_id
      group by s.id, s.name
      order by count(distinct js.job_id) desc
      limit 1)                                                           as most_demanded_skill,
    (select max(cnt)
       from (select count(distinct js.job_id) as cnt
               from job_skills js group by js.skill_id) sub)             as most_demanded_skill_jobs,
    (select count(*) from jobs
      where salary_min is not null and salary_max is not null)           as jobs_with_salary,
    (select count(*) from jobs
      where seniority = 'Senior')                                        as senior_jobs;

create or replace view analytics_jobs_by_seniority as
select seniority, count(*) as count
from jobs
group by seniority
order by count desc;

create or replace view analytics_jobs_by_employment_type as
select employment_type, count(*) as count
from jobs
group by employment_type
order by count desc;

create or replace view analytics_jobs_by_remote_type as
select remote_type, count(*) as count
from jobs
group by remote_type
order by count desc;

create or replace view analytics_jobs_by_company as
select c.name as company, count(j.id) as count
from jobs j
join companies c on c.id = j.company_id
group by c.id, c.name
order by count desc;

create or replace view analytics_jobs_by_location as
select l.display_name as location, count(distinct jl.job_id) as count
from job_locations jl
join locations l on l.id = jl.location_id
group by l.id, l.display_name
order by count desc;

create or replace view analytics_jobs_over_time as
select to_char(j.scraped_at, 'YYYY-MM') as month, count(*) as count
from jobs j
group by month
order by month;

create or replace view analytics_jobs_by_country as
select coalesce(l.country_code, 'Unknown') as country,
       count(distinct jl.job_id) as count
from job_locations jl
join locations l on l.id = jl.location_id
group by country
order by count desc;

create or replace view analytics_top_skills as
select s.name as skill, s.category,
       count(distinct js.job_id) as jobs,
       round(100.0 * count(distinct js.job_id) /
             nullif((select count(*) from jobs), 0), 1) as percentage
from job_skills js
join skills s on s.id = js.skill_id
group by s.id, s.name, s.category
order by jobs desc;

create or replace view analytics_skills_by_seniority as
select s.name as skill, j.seniority, count(*) as count
from job_skills js
join skills s on s.id = js.skill_id
join jobs j on j.id = js.job_id
where j.seniority is not null
group by s.name, j.seniority
order by j.seniority, count desc;

create or replace view analytics_skills_by_location as
select l.display_name as location, s.name as skill, count(distinct js.job_id) as count
from job_skills js
join skills s on s.id = js.skill_id
join job_locations jl on jl.job_id = js.job_id
join locations l on l.id = jl.location_id
group by l.display_name, s.name
order by count desc
limit 200;

create or replace view analytics_skill_combinations as
with pairs as (
    select a.job_id, a.skill_id as skill_a, b.skill_id as skill_b
    from job_skills a
    join job_skills b on b.job_id = a.job_id and b.skill_id > a.skill_id
)
select sa.name as skill_a, sb.name as skill_b, count(*) as co_occurrences
from pairs
join skills sa on sa.id = pairs.skill_a
join skills sb on sb.id = pairs.skill_b
group by sa.name, sb.name
order by co_occurrences desc
limit 12;

create or replace view analytics_skill_trends as
select s.name as skill, to_char(j.scraped_at, 'YYYY-MM') as month, count(*) as count
from job_skills js
join skills s on s.id = js.skill_id
join jobs j on j.id = js.job_id
group by s.name, month
order by month, count desc;

create or replace view analytics_seniority_over_time as
select seniority, to_char(scraped_at, 'YYYY-MM') as month, count(*) as count
from jobs
group by seniority, month
order by month;

-- ---------------------------------------------------------------------
-- Access control for the public analytics experience.
-- The dashboards are intentionally public (read-only via the anon key).
-- The ETL uses the service-role key (server-side only) to write data.
-- ---------------------------------------------------------------------

grant usage on schema public to anon, authenticated, service_role;

grant select on all tables  in schema public to anon, authenticated;
grant select on all views   in schema public to anon, authenticated;

grant insert, update, delete on all tables      in schema public to service_role;
grant usage,  select         on all sequences   in schema public to service_role;