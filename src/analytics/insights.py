"""Job-market insights.

Every insight is derived from real, server-side aggregations. Each item
carries a ``basis`` describing the underlying query so the claim can be
verified against the data. No claims are generated for numbers that do not
exist in the dataset.
"""

from __future__ import annotations

from typing import Any


def _pct(jobs: int, total: int) -> float:
    return round(100.0 * jobs / total, 1) if total else 0.0


def compute_insights(bundle: dict[str, Any]) -> list[dict[str, str]]:
    """Generate insights from an analytics bundle (see ``build_analytics_bundle``)."""
    overview = bundle.get("overview", {})
    total_jobs = overview.get("total_jobs", 0)
    insights: list[dict[str, str]] = []

    if total_jobs == 0:
        return [{
            "title": "Awaiting data",
            "text": "No job postings have been collected yet. Run the ETL to begin analysis.",
            "basis": "analytics/overview/total_jobs",
        }]

    # Skills
    top_skills = bundle.get("top_skills", [])
    if top_skills:
        top = top_skills[0]
        insights.append({
            "title": f"{top['skill']} is the most demanded skill",
            "text": (
                f"{top['skill']} appears in {top['jobs']} job postings "
                f"({top['percentage']}% of the {total_jobs} collected postings)."
            ),
            "basis": "analytics/skills?limit=1",
        })
        pairs = [f"{s['skill']} ({s['jobs']})" for s in top_skills[1:3]]
        if pairs:
            insights.append({
                "title": "Demand is diversified",
                "text": f"Additional high-demand skills include {', '.join(pairs)}.",
                "basis": "analytics/skills?limit=3",
            })

    # Seniority
    seniority = bundle.get("jobs_by_seniority", [])
    known = [row for row in seniority if row.get("seniority") not in (None, "Unknown")]
    if known:
        top_seniority = known[0]
        additional = [row for row in known[1:4]]
        extra = ", ".join(f"{row['seniority']} ({row['count']})" for row in additional)
        insights.append({
            "title": f"{top_seniority['seniority']} roles lead the dataset",
            "text": (
                f"{top_seniority['seniority']} positions make up {top_seniority['count']} "
                f"postings ({_pct(top_seniority['count'], total_jobs)}%)."
                + (f" Also present: {extra}." if extra else "")
            ),
            "basis": "analytics/seniority?exclude_unknown=true",
        })

    # Remote / employment
    remote = bundle.get("jobs_by_remote_type", [])
    remote_count = sum(r["count"] for r in remote if r.get("remote_type") == "Remote")
    if remote_count:
        insights.append({
            "title": f"Remote positions represent {_pct(remote_count, total_jobs)}% of postings",
            "text": (
                f"{remote_count} of {total_jobs} postings are classified as remote "
                "based on explicit evidence in the posting text."
            ),
            "basis": "analytics/remote?type=Remote",
        })

    # Location
    locations = bundle.get("jobs_by_location", [])
    if locations and total_jobs:
        loc = locations[0]
        insights.append({
            "title": f"{loc['location']} is the most active location",
            "text": f"{loc['location']} appears in {loc['count']} collected postings.",
            "basis": "analytics/locations?limit=1",
        })

    # Company
    companies = bundle.get("jobs_by_company", [])
    if companies and total_jobs:
        comp = companies[0]
        insights.append({
            "title": f"{comp['company']} is the most active company",
            "text": f"{comp['company']} accounts for {comp['count']} postings ({_pct(comp['count'], total_jobs)}%).",
            "basis": "analytics/companies?limit=1",
        })

    # Skill combinations
    combos = bundle.get("skill_combinations", [])
    if combos:
        combo = combos[0]
        insights.append({
            "title": f"{combo['skill_a']} and {combo['skill_b']} co-occur frequently",
            "text": (
                f"{combo['skill_a']} + {combo['skill_b']} appear together in "
                f"{combo['co_occurrences']} postings."
            ),
            "basis": "analytics/skills/combinations?limit=1",
        })

    # Skills by seniority
    skills_by_seniority = bundle.get("skills_by_seniority", [])
    if skills_by_seniority:
        from collections import Counter
        leads = Counter()
        for row in skills_by_seniority:
            leads[(row["seniority"], row["skill"])] += row["count"]
        if leads:
            (sen, skill), count = leads.most_common(1)[0]
            insights.append({
                "title": f"{skill} is frequently requested for {sen} roles",
                "text": f"{skill} appears {count} time(s) across {sen} postings.",
                "basis": "analytics/skills/by-seniority?limit=1",
            })

    # Salary
    salary = (overview or {}).get("salary")
    if salary and salary.get("count"):
        insights.append({
            "title": f"Salary disclosed for {salary['count']} postings",
            "text": (
                f"Reported US base-salary ranges span ${int(salary['min_salary']):,} - "
                f"${int(salary['max_salary']):,} with an average midpoint of "
                f"${int(salary['avg_salary']):,}."
            ),
            "basis": "analytics/salary",
        })

    return insights