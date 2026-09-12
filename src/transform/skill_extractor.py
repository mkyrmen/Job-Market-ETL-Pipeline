"""Technical skill extraction from job titles and descriptions.

A maintainable dictionary maps aliases/variants to canonical skill names and
categories. Matching is case-insensitive and word-bounded to avoid
substring false positives. Only skills actually present in the text are
reported.
"""

from __future__ import annotations

import re

from src.models import SkillItem

# category -> list of (canonical_name, [alias, ...])
SKILL_DICTIONARY: dict[str, list[tuple[str, list[str]]]] = {
    "Language": [
        ("Python", ["python"]),
        ("Java", ["java", "java se"]),
        ("JavaScript", ["javascript", "js"]),
        ("TypeScript", ["typescript", "ts"]),
        ("C++", ["c++", "cpp"]),
        ("C", ["\bc\b"]),
        ("C#", ["c#", "c sharp"]),
        ("Go", ["\bgo\b", "golang"]),
        ("Rust", ["rust"]),
        ("SQL", ["sql"]),
        ("R", ["\br\b", "r programming"]),
        ("Scala", ["scala"]),
        ("Ruby", ["ruby"]),
        ("Kotlin", ["kotlin"]),
        ("Swift", ["swift"]),
        ("PHP", ["php"]),
        ("Shell", ["shell scripting", "bash"]),
        ("Dart", ["dart"]),
        ("HTML", ["html"]),
        ("CSS", ["css"]),
        ("Perl", ["perl"]),
    ],
    "Database & Data Store": [
        ("PostgreSQL", ["postgresql", "postgres"]),
        ("MySQL", ["mysql"]),
        ("SQLite", ["sqlite"]),
        ("MongoDB", ["mongodb", "mongo"]),
        ("Redis", ["redis"]),
        ("Oracle", ["oracle database", "oracle"]),
        ("Cassandra", ["cassandra"]),
        ("Elasticsearch", ["elasticsearch"]),
        ("BigQuery", ["bigquery"]),
        ("Snowflake", ["snowflake"]),
        ("DynamoDB", ["dynamodb"]),
        ("Redshift", ["amazon redshift", "redshift"]),
        ("Firestore", ["firestore"]),
        ("Neo4j", ["neo4j"]),
        ("Spark SQL", ["spark sql"]),
    ],
    "Framework": [
        ("React", ["react", "react.js", "reactjs"]),
        ("Next.js", ["next.js", "nextjs", "next js"]),
        ("Node.js", ["node.js", "nodejs", "node js", "node"]),
        ("Django", ["django"]),
        ("Flask", ["flask"]),
        ("FastAPI", ["fastapi"]),
        ("Spring", ["spring boot", "spring framework", "spring"]),
        ("Express", ["express.js", "expressjs", "express"]),
        ("Angular", ["angular"]),
        ("Vue.js", ["vue.js", "vuejs", "vue"]),
        ("Svelte", ["svelte"]),
        ("Rails", ["ruby on rails", "rails"]),
        (".NET", [".net", "dotnet"]),
        ("ASP.NET", ["asp.net"]),
        ("Laravel", ["laravel"]),
        ("Symfony", ["symfony"]),
        ("jQuery", ["jquery"]),
    ],
    "Cloud": [
        ("AWS", ["\baws\b", "amazon web services", "amazon webservices"]),
        ("Azure", ["\bazure\b", "microsoft azure"]),
        ("Google Cloud", ["google cloud platform", "\bgcp\b", "google cloud"]),
        ("Google Cloud Storage", ["google cloud storage"]),
        ("AWS Lambda", ["aws lambda", "lambda"]),
        ("AWS SageMaker", ["sagemaker"]),
    ],
    "DevOps & Infrastructure": [
        ("Docker", ["docker"]),
        ("Kubernetes", ["kubernetes", "k8s"]),
        ("Terraform", ["terraform"]),
        ("Ansible", ["ansible"]),
        ("Jenkins", ["jenkins"]),
        ("GitHub Actions", ["github actions"]),
        ("GitLab", ["gitlab"]),
        ("CI/CD", ["ci/cd", "cicd", "continuous integration", "continuous delivery"]),
        ("Prometheus", ["prometheus"]),
        ("Grafana", ["grafana"]),
        ("Nginx", ["nginx"]),
        ("Kafka", ["kafka", "apache kafka"]),
        ("Airflow", ["airflow"]),
        ("Hadoop", ["hadoop"]),
        ("Pulumi", ["pulumi"]),
    ],
    "Data Science & ML": [
        ("Pandas", ["pandas"]),
        ("NumPy", ["numpy"]),
        ("TensorFlow", ["tensorflow"]),
        ("PyTorch", ["pytorch", "torch"]),
        ("scikit-learn", ["scikit-learn", "sklearn", "scikit learn"]),
        ("Machine Learning", ["machine learning", "\bml\b"]),
        ("Deep Learning", ["deep learning"]),
        ("Natural Language Processing", ["natural language processing", "nlp"]),
        ("Large Language Models", ["large language model", "llm"]),
        ("Generative AI", ["generative ai", "genai"]),
        ("Computer Vision", ["computer vision"]),
        ("Spark", ["spark"]),
        ("Databricks", ["databricks"]),
        ("Hive", ["hive"]),
        ("Jupyter", ["jupyter"]),
        ("Statistical Modeling", ["statistical modeling", "statistical modelling"]),
        ("A/B Testing", ["a/b testing", "ab testing"]),
    ],
    "Data & Analytics Tooling": [
        ("Tableau", ["tableau"]),
        ("Power BI", ["power bi", "powerbi"]),
        ("Looker", ["looker"]),
        ("Excel", ["excel"]),
        ("Google Sheets", ["google sheets"]),
        ("Matplotlib", ["matplotlib"]),
        ("Seaborn", ["seaborn"]),
        ("ETL", ["\betl\b"]),
        ("Data Pipeline", ["data pipeline", "data pipelines"]),
        ("Data Warehousing", ["data warehousing", "data warehouse"]),
    ],
    "Testing": [
        ("Pytest", ["pytest"]),
        ("JUnit", ["junit"]),
        ("Selenium", ["selenium"]),
        ("Cypress", ["cypress"]),
        ("Jest", ["jest"]),
        ("Mockito", ["mockito"]),
    ],
    "Platform & Tooling": [
        ("Git", ["\bgit\b"]),
        ("GitHub", ["github"]),
        ("Linux", ["linux", "unix"]),
        ("REST APIs", ["rest api", "restful api", "rest"]),
        ("GraphQL", ["graphql"]),
        ("gRPC", ["grpc"]),
        ("WebSockets", ["websockets"]),
        ("Agile", ["agile"]),
        ("Scrum", ["scrum"]),
        ("D3.js", ["d3.js", "d3"]),
        ("Terraform", ["terraform"]),
    ],
}

