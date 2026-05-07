#!/usr/bin/env python3
"""Resume vs Job Description Analyzer — CLI tool powered by LLM APIs.

Analyzes a candidate's resume against a job description using an 8-step
framework, streams formatted output, and tracks skill gaps over time.

Supports: OpenAI, Anthropic (Claude), and any OpenAI-compatible API.

Usage:
    python analyzer.py -r resume/Resume_Data_Scientist.pdf -j posting.txt
    python analyzer.py -r resume/Resume_Data_Scientist.pdf -i
    python analyzer.py --list
    python analyzer.py --stats
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pdfplumber
from dotenv import load_dotenv
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

try:
    from openai import (
        AuthenticationError as OpenAIAuthError,
        APIConnectionError as OpenAIConnError,
        RateLimitError as OpenAIRateLimit,
    )
except ImportError:
    OpenAIAuthError = OpenAIConnError = OpenAIRateLimit = Exception  # type: ignore[assignment,misc]

try:
    from anthropic import (
        AuthenticationError as AnthropicAuthError,
        APIConnectionError as AnthropicConnError,
        RateLimitError as AnthropicRateLimit,
    )
except ImportError:
    AnthropicAuthError = AnthropicConnError = AnthropicRateLimit = Exception  # type: ignore[assignment,misc]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
RESUME_DIR = BASE_DIR / "resume"
OUTPUT_DIR = BASE_DIR / "output"
DATA_DIR = BASE_DIR / "data"
HISTORY_FILE = DATA_DIR / "history.jsonl"
PROMPT_FILE = BASE_DIR / "prompt.md"
MAX_TOKENS_ANALYSIS = 8192
MAX_TOKENS_EXTRACT = 2048
MIN_JD_CHARS = 50
JD_PREVIEW_CHARS = 120
BAR_WIDTH = 20
BAR_FILLED = "█"
BAR_EMPTY = "░"
LIVE_REFRESH_PER_SECOND = 1
LIVE_CHUNK_FLUSH_INTERVAL = 5
SLUG_MAX_LEN = 80
JOB_TITLE_TRIM_FRACTION = 0.75   # used for filename slug


@dataclass(frozen=True)
class ProviderConfig:
    env_var: str | None
    default_model: str
    base_url: str | None


PROVIDERS: dict[str, ProviderConfig] = {
    "openai":    ProviderConfig("OPENAI_API_KEY",    "gpt-4o",            None),
    "anthropic": ProviderConfig("ANTHROPIC_API_KEY", "claude-sonnet-4-6", None),
    "deepseek":  ProviderConfig("DEEPSEEK_API_KEY",  "deepseek-chat",     "https://api.deepseek.com"),
    "ollama":    ProviderConfig(None,                "deepseek-r1:8b",    "http://localhost:11434/v1"),
    "gemma":     ProviderConfig(None,                "gemma3:12b",        "http://localhost:11434/v1"),
}

console = Console()

# ---------------------------------------------------------------------------
# LLM client abstraction
# ---------------------------------------------------------------------------


class LLMClient:
    """Unified client for OpenAI, Anthropic, DeepSeek, Ollama, and Gemma APIs.

    Selects the underlying SDK based on provider: Anthropic uses the official
    anthropic SDK; all others use the openai-compatible SDK. Local providers
    (ollama, gemma) require no API key. Expected env vars are declared in
    PROVIDERS[provider].env_var. The _api_type attribute maps to "openai" or
    "anthropic" and drives all branching in stream_chat / chat.
    """

    def __init__(self, provider: str, model: str):
        self.provider = provider
        self.model = model
        # DeepSeek and Ollama use the OpenAI-compatible API
        self._api_type = "anthropic" if provider == "anthropic" else "openai"

        if self._api_type == "openai":
            from openai import OpenAI
            base_url = PROVIDERS[provider].base_url
            client_options: dict = {}
            if base_url:
                client_options["base_url"] = base_url
            if provider in ("ollama", "gemma"):
                # Local Ollama models don't need an API key
                client_options["api_key"] = "ollama"
            self.client = OpenAI(**client_options)
        elif self._api_type == "anthropic":
            from anthropic import Anthropic
            self.client = Anthropic()
        else:
            console.print(f"[red]Error:[/red] Unknown provider: {provider}")
            sys.exit(1)

    def stream_chat(self, system_prompt: str, user_message: str, max_tokens: int) -> Iterator[str]:
        """Yields plain-text deltas as the model streams the response.

        Caller must consume the generator to receive output.
        """
        if self._api_type == "openai":
            stream = self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content

        elif self._api_type == "anthropic":
            with self.client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            ) as stream:
                for text in stream.text_stream:
                    yield text

    def chat(self, user_message: str, max_tokens: int) -> str:
        """Single non-streaming call; used when streaming is unnecessary (e.g. structured-data extraction fallback)."""
        if self._api_type == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.choices[0].message.content or ""

        elif self._api_type == "anthropic":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text
        return ""


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------

def extract_pdf_text(pdf_path: Path) -> str:
    """Extract all text from a PDF file using pdfplumber."""
    if not pdf_path.exists():
        console.print(f"[red]Error:[/red] File not found: {pdf_path}")
        sys.exit(1)
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    if not pages:
        console.print(
            f"[red]Error:[/red] Could not extract text from {pdf_path.name}. "
            "The PDF may be image-based (scanned)."
        )
        sys.exit(1)
    return "\n\n".join(pages)


# ---------------------------------------------------------------------------
# Resume listing
# ---------------------------------------------------------------------------

def list_resumes() -> None:
    """Print a table of available PDF resumes."""
    pdfs = sorted(RESUME_DIR.glob("*.pdf"))
    if not pdfs:
        console.print("[yellow]No PDF resumes found in resume/ directory.[/yellow]")
        return
    table = Table(title="Available Resumes", show_lines=False)
    table.add_column("#", style="dim", width=4)
    table.add_column("File", style="cyan")
    table.add_column("Size", justify="right", style="green")
    for index, pdf_path in enumerate(pdfs, 1):
        size_kb = pdf_path.stat().st_size / 1024
        table.add_row(str(index), pdf_path.name, f"{size_kb:.0f} KB")
    console.print(table)


# ---------------------------------------------------------------------------
# Job description input
# ---------------------------------------------------------------------------

def get_jd_interactive() -> str:
    """Read a job description from interactive multi-line input."""
    console.print(
        Panel(
            "[bold]Paste the job description below.[/bold]\n"
            "Press [cyan]Enter twice[/cyan] on an empty line to finish.",
            title="Job Description Input",
            border_style="blue",
        )
    )
    lines = []
    empty_count = 0
    try:
        while True:
            line = input()
            if line.strip() == "":
                empty_count += 1
                if empty_count >= 2:
                    break
                lines.append("")
            else:
                empty_count = 0
                lines.append(line)
    except EOFError:
        pass
    return "\n".join(lines).strip()


def get_jd_from_file(path: Path) -> str:
    """Read job description text from a file."""
    if not path.exists():
        console.print(f"[red]Error:[/red] JD file not found: {path}")
        sys.exit(1)
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        console.print(f"[red]Error:[/red] JD file is empty: {path}")
        sys.exit(1)
    return text


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def load_system_prompt() -> str:
    """Load prompt.md and strip the INPUTS placeholder section."""
    if not PROMPT_FILE.exists():
        console.print(f"[red]Error:[/red] prompt.md not found at {PROMPT_FILE}")
        sys.exit(1)
    raw = PROMPT_FILE.read_text(encoding="utf-8")
    # Remove the ## INPUTS section (placeholders) — we send data in user message
    cleaned = re.sub(
        r"## INPUTS.*?(?=## STEP 1)", "", raw, flags=re.DOTALL
    )
    return cleaned.strip()


JSON_SUFFIX_INSTRUCTION = """

