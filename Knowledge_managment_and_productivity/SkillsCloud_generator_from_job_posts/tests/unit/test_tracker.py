"""Unit tests for JobSkillsTracker"""

import json
import pytest
from pathlib import Path
from job_skills_tracker import JobSkillsTracker


@pytest.fixture
def tracker(tmp_path):
    return JobSkillsTracker(data_file=str(tmp_path / "test_data.json"))


@pytest.fixture
def populated_tracker(tmp_path):
    t = JobSkillsTracker(data_file=str(tmp_path / "test_data.json"))
    t.add_job_description(
        "Data Scientist role. We need Python, SQL, machine learning, and pandas expertise.",
        "https://example.com/job/1",
    )
    return t


class TestDataPersistence:
    def test_load_creates_default_when_file_missing(self, tmp_path):
        t = JobSkillsTracker(data_file=str(tmp_path / "nonexistent.json"))
        assert t.skills_data == {"skills": {}, "job_titles": {}, "jobs": []}

    def test_load_handles_corrupt_json(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{not valid json")
        t = JobSkillsTracker(data_file=str(bad_file))
        assert t.skills_data == {"skills": {}, "job_titles": {}, "jobs": []}

    def test_save_and_reload(self, tmp_path):
        data_file = str(tmp_path / "data.json")
        t = JobSkillsTracker(data_file=data_file)
        t.add_job_description("Python and SQL required", "https://example.com/job/1")

        t2 = JobSkillsTracker(data_file=data_file)
        assert len(t2.skills_data["jobs"]) == 1
        assert "python" in t2.skills_data["skills"]

    def test_load_patches_missing_keys_in_partial_file(self, tmp_path):
        partial = tmp_path / "partial.json"
        partial.write_text('{"skills": {}}')
        t = JobSkillsTracker(data_file=str(partial))
        assert "job_titles" in t.skills_data
        assert "jobs" in t.skills_data

    def test_data_file_stored_as_path(self, tracker):
        assert isinstance(tracker.data_file, Path)


class TestSkillExtraction:
    def test_detects_single_skill(self, tracker):
        assert "python" in tracker.extract_skills("We need a Python developer")

    def test_detects_multiple_skills(self, tracker):
        skills = tracker.extract_skills("Experience with Python, SQL, and Docker required")
        assert {"python", "sql", "docker"}.issubset(skills)

    def test_case_insensitive(self, tracker):
        assert "python" in tracker.extract_skills("PYTHON DEVELOPER NEEDED")

    def test_word_boundary_prevents_false_match_on_r(self, tracker):
        # "r" must not match inside words like "framework" or "very"
        skills = tracker.extract_skills("Very good Java framework skills here")
        assert "r" not in skills

    def test_empty_text_returns_empty_set(self, tracker):
        assert tracker.extract_skills("") == set()

    def test_no_skills_in_generic_text(self, tracker):
        assert tracker.extract_skills("We offer a great salary and benefits") == set()

    def test_multiword_skill_detection(self, tracker):
        assert "machine learning" in tracker.extract_skills("5 years of machine learning experience")

    def test_returns_set(self, tracker):
        result = tracker.extract_skills("Python Python Python")
        assert isinstance(result, set)
        assert result == {"python"}


class TestJobTitleExtraction:
    def test_extracts_from_explicit_title_field(self, tracker):
        text = "Title: Senior Data Scientist\nJob Description..."
        assert tracker.extract_job_title(text) == "Senior Data Scientist"

    def test_extracts_from_first_lines(self, tracker):
        text = "Data Engineer - Full Time\nCompany: Acme Corp\nWe are looking for..."
        assert tracker.extract_job_title(text) == "Data Engineer"

    def test_fallback_to_full_text(self, tracker):
        text = "About the role\nWe are hiring a Machine Learning Engineer to join our team"
        assert tracker.extract_job_title(text) == "Machine Learning Engineer"

    def test_returns_unspecified_for_unknown_title(self, tracker):
        text = "Join our marketing team as a content writer and copyeditor"
        assert tracker.extract_job_title(text) == "Unspecified Role"

    def test_prefers_longer_match(self, tracker):
        # "Senior Data Scientist" should win over "Data Scientist"
        text = "Senior Data Scientist role available immediately"
        title = tracker.extract_job_title(text)
        assert title == "Senior Data Scientist"

    def test_title_case_output(self, tracker):
        text = "data scientist needed"
        title = tracker.extract_job_title(text)
        assert title == title.title()


class TestAddJobDescription:
    def test_adds_job_to_jobs_list(self, tracker):
        tracker.add_job_description("Python and SQL required", "https://example.com/1")
        assert len(tracker.skills_data["jobs"]) == 1

    def test_job_stores_url(self, tracker):
        url = "https://example.com/1"
        tracker.add_job_description("Python developer needed", url)
        assert tracker.skills_data["jobs"][0]["url"] == url

    def test_updates_skills_index(self, tracker):
        tracker.add_job_description("Python and SQL required", "https://example.com/1")
        assert "python" in tracker.skills_data["skills"]
        assert tracker.skills_data["skills"]["python"]["count"] == 1

    def test_increments_count_on_repeated_skill(self, tracker):
        tracker.add_job_description("Python developer needed", "https://example.com/1")
        tracker.add_job_description("We need a Python expert", "https://example.com/2")
        assert tracker.skills_data["skills"]["python"]["count"] == 2

    def test_returns_extracted_skills(self, tracker):
        result = tracker.add_job_description("Python and SQL required", "https://example.com/1")
        assert "python" in result["skills"]
        assert "sql" in result["skills"]

    def test_returns_empty_skills_when_none_found(self, tracker):
        result = tracker.add_job_description("No tech content here", "https://example.com/1")
        assert result["skills"] == {}

    def test_job_still_added_when_no_skills_found(self, tracker):
        tracker.add_job_description("No tech content here", "https://example.com/1")
        assert len(tracker.skills_data["jobs"]) == 1

    def test_updates_job_titles_index(self, tracker):
        tracker.add_job_description(
            "Data Scientist role. Python and machine learning required.",
            "https://example.com/1",
        )
        assert "Data Scientist" in tracker.skills_data["job_titles"]

    def test_tracks_job_ids_per_skill(self, tracker):
        tracker.add_job_description("Python developer role", "https://example.com/1")
        assert 0 in tracker.skills_data["skills"]["python"]["job_ids"]

    def test_sequential_job_ids(self, tracker):
        tracker.add_job_description("Python needed", "https://example.com/1")
        tracker.add_job_description("SQL needed", "https://example.com/2")
        assert tracker.skills_data["jobs"][0]["id"] == 0
        assert tracker.skills_data["jobs"][1]["id"] == 1


class TestFrequencyQueries:
    def test_get_skills_frequencies_returns_counts(self, populated_tracker):
        freqs = populated_tracker.get_skills_frequencies()
        assert freqs["python"] == 1
        assert freqs["sql"] == 1

    def test_get_skills_frequencies_empty_when_no_data(self, tracker):
        assert tracker.get_skills_frequencies() == {}

    def test_get_job_title_frequencies_returns_at_least_one(self, populated_tracker):
        freqs = populated_tracker.get_job_title_frequencies()
        assert len(freqs) >= 1

    def test_get_jobs_for_skill_returns_correct_url(self, populated_tracker):
        jobs = populated_tracker.get_jobs_for_skill("python")
        assert len(jobs) == 1
        assert jobs[0]["url"] == "https://example.com/job/1"

    def test_get_jobs_for_nonexistent_skill(self, tracker):
        assert tracker.get_jobs_for_skill("cobol") == []

    def test_get_jobs_for_title_returns_jobs(self, populated_tracker):
        title = list(populated_tracker.skills_data["job_titles"].keys())[0]
        jobs = populated_tracker.get_jobs_for_title(title)
        assert len(jobs) == 1

    def test_get_jobs_for_unknown_title(self, tracker):
        assert tracker.get_jobs_for_title("Astronaut") == []

    def test_get_skills_for_job_title(self, populated_tracker):
        title = list(populated_tracker.skills_data["job_titles"].keys())[0]
        skills = populated_tracker.get_skills_for_job_title(title)
        assert "python" in skills

    def test_get_skills_for_unknown_title(self, tracker):
        assert tracker.get_skills_for_job_title("Astronaut") == {}

    def test_get_job_titles_for_skill(self, populated_tracker):
        titles = populated_tracker.get_job_titles_for_skill("python")
        assert len(titles) >= 1

    def test_get_job_titles_for_unknown_skill(self, tracker):
        assert tracker.get_job_titles_for_skill("cobol") == {}


class TestGetCounts:
    def test_returns_zero_counts_when_empty(self, tracker):
        assert tracker.get_counts() == {"jobs": 0, "skills": 0, "job_titles": 0}

    def test_counts_update_after_adding_job(self, tracker):
        tracker.add_job_description("Python and SQL developer", "https://example.com/1")
        counts = tracker.get_counts()
        assert counts["jobs"] == 1
        assert counts["skills"] >= 2

    def test_jobs_count_increments_even_without_skills(self, tracker):
        tracker.add_job_description("No tech here", "https://example.com/1")
        assert tracker.get_counts()["jobs"] == 1


class TestClearAllData:
    def test_clears_all_data(self, populated_tracker):
        populated_tracker.clear_all_data()
        assert populated_tracker.get_counts() == {"jobs": 0, "skills": 0, "job_titles": 0}

    def test_clear_persists_to_disk(self, tmp_path):
        data_file = str(tmp_path / "data.json")
        t = JobSkillsTracker(data_file=data_file)
        t.add_job_description("Python developer needed", "https://example.com/1")
        t.clear_all_data()

        t2 = JobSkillsTracker(data_file=data_file)
        assert t2.get_counts() == {"jobs": 0, "skills": 0, "job_titles": 0}

    def test_can_add_after_clear(self, populated_tracker):
        populated_tracker.clear_all_data()
        populated_tracker.add_job_description("Python needed", "https://example.com/1")
        assert populated_tracker.get_counts()["jobs"] == 1
