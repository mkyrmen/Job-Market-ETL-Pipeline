"""SQL aggregation queries for the analytics engine.

SQLite dialect. The shapes produced here mirror the PostgreSQL analytics
views defined in ``supabase/migrations`` so the web application can consume
identical payloads from Supabase.
"""

from __future__ import annotations

MONTH_BUCKET = "strftime('%Y-%m', scraped_at)"

# --------------------------------------------------------------------------
# Overview
# --------------------------------------------------------------------------

TOTAL_JOBS = "SELECT COUNT(*) AS total FROM jobs"
TOTAL_COMPANIES = "SELECT COUNT(*) AS total FROM companies"
TOTAL_LOCATIONS = "SELECT COUNT(*) AS total FROM locations"
TOTAL_SKILLS = "SELECT COUNT(*) AS total FROM skills"
TOTAL_SOURCES = "SELECT COUNT(*) AS total FROM sources"

MOST_DEMANDED_SKILL = f"""
SELECT s.name AS skill, COUNT(DISTINCT js.job_id) AS jobs
FROM job_skills js
JOIN skills s ON s.id = js.skill_id
GROUP BY s.id, s.name
ORDER BY jobs DESC
LIMIT 1
"""

SALARY_STATS = """
SELECT COUNT(*) AS count,
       MIN(salary_min) AS min_salary,
       MAX(salary_max) AS max_salary,
       AVG((salary_min + salary_max) / 2.0) AS avg_salary
FROM jobs
WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL
"""

JOBS_WITH_SALARY = """
SELECT COUNT(*) AS total
FROM jobs
WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL
"""

# --------------------------------------------------------------------------
# Job distributions
# --------------------------------------------------------------------------

JOBS_BY_SENIORITY = """
SELECT seniority, COUNT(*) AS count
FROM jobs
GROUP BY seniority
ORDER BY count DESC
"""

JOBS_BY_EMPLOYMENT_TYPE = """
SELECT employment_type, COUNT(*) AS count
FROM jobs
GROUP BY employment_type
ORDER BY count DESC
"""

JOBS_BY_REMOTE_TYPE = """
SELECT remote_type, COUNT(*) AS count
FROM jobs
GROUP BY remote_type
ORDER BY count DESC
"""

JOBS_BY_COMPANY = """
SELECT c.name AS company, COUNT(j.id) AS count
FROM jobs j
JOIN companies c ON c.id = j.company_id
GROUP BY c.id, c.name
ORDER BY count DESC
LIMIT 15
"""

JOBS_BY_LOCATION = """
SELECT l.display_name AS location, COUNT(DISTINCT jl.job_id) AS count
FROM job_locations jl
JOIN locations l ON l.id = jl.location_id
GROUP BY l.id, l.display_name
ORDER BY count DESC
LIMIT 15
"""

JOBS_OVER_TIME = f"""
SELECT {MONTH_BUCKET} AS month, COUNT(*) AS count
FROM jobs
GROUP BY month
ORDER BY month
"""

JOBS_COUNT_BY_COUNTRY = """
SELECT COALESCE(l.country_code, 'Unknown') AS country,
       COUNT(DISTINCT jl.job_id) AS count
FROM job_locations jl
JOIN locations l ON l.id = jl.location_id
GROUP BY country
ORDER BY count DESC
"""

# --------------------------------------------------------------------------
# Skills
# --------------------------------------------------------------------------

TOP_SKILLS = f"""
SELECT s.name AS skill, s.category AS category, COUNT(DISTINCT js.job_id) AS jobs,
       ROUND(100.0 * COUNT(DISTINCT js.job_id) / NULLIF((SELECT COUNT(*) FROM jobs), 0), 1) AS percentage
FROM job_skills js
JOIN skills s ON s.id = js.skill_id
GROUP BY s.id, s.name, s.category
ORDER BY jobs DESC
"""

SKILLS_BY_SENIORITY = """
SELECT s.name AS skill, j.seniority, COUNT(*) AS count
FROM job_skills js
JOIN skills s ON s.id = js.skill_id
JOIN jobs j ON j.id = js.job_id
WHERE j.seniority IS NOT NULL
GROUP BY s.name, j.seniority
ORDER BY j.seniority, count DESC
"""

SKILLS_BY_LOCATION = """
SELECT l.display_name AS location, s.name AS skill, COUNT(DISTINCT js.job_id) AS count
FROM job_skills js
JOIN skills s ON s.id = js.skill_id
JOIN job_locations jl ON jl.job_id = js.job_id
JOIN locations l ON l.id = jl.location_id
GROUP BY l.display_name, s.name
ORDER BY count DESC
LIMIT 200
"""

SKILL_COMBINATIONS = """
WITH pairs AS (
    SELECT a.job_id, a.skill_id AS skill_a, b.skill_id AS skill_b
    FROM job_skills a
    JOIN job_skills b ON b.job_id = a.job_id AND b.skill_id > a.skill_id
)
SELECT sa.name AS skill_a, sb.name AS skill_b, COUNT(*) AS co_occurrences
FROM pairs
JOIN skills sa ON sa.id = pairs.skill_a
JOIN skills sb ON sb.id = pairs.skill_b
GROUP BY sa.name, sb.name
ORDER BY co_occurrences DESC
LIMIT 12
"""

TOP_SKILL_COUNTS = """
SELECT s.name AS skill, COUNT(DISTINCT js.job_id) AS count
FROM job_skills js
JOIN skills s ON s.id = js.skill_id
GROUP BY s.name
ORDER BY count DESC
LIMIT 15
"""

SKILL_TRENDS = f"""
SELECT s.name AS skill, {MONTH_BUCKET} AS month, COUNT(*) AS count
FROM job_skills js
JOIN skills s ON s.id = js.skill_id
JOIN jobs j ON j.id = js.job_id
GROUP BY s.name, month
ORDER BY month, count DESC
"""

SENIORITY_OVER_TIME = f"""
SELECT seniority, {MONTH_BUCKET} AS month, COUNT(*) AS count
FROM jobs
GROUP BY seniority, month
ORDER BY month
"""

SKILL_MONTHLY_GROWTH = f"""
WITH base AS (
    SELECT s.name AS skill, {MONTH_BUCKET} AS month, COUNT(*) AS count
    FROM job_skills js
    JOIN skills s ON s.id = js.skill_id
    JOIN jobs j ON j.id = js.job_id
    GROUP BY s.name, month
)
SELECT skill, month, count,
       LAG(count) OVER (PARTITION BY skill ORDER BY month) AS prev_count
FROM base
"""