---

## STEP 9: Structured Data (REQUIRED — MUST be the LAST section)

After completing all 8 steps above, output a fenced JSON block as the very last
thing in your response.  The block MUST start with ```json and end with ```.
Use this exact schema (no extra keys):

```json
{
  "job_title": "<string>",
  "company": "<string or null>",
  "match_score": <integer 0-100>,
  "confidence": "<Low|Medium|High>",
  "hiring_likelihood": "<High|Medium|Low>",
  "skills": [
    {"skill": "<name>", "required_level": "<level>", "candidate_level": "<level>", "match": "<strong|transferable|gap>"}
  ],
  "top_strengths": ["<skill1>", "<skill2>"],
  "top_gaps": ["<skill1>", "<skill2>"]
}
```
"""


def build_messages(resume_text: str, jd_text: str) -> tuple[str, str]:
    """Return (system_prompt, user_message) for the analysis API call."""
    system_prompt = load_system_prompt() + JSON_SUFFIX_INSTRUCTION
    user_message = (
        "## Resume:\n\n"
        f"{resume_text}\n\n"
        "---\n\n"
        "## Job Description:\n\n"
        f"{jd_text}\n\n"
        "---\n\n"
        "Please perform the complete 8-step analysis as described in your instructions, "
        "and include the STEP 9 structured JSON block at the very end."
    )
    return system_prompt, user_message


# ---------------------------------------------------------------------------
# Analysis (streaming)
# ---------------------------------------------------------------------------

def run_analysis(llm: LLMClient, system_prompt: str, user_message: str) -> str:
    """Stream the 8-step analysis and render live markdown.

    Uses a lower refresh rate and buffers chunks to reduce terminal flickering
    on Windows — the full markdown is only re-rendered once per second instead
    of on every tiny streaming chunk. Returns the full assembled markdown text
    for downstream parsing.
    """
    full_text = ""
    pending_chunks = 0

    console.print()
    with Live(console=console, refresh_per_second=LIVE_REFRESH_PER_SECOND, vertical_overflow="visible") as live:
        for text in llm.stream_chat(system_prompt, user_message, MAX_TOKENS_ANALYSIS):
            full_text += text
            pending_chunks += 1
            # Only push a visual update every N chunks to avoid excessive re-renders
            if pending_chunks >= LIVE_CHUNK_FLUSH_INTERVAL:
                live.update(Markdown(full_text))
                pending_chunks = 0
        # Final render with complete text
        live.update(Markdown(full_text))

    console.print()
    return full_text


# ---------------------------------------------------------------------------
# Structured data extraction (for stats)
# ---------------------------------------------------------------------------

def _repair_json(raw: str) -> str:
    """Best-effort repair of common JSON issues from small models."""
    # Strip markdown fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    # Remove trailing commas before } or ]
    raw = re.sub(r",\s*([}\]])", r"\1", raw)
    # Remove ... ellipsis in arrays
    raw = re.sub(r",?\s*\.{3}\s*", "", raw)
    # Strip any text before the first { or after the last }
    first_brace = raw.find("{")
    last_brace = raw.rfind("}")
    if first_brace != -1 and last_brace != -1:
        raw = raw[first_brace:last_brace + 1]
    # Replace single quotes with double quotes (but not inside words like don't)
    raw = re.sub(r"(?<![a-zA-Z])'|'(?![a-zA-Z])", '"', raw)
    return raw


def _try_parse_json(raw: str) -> dict | None:
    """Run _repair_json + json.loads over raw and each JSON object candidate; return first success."""
    try:
        return json.loads(_repair_json(raw))
    except json.JSONDecodeError:
        pass
    for candidate in re.findall(r"\{[\s\S]*\}", raw):
        try:
            return json.loads(_repair_json(candidate))
        except json.JSONDecodeError:
            pass
    return None


def extract_structured_data_from_text(analysis_text: str) -> dict | None:
    """Parse the structured JSON block that the LLM appended at the end of its analysis.

    This avoids a second API call — the JSON is already embedded in the response.
    Falls back to a broader regex search if the fenced block isn't found cleanly.
    """
    # Look for the last ```json ... ``` fenced block
    fenced_blocks = re.findall(r"```json\s*([\s\S]*?)```", analysis_text)
    if fenced_blocks:
        result = _try_parse_json(fenced_blocks[-1])
        if result is not None:
            return result

    result = _try_parse_json(analysis_text)
    if result is not None:
        return result

    console.print("[yellow]Warning:[/yellow] Could not parse structured data from analysis output.")
    return None


# Keep the old API-based extractor as a fallback for models that ignore the JSON instruction
EXTRACTION_PROMPT = """\
You are a data extraction assistant. Given the analysis below, extract structured data as JSON.

