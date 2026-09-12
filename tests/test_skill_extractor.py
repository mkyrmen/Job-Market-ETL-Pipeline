from src.transform.skill_extractor import extract_skills, skill_categories


def names(skills):
    return sorted(s.name for s in skills)


class TestSkillExtraction:
    def test_basic(self):
        result = extract_skills("We use Python and PostgreSQL for data pipelines.")
        assert "Python" in names(result)
        assert "PostgreSQL" in names(result)

    def test_alias_normalisation(self):
        result = extract_skills("Experience with JS and TS on Node.")
        assert names(result) == ["JavaScript", "Node.js", "TypeScript"]

    def test_alias_postgres(self):
        result = extract_skills("Stack includes Postgres and SQL.")
        assert "PostgreSQL" in names(result)
        assert "SQL" in names(result)

    def test_k8s_alias(self):
        result = extract_skills("Container orchestration with k8s and Docker.")
        assert "Kubernetes" in names(result)
        assert "Docker" in names(result)

    def test_word_boundary_no_substring_matches(self):
        result = extract_skills("Pythons roam in the wild; light and big tables at scale.")
        # 'pythons' must not match 'Python'; 'big tables' must not match BigQuery.
        assert "Python" not in names(result)

    def test_ml_alias(self):
        result = extract_skills("Strong background in machine learning and ML systems.")
        assert "Machine Learning" in names(result)

    def test_no_false_positive_go(self):
        # "Growth" must not match the language "Go".
        result = extract_skills("Platform Growth and Commerce")
        assert "Go" not in names(result)

    def test_categories_assigned(self):
        result = extract_skills("Python, Docker and Tableau")
        categories = {s.name: s.category for s in result}
        assert categories["Python"] == "Language"
        assert categories["Docker"] == "DevOps & Infrastructure"
        assert categories["Tableau"] == "Data & Analytics Tooling"

    def test_dedupe_within_job(self):
        result = extract_skills("Python is great. We also love Python.", title="Python Engineer")
        assert sum(1 for s in result if s.name == "Python") == 1

    def test_empty(self):
        assert extract_skills("") == []
        assert extract_skills("No technical content here.") == []

    def test_categories_exposed(self):
        assert "Language" in skill_categories()
        assert "Cloud" in skill_categories()