# Canonical name -> category lookup
_CANONICAL_CATEGORY: dict[str, str] = {
    skill: category
    for category, entries in SKILL_DICTIONARY.items()
    for skill, _aliases in entries
}

# Build compiled matchers lazily.
_COMPILED: dict[str, list[tuple[re.Pattern, str, str]]] | None = None


def _compile_matchers() -> dict[str, list[tuple[re.Pattern, str, str]]]:
    """Compile (pattern, canonical_name, matched_literal) tuples per category."""
    compiled: dict[str, list[tuple[re.Pattern, str, str]]] = {}
    for category, entries in SKILL_DICTIONARY.items():
        items: list[tuple[re.Pattern, str, str]] = []
        for canonical, aliases in entries:
            for alias in aliases:
                pattern = _to_word_pattern(alias)
                items.append((pattern, canonical, alias))
        compiled[category] = items
    return compiled


def _to_word_pattern(alias: str) -> re.Pattern:
    """Build a word-bounded, case-insensitive pattern for an alias.

    Aliases already carrying explicit word boundaries (``\\b...\\b``) are
    passed through; multi-word and symbol-heavy aliases get safe boundaries.
    """
    if alias.startswith("\\b"):
        return re.compile(alias, re.IGNORECASE)
    if "." in alias or "#" in alias or "+" in alias or " " in alias:
        pattern = re.escape(alias)
        return re.compile(r"(?<![A-Za-z0-9])" + pattern + r"(?![A-Za-z0-9])", re.IGNORECASE)
    return re.compile(r"\b" + re.escape(alias) + r"\b", re.IGNORECASE)


def get_compiled() -> dict[str, list[tuple[re.Pattern, str, str]]]:
    global _COMPILED
    if _COMPILED is None:
        _COMPILED = _compile_matchers()
    return _COMPILED


def extract_skills(text: str, *, title: str = "") -> list[SkillItem]:
    """Return the ordered, de-duplicated skills detected in *text*.

    The title is scanned separately first so that a skill present in both
    title and description is only reported once.
    """
    haystack = " ".join([title or "", text or ""])
    if not haystack.strip():
        return []

    found: dict[str, tuple[str, str]] = {}  # canonical -> (category, matched_text)
    for category, matchers in get_compiled().items():
        for pattern, canonical, alias in matchers:
            m = pattern.search(haystack)
            if m:
                matched = m.group(0)
                # Skip single-character false positives like "c" in "c.",
                # "go" in "Growth".
                if len(matched.strip()) == 1 and not matched.isalnum():
                    continue
                if canonical not in found:
                    found[canonical] = (category, matched.strip())

    return [
        SkillItem(name=name, category=category, matched_text=matched_text)
        for name, (category, matched_text) in found.items()
    ]


def normalize_skill_name(name: str) -> str:
    """Return the canonical skill name for a detected alias."""
    for category, entries in SKILL_DICTIONARY.items():
        for canonical, aliases in entries:
            if name.lower() in [a.lstrip("\\b").rstrip("\\b") for a in aliases]:
                return canonical
    return name


def skill_categories() -> list[str]:
    return sorted(SKILL_DICTIONARY.keys())