#!/usr/bin/env python3
"""Batch Job Posting Analyzer — fetch URLs from job_postings/, extract JD text, run analyzer.py.

Reads Windows .url shortcut files from job_postings/, fetches each page,
extracts the job description (filtering out noise), and invokes analyzer.py
for each one.

Usage:
    python batch_analyze.py
    python batch_analyze.py --dry-run
    python batch_analyze.py --force
"""

import configparser
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
JOB_POSTINGS_DIR = BASE_DIR / "job_postings"
RESUME_PATH = BASE_DIR / "resume" / "Resume_ATS_v2.pdf"
PROCESSED_FILE = BASE_DIR / "data" / "batch_processed.txt"
ANALYZER_SCRIPT = BASE_DIR / "analyzer.py"

console = Console()

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
REQUEST_TIMEOUT = 30
MAX_RETRIES = 2
MIN_JD_CHARS = 50
MIN_NOISE_SECTION_CHARS = 200
MIN_MAIN_BLOCK_CHARS = 200
MIN_JSONLD_DESCRIPTION_CHARS = 50
SUBPROCESS_TIMEOUT_SECONDS = 300
INTER_REQUEST_DELAY_SECONDS = 2
BACKOFF_BASE_SECONDS = 2
DRY_RUN_PREVIEW_CHARS = 300

# CSS selectors for elements to remove (noise)
NOISE_SELECTORS = [
    "nav", "header", "footer",
    "[role='navigation']", "[role='banner']", "[role='contentinfo']",
    "[class*='sidebar']", "[class*='Sidebar']",
    "[class*='footer']", "[class*='Footer']",
    "[class*='header']", "[class*='Header']",
    "[class*='nav-']", "[class*='Nav-']",
    "[class*='similar']", "[class*='Similar']",
    "[class*='recommendation']", "[class*='Recommendation']",
    "[class*='related']", "[class*='Related']",
    "[class*='salary']", "[class*='Salary']", "[class*='compensation']",
    "[class*='cookie']", "[class*='Cookie']",
    "[class*='banner']", "[class*='Banner']",
    "[class*='advert']", "[class*='Advert']", "[class*='-ad-']", "[class*='_ad_']",
    "[class*='signup']", "[class*='SignUp']", "[class*='sign-up']",
    "[class*='login']", "[class*='Login']",
    "[class*='share']", "[class*='Share']",
    "[class*='apply-btn']", "[class*='applyButton']",
    "[id*='footer']", "[id*='header']", "[id*='nav']",
    "[id*='sidebar']", "[id*='similar']", "[id*='cookie']",
    "script", "style", "noscript", "iframe", "svg",
]

