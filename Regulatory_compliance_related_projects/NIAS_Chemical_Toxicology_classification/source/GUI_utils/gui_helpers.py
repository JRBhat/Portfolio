# gui_helpers.py
import os
import json
import logging
from PySide6.QtWidgets import QFileDialog

from GUI_utils.file_paths import get_recent_paths_file

def load_recent_paths(self):
    """Load previously selected paths from recent paths JSON and populate fields."""
    try:
        recent_file = get_recent_paths_file()
        if os.path.exists(recent_file):
            with open(recent_file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            # Fill GUI fields if keys exist
            self.config_path_field.setText(data.get("config_path", ""))
            self.xlsx_path_field.setText(data.get("xlsx_path", ""))
            self.db_path_field.setText(data.get("db_path", ""))
            self.template_path_field.setText(data.get("template_path", ""))
            self.out_path_field.setText(data.get("out_path", ""))
            self.missing_path_field.setText(data.get("missing_path", ""))

            # Also pre-populate the reporting object's fields
            self.reporting.config_path = data.get("config_path", "") or None
            self.reporting.xlsx_path = data.get("xlsx_path", "") or ""
            self.reporting.db_path = data.get("db_path", "") or ""
            self.reporting.template_path = data.get("template_path", "") or ""
            self.reporting.template = os.path.splitext(os.path.basename(data.get("template_path", "")))[0] if data.get("template_path") else ""
            self.reporting.out_path = data.get("out_path", "") or ""
            self.reporting.debug_path = data.get("missing_path", "") or ""
    except Exception:
        logging.exception("Failed to load recent paths")


def save_recent_paths(self):
    """Save current GUI fields to the chosen recent-paths JSON for next time."""
    data = {
        "config_path": self.config_path_field.text().strip(),
        "xlsx_path": self.xlsx_path_field.text().strip(),
        "db_path": self.db_path_field.text().strip(),
        "template_path": self.template_path_field.text().strip(),
        "out_path": self.out_path_field.text().strip(),
        "missing_path": self.missing_path_field.text().strip()
    }
    try:
        recent_file = get_recent_paths_file()
        # Ensure parent dir exists for the chosen file (for APPDATA/XDG paths)
        os.makedirs(os.path.dirname(recent_file), exist_ok=True)
        with open(recent_file, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    except Exception:
        logging.exception("Failed to save recent paths")


def browse_config_file(self):
    file_dialog = QFileDialog(self)
    file_path, _ = file_dialog.getOpenFileName(
        self, "Select Config File", "", "Config Files (*.ini);;All Files (*)"
    )
    if file_path:
        self.config_path_field.setText(file_path)
        self.reporting.config_path = file_path
        save_recent_paths(self)


def browse_xlsx_file(self):
    file_path, _ = QFileDialog.getOpenFileName(
        self, "Select Excel File", "", "Excel Files (*.xlsx *.xls);;All Files (*)"
    )
    if file_path:
        self.xlsx_path_field.setText(file_path)
        self.reporting.xlsx_path = file_path
        save_recent_paths(self)


def browse_db_file(self):
    file_path, _ = QFileDialog.getOpenFileName(
        self, "Select DB File", "", "Excel/DB Files (*.xlsx *.xls *.db *.xlsm);;All Files (*)"
    )
    if file_path:
        self.db_path_field.setText(file_path)
        self.reporting.db_path = file_path
        save_recent_paths(self)


def browse_template_file(self):
    file_path, _ = QFileDialog.getOpenFileName(
        self, "Select Template File", "", "All Files (*)"
    )
    if file_path:
        self.template_path_field.setText(file_path)
        # keep full path as template_path, but store template as filename without extension
        self.reporting.template_path = file_path
        self.reporting.template = os.path.splitext(os.path.basename(file_path))[0]
        save_recent_paths(self)


def browse_out_folder(self):
    folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
    if folder:
        self.out_path_field.setText(folder)
        self.reporting.out_path = folder
        save_recent_paths(self)


def browse_missing_folder(self):
    folder = QFileDialog.getExistingDirectory(self, "Select Missing Folder")
    if folder:
        self.missing_path_field.setText(folder)
        self.reporting.debug_path = folder
        save_recent_paths(self)