Return ONLY valid JSON with this exact schema (no markdown fences, no extra text):
{
  "job_title": "<string>",
  "company": "<string or null if unknown>",
  "match_score": <integer 0-100>,
  "confidence": "<Low|Medium|High>",
  "hiring_likelihood": "<High|Medium|Low>",
  "skills": [
    {"skill": "<name>", "required_level": "<level>", "candidate_level": "<level>", "match": "<strong|transferable|gap>"}
  ],
  "top_strengths": ["<skill1>", "<skill2>", ...],
  "top_gaps": ["<skill1>", "<skill2>", ...]
}

Analysis:
"""


def extract_structured_data_via_api(llm: LLMClient, analysis_text: str) -> dict | None:
    """Fallback: make a separate API call to extract structured JSON."""
    try:
        raw = llm.chat(EXTRACTION_PROMPT + analysis_text, MAX_TOKENS_EXTRACT)
        result = _try_parse_json(raw)
        if result is not None:
            return result
        console.print("[yellow]Warning:[/yellow] Could not parse structured data from model output.")
        return None
    except (json.JSONDecodeError, AttributeError, ValueError) as e:
        console.print(f"[yellow]Warning:[/yellow] Extraction API call failed: {e}")
        return None


# ---------------------------------------------------------------------------
# History persistence
# ---------------------------------------------------------------------------

def save_history(record: dict) -> None:
    """Append a JSON record to history.jsonl."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with HISTORY_FILE.open("a", encoding="utf-8") as history_file:
        history_file.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_history() -> list[dict]:
    """Load all records from history.jsonl, skipping corrupt lines."""
    if not HISTORY_FILE.exists():
        return []
    records = []
    with HISTORY_FILE.open(encoding="utf-8") as history_file:
        for line_number, line in enumerate(history_file, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                console.print(f"[yellow]Warning:[/yellow] Skipping corrupt line {line_number} in history.")
    return records


# ---------------------------------------------------------------------------
# Stats display
# ---------------------------------------------------------------------------

def _render_bar(pct: float, width: int = BAR_WIDTH) -> str:
    """Render a filled/empty progress bar string for a percentage value."""
    filled = int(pct * width / 100)
    return BAR_FILLED * filled + BAR_EMPTY * (width - filled)


def show_stats() -> None:
    """Display aggregated stats from all past analyses."""
    records = load_history()
    if not records:
        console.print("[yellow]No analysis history found.[/yellow] Run some analyses first.")
        return

    total = len(records)
    scores = [r["match_score"] for r in records if "match_score" in r]
    avg_score = sum(scores) / len(scores) if scores else 0
    dates = [r.get("date", "?") for r in records]

    # --- Summary ---
    console.print(Panel(
        f"[bold]Total analyses:[/bold] {total}\n"
        f"[bold]Average match score:[/bold] {avg_score:.0f}%\n"
        f"[bold]Date range:[/bold] {min(dates)} to {max(dates)}",
        title="Analysis Summary",
        border_style="cyan",
    ))

    # --- Skill gap frequency ---
    gap_counter: Counter = Counter()
    strength_counter: Counter = Counter()
    demanded_counter: Counter = Counter()

    for record in records:
        for skill_entry in record.get("skills", []):
            skill_name = skill_entry.get("skill", "")
            match_type = skill_entry.get("match", "").lower()
            demanded_counter[skill_name] += 1
            if match_type == "gap":
                gap_counter[skill_name] += 1
            elif match_type == "strong":
                strength_counter[skill_name] += 1
        # Also count from top_gaps / top_strengths as fallback
        for gap_skill in record.get("top_gaps", []):
            gap_counter[gap_skill] += 1
        for strength_skill in record.get("top_strengths", []):
            strength_counter[strength_skill] += 1

    # Skill Gaps table
    if gap_counter:
        gaps_table = Table(title="Most Common Skill Gaps (across all analyses)", show_lines=False)
        gaps_table.add_column("Skill", style="red")
        gaps_table.add_column("Appearances", justify="right")
        gaps_table.add_column("Frequency", justify="right", style="yellow")
        gaps_table.add_column("Bar", style="red")
        for skill, count in gap_counter.most_common(15):
            pct = count / total * 100
            gaps_table.add_row(skill, f"{count}/{total}", f"{pct:.0f}%", _render_bar(pct))
        console.print(gaps_table)

    # Strengths table
    if strength_counter:
        strengths_table = Table(title="Strongest Skills (most frequently matched)", show_lines=False)
        strengths_table.add_column("Skill", style="green")
        strengths_table.add_column("Appearances", justify="right")
        strengths_table.add_column("Frequency", justify="right", style="cyan")
        strengths_table.add_column("Bar", style="green")
        for skill, count in strength_counter.most_common(15):
            pct = count / total * 100
            strengths_table.add_row(skill, f"{count}/{total}", f"{pct:.0f}%", _render_bar(pct))
        console.print(strengths_table)

    # Top demanded skills
    if demanded_counter:
        demanded_table = Table(title="Most Demanded Skills (across all JDs)", show_lines=False)
        demanded_table.add_column("Skill", style="cyan")
        demanded_table.add_column("Appearances", justify="right")
        demanded_table.add_column("Frequency", justify="right")
        for skill, count in demanded_counter.most_common(15):
            pct = count / total * 100
            demanded_table.add_row(skill, f"{count}/{total}", f"{pct:.0f}%")
        console.print(demanded_table)

    # Per-resume breakdown
    resume_scores: defaultdict[str, list[int]] = defaultdict(list)
    for record in records:
        if "match_score" in record:
            resume_scores[record.get("resume", "unknown")].append(record["match_score"])

    if resume_scores:
        resumes_table = Table(title="Match Scores by Resume Variant", show_lines=False)
        resumes_table.add_column("Resume", style="cyan")
        resumes_table.add_column("Analyses", justify="right")
        resumes_table.add_column("Avg Score", justify="right", style="bold")
        resumes_table.add_column("Range", justify="right")
        for resume_name, resume_scores_list in sorted(resume_scores.items()):
            avg = sum(resume_scores_list) / len(resume_scores_list)
            resumes_table.add_row(
                resume_name,
                str(len(resume_scores_list)),
                f"{avg:.0f}%",
                f"{min(resume_scores_list)}%–{max(resume_scores_list)}%",
            )
        console.print(resumes_table)

    # Match score timeline
    console.print(Panel("[bold]Match Score Timeline[/bold]", border_style="dim"))
    for record in records:
        date = record.get("date", "?")
        score = record.get("match_score", 0)
        title = record.get("job_title", "?")
        company = record.get("company") or ""
        label = f"{title} @ {company}" if company else title
        console.print(f"  {date}  {_render_bar(score)} {score}%  [dim]{label}[/dim]")
    console.print()


# ---------------------------------------------------------------------------
# Save analysis markdown
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    """Turn a string into a safe filename slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text[:SLUG_MAX_LEN].strip("_")


def save_analysis(
    text: str,
    resume_name: str,
    job_title: str | None = None,
    company: str | None = None,
) -> Path:
    """Save the full analysis as a markdown file in output/.

    Filename precedence: job_title (first JOB_TITLE_TRIM_FRACTION of text) →
    company → resume stem. Timestamp suffix prevents collisions.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if job_title:
        name = _slugify(job_title[:int(len(job_title) * JOB_TITLE_TRIM_FRACTION)])
    elif company:
        name = _slugify(company)
    else:
        name = Path(resume_name).stem

    filename = f"{name}_{timestamp}.md"
    filepath = OUTPUT_DIR / filename
    filepath.write_text(text, encoding="utf-8")
    return filepath


# ---------------------------------------------------------------------------
# Provider detection
# ---------------------------------------------------------------------------

def detect_provider() -> str | None:
    """Auto-detect provider from available API keys in environment."""
    for name, config in PROVIDERS.items():
        if config.env_var and os.environ.get(config.env_var):
            return name
    return None


# ---------------------------------------------------------------------------
# Main CLI helpers
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Analyze your resume against a job description using AI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python analyzer.py -r resume/Resume_Data_Scientist.pdf -j posting.txt\n"
            "  python analyzer.py -r resume/Resume_ATS_v2.pdf -i\n"
            "  python analyzer.py -r resume/Resume_ATS_v2.pdf --provider openai\n"
            "  python analyzer.py --list\n"
            "  python analyzer.py --stats\n"
        ),
    )
    parser.add_argument("-r", "--resume", type=str, help="Path to resume PDF")
    parser.add_argument("-j", "--jd", type=str, help="Path to job description text file")
    parser.add_argument("-i", "--interactive", action="store_true", help="Paste JD interactively")
    parser.add_argument("-l", "--list", action="store_true", help="List available resume PDFs")
    parser.add_argument("-s", "--save", action="store_true", help="(deprecated — analyses are now always saved)")
    parser.add_argument("--stats", action="store_true", help="Show aggregated stats from past analyses")
    parser.add_argument(
        "-p", "--provider", type=str, choices=list(PROVIDERS),
        help="LLM provider (default: auto-detect from API keys)",
    )
    parser.add_argument(
        "-m", "--model", type=str, default=None,
        help="Model name (default: gpt-4o / claude-sonnet-4-6 / deepseek-chat / deepseek-r1:8b / gemma3:12b)",
    )
    return parser


