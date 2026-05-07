"""
NIAS Reporting - Main Entry Point
==================================
This module is the application entry point for the NIAS (Non-food Items from Analysis
Systems) Reporting tool. It initialises a PySide6 Qt GUI application, loads the main
window, and starts the Qt event loop.

Suppressed warnings:
    - DeprecationWarning: third-party library deprecation noise.
    - urllib3.InsecureRequestWarning: SSL certificate warnings during PubChem API calls.

Logging:
    Only ERROR-level messages are written to stdout with timestamps and log-level labels.

Usage:
    Run this script directly to launch the NIAS Reporting GUI:
        python main.py
"""

import sys
import warnings
import urllib3
import logging
from PySide6.QtWidgets import QApplication

from GUI_logic.gui_mainwindow import MainWindow

# Suppress DeprecationWarnings from third-party libraries to keep console output clean
warnings.simplefilter('ignore', DeprecationWarning)

# Suppress InsecureRequestWarning that appears when SSL verification is skipped during
# PubChem REST API queries (e.g. in restricted network environments)
warnings.simplefilter('ignore', urllib3.exceptions.InsecureRequestWarning)

# Configure root logger: only show ERROR and above so normal operation is quiet;
# errors will be timestamped for easy triage
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

if __name__ == '__main__':
    # Create the Qt application instance (no command-line args needed)
    app = QApplication([])

    # Instantiate and show the main window; all UI wiring is handled inside MainWindow
    window = MainWindow()

    # Hand control to the Qt event loop; sys.exit propagates the exit code back to the OS
    sys.exit(app.exec())
