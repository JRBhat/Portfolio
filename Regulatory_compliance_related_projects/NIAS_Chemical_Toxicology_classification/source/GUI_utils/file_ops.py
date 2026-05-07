# utils/file_ops.py
import sys
import os
import subprocess
from PySide6.QtWidgets import QMessageBox

def open_file_with_default_app(self, path):
    """Open `path` with the system default application. Returns True on success."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception as e:
        try:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Cannot Open File")
            msg.setText(f"Could not open the file automatically: {path}\n\nError: {e}")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
        except Exception:
            pass
        return False