def _resolve_provider_and_model(args: argparse.Namespace) -> tuple[str, str]:
    """Resolve provider and model from args, exiting with an error if none can be detected."""
    provider = args.provider or detect_provider()
    if not provider:
        console.print(
            "[red]Error:[/red] No API key found.\n"
            "Set one of the following in your [cyan].env[/cyan] file:\n"
            "  OPENAI_API_KEY=sk-...\n"
            "  ANTHROPIC_API_KEY=sk-ant-...\n"
            "  DEEPSEEK_API_KEY=sk-...\n"
            "Or use [cyan]--provider ollama[/cyan] for local models (no key needed).\n"
        )
        sys.exit(1)

    config = PROVIDERS[provider]
    if config.env_var and not os.environ.get(config.env_var):
        console.print(f"[red]Error:[/red] {config.env_var} not set. Add it to your .env file.")
        sys.exit(1)

    model = args.model or config.default_model
    return provider, model


def _load_jd(args: argparse.Namespace) -> str:
    """Load job description text from file or interactive input."""
    if args.jd:
        return get_jd_from_file(Path(args.jd))
    return get_jd_interactive()


# ---------------------------------------------------------------------------
# Main CLI
# ---------------------------------------------------------------------------

def main() -> None:
    load_dotenv()

    parser = _build_arg_parser()
    args = parser.parse_args()

    # --- List mode ---
    if args.list:
        list_resumes()
        return

    # --- Stats mode ---
    if args.stats:
        show_stats()
        return

    # --- Analysis mode: validate inputs ---
    if not args.resume:
        console.print("[red]Error:[/red] --resume / -r is required for analysis.")
        console.print("Use [cyan]--list[/cyan] to see available resumes, or [cyan]--stats[/cyan] for history.")
        sys.exit(1)

    provider, model = _resolve_provider_and_model(args)

    resume_path = Path(args.resume)
    if resume_path.suffix.lower() != ".pdf":
        console.print("[red]Error:[/red] Resume must be a PDF file.")
        sys.exit(1)

    # Extract resume text
    console.print(f"[dim]Extracting text from[/dim] [cyan]{resume_path.name}[/cyan]...")
    resume_text = extract_pdf_text(resume_path)
    console.print(f"[dim]Extracted {len(resume_text):,} characters from resume.[/dim]")

    # Get job description
    jd_text = _load_jd(args)

    if len(jd_text) < MIN_JD_CHARS:
        console.print(
            f"[red]Error:[/red] Job description is too short (< {MIN_JD_CHARS} chars). "
            "Please provide more text."
        )
        sys.exit(1)

    # Show summary
    jd_preview = (
        jd_text[:JD_PREVIEW_CHARS].replace("\n", " ")
        + ("..." if len(jd_text) > JD_PREVIEW_CHARS else "")
    )
    console.print(
        Panel(
            f"[bold]Resume:[/bold]    {resume_path.name}\n"
            f"[bold]Provider:[/bold]  {provider}\n"
            f"[bold]Model:[/bold]     {model}\n"
            f"[bold]JD:[/bold]        {jd_preview}",
            title="Starting Analysis",
            border_style="green",
        )
    )

    # Create LLM client and run analysis
    llm = LLMClient(provider, model)

    try:
        system_prompt, user_message = build_messages(resume_text, jd_text)
        analysis_text = run_analysis(llm, system_prompt, user_message)
    except KeyboardInterrupt:
        console.print("\n[yellow]Analysis cancelled.[/yellow]")
        sys.exit(0)
    except (OpenAIAuthError, AnthropicAuthError):
        console.print(f"[red]Error:[/red] Invalid API key for {provider}. Check your .env file.")
        sys.exit(1)
    except (OpenAIRateLimit, AnthropicRateLimit):
        console.print(
            "[red]Error:[/red] Quota exceeded or rate limited.\n"
            "You may need to add credits to your API account, or try a free provider:\n"
            "  [cyan]--provider ollama -m qwen2.5:7b[/cyan]  (free, local)\n"
            "  [cyan]--provider deepseek[/cyan]              (very cheap)"
        )
        sys.exit(1)
    except (OpenAIConnError, AnthropicConnError):
        console.print("[red]Error:[/red] Cannot reach API. Check your internet connection.")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {type(e).__name__}: {e}")
        sys.exit(1)

    console.print(Panel("[bold green]Analysis complete![/bold green]", border_style="green"))

    # Extract structured data from the analysis text (no extra API call needed)
    console.print("[dim]Extracting structured data for stats tracking...[/dim]")
    structured = extract_structured_data_from_text(analysis_text)
    if not structured:
        # Fallback: make a separate API call (for models that ignored the JSON instruction)
        console.print("[dim]Inline JSON not found — falling back to API extraction...[/dim]")
        structured = extract_structured_data_via_api(llm, analysis_text)
    if structured:
        record = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "resume": resume_path.name,
            "provider": provider,
            "model": model,
            **structured,
        }
        save_history(record)
        console.print("[dim]Saved to analysis history.[/dim]")
    else:
        console.print("[yellow]Structured data extraction failed — analysis not saved to history.[/yellow]")

    # Save analysis as markdown (uses first portion of extracted job_title as filename)
    job_title = structured.get("job_title") if structured else None
    company = structured.get("company") if structured else None
    filepath = save_analysis(analysis_text, resume_path.name, job_title, company)
    console.print(f"[green]Analysis saved to:[/green] {filepath}")


if __name__ == "__main__":
    main()
