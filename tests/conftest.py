import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def raw_record():
    """A realistic raw record as produced by the Google Careers extractor."""
    return {
        "source": "google_careers",
        "external_job_id": "92016217459434182",
        "title": "Software Engineer, Infrastructure",
        "company": "Google",
        "company_external_id": "ebbbf0d1-8121-483c-8f99-ee92597591fc",
        "locations": [
            {
                "display_name": "Sunnyvale, CA, USA",
                "city": "Sunnyvale",
                "state": "CA",
                "country_code": "US",
            }
        ],
        "description_html": "<p>Design systems at scale using Python and PostgreSQL.</p>",
        "overview_html": "<p>Join our team.</p>",
        "qualifications_html": "<p>Bachelor's degree. 5 years of experience.</p>",
        "additional_qualifications_html": None,
        "job_url": "https://www.google.com/about/careers/applications/jobs/results/92016217459434182",
        "apply_url": "https://www.google.com/about/careers/applications/signin?jobId=abc",
        "posted_at": "2026-08-20T04:42:36",
        "scraped_at": "2026-09-12T00:00:00",
        "payload": {"record": [None]},
    }


@pytest.fixture
def job_record(raw_record):
    from src.models import RawRecord
    from src.transform.pipeline import transform_record

    return transform_record(RawRecord.model_validate(raw_record))