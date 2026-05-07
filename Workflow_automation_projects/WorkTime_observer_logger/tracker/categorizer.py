"""Maps application executable names and window titles to activity categories."""
from __future__ import annotations

# ── Known executable sets ─────────────────────────────────────────────────────

WORK_EXES: frozenset[str] = frozenset({
    # IDEs & code editors
    "code.exe", "code - insiders.exe",
    "pycharm64.exe", "idea64.exe", "webstorm64.exe", "clion64.exe",
    "rider64.exe", "goland64.exe", "datagrip64.exe",
    "devenv.exe",                                       # Visual Studio
    "notepad++.exe", "sublime_text.exe",
    # Office & productivity
    "excel.exe", "winword.exe", "powerpnt.exe", "onenote.exe",
    "mspub.exe", "visio.exe",
    # Email & calendar
    "outlook.exe", "thunderbird.exe",
    # Communication (work)
    "teams.exe", "msteams.exe", "slack.exe", "zoom.exe",
    "skype.exe", "lync.exe", "webex.exe",
    # Notes & PKM
    "obsidian.exe", "notion.exe",
    # Terminals & shells
    "cmd.exe", "powershell.exe", "pwsh.exe",
    "wt.exe", "windowsterminal.exe",
    # Language runtimes (in a dev context)
    "python.exe", "pythonw.exe", "node.exe", "ruby.exe", "java.exe",
    # API & database tools
    "postman.exe", "insomnia.exe",
    "dbeaver.exe", "ssms.exe", "tableplus.exe", "heidisql.exe",
    # Version control GUIs
    "sourcetree.exe", "gitkraken.exe", "fork.exe",
    # Container tools
    "docker desktop.exe", "docker.exe",
    # Design & diagramming
    "figma.exe", "sketch.exe",
})

LEISURE_EXES: frozenset[str] = frozenset({
    "spotify.exe", "vlc.exe", "mpv.exe", "mpc-hc64.exe",
    "steam.exe", "epicgameslauncher.exe", "gog galaxy.exe",
    "discord.exe", "telegram.exe", "signal.exe",
    "netflix.exe", "primevideo.exe",
})

BROWSER_EXES: frozenset[str] = frozenset({
    "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe",
    "opera.exe", "vivaldi.exe", "iexplore.exe",
})

SYSTEM_EXES: frozenset[str] = frozenset({
    "explorer.exe", "taskmgr.exe", "regedit.exe", "mmc.exe",
    "settingshost.exe", "systemsettings.exe", "control.exe",
    "desktop",                                          # no active window
    "lockapp.exe", "logonui.exe",
    "elevated_process",                                 # UAC-protected windows
})

# ── Title keyword lists (applied to browsers and unrecognized exes) ───────────

WORK_TITLE_KEYWORDS: tuple[str, ...] = (
    "github", "gitlab", "bitbucket", "jira", "confluence",
    "azure devops", "azure portal",
    "stack overflow", "docs.python", "mdn web docs",
    "pull request", "code review",
    "linear.app", "notion.so", "figma",
    "miro", "lucidchart", "drawio",
)

LEISURE_TITLE_KEYWORDS: tuple[str, ...] = (
    "youtube", "netflix", "twitch", "reddit",
    "twitter", "x.com", "facebook", "instagram",
    "tiktok", "9gag", "imgur", "pinterest",
    "hacker news",
)


class Categorizer:
    """
    Classifies an activity session as 'work', 'leisure', 'system', or 'unknown'.

    Resolution order:
      1. Exact exe match against SYSTEM_EXES / WORK_EXES / LEISURE_EXES
      2. Browser exe → refine by window-title keyword
      3. Title keyword fallback for unrecognised exes
      4. Default: 'unknown'
    """

    def categorize(self, exe_name: str, window_title: str) -> str:
        exe = exe_name.lower()
        title = window_title.lower()

        if exe in SYSTEM_EXES:
            return "system"
        if exe in WORK_EXES:
            return "work"
        if exe in LEISURE_EXES:
            return "leisure"
        if exe in BROWSER_EXES:
            # Browsers are work or leisure depending on what's open
            if any(k in title for k in WORK_TITLE_KEYWORDS):
                return "work"
            if any(k in title for k in LEISURE_TITLE_KEYWORDS):
                return "leisure"
            return "leisure"   # unrecognised tab → assume leisure

        # Unknown exe: use title keywords as last resort
        if any(k in title for k in WORK_TITLE_KEYWORDS):
            return "work"
        if any(k in title for k in LEISURE_TITLE_KEYWORDS):
            return "leisure"

        return "unknown"
