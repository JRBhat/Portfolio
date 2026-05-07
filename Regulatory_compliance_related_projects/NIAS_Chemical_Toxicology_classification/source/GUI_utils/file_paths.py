import os
import sys

#RECENT_PATHS_FILE = os.path.join(os.path.expanduser("~"), ".nias_reporting_paths.json")
# Replace the old RECENT_PATHS_FILE constant with this helper function
def get_recent_paths_file():
    """
    Return a path for the recent-paths JSON file.

    Preference order:
      1. If the app is frozen and the executable directory is persistent & writable -> use exe dir.
      2. If frozen but running from a temp extraction (PyInstaller --onefile) -> use APPDATA / XDG_CONFIG_HOME / home.
      3. If not frozen -> try script directory if writable, otherwise use home.
      4. Always fall back to the user's home directory.
    """
    try:
        # Helper to test whether a dir is writable
        def _writable_dir(path):
            try:
                testfile = os.path.join(path, ".nias_write_test")
                with open(testfile, "w", encoding="utf-8") as fh:
                    fh.write("x")
                os.remove(testfile)
                return True
            except Exception:
                return False

        # If running as a bundled executable (PyInstaller, cx_Freeze, etc.)
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
            # Many PyInstaller --onefile builds extract to a tempdir; check for that
            import tempfile
            tmpdir = tempfile.gettempdir()
            try:
                # If the exe_dir is inside the platform temp dir, avoid writing there (ephemeral)
                if os.path.commonpath([exe_dir, tmpdir]) == tmpdir:
                    # Try platform-specific persistent config locations
                    if sys.platform.startswith("win"):
                        appdata = os.getenv("APPDATA") or os.path.expanduser("~")
                        return os.path.join(appdata, "nias_reporting_paths.json")
                    xdg = os.getenv("XDG_CONFIG_HOME")
                    if xdg:
                        return os.path.join(xdg, "nias_reporting_paths.json")
                    return os.path.join(os.path.expanduser("~"), "nias_reporting_paths.json")
            except Exception:
                # If commonpath check failed for any reason, continue and try exe_dir
                pass

            # If exe_dir looks persistent, try to write next to the exe
            candidate = os.path.join(exe_dir, "nias_reporting_paths.json")
            if _writable_dir(exe_dir):
                return candidate
            # fallback
            return os.path.join(os.path.expanduser("~"), "nias_reporting_paths.json")

        # Not frozen: prefer script directory (useful during development)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidate = os.path.join(script_dir, "nias_reporting_paths.json")
        if _writable_dir(script_dir):
            return candidate
        # fallback to user's home
        return os.path.join(os.path.expanduser("~"), "nias_reporting_paths.json")
    except Exception:
        # ultimate fallback
        return os.path.join(os.path.expanduser("~"), "nias_reporting_paths.json")
