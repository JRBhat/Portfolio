"""
Test suite for tracker.categorizer.Categorizer

Tests the logic that maps (exe_name, window_title) pairs to activity
categories: 'work', 'leisure', 'system', 'unknown'.

Run with: pytest tests/test_categorizer.py -v
"""
import pytest

from tracker.categorizer import Categorizer


@pytest.fixture
def cat():
    """Return a fresh Categorizer instance."""
    return Categorizer()


# ── Exact-exe matching ────────────────────────────────────────────────────────

def test_known_ide_is_work(cat):
    """
    code.exe, pycharm64.exe, devenv.exe → 'work'

    Verifies that IDEs in WORK_EXES are always categorised as work regardless
    of the window title.
    """
    assert cat.categorize("code.exe", "main.py") == "work"
    assert cat.categorize("pycharm64.exe", "Project") == "work"
    assert cat.categorize("devenv.exe", "Solution") == "work"


def test_known_leisure_exe_is_leisure(cat):
    """
    spotify.exe, steam.exe, discord.exe → 'leisure'

    Verifies that apps in LEISURE_EXES return 'leisure' for any title.
    """
    assert cat.categorize("spotify.exe", "Now Playing") == "leisure"
    assert cat.categorize("steam.exe", "Library") == "leisure"
    assert cat.categorize("discord.exe", "General") == "leisure"


def test_system_exe_is_system(cat):
    """
    explorer.exe, taskmgr.exe, "desktop", "elevated_process" → 'system'

    Verifies that SYSTEM_EXES are labelled 'system' regardless of title.
    """
    assert cat.categorize("explorer.exe", "Documents") == "system"
    assert cat.categorize("taskmgr.exe", "Performance") == "system"
    assert cat.categorize("desktop", "") == "system"
    assert cat.categorize("elevated_process", "") == "system"


# ── Browser title-based refinement ───────────────────────────────────────────

def test_browser_with_github_title_is_work(cat):
    """
    chrome.exe + "GitHub – Pull Request #42" → 'work'

    Browsers are in BROWSER_EXES (not WORK_EXES). The categorizer should
    fall through to title-keyword matching and return 'work'.
    """
    assert cat.categorize("chrome.exe", "GitHub – Pull Request #42") == "work"


def test_browser_with_youtube_title_is_leisure(cat):
    """
    msedge.exe + "YouTube – My Playlist" → 'leisure'
    """
    assert cat.categorize("msedge.exe", "YouTube – My Playlist") == "leisure"


def test_browser_with_unknown_title_is_leisure(cat):
    """
    firefox.exe + "some internal wiki page" → 'leisure'

    When no keyword matches, browsers default to 'leisure'.
    """
    assert cat.categorize("firefox.exe", "some internal wiki page") == "leisure"


def test_browser_title_check_is_case_insensitive(cat):
    """
    chrome.exe + "GITHUB.COM – your repositories" → 'work'

    Title keyword matching must be case-insensitive (both sides lowercased).
    """
    assert cat.categorize("chrome.exe", "GITHUB.COM – your repositories") == "work"


# ── Unknown-exe title fallback ────────────────────────────────────────────────

def test_unknown_exe_with_jira_title_is_work(cat):
    """
    "myapp.exe" + "Jira – PROJ-1234 Bug Fix" → 'work'

    For exes not in any known set, WORK_TITLE_KEYWORDS take precedence.
    """
    assert cat.categorize("myapp.exe", "Jira – PROJ-1234 Bug Fix") == "work"


def test_unknown_exe_with_no_keywords_is_unknown(cat):
    """
    "random_game.exe" + "Loading…" → 'unknown'

    When the exe is unrecognised and no title keyword matches, return 'unknown'.
    """
    assert cat.categorize("random_game.exe", "Loading…") == "unknown"


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_empty_exe_and_title_returns_unknown(cat):
    """
    ("", "") → 'unknown'

    Categorizer must not raise on empty strings.
    """
    assert cat.categorize("", "") == "unknown"


def test_categorize_is_deterministic(cat):
    """
    Calling categorize() twice with the same args returns the same result.

    The Categorizer has no mutable state; result must be stable.
    """
    result1 = cat.categorize("code.exe", "main.py")
    result2 = cat.categorize("code.exe", "main.py")
    assert result1 == result2 == "work"
