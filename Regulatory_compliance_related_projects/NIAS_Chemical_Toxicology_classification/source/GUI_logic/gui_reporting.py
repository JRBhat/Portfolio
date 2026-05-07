# gui_reporting.py
import os
import logging
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import Qt

from GUI_utils.gui_helpers import save_recent_paths

def start_reporting(self):
    # Validate config path
    config_path = self.config_path_field.text().strip()
    if not config_path or not os.path.exists(config_path):
        self.log_field.append("❌ Error: Config file not found.")
        return

    # Validate excel
    xlsx_path = self.xlsx_path_field.text().strip()
    if not xlsx_path or not os.path.exists(xlsx_path):
        self.log_field.append("❌ Error: Excel file not found.")
        return

    # Validate DB
    db_path = self.db_path_field.text().strip()
    if not db_path or not os.path.exists(db_path):
        self.log_field.append("❌ Error: DB file not found.")
        return

    # Validate template
    template_path = self.template_path_field.text().strip()
    if not template_path or not os.path.exists(template_path):
        self.log_field.append("❌ Error: Template file not found.")
        return

    # Output folder (create if missing)
    out_path = self.out_path_field.text().strip()
    if not out_path:
        self.log_field.append("❌ Error: Output folder not specified.")
        return
    os.makedirs(out_path, exist_ok=True)

    # Missing folder (create if missing)
    missing_path = self.missing_path_field.text().strip()
    if not missing_path:
        self.log_field.append("❌ Error: Missing folder not specified.")
        return
    os.makedirs(missing_path, exist_ok=True)

    # Read and validate parameters from GUI fields
    def _parse_number(text: str, name: str):
        text = (text or "").strip()
        if not text:
            raise ValueError(f"{name} cannot be empty.")
        # allow commas as decimal separator
        text = text.replace(',', '.')
        try:
            # evaluate simple arithmetic safely by disabling builtins
            value = eval(text, {"__builtins__": None}, {})
        except Exception as e:
            raise ValueError(f"Could not parse {name}: {e}")
        # reject booleans (bool is subclass of int)
        # check for zeros or negative
        if value <= 0:
            raise ValueError(f"{name} must be a positive non-zero number.")
        
        
        
        if isinstance(value, bool):
            raise ValueError(f"{name} must be a number, not a boolean.")
        if not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be a number.")
        return value

    try:
        k_gewicht = _parse_number(self.k_gewicht_field.text(), "K_gewicht")
        uf_tenax = _parse_number(self.uf_tenax_field.text(), "Umrechnungsfaktor_Tenax")
        if "/" not in str(self.uf_real_field.text()):
            # Warn if uf_real is not a fraction (common user error)
            raise ValueError("Umrechnungsfaktor_Real does not appear to be a fraction (e.g., '1 / 6'). Or Check Sign USE THIS '/' NOT THIS '\\'.") 
        uf_real = _parse_number(self.uf_real_field.text(), "Umrechnungsfaktor_Real")
        uf_exposition = _parse_number(self.uf_exposition_field.text(), "Umrechnungsfaktor_Exposition")

        # CASColumn_Table3 - read from checkbox
        cas_column = self.cas_column_checkbox.isChecked()
        
        # Warn if uf_real does not look like a fraction (e.g., "1 / 6")
 
    except Exception as e:
        # Catch all parsing-related exceptions and show a clear message in the UI
        self.log_field.append(f"❌ Error parsing parameters: {e}")
        return

    # Assign paths to reporting object (GUI selections take precedence)
    self.reporting.config_path = config_path
    self.reporting.xlsx_path = xlsx_path
    self.reporting.db_path = db_path

    # Keep full path if needed
    self.reporting.template_path = template_path
    # template WITHOUT extension (basename)
    self.reporting.template = os.path.splitext(os.path.basename(template_path))[0]

    self.reporting.out_path = out_path
    # 'debug_path' is used in reporting.py as missingPath
    self.reporting.debug_path = missing_path

    # Assign parameters from GUI fields
    self.reporting.K_gewicht = k_gewicht
    self.reporting.uf_tenax = uf_tenax
    self.reporting.uf_real = uf_real
    self.reporting.uf_exposition = uf_exposition
    self.reporting.cas_column = cas_column

    # Save these selections for next time
    save_recent_paths(self)

    # Update UI
    self.start_button.setText("Running")
    self.start_button.setEnabled(False)

    # reset last-run outcome indicator before starting
    self._last_run_success = None

    # reconnect text_changed just in case
    try:
        self.reporting.text_changed.disconnect(self._update_text_edit_slot)
    except Exception:
        pass
    self.reporting.text_changed.connect(self._update_text_edit_slot)

    # Make sure finished is connected (it is in __init__, but reconnecting is harmless)
    try:
        self.reporting.finished.disconnect(self._finished_slot)
    except Exception:
        pass
    self.reporting.finished.connect(self._finished_slot)

    # Start the reporting thread
    try:
        self.reporting.start()
    except Exception:
        # If starting the thread itself fails, reset UI and report error
        logging.exception("Failed to start reporting thread")
        self.start_button.setText("Start")
        self.start_button.setEnabled(True)
        self.log_field.append("❌ Error: Could not start reporting thread.")


