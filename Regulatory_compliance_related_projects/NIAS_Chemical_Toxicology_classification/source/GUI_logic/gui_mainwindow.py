from PySide6.QtWidgets import (
    QMainWindow, QTextEdit, QPushButton,
    QVBoxLayout, QLineEdit, QLabel, QWidget, QHBoxLayout, QCheckBox, QGridLayout
)
from PySide6.QtCore import Qt

from reporting import Reporting
from GUI_utils.file_ops import open_file_with_default_app
from excel_config_sheet import write_config_sheet

# helpers moved out
from GUI_utils.gui_helpers import (
    load_recent_paths, browse_config_file, browse_xlsx_file, browse_db_file,
    browse_template_file, browse_out_folder, browse_missing_folder
)
from GUI_logic.gui_reporting import start_reporting, on_reporting_finished
from GUI_logic.gui_autofill import on_fill_db_clicked
from GUI_logic.gui_logging import update_text_edit, closeEvent


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('NIAS Reporting')
        self.resize(900, 700)

        layout = QVBoxLayout()

        # Config file selector (kept)
        self.config_label = QLabel("Select Config File:")
        layout.addWidget(self.config_label)
        self.config_path_field = QLineEdit()
        layout.addWidget(self.config_path_field)
        self.browse_config_button = QPushButton("Browse Config")
        self.browse_config_button.clicked.connect(lambda: browse_config_file(self))
        layout.addWidget(self.browse_config_button)

        # Excel file selector
        self.xlsx_label = QLabel("Select Excel File (xlsx):")
        layout.addWidget(self.xlsx_label)
        h = QHBoxLayout()
        self.xlsx_path_field = QLineEdit()
        h.addWidget(self.xlsx_path_field)
        self.browse_xlsx_button = QPushButton("Browse Excel")
        self.browse_xlsx_button.clicked.connect(lambda: browse_xlsx_file(self))
        h.addWidget(self.browse_xlsx_button)
        layout.addLayout(h)

        # DB file selector
        self.db_label = QLabel("Select Database File (db):")
        layout.addWidget(self.db_label)
        h = QHBoxLayout()
        self.db_path_field = QLineEdit()
        h.addWidget(self.db_path_field)
        self.browse_db_button = QPushButton("Browse DB")
        self.browse_db_button.clicked.connect(lambda: browse_db_file(self))
        h.addWidget(self.browse_db_button)
        layout.addLayout(h)

        # Template file selector
        self.template_label = QLabel("Select Template File (Template):")
        layout.addWidget(self.template_label)
        h = QHBoxLayout()
        self.template_path_field = QLineEdit()
        h.addWidget(self.template_path_field)
        self.browse_template_button = QPushButton("Browse Template")
        self.browse_template_button.clicked.connect(lambda: browse_template_file(self))
        h.addWidget(self.browse_template_button)
        layout.addLayout(h)

        # Output folder selector
        self.out_label = QLabel("Select Output Folder (outPath):")
        layout.addWidget(self.out_label)
        h = QHBoxLayout()
        self.out_path_field = QLineEdit()
        h.addWidget(self.out_path_field)
        self.browse_out_button = QPushButton("Browse Output Folder")
        self.browse_out_button.clicked.connect(lambda: browse_out_folder(self))
        h.addWidget(self.browse_out_button)
        layout.addLayout(h)

        # Missing folder selector
        self.missing_label = QLabel("Select Missing Folder (missingPath):")
        layout.addWidget(self.missing_label)
        h = QHBoxLayout()
        self.missing_path_field = QLineEdit()
        h.addWidget(self.missing_path_field)
        self.browse_missing_button = QPushButton("Browse Missing Folder")
        self.browse_missing_button.clicked.connect(lambda: browse_missing_folder(self))
        h.addWidget(self.browse_missing_button)
        layout.addLayout(h)

        # Parameters section - using grid layout for compact display
        params_label = QLabel("Parameters:")
        params_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(params_label)

        # Create grid layout for parameters (2 columns)
        params_grid = QGridLayout()
        params_grid.setVerticalSpacing(5)
        params_grid.setHorizontalSpacing(5)
        params_grid.setContentsMargins(0, 0, 0, 0)
        # Make input columns expand (so labels stay compact and fields grow)
        params_grid.setColumnStretch(1, 1)  # Allow column 1 to stretch (inputs)
        params_grid.setColumnStretch(3, 1)  # Allow column 3 to stretch (inputs)

        # K_gewicht (row 0, col 0-1)
        k_label = QLabel("K_gewicht:")
        k_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        params_grid.addWidget(k_label, 0, 0)
        self.k_gewicht_field = QLineEdit("60")
        # allow input to expand to fill column
        params_grid.addWidget(self.k_gewicht_field, 0, 1)

        # Umrechnungsfaktor_Tenax (row 0, col 2-3)
        tenax_label = QLabel("UF Tenax:")
        tenax_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        params_grid.addWidget(tenax_label, 0, 2)
        self.uf_tenax_field = QLineEdit("1")
        # allow input to expand to fill column
        params_grid.addWidget(self.uf_tenax_field, 0, 3)

        # Umrechnungsfaktor_Real (row 1, col 0-1)
        real_label = QLabel("UF Real:")
        real_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        params_grid.addWidget(real_label, 1, 0)
        self.uf_real_field = QLineEdit("1 / 6")
        # allow input to expand to fill column
        params_grid.addWidget(self.uf_real_field, 1, 1)

        # Umrechnungsfaktor_Exposition (row 1, col 2-3)
        expo_label = QLabel("UF Exposition:")
        expo_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        params_grid.addWidget(expo_label, 1, 2)
        self.uf_exposition_field = QLineEdit("0.36")
        # allow input to expand to fill column
        params_grid.addWidget(self.uf_exposition_field, 1, 3)

        # CASColumn_Table3 as checkbox (row 2, col 0-1) - text on right side
        cas_label = QLabel("CAS Column Table 3:")
        cas_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        params_grid.addWidget(cas_label, 2, 0)
        self.cas_column_checkbox = QCheckBox()
        self.cas_column_checkbox.setChecked(True)
        params_grid.addWidget(self.cas_column_checkbox, 2, 1)

        layout.addLayout(params_grid)

        # Log field
        self.log_field = QTextEdit()
        self.log_field.setReadOnly(True)
        layout.addWidget(self.log_field)

        # Start button
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(lambda: start_reporting(self))
        layout.addWidget(self.start_button)

        # FILL DB button (autofill using latest missing file)
        self.fill_button = QPushButton("FILL DB")
        self.fill_button.clicked.connect(lambda: on_fill_db_clicked(self))
        layout.addWidget(self.fill_button)

        # Keep track of run-related controls for enabling/disabling during modal dialogs
        self.run_controls = [self.start_button, self.fill_button]
        # a small lock flag to prevent re-opening the same dialog
        self._dialog_lock = False

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Reporting thread instance
        self.reporting = Reporting()

        # Create persistent callable slots so we can disconnect/reconnect reliably
        self._update_text_edit_slot = lambda t: update_text_edit(self, t)
        self._finished_slot = lambda: on_reporting_finished(self)

        self.reporting.text_changed.connect(self._update_text_edit_slot)
        self.reporting.finished.connect(self._finished_slot)

        # track most recent run outcome (None = not finished yet)
        self._last_run_success = None
        # This will be filled when update_text_edit sees the "Missing File written to ..." message
        self._last_missing_file = None
        # track whether we've already written CONFIG for a particular missing file
        self._config_written_for = None
        # Track last produced docx report file path (populated from export_document messages)
        self._last_docx_file = None

        # Load saved (recent) paths if available
        load_recent_paths(self)

        self.show()

    # Keep existing small passthroughs for external helpers (exact same names)
    def write_config_sheet(self, missing_file_path: str):
        return write_config_sheet(self, missing_file_path)

    def _open_file_with_default_app(self, path):
        return open_file_with_default_app(self, path)

    # Use closeEvent helper (keeps same name)
    def closeEvent(self, event):
        return closeEvent(self, event)