# Patterns for short noise *sections* (headings/labels, not body text).
# Only applied to sections shorter than MIN_NOISE_SECTION_CHARS chars to avoid killing real JD content.
NOISE_SECTION_PATTERNS = re.compile(
    r"^(similar\s+jobs|related\s+jobs|you\s+might\s+also\s+like|"
    r"other\s+jobs|more\s+jobs|share\s+this\s+job|"
    r"report\s+this\s+job|save\s+this\s+job|"
    r"ähnliche\s+stellen|aehnliche\s+stellen|"
    r"jetzt\s+bewerben|diese\s+stelle\s+teilen|"
    r"weitere\s+stellen|mehr\s+jobs)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Site-specific CSS selector lists (tried in order; first match wins)
XING_SELECTORS = [
    '[class*="DescriptionContainer"]',
    '[class*="DescriptionWrapper"]',
    '[class*="description-module"]',
    '[data-testid="job-description"]',
    '[class*="jobDescription"]',
    '[class*="job-description"]',
    '[class*="posting-text"]',
    "article",
]
LINKEDIN_SELECTORS = [
    '[class*="description__text"]',
    '[class*="show-more-less-html"]',
    '[class*="job-description"]',
]
INDEED_SELECTORS = [
    "#jobDescriptionText",
    '[class*="jobsearch-jobDescriptionText"]',
    '[id*="jobDescription"]',
]
STEPSTONE_SELECTORS = [
    '[class*="listing-content"]',
    '[data-at="job-ad-content"]',
    '[class*="job-ad-content"]',
    "article",
]
GLASSDOOR_SELECTORS = [
    '[class*="jobDescriptionContent"]',
    '[class*="desc"]',
    "#JobDescriptionContainer",
]


# ---------------------------------------------------------------------------
# URL file parsing
# ---------------------------------------------------------------------------

def parse_url_file(filepath: Path) -> str | None:
    """Extract the URL from a Windows .url shortcut file."""
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read(filepath, encoding="utf-8")
        return parser.get("InternetShortcut", "URL")
    except (configparser.NoSectionError, configparser.NoOptionError):
        pass
    # Fallback: scan lines for URL=
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            if line.strip().upper().startswith("URL="):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return None


# ---------------------------------------------------------------------------
# HTTP fetching
# ---------------------------------------------------------------------------

def fetch_page(url: str, session: requests.Session) -> str | None:
    """Fetch a URL with retries. Returns HTML string or None on failure."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding
            return resp.text
        except requests.RequestException as e:
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_BASE_SECONDS * attempt)
            else:
                console.print(f"  [red]Failed after {MAX_RETRIES} attempts:[/red] {e}")
                return None
    return None


# ---------------------------------------------------------------------------
# Text cleaning helpers
# ---------------------------------------------------------------------------

def _remove_noise(soup: BeautifulSoup) -> BeautifulSoup:
    """Remove navigation, footers, sidebars, ads, and similar-jobs blocks."""
    for selector in NOISE_SELECTORS:
        for element in soup.select(selector):
            element.decompose()
    return soup


def _clean_text(text: str) -> str:
    """Normalize whitespace and remove short noise-only sections."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = "\n".join(lines)
    # Only filter out short sections that are purely noise headings/labels
    sections = text.split("\n\n")
    filtered = []
    for section in sections:
        if len(section) < MIN_NOISE_SECTION_CHARS and NOISE_SECTION_PATTERNS.search(section):
            continue
        filtered.append(section)
    return "\n\n".join(filtered).strip()


def _extract_main_content(soup: BeautifulSoup) -> str:
    """Generic fallback: remove noise, find the largest text block."""
    soup = _remove_noise(soup)
    best_element = None
    best_len = 0
    for element in soup.find_all(["main", "article", "section", "div"]):
        text = element.get_text(separator="\n", strip=True)
        if len(text) > best_len and len(text) > MIN_MAIN_BLOCK_CHARS:
            best_element = element
            best_len = len(text)
    if best_element:
        return _clean_text(best_element.get_text(separator="\n", strip=True))
    body = soup.find("body")
    if body:
        return _clean_text(body.get_text(separator="\n", strip=True))
    return ""


# ---------------------------------------------------------------------------
# Site-specific extractors
# ---------------------------------------------------------------------------

def _extract_jsonld_description(soup: BeautifulSoup) -> str | None:
    """Extract job description from JSON-LD structured data if present."""
    for script in soup.find_all("script", type="application/ld+json"):
        if script.string is None:
            continue
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and "description" in data:
                # Description may contain HTML — parse it to plain text
                desc_html = data["description"]
                desc_soup = BeautifulSoup(desc_html, "html.parser")
                text = desc_soup.get_text(separator="\n", strip=True)
                if len(text) >= MIN_JSONLD_DESCRIPTION_CHARS:
                    # Prepend title if available
                    title = data.get("title", "")
                    company = ""
                    org = data.get("hiringOrganization")
                    if isinstance(org, dict):
                        company = org.get("name", "")
                    header_parts = [p for p in [title, company] if p]
                    header = " — ".join(header_parts)
                    if header:
                        text = f"{header}\n\n{text}"
                    return _clean_text(text)
        except (json.JSONDecodeError, TypeError, AttributeError):
            continue
    return None


def _first_match(soup: BeautifulSoup, selectors: list[str]) -> str | None:
    """Return cleaned text from the first CSS selector that yields a non-empty match."""
    for selector in selectors:
        el = soup.select_one(selector)
        if el:
            text = _clean_text(el.get_text(separator="\n", strip=True))
            if text:
                return text
    return None


def extract_xing(soup: BeautifulSoup) -> str:
    """Extract JD from XING job posting pages.

    Prefers JSON-LD structured data; falls back to XING_SELECTORS in order, then generic content extraction.
    """
    jsonld = _extract_jsonld_description(soup)
    if jsonld:
        return jsonld
    return _first_match(soup, XING_SELECTORS) or _extract_main_content(soup)


def extract_linkedin(soup: BeautifulSoup) -> str:
    """Extract JD from LinkedIn job postings.

    Uses LINKEDIN_SELECTORS in order; falls back to generic content extraction.
    """
    return _first_match(soup, LINKEDIN_SELECTORS) or _extract_main_content(soup)


def extract_indeed(soup: BeautifulSoup) -> str:
    """Extract JD from Indeed job postings.

    Uses INDEED_SELECTORS in order; falls back to generic content extraction.
    """
    return _first_match(soup, INDEED_SELECTORS) or _extract_main_content(soup)


def extract_stepstone(soup: BeautifulSoup) -> str:
    """Extract JD from StepStone job postings.

    Uses STEPSTONE_SELECTORS in order; falls back to generic content extraction.
    """
    return _first_match(soup, STEPSTONE_SELECTORS) or _extract_main_content(soup)


def extract_glassdoor(soup: BeautifulSoup) -> str:
    """Extract JD from Glassdoor job postings.

    Uses GLASSDOOR_SELECTORS in order; falls back to generic content extraction.
    """
    return _first_match(soup, GLASSDOOR_SELECTORS) or _extract_main_content(soup)


def extract_generic(soup: BeautifulSoup) -> str:
    """Generic extractor for unknown job boards."""
    jsonld = _extract_jsonld_description(soup)
    if jsonld:
        return jsonld
    return _extract_main_content(soup)


# ---------------------------------------------------------------------------
# JD extraction dispatcher
# ---------------------------------------------------------------------------

def extract_jd_text(html: str, url: str) -> str | None:
    """Extract clean job description text from HTML, dispatching by site."""
    soup = BeautifulSoup(html, "html.parser")
    domain = urlparse(url).netloc.lower()

    if "xing.com" in domain:
        text = extract_xing(soup)
    elif "linkedin.com" in domain:
        text = extract_linkedin(soup)
    elif "indeed.com" in domain or "indeed.de" in domain:
        text = extract_indeed(soup)
    elif "stepstone" in domain:
        text = extract_stepstone(soup)
    elif "glassdoor" in domain:
        text = extract_glassdoor(soup)
    else:
        text = extract_generic(soup)

    if text and len(text) >= MIN_JD_CHARS:
        return text
    return None


# ---------------------------------------------------------------------------
# Analyzer invocation
# ---------------------------------------------------------------------------

def run_analyzer(jd_text: str, resume_path: Path, provider: str, model: str) -> bool:
    """Write JD to a temp file and invoke analyzer.py via subprocess."""
    temp_jd_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", prefix="jd_", dir=str(BASE_DIR),
            delete=False, encoding="utf-8",
        ) as temp_jd_file:
            temp_jd_file.write(jd_text)
            temp_jd_path = Path(temp_jd_file.name)

        result = subprocess.run(
            [sys.executable, str(ANALYZER_SCRIPT),
             "-r", str(resume_path),
             "-j", str(temp_jd_path),
             "-p", provider,
             "-m", model],
            cwd=str(BASE_DIR),
            timeout=SUBPROCESS_TIMEOUT_SECONDS,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        console.print(f"  [red]Analysis timed out ({SUBPROCESS_TIMEOUT_SECONDS // 60} min limit).[/red]")
        return False
    except Exception as e:
        console.print(f"  [red]Subprocess error:[/red] {e}")
        return False
    finally:
        if temp_jd_path:
            try:
                temp_jd_path.unlink(missing_ok=True)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Dedup tracking
# ---------------------------------------------------------------------------

def load_processed(path: Path) -> set[str]:
    """Load set of already-processed URLs from tracking file."""
    if not path.exists():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def save_processed(path: Path, url: str) -> None:
    """Append a successfully processed URL to the tracking file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(url + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Batch-analyze job postings against your resume.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and extract only, do not run analyzer")
    parser.add_argument("--force", action="store_true", help="Re-analyze even if URL was already processed")
    parser.add_argument("-p", "--provider", type=str, default="ollama",
                        choices=["openai", "anthropic", "deepseek", "ollama", "gemma"],
                        help="LLM provider (default: ollama)")
    parser.add_argument("-m", "--model", type=str, default="qwen2.5:14b",
                        help="Model name (default: qwen2.5:14b)")
    args = parser.parse_args()

    # Validate prerequisites
    if not JOB_POSTINGS_DIR.exists():
        console.print(f"[red]Error:[/red] Directory not found: {JOB_POSTINGS_DIR}")
        sys.exit(1)
    if not RESUME_PATH.exists():
        console.print(f"[red]Error:[/red] Resume not found: {RESUME_PATH}")
        sys.exit(1)
    if not ANALYZER_SCRIPT.exists():
        console.print(f"[red]Error:[/red] analyzer.py not found: {ANALYZER_SCRIPT}")
        sys.exit(1)

    # Discover URL files
    url_files = sorted(
        p for p in JOB_POSTINGS_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in (".url", ".txt")
    )
    if not url_files:
        console.print("[yellow]No job posting files found in job_postings/.[/yellow]")
        return

    # Load already-processed set
    processed = set() if args.force else load_processed(PROCESSED_FILE)

    # Parse all URLs
    jobs: list[tuple[Path, str]] = []
    skipped_parse = 0
    skipped_done = 0
    for url_file in url_files:
        url = parse_url_file(url_file)
        if not url:
            console.print(f"  [yellow]Skipping (no URL found):[/yellow] {url_file.name}")
            skipped_parse += 1
            continue
        if url in processed:
            skipped_done += 1
            continue
        jobs.append((url_file, url))

    # Summary panel
    console.print(Panel(
        f"[bold]Total files:[/bold]       {len(url_files)}\n"
        f"[bold]Already analyzed:[/bold]  {skipped_done}\n"
        f"[bold]Parse failures:[/bold]    {skipped_parse}\n"
        f"[bold]To process:[/bold]        {len(jobs)}",
        title="Batch Analysis",
        border_style="cyan",
    ))

    if not jobs:
        console.print("[green]All jobs already analyzed. Nothing to do.[/green]")
        return

    # Process each job
    session = requests.Session()
    results = {"success": 0, "fetch_fail": 0, "extract_fail": 0, "analyze_fail": 0}

    for i, (filepath, url) in enumerate(jobs, 1):
        console.print(Panel(
            f"[bold cyan]{filepath.stem}[/bold cyan]\n[dim]{url}[/dim]",
            title=f"Job {i}/{len(jobs)}",
            border_style="blue",
        ))

        # Fetch
        console.print("  Fetching page...")
        html = fetch_page(url, session)
        if not html:
            results["fetch_fail"] += 1
            continue

        # Extract JD text
        console.print("  Extracting job description...")
        jd_text = extract_jd_text(html, url)
        if not jd_text:
            console.print("  [red]Could not extract JD text (too short or empty).[/red]")
            results["extract_fail"] += 1
            continue
        console.print(f"  [dim]Extracted {len(jd_text):,} characters.[/dim]")

        if args.dry_run:
            console.print("  [yellow]Dry run — skipping analysis.[/yellow]")
            # Show a preview of the extracted text (ASCII-safe for Windows console)
            preview = (
                jd_text[:DRY_RUN_PREVIEW_CHARS]
                .replace("\n", " ")
                .encode("ascii", "replace")
                .decode("ascii")
            )
            console.print(f"  [dim]Preview: {preview}...[/dim]")
            results["success"] += 1
            continue

        # Run analyzer
        console.print("  Running analysis...")
        success = run_analyzer(jd_text, RESUME_PATH, args.provider, args.model)
        if success:
            results["success"] += 1
            save_processed(PROCESSED_FILE, url)
            console.print("  [green]Done.[/green]")
        else:
            results["analyze_fail"] += 1
            console.print("  [red]Analysis failed.[/red]")

        # Rate-limit between requests
        if i < len(jobs):
            time.sleep(INTER_REQUEST_DELAY_SECONDS)

    # Final summary
    table = Table(title="Batch Results", show_lines=False)
    table.add_column("Outcome", style="bold")
    table.add_column("Count", justify="right")
    table.add_row("[green]Successful[/green]", str(results["success"]))
    table.add_row("[red]Fetch failed[/red]", str(results["fetch_fail"]))
    table.add_row("[red]Extract failed[/red]", str(results["extract_fail"]))
    table.add_row("[red]Analysis failed[/red]", str(results["analyze_fail"]))
    console.print(table)


if __name__ == "__main__":
    main()
