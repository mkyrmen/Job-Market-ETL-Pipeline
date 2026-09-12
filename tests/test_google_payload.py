"""Tests for the Google Careers payload parser using a synthetic page."""


def _record(job_id: str, title: str, desc: str, company: str = "Google",
            ts: int = 1788192528, locs=None):
    return [
        job_id,
        title,
        f"https://www.google.com/about/careers/applications/signin?jobId=TOKEN{job_id}",
        [None, f"<ul><li>{desc}</li></ul>"],
        [None, "<h3>Minimum qualifications:</h3><ul><li>BSc</li></ul>"],
        "projects/gweb-careers-proto/tenants/60107626-8e00-0000-0000-0071646e0806/companies/ebbbf0d1-8121-483c-8f99-ee92597591fc",
        None,
        company,
        "en-US",
        locs or [["Mountain View, CA, USA", ["Mountain View, CA, USA"], "Mountain View", None, "CA", "US"]],
        [None, "<p>Overview text</p>"],
        [2, 3],
        [ts, 610000000],
        [ts, 610000000],
        [ts, 680000000],
        [None, "<p>Right to work note</p>"],
        None,
        None,
        [None, ""],
        [None, ""],
        1,
    ]


def _page(job_records) -> str:
    import json

    payload = json.dumps([job_records])
    return (
        "<html><script>AF_initDataCallback({key: 'ds:1', hash: '2', data:"
        + payload
        + "[]]});</script></html>"
    )


def test_parse_google_payload():
    from src.extract.google_careers import parse_google_payload

    jobs = [
        _record("92016217459434182", "Software Engineer", "Build with Python and SQL"),
        _record("89265924414022342", "Senior Data Analyst", "Analyse with SQL"),
    ]
    html = _page(jobs)
    raw_records = parse_google_payload(html, query="test")
    assert len(raw_records) == 2
    first = raw_records[0]
    assert first["source"] == "google_careers"
    assert first["external_job_id"] == "92016217459434182"
    assert first["company"] == "Google"
    assert first["company_external_id"] == "ebbbf0d1-8121-483c-8f99-ee92597591fc"
    assert first["job_url"] == (
        "https://www.google.com/about/careers/applications/jobs/results/92016217459434182"
    )
    assert first["locations"][0]["country_code"] == "US"
    assert first["posted_at"] is not None


def test_parse_ignores_malformed_rows():
    from src.extract.google_careers import parse_google_payload

    good = _record("92016217459434182", "Good Engineer", "desc")
    bad = ["not-an-id", "No numeric id so dropped"]
    html = _page([good, bad])
    records = parse_google_payload(html)
    assert len(records) == 1
    assert records[0]["external_job_id"] == "92016217459434182"


def test_missing_payload_raises():
    from src.extract.google_careers import ExtractionError, parse_google_payload

    try:
        parse_google_payload("<html><body>no payload</body></html>")
        raised = None
    except ExtractionError as exc:
        raised = exc
    assert raised is not None