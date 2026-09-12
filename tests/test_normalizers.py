from src.transform.normalizers import (
    build_location_items,
    normalize_company,
    normalize_location_key,
    normalize_title,
    normalize_url,
)


class TestNormalizeTitle:
    def test_sr_expansion(self):
        assert normalize_title("Sr. Software Engineer") == "Senior Software Engineer"

    def test_jr_expansion(self):
        assert normalize_title("AI Jr. Researcher") == "AI Junior Researcher"

    def test_company_suffix_stripped(self):
        assert normalize_title("Data Analyst (Remote)") == "Data Analyst"

    def test_existing_senior_unchanged(self):
        assert normalize_title("Senior Data Analyst") == "Senior Data Analyst"


class TestNormalizeCompany:
    def test_inc_stripped(self):
        assert normalize_company("Google Inc.") == "Google"

    def test_plain(self):
        assert normalize_company("DeepMind") == "DeepMind"

    def test_unknown_fallback(self):
        assert normalize_company("") == "Unknown"


class TestNormalizeUrl:
    def test_tracking_params_removed(self):
        url = "https://Example.com/path?utm_source=x&a=1#frag"
        assert normalize_url(url) == "https://example.com/path?a=1"

    def test_empty(self):
        assert normalize_url("") == ""


class TestLocations:
    def test_location_key(self):
        assert normalize_location_key("Dublin, Ireland", "IE") == "ie|dublin, ireland"

    def test_build_items_ranks(self):
        items = build_location_items(
            [
                {"display_name": "Sunnyvale, CA, USA", "city": "Sunnyvale", "state": "CA", "country_code": "US"},
                {"display_name": "Kirkland, WA, USA", "city": "Kirkland", "state": "WA", "country_code": "US"},
            ]
        )
        assert len(items) == 2
        assert [i.rank for i in items] == [0, 1]
        assert items[0].normalized_key == "us|sunnyvale, ca, usa"

    def test_country_inferred_from_display(self):
        items = build_location_items([{"display_name": "Dublin, Ireland"}])
        assert items[0].country_code == "IE"

    def test_empty_locations(self):
        assert build_location_items([]) == []