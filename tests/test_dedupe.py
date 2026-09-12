from src.transform.dedupe import compute_dedupe_key, dedupe_key_for_job, deduplicate


def test_key_stable_without_timestamps():
    a = compute_dedupe_key("google_careers", "https://x.com/j/1", "Data Analyst", "Google", ["us|mountain view"])
    b = compute_dedupe_key("google_careers", "https://x.com/j/1", "Data Analyst", "Google", ["us|mountain view"])
    c = compute_dedupe_key("google_careers", "https://x.com/j/2", "Data Analyst", "Google", ["us|mountain view"])
    assert a == b
    assert a != c


def test_key_changes_with_any_stable_field():
    base = compute_dedupe_key("google_careers", "https://x.com/j/1", "Data Analyst", "Google", None)
    assert base != compute_dedupe_key("google", "https://x.com/j/1", "Data Analyst", "Google", None)
    assert base != compute_dedupe_key("google_careers", "https://x.com/j/1", "Analyst", "Google", None)
    assert base != compute_dedupe_key("google_careers", "https://x.com/j/1", "Data Analyst", "YouTube", None)


def test_location_order_insensitive():
    a = compute_dedupe_key("g", "u", "t", "c", ["a", "b"])
    b = compute_dedupe_key("g", "u", "t", "c", ["b", "a"])
    assert a == b


def test_dedupe_key_from_record(job_record):
    key = dedupe_key_for_job(job_record)
    assert key
    assert len(key) == 64
    assert job_record.dedupe_key == key


def test_deduplicate_keeps_first(job_record):
    from src.models import JobRecord

    base = JobRecord.model_validate(job_record.model_dump())
    dup = base.model_copy()
    unique, dropped = deduplicate([base, dup])
    assert len(unique) == 1
    assert dropped == 1