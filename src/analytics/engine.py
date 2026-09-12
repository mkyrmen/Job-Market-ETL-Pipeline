"""Analytics engine: run SQL aggregations and assemble an analytics bundle.

All metrics are computed server-side via SQL aggregation — the application
never transfers the full table to a client.
"""

from __future__ import annotations

import sqlite3
from typing import Any

import src.analytics.queries as q


class AnalyticsEngine:
    """Runs analytics queries against a SQLite connection."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def _rows(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        return [dict(row) for row in self.conn.execute(sql, params).fetchall()]

    def _one(self, sql: str, params: tuple = ()) -> dict[str, Any]:
        row = self.conn.execute(sql, params).fetchone()
        return dict(row) if row else {}

    # -- overview ---------------------------------------------------------

    def overview(self) -> dict[str, Any]:
        total_jobs = self._one(q.TOTAL_JOBS)["total"]
        most_demanded = self._one(q.MOST_DEMANDED_SKILL) or {}
        salary = self._one(q.SALARY_STATS) or {}
        jobs_with_salary = self._one(q.JOBS_WITH_SALARY)["total"]
        return {
            "total_jobs": total_jobs,
            "total_companies": self._one(q.TOTAL_COMPANIES)["total"],
            "total_locations": self._one(q.TOTAL_LOCATIONS)["total"],
            "total_skills": self._one(q.TOTAL_SKILLS)["total"],
            "total_sources": self._one(q.TOTAL_SOURCES)["total"],
            "most_demanded_skill": most_demanded.get("skill"),
            "most_demanded_skill_jobs": most_demanded.get("jobs", 0),
            "jobs_with_salary": jobs_with_salary,
            "salary": salary if salary.get("count") else None,
        }

    def jobs_by_seniority(self) -> list[dict[str, Any]]:
        return self._rows(q.JOBS_BY_SENIORITY)

    def jobs_by_employment_type(self) -> list[dict[str, Any]]:
        return self._rows(q.JOBS_BY_EMPLOYMENT_TYPE)

    def jobs_by_remote_type(self) -> list[dict[str, Any]]:
        return self._rows(q.JOBS_BY_REMOTE_TYPE)

    def jobs_by_company(self, limit: int = 15) -> list[dict[str, Any]]:
        rows = self._rows(q.JOBS_BY_COMPANY)
        return rows[:limit]

    def jobs_by_location(self, limit: int = 15) -> list[dict[str, Any]]:
        rows = self._rows(q.JOBS_BY_LOCATION)
        return rows[:limit]

    def jobs_over_time(self) -> list[dict[str, Any]]:
        return self._rows(q.JOBS_OVER_TIME)

    def jobs_by_country(self) -> list[dict[str, Any]]:
        return self._rows(q.JOBS_COUNT_BY_COUNTRY)

    # -- skills ------------------------------------------------------------

    def top_skills(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._rows(q.TOP_SKILLS)[:limit]

    def skills_by_seniority(self) -> list[dict[str, Any]]:
        return self._rows(q.SKILLS_BY_SENIORITY)

    def skills_by_location(self) -> list[dict[str, Any]]:
        return self._rows(q.SKILLS_BY_LOCATION)

    def skill_combinations(self, limit: int = 12) -> list[dict[str, Any]]:
        return self._rows(q.SKILL_COMBINATIONS)[:limit]

    def skill_trends(self) -> list[dict[str, Any]]:
        return self._rows(q.SKILL_TRENDS)

    def seniority_over_time(self) -> list[dict[str, Any]]:
        return self._rows(q.SENIORITY_OVER_TIME)


def build_analytics_bundle(conn: sqlite3.Connection) -> dict[str, Any]:
    """Return the complete analytics bundle used by CLI reports and insights."""
    engine = AnalyticsEngine(conn)
    return {
        "overview": engine.overview(),
        "jobs_by_seniority": engine.jobs_by_seniority(),
        "jobs_by_employment_type": engine.jobs_by_employment_type(),
        "jobs_by_remote_type": engine.jobs_by_remote_type(),
        "jobs_by_company": engine.jobs_by_company(),
        "jobs_by_location": engine.jobs_by_location(),
        "jobs_over_time": engine.jobs_over_time(),
        "jobs_by_country": engine.jobs_by_country(),
        "top_skills": engine.top_skills(),
        "skill_combinations": engine.skill_combinations(),
        "skills_by_seniority": engine.skills_by_seniority(),
        "skill_trends": engine.skill_trends(),
        "seniority_over_time": engine.seniority_over_time(),
    }


def run_analysis_report(conn: sqlite3.Connection) -> dict[str, Any]:
    """Compute the analytics bundle for reporting purposes."""
    return build_analytics_bundle(conn)