# gui_autofill.py
import os
import logging
from pathlib import Path
from PySide6.QtWidgets import QMessageBox

from GUI_utils.file_finders import find_latest_user_file
from autofill_db_to_update_missing import merge_user_files_into_db_and_report

def on_fill_db_clicked(self):
    """Autofill DB from latest missing file in the configured Missing Folder."""
    # Basic checks
    if merge_user_files_into_db_and_report is None:
        self.log_field.append("❌ Error: merge function not available (import failed).")
        QMessageBox.critical(self, "Autofill Error",
                             "merge_user_files_into_db_and_report is not available. Check imports.")
        return

    missing_folder = self.missing_path_field.text().strip()
    if not missing_folder:
        self.log_field.append("❌ Error: Missing folder not specified.")
        QMessageBox.critical(self, "Autofill Error", "Please specify the Missing Folder first.")
        return

    folder_path = Path(missing_folder)
    if not folder_path.exists() or not folder_path.is_dir():
        self.log_field.append(f"❌ Error: Missing folder not found: {missing_folder}")
        QMessageBox.critical(self, "Autofill Error", f"Missing folder not found: {missing_folder}")
        return

    # Find latest missing file
    latest_file = find_latest_user_file(folder_path)
    if latest_file is None:
        msg = f"No suitable .xlsx missing files found in: {missing_folder}"
        self.log_field.append("❌ " + msg)
        QMessageBox.information(self, "No Missing File", msg)
        return

    self.log_field.append(f"ℹ️ Using latest missing file: {str(latest_file)}")

    # Validate DB path
    db_path = self.db_path_field.text().strip()
    if not db_path or not os.path.exists(db_path):
        msg = "DB file not found. Please select a valid DB file."
        self.log_field.append("❌ " + msg)
        QMessageBox.critical(self, "Autofill Error", msg)
        return

    # call the merge function (it raises RuntimeError on validation failure)
    try:
        summary = merge_user_files_into_db_and_report(Path(db_path),
                                                     [Path(latest_file)],
                                                     out_path=None,       # let the function auto-generate
                                                     report_path=None,    # let function auto-generate
                                                     dry_run=False)
    except RuntimeError as rex:
        # This is how your merge function signals validation error (missing mapped fields)
        self.log_field.append(f"❌ Autofill aborted due to validation error:\n{rex}")
        QMessageBox.critical(self, "Autofill Aborted",
                             f"Validation failed while processing {latest_file}.\n\nDetails:\n{rex}")
        return
    except Exception as ex:
        logging.exception("Autofill failed with unexpected error")
        self.log_field.append(f"❌ Unexpected error during autofill: {ex}")
        QMessageBox.critical(self, "Autofill Error",
                             f"Unexpected error during autofill:\n{ex}")
        return

    # If merge returns successfully, show a summary
    try:
        appended_sub = summary.get("appended_sub", 0)
        appended_cl = summary.get("appended_cl", 0)
        highlighted = summary.get("highlighted", 0)
        processed = summary.get("processed_rows", 0)
        report_path = summary.get("report_path", "")
        out_path = summary.get("out_path", "")

        # If nothing changed at all, inform the user
        if appended_sub == 0 and appended_cl == 0 and highlighted == 0:
            msg = (f"No rows were appended or highlighted when processing {latest_file}.\n"
                   "The file may already have been merged or no actionable rows were present.")
            self.log_field.append("ℹ️ " + msg)
            QMessageBox.information(self, "No Changes", msg)
        else:
            msg = (f"Autofill finished successfully.\nProcessed rows: {processed}\n"
                   f"Substance appended: {appended_sub}\nCL appended: {appended_cl}\n"
                   f"Existing rows highlighted: {highlighted}\n\nReport: {report_path}\nDB out: {out_path}")
            self.log_field.append("✅ " + msg)
            QMessageBox.information(self, "Autofill Complete", msg)
    except Exception:
        # keep UI robust
        self.log_field.append("✅ Autofill completed (summary unavailable).")
        QMessageBox.information(self, "Autofill Complete", "Autofill completed successfully.")
