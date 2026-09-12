from src.transform.classifiers import (
    classify_employment_type,
    classify_remote_type,
    classify_seniority,
)


class TestSeniority:
    def test_senior(self):
        assert classify_seniority("Senior Data Engineer") == "Senior"

    def test_sr_abbreviation(self):
        assert classify_seniority("Sr. Software Engineer") == "Senior"

    def test_intern(self):
        assert classify_seniority("Software Engineer Intern") == "Intern"
        assert classify_seniority("Internship Program") == "Intern"

    def test_entry_level(self):
        assert classify_seniority("Entry Level Analyst") == "Entry Level"

    def test_junior(self):
        assert classify_seniority("Junior Developer") == "Junior"

    def test_lead(self):
        assert classify_seniority("Analytical Lead, Shopping") == "Lead"

    def test_manager(self):
        assert classify_seniority("Engineering Manager") == "Manager"

    def test_director(self):
        assert classify_seniority("Director of Analytics") == "Director"

    def test_roman_levels(self):
        assert classify_seniority("Software Engineer II") == "Mid Level"
        assert classify_seniority("Software Engineer III") == "Senior"
        assert classify_seniority("Software Engineer V") == "Staff"

    def test_description_evidence_only_when_explicit(self):
        # A generic YouTube job listing with "5 years of experience" must NOT
        # be classified Senior (Google uses 5 years as a common baseline).
        desc = "Minimum qualifications: 5 years of experience in analytics."
        assert classify_seniority("Search Quality Analyst", desc) == "Unknown"

    def test_explicit_description_phrase(self):
        desc = "This is a senior role in our trust and safety organization."
        assert classify_seniority("Analyst, Trust and Safety", desc) == "Senior"

    def test_unknown(self):
        assert classify_seniority("Analyst, Consumer Insights") == "Unknown"

    def test_empty_title(self):
        assert classify_seniority("") == "Unknown"


class TestRemote:
    def test_remote(self):
        assert classify_remote_type("Data Analyst", "Remote role") == "Remote"

    def test_hybrid(self):
        assert classify_remote_type("Engineer", "Hybrid working model") == "Hybrid"

    def test_onsite(self):
        assert classify_remote_type("Engineer", "based in Denver") == "Onsite"

    def test_unknown(self):
        assert classify_remote_type("Analyst", "We work together to give everyone a voice.") == "Unknown"


class TestEmployment:
    def test_internship(self):
        assert classify_employment_type("Software Engineer Intern", "Internship") == "Internship"

    def test_part_time(self):
        assert classify_employment_type("Analyst", "This is a part-time role.") == "Part-time"

    def test_contract(self):
        assert classify_employment_type("Consultant", "Fixed-term contract for 12 months") == "Contract"

    def test_full_time(self):
        assert classify_employment_type("Analyst", "full-time position") == "Full-time"

    def test_unknown(self):
        assert classify_employment_type("Analyst", "You will work with stakeholders.") == "Unknown"