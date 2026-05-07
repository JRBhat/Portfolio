# gui_logging.py
import os
import re
import logging

def update_text_edit(self, text):
    # keep existing behavior
    self.log_field.append(text)

    # detect message that contains the generated missing file path and final .docx report ---
    # Example missing file emitted text (from reporting code):
    # "✅ Missing File written to /path/to/missing_20250101_120000.xlsx; ALL_BAD_CAS updated in /path/to/db.xlsx"
    # Example docx emitted text (from export_document):
    # "Writing C:\path\to\input_Template_DE_results.docx"
    try:
        if isinstance(text, str):
            # 1) missing xlsx detection (accept quoted paths and spaces)
            m = re.search(r"Missing File written to\s+([\"']?(.+?\.xlsx)[\"']?)", text, flags=re.IGNORECASE)
            if m:
                path = m.group(2)
                path = os.path.expanduser(path)
                self._last_missing_file = path
                # Optional small status in log
                self.log_field.append(f"ℹ️ Detected missing file: {self._last_missing_file}")

            # 2) final DOCX report detection (messages like 'Writing <path>\\file.docx')
            m2 = re.search(r"Writing\s+([\"']?(.+?\.docx)[\"']?)", text, flags=re.IGNORECASE)
            if m2:
                docx_path = m2.group(2)
                docx_path = os.path.expanduser(docx_path)
                self._last_docx_file = docx_path
                self.log_field.append(f"ℹ️ Detected generated report: {self._last_docx_file}")
    except Exception:
        # don't let parsing errors crash the GUI; just ignore
        logging.exception("Failed to parse file path from reporting output")


def closeEvent(self, event):
    # Use the QThread isRunning method if available; this prevents the window closing
    # while the reporting thread is still running.
    try:
        running = False
        if hasattr(self.reporting, "isRunning"):
            running = self.reporting.isRunning()
        else:
            # fallback: check internal flag or result we set earlier
            running = getattr(self.reporting, "running", False)
        if running:
            self.log_field.append(
                "Reporting is still running. Please wait until it finishes."
            )
            event.ignore()
            return
    except Exception:
        # If anything goes wrong while checking, be conservative and block close only if thread reports running.
        pass

    event.accept()