def on_reporting_finished(self):
    # Re-enable UI
    self.start_button.setText("Start")
    self.start_button.setEnabled(True)

    # Prefer explicit flag from Reporting
    success = getattr(self.reporting, "success", None)
    reason = getattr(self.reporting, "last_exception", None)

    if success is True:
        # If we detected a missing file earlier, try again to ensure CONFIG sheet is present
        try:
            if getattr(self, "_last_missing_file", None):
                if getattr(self, "_config_written_for", None) != self._last_missing_file:
                    self.write_config_sheet(self._last_missing_file)
                    self._config_written_for = self._last_missing_file
        except Exception:
            logging.exception("Failed to write CONFIG sheet in on_reporting_finished")

        self.log_field.append("✅ Reporting process finished.")

        # try to open the generated missing file automatically if we detected it ---
        if getattr(self, "_last_missing_file", None):
            missing_file = self._last_missing_file
            try:
                if os.path.exists(missing_file):
                    opened = self._open_file_with_default_app(missing_file)
                    if opened:
                        self.log_field.append(f"ℹ️ Opened missing file: {missing_file}")
                    else:
                        self.log_field.append(f"⚠️ Could not open missing file automatically: {missing_file}")
                else:
                    self.log_field.append(f"⚠️ Missing file not found on disk: {missing_file}")
            except Exception:
                logging.exception("Error while attempting to open missing file")

        # --- attempt to open final DOCX report if detected ---
        if getattr(self, "_last_docx_file", None):
            docx_file = self._last_docx_file
            try:
                if os.path.exists(docx_file):
                    opened = self._open_file_with_default_app(docx_file)
                    if opened:
                        self.log_field.append(f"ℹ️ Opened report: {docx_file}")
                    else:
                        self.log_field.append(f"⚠️ Could not open report automatically: {docx_file}")
                else:
                    self.log_field.append(f"⚠️ Report file not found on disk: {docx_file}")
            except Exception:
                logging.exception("Error while attempting to open report file")


        # --- Show modal info dialog and freeze start controls until user presses OK ---
        if getattr(self, "_dialog_lock", False):
            # If a dialog is already open, ignore duplicate requests
            self.log_field.append("⚠️ Info dialog already open — ignoring duplicate request.")
        else:
            self._dialog_lock = True
            _disabled_widgets = []

            # Disable all run controls listed in self.run_controls
            for w in getattr(self, "run_controls", []):
                try:
                    if w.isEnabled():
                        w.setEnabled(False)
                        _disabled_widgets.append(w)
                except Exception:
                    pass

            try:
                # Build modal QMessageBox parented to main window
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle("Process Complete ✅")
                msg.setText("The reporting process has finished successfully.")
                msg.setStandardButtons(QMessageBox.StandardButton.Ok)

                # Make it application-modal so the user cannot interact with other windows.
                msg.setWindowModality(Qt.ApplicationModal)

                # In PySide6 use exec() which blocks until user closes the dialog
                res = msg.exec()

                # Robust OK-check across versions: bitwise-check is safe if res is int/enum
                try:
                    ok_pressed = bool(int(res) & int(QMessageBox.StandardButton.Ok))
                except Exception:
                    ok_pressed = (res == QMessageBox.StandardButton.Ok)

                if ok_pressed:
                    # user pressed OK — close main window (same behavior as before)
                    self.close()

            finally:
                # Re-enable run controls (safe even if close() was called)
                for w in _disabled_widgets:
                    try:
                        w.setEnabled(True)
                    except Exception:
                        pass
                self._dialog_lock = False

    else:
        # If we detected a missing file earlier, try again to ensure CONFIG sheet is present
        try:
            if getattr(self, "_last_missing_file", None):
                if getattr(self, "_config_written_for", None) != self._last_missing_file:
                    self.write_config_sheet(self._last_missing_file)
                    self._config_written_for = self._last_missing_file
        except Exception:
            logging.exception("Failed to write CONFIG sheet in on_reporting_finished")

        # Provide helpful feedback and keep the app open for inspection
        self.log_field.append("❌ Reporting process finished with errors.")
        if reason:
            self.log_field.append(f"ℹ️ Reason: {reason}")

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Process Failed ❌")
        text = "The reporting process did not complete successfully. Please check the log for details."
        if reason:
            text += f"\n\nReason (short): {reason}"
        msg.setText(text)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
