# Job Skills Tracker — Interactive Word Cloud

A desktop tool that extracts tech skills and job titles from job descriptions you paste in, then visualizes them as interactive, clickable word clouds. Designed to help job seekers identify the most in-demand skills across the roles they are targeting.

## Features

- **Skill extraction** — regex-based detection of 100+ tech skills with word-boundary matching to avoid false positives
- **Job title detection** — three-tier heuristic (explicit label → header lines → full-text fallback)
- **Dual word clouds** — one for skills (coloured with `viridis`), one for job titles (coloured with `plasma`)
- **Click-through drill-down** — click any word to open a popup showing the source job URLs and co-occurring titles/skills
- **Persistent storage** — all data is saved to a local JSON file; state survives restarts
- **Live statistics** — job count, unique skill count, and unique title count updated on every add

## Tech Stack

| Layer | Library |
|---|---|
| GUI | `tkinter` (stdlib) |
| Word cloud | `wordcloud` 1.9+ |
| Plotting | `matplotlib` 3.8+ |
| Data | `json` (stdlib), `pathlib` (stdlib) |
| Runtime | Python 3.14+ |
| Package mgr | [pixi](https://prefix.dev/) (conda-forge) |

## Installation

### Using pixi (recommended)

```bash
git clone https://github.com/your-username/SkillsCloud_generator_from_job_posts.git
cd SkillsCloud_generator_from_job_posts
pixi install
pixi run python job_skills_tracker.py
```

### Using pip

```bash
pip install -r requirements.txt
python job_skills_tracker.py
```

## Usage

1. **Run the app:**
   ```bash
   python job_skills_tracker.py
   ```

2. **Add a job description:**
   - Paste the job posting URL into the "Job URL" field
   - Copy and paste the full job description text into the text area
   - Click **Add Job Description**
   - The app extracts skills and job title, updates both word clouds, and saves to disk

3. **Explore the Skills word cloud** (first tab):
   - Word size reflects how often a skill appears across all saved jobs
   - Click any skill to see the job URLs that require it and which job titles demand it most

4. **Explore the Job Titles word cloud** (second tab):
   - Shows which roles appear most frequently in your saved jobs
   - Click any title to see the relevant job URLs and the skills most often listed for that role

5. **Reset:** Click **Clear All Data** to wipe the stored data and start fresh

## Demo

Load the bundled fictional dataset to see the app in action without adding real jobs:

```bash
python job_skills_tracker.py
```

Then copy `sample_data.json` to `job_skills_data.json` before launching:

```bash
cp sample_data.json job_skills_data.json
python job_skills_tracker.py
```

The sample data includes 4 fictional job postings across Data Scientist, Data Engineer, and Machine Learning Engineer roles.

## Data Storage

Your job data is saved to `job_skills_data.json` in the project directory. This file is excluded from version control (see `.gitignore`) because it contains your personal job search history.

**Schema:**
```json
{
  "skills": {
    "python": { "count": 4, "job_ids": [0, 1, 2, 3], "job_titles": { "Data Scientist": 2 } }
  },
  "job_titles": {
    "Data Scientist": { "count": 2, "job_ids": [0, 1], "skills": { "python": 2 } }
  },
  "jobs": [
    { "id": 0, "url": "https://...", "title": "Data Scientist", "skills": ["python", "sql"] }
  ]
}
```

## Customisation

Add skills to the `tech_skills` set in `JobSkillsTracker.__init__()`, or add job title patterns to `job_title_keywords`. Both are plain Python sets — no configuration files needed.

## Running Tests

```bash
pixi run python -m pytest tests/ -v
```

Tests cover the full `JobSkillsTracker` logic (data persistence, skill extraction, title detection, index updates, frequency queries, clear/reset). The GUI layer is excluded from automated tests as it requires a display.

```
tests/
├── conftest.py              # mocks tkinter + sets matplotlib Agg backend
├── unit/
│   └── test_tracker.py      # 46 unit tests
└── integration/
    └── test_pipeline.py     # 9 end-to-end pipeline tests
```

## Project Structure

```
SkillsCloud_generator_from_job_posts/
├── job_skills_tracker.py    # Main application (tracker logic + GUI)
├── sample_data.json         # Fictional demo dataset
├── requirements.txt         # pip dependencies
├── pixi.toml                # pixi/conda-forge environment
└── tests/
    ├── conftest.py
    ├── unit/
    │   └── test_tracker.py
    └── integration/
        └── test_pipeline.py
```

## Tips for Best Results

- Paste the **full** job description (requirements, qualifications, and responsibilities sections)
- Add **10–20+ jobs** to get meaningful frequency patterns in the word cloud
- Focus on roles you are actively targeting to surface the most relevant skills
- Use the title word cloud to identify whether companies label the same role differently (e.g. "ML Engineer" vs "Machine Learning Engineer")

## License

Free to use and modify for personal job search optimisation.
