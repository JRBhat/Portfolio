# 🤖 LLM-Powered Resume & Job Description Analyzer

CLI tool that analyzes your resume against job descriptions using multiple LLM providers — including free local models via Ollama — with real-time streaming output, structured history tracking, and batch processing for major job boards.

---

## 🧠 Project Overview

- **Problem**: Job seekers lack quick, structured feedback on how well their resume matches a specific job description and where the critical skill gaps are.
- **Type**: AI/LLM Application / Developer Tool
- **Approach**: PDF resume extraction → prompt assembly → LLM streaming analysis with an 8-step framework → structured JSON extraction from the response tail → append-only history persistence → aggregated skill-gap statistics across all analyses.

---

## 🎯 Objective

- Give actionable, structured feedback on resume-JD match quality without paying per-query API costs (local Ollama models are free).
- Track analyses over time to identify recurring skill gaps and the most in-demand skills across a job search campaign.

---

## 📊 Dataset

| Field | Details |
|---|---|
| Source | User-provided — resume PDFs + job description text (file or interactive paste) |
| Size | Not applicable — processes one resume + one JD per analysis run |
| Features | Resume skills and experience (extracted from PDF), JD requirements (text) |
| Target | Not applicable — this is a generative analysis tool, not a trained model |

Analysis history is stored locally as `data/history.jsonl` (append-only JSONL). No sample data is included in the repository.

---

## ⚙️ Methodology

1. **PDF Extraction** — `pdfplumber` extracts full text from the resume PDF.
2. **JD Input** — Reads from a file path (`-j`) or interactive multi-line paste (`-i`).
3. **Prompt Assembly** — Loads the user-supplied `prompt.md` (8-step analysis framework), appends a structured JSON output instruction as Step 9.
4. **LLM Streaming** — Sends the prompt to the selected provider; renders markdown output in real-time using `rich.live.Live`.
5. **JSON Extraction** — Parses the trailing ` ```json ``` ` block from the LLM response with repair heuristics (trailing commas, mismatched quotes). No second API call needed.
6. **Persistence** — Appends a structured record to `data/history.jsonl`; saves the full markdown analysis to `output/<job-title>_<timestamp>.md`.
7. **Statistics** — `--stats` mode aggregates history to surface top skill gaps, strongest skills, most demanded skills, and per-resume score breakdowns.

---

## 🧩 Code Structure

```
job_search_agent_with_Ollama_and_frontier_models/
├── analyzer.py          # Main CLI — PDF extraction, LLM client, streaming, history, stats
├── batch_analyze.py     # Batch processor — fetches JDs from job board URLs, invokes analyzer
├── prompt.md            # 8-step analysis prompt (user-supplied, not included in repo)
├── pixi.toml            # Conda-based package manifest (Python 3.11+, 4 CLI tasks)
├── .env                 # API keys (gitignored)
├── resume/              # PDF resume variants
├── job_postings/        # Windows .url shortcuts for batch mode
├── output/              # Per-analysis markdown reports (timestamped)
└── data/
    ├── history.jsonl        # Append-only analysis records
    └── batch_processed.txt  # URL deduplication tracker
```

---

## 🧠 Key Logic / Algorithm

The provider abstraction layer (`LLMClient`) is the key engineering decision: it uses the Anthropic SDK for Claude and the OpenAI-compatible endpoint interface for everything else (DeepSeek, Ollama, Gemma). This means any OpenAI-compatible local model can be swapped in by changing one environment variable — no code changes.Moreover, choosing Ollama models means no vendor locking.

JSON extraction uses repair heuristics rather than requiring the LLM to produce perfect JSON every time. The parser strips trailing commas, normalizes quotes, and handles ellipsis artifacts before attempting to parse — this makes the tool significantly more robust across models with different formatting habits.

Supported providers:

| Provider | Model | Requires |
|---|---|---|
| OpenAI | gpt-4o | `OPENAI_API_KEY` |
| Anthropic | claude-sonnet-4-6 | `ANTHROPIC_API_KEY` |
| DeepSeek | deepseek-chat | `DEEPSEEK_API_KEY` |
| Ollama | deepseek-r1:8b | Local Ollama server |
| Gemma | gemma3:12b | Local Ollama server |

---

## 📈 Results

> No example results are included in the repository.

The `--stats` mode produces:
- Total analyses and average match score across all runs
- Top 15 most-seen skill gaps (frequency ranked)
- Top 15 strongest skills across all analyzed JDs
- Per-resume variant breakdown (average score, min/max range)
- Match score timeline (chronological, bar-chart style)

Each individual analysis outputs an 8-step markdown report covering: job summary, required vs. candidate skills (strong/transferable/gap rated per skill), top strengths, critical gaps, fit score, confidence, and hiring likelihood assessment.

---

## ⚠️ Limitations

- **`prompt.md` not included** — the 8-step analysis prompt must be written and supplied by the user before running.
- **Batch mode is Windows-specific** — relies on `.url` shortcut file format from Windows Explorer for job board URLs.
- **Local model quality varies** — smaller Ollama models (8B parameters) produce less structured output than frontier models; JSON repair may still fail occasionally.
- **Job board scraping may break** — site-specific CSS selectors in `batch_analyze.py` are fragile and may stop working if job boards update their HTML structure.
- **Personal data in resume files** — real name, email, employer names, and university appear in resume PDFs; review before publishing publicly.

---

## 🛠️ Tech Stack

| Category | Tools |
|---|---|
| Language | Python 3.11+ |
| PDF Extraction | pdfplumber |
| LLM APIs | anthropic, openai (OpenAI-compatible) |
| Web Scraping | requests, beautifulsoup4 |
| Terminal UI | rich (Live streaming, tables, panels) |
| Config | python-dotenv |
| Package Management | pixi (conda-based) |

---

## ▶️ How to Run

```bash
# 1. Clone the repo
git clone "repo path"
cd job_search_agent_with_Ollama_and_frontier_models

# 2. Install dependencies via pixi
pixi install

# 3. Configure API keys in .env
echo "ANTHROPIC_API_KEY=your-key-here" > .env
# Or for local models, start Ollama: ollama serve

# 4. Write your prompt.md with the 8-step analysis framework

# 5. Single analysis
pixi run analyze -- -r resume/YourResume.pdf -j job_description.txt

# 6. Interactive JD input
pixi run analyze -- -r resume/YourResume.pdf -i

# 7. View aggregated stats
pixi run stats

# 8. Batch analyze from job_postings/ folder (Windows)
pixi run batch
```

---

## 💡 Business / Practical Value

A typical job search involves reviewing dozens of postings and mentally comparing each to your resume — a cognitively expensive, inconsistent process. This tool replaces that with a structured, repeatable analysis that surfaces specific skill gaps and match scores in under a minute per posting. The history tracking and `--stats` mode turn a single-use tool into a job search analytics dashboard, showing which skills keep appearing as gaps and which resume variant performs best across different JD types.

---

## 👤 Author

Jayesh Bhat · [LinkedIn](https://linkedin.com/in/your-profile) · [GitHub](https://github.com/your-username)
