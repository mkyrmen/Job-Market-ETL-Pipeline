import pytest

from src.load.sqlite_loader import SQLiteLoader
from src.models import JobRecord


@pytest.fixture
def loader(tmp_path):
    db = tmp_path / "test.db"
    return SQLiteLoader(db)


def test_upsert_inserts_then_skips_duplicates(loader, job_record):
    first = loader.upsert_jobs([job_record])
    assert first.inserted == 1
    assert first.duplicates_skipped == 0

    second = loader.upsert_jobs([job_record])
    assert second.inserted == 0
    assert second.duplicates_skipped == 1

    total = loader.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    assert total == 1


def test_job_skills_are_relational(loader, job_record):
    loader.upsert_jobs([job_record])
    assert len(job_record.skills) > 0
    rows = loader.conn.execute(
        "SELECT s.name FROM job_skills js JOIN skills s ON s.id = js.skill_id"
    ).fetchall()
    assert {r[0] for r in rows} == {s.name for s in job_record.skills}


def test_job_locations_are_relational(loader, job_record):
    loader.upsert_jobs([job_record])
    rows = loader.conn.execute(
        "SELECT l.display_name FROM job_locations jl JOIN locations l ON l.id = jl.location_id"
    ).fetchall()
    assert {r[0] for r in rows} == {loc.display_name for loc in job_record.locations}


def test_schema_persists_across_reopen(tmp_path, job_record):
    db = tmp_path / "test.db"
    first = SQLiteLoader(db)
    first.upsert_jobs([job_record])
    first.close()

    second = SQLiteLoader(db)
    assert second.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1
    second.close()


def test_dedupe_key_uniqueness_enforced(loader, job_record):
    dup = job_record.model_copy()
    loader.upsert_jobs([job_record])
    loader.upsert_jobs([dup])
    assert loader.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1


def test_missing_company_ok(tmp_path):
    db = tmp_path / "test.db"
    loader = SQLiteLoader(db)
    job = JobRecord(
        source="file",
        title="Analyst",
        original_title="Analyst",
        company="",
        company_normalized="Unknown",
        job_url="https://example.org/job",
        dedupe_key="k1",
    )
    result = loader.upsert_jobs([job])
    assert result.inserted == 1
    loader.close()