import sqlite3

import pytest

from src.analytics.engine import AnalyticsEngine, build_analytics_bundle
from src.analytics.insights import compute_insights
from src.load.sqlite_loader import SQLiteLoader


@pytest.fixture
def seeded_conn(tmp_path, job_record):
    db = tmp_path / "analytics.db"
    loader = SQLiteLoader(db)
    second = job_record.model_copy(update={"dedupe_key": "second-key", "external_job_id": "999"})
    third = job_record.model_copy(update={"dedupe_key": "third-key", "external_job_id": "888"})
    loader.upsert_jobs([job_record, second, third])
    loader.conn.commit()
    conn = sqlite3.connect(db, uri=True)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def test_overview_counts(seeded_conn):
    engine = AnalyticsEngine(seeded_conn)
    overview = engine.overview()
    assert overview["total_jobs"] == 3
    assert overview["total_companies"] == 1
    assert overview["total_skills"] >= 2


def test_top_skills_percentage(seeded_conn):
    engine = AnalyticsEngine(seeded_conn)
    top = engine.top_skills()
    assert top
    assert all(0 <= row["percentage"] <= 100 for row in top)


def test_jobs_over_time_months(seeded_conn):
    engine = AnalyticsEngine(seeded_conn)
    series = engine.jobs_over_time()
    assert series and any(row["month"] for row in series)


def test_bundle_shape(seeded_conn):
    bundle = build_analytics_bundle(seeded_conn)
    assert "overview" in bundle
    assert "top_skills" in bundle
    assert "jobs_by_seniority" in bundle
    assert "skill_trends" in bundle
    assert "jobs_over_time" in bundle


def test_insights_require_data():
    insights = compute_insights({"overview": {"total_jobs": 0}})
    assert insights
    assert insights[0]["title"] == "Awaiting data"


def test_insights_from_real_bundle(seeded_conn):
    bundle = build_analytics_bundle(seeded_conn)
    insights = compute_insights(bundle)
    assert insights
    assert all(item.get("basis") for item in insights)


def test_empty_database_insights(tmp_path):
    db = tmp_path / "empty.db"
    SQLiteLoader(db).close()
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    suite = AnalyticsEngine(conn)
    bundle = {
        "overview": suite.overview(),
        "top_skills": suite.top_skills(),
        "jobs_by_seniority": suite.jobs_by_seniority(),
        "jobs_by_remote_type": suite.jobs_by_remote_type(),
        "jobs_by_company": suite.jobs_by_company(),
        "jobs_by_location": suite.jobs_by_location(),
        "skill_combinations": suite.skill_combinations(),
        "skills_by_seniority": suite.skills_by_seniority(),
        "jobs_over_time": suite.jobs_over_time(),
    }
    insights = compute_insights(bundle)
    assert any(i["title"] == "Awaiting data" for i in insights)
    conn.close()