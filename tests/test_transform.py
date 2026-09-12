from src.models import RawRecord
from src.transform.pipeline import transform_record


class TestTransformRecord:
    def test_original_title_preserved(self, raw_record):
        job = transform_record(RawRecord.model_validate(raw_record))
        assert job.original_title == "Software Engineer, Infrastructure"
        assert job.title == "Software Engineer, Infrastructure"

    def test_seniority_from_title(self, raw_record):
        raw = dict(raw_record)
        raw["title"] = "Senior Data Engineer"
        job = transform_record(RawRecord.model_validate(raw))
        assert job.seniority == "Senior"

    def test_sr_normalised_in_title(self, raw_record):
        raw = dict(raw_record)
        raw["title"] = "Sr. Data Engineer"
        job = transform_record(RawRecord.model_validate(raw))
        assert job.title == "Senior Data Engineer"
        assert job.original_title == "Sr. Data Engineer"

    def test_salary_extracted_from_description(self, raw_record):
        raw = dict(raw_record)
        raw["description_html"] = (
            "<p>The US base salary range for this full-time position is "
            "$110,400 - $153,000 + bonus + equity.</p>"
        )
        job = transform_record(RawRecord.model_validate(raw))
        assert job.salary_min == 110400.0
        assert job.salary_max == 153000.0
        assert job.salary_currency == "USD"

    def test_no_salary_when_absent(self, raw_record):
        raw = dict(raw_record)
        raw["description_html"] = "<p>We are an equal opportunity employer.</p>"
        job = transform_record(RawRecord.model_validate(raw))
        assert job.salary_min is None
        assert job.salary_max is None

    def test_skills_extracted(self, job_record):
        names = {s.name for s in job_record.skills}
        assert "Python" in names
        assert "PostgreSQL" in names

    def test_missing_fields_tolerated(self):
        raw = {
            "source": "file",
            "title": "Data Analyst",
            "description": "Remote friendly role.",
        }
        job = transform_record(RawRecord.model_validate(raw))
        assert job.company == "Unknown"
        assert job.locations == []
        assert job.dedupe_key

    def test_missing_location_not_fabricated(self, raw_record):
        raw = dict(raw_record)
        raw["locations"] = []
        job = transform_record(RawRecord.model_validate(raw))
        assert job.locations == []

    def test_remote_classified_from_description(self, raw_record):
        raw = dict(raw_record)
        raw["description_html"] = "<p>This role is fully remote.</p>"
        job = transform_record(RawRecord.model_validate(raw))
        assert job.remote_type == "Remote"