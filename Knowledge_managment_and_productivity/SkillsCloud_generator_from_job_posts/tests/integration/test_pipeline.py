"""Integration tests: full add → query pipeline across multiple jobs"""

import pytest
from job_skills_tracker import JobSkillsTracker


@pytest.fixture
def tracker(tmp_path):
    return JobSkillsTracker(data_file=str(tmp_path / "integration_data.json"))


SAMPLE_JOBS = [
    (
        "Data Scientist role. Looking for Python, machine learning, pandas, and SQL experience.",
        "https://example.com/job/ds-1",
    ),
    (
        "Senior Data Scientist needed. Must know Python, deep learning, tensorflow, and statistics.",
        "https://example.com/job/ds-2",
    ),
    (
        "Data Engineer position. Skills: Python, SQL, spark, docker, and kafka required.",
        "https://example.com/job/de-1",
    ),
]


class TestMultiJobPipeline:
    def test_skill_counts_accumulate_across_jobs(self, tracker):
        for text, url in SAMPLE_JOBS:
            tracker.add_job_description(text, url)

        freqs = tracker.get_skills_frequencies()
        assert freqs["python"] == 3      # appears in all 3
        assert freqs["sql"] == 2         # job 1 and 3
        assert freqs["deep learning"] == 1  # job 2 only

    def test_skill_links_to_correct_job(self, tracker):
        for text, url in SAMPLE_JOBS:
            tracker.add_job_description(text, url)

        spark_jobs = tracker.get_jobs_for_skill("spark")
        assert len(spark_jobs) == 1
        assert spark_jobs[0]["url"] == "https://example.com/job/de-1"

    def test_job_title_frequencies_aggregate(self, tracker):
        for text, url in SAMPLE_JOBS:
            tracker.add_job_description(text, url)

        title_freqs = tracker.get_job_title_frequencies()
        ds_count = title_freqs.get("Data Scientist", 0) + title_freqs.get("Senior Data Scientist", 0)
        assert ds_count >= 2

    def test_skills_linked_to_correct_titles(self, tracker):
        for text, url in SAMPLE_JOBS:
            tracker.add_job_description(text, url)

        titles_for_spark = tracker.get_job_titles_for_skill("spark")
        assert "Data Engineer" in titles_for_spark

    def test_data_survives_reload(self, tmp_path):
        data_file = str(tmp_path / "data.json")
        t1 = JobSkillsTracker(data_file=data_file)
        for text, url in SAMPLE_JOBS:
            t1.add_job_description(text, url)

        t2 = JobSkillsTracker(data_file=data_file)
        assert t2.get_counts()["jobs"] == 3
        assert t2.get_skills_frequencies()["python"] == 3

    def test_clear_then_readd_resets_counts(self, tracker):
        for text, url in SAMPLE_JOBS:
            tracker.add_job_description(text, url)

        tracker.clear_all_data()
        assert tracker.get_counts()["jobs"] == 0

        tracker.add_job_description(SAMPLE_JOBS[0][0], SAMPLE_JOBS[0][1])
        assert tracker.get_counts()["jobs"] == 1
        assert tracker.get_skills_frequencies()["python"] == 1

    def test_get_jobs_for_title_returns_all_matching(self, tracker):
        for text, url in SAMPLE_JOBS:
            tracker.add_job_description(text, url)

        de_jobs = tracker.get_jobs_for_title("Data Engineer")
        assert len(de_jobs) == 1
        assert de_jobs[0]["url"] == "https://example.com/job/de-1"

    def test_skills_for_title_contain_expected_skills(self, tracker):
        for text, url in SAMPLE_JOBS:
            tracker.add_job_description(text, url)

        skills = tracker.get_skills_for_job_title("Data Engineer")
        assert "python" in skills
        assert "spark" in skills

    def test_total_job_count_matches_inputs(self, tracker):
        for text, url in SAMPLE_JOBS:
            tracker.add_job_description(text, url)
        assert tracker.get_counts()["jobs"] == len(SAMPLE_JOBS)
