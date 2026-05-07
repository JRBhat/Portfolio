# Excel Template to PDF Converter

> Reads clinical study image paths and metadata from an Excel configuration file, generates a structured LaTeX document, and compiles it to a PDF — with support for multiple template layouts and Visia camera file handling.

---

## Project Overview

- **Problem**: Clinical imaging studies produce large sets of images that need to be compiled into standardised PDF reports with consistent layout, randomised ordering, and traceability headers. Assembling these manually from Excel data is error-prone and time-consuming.
- **Type**: Document generation pipeline / automation utility
- **Approach**: Reads an Excel "Modify_Template_here" sheet to determine which template type and layout to use, locates the corresponding image files, builds a LaTeX document from modular template functions, and calls a LaTeX compiler to produce the final PDF.

---

## Objective

- Automate the generation of image overview PDFs from Excel-configured study data.
- Support multiple output layouts (standard, transposed, custom, per-row column names) without code changes — driven entirely by the Excel sheet configuration.

---

## Dataset

| Field | Details |
|---|---|
| Source | Excel workbook with a "Modify_Template_here" sheet |
| Images | JPEG/TIF files converted and standardised before PDF generation |
| Config keys | Template type flag (`*` = custom, `§` = column-names-per-row), study number, filename mask |
| Output | Compiled `.pdf` file |

---

## Methodology

1. **Import configuration** — `InternalImport` reads a JSON config file containing the image path, study number, filename mask, draft flag, and Visia flag.
2. **Image validation** — Images are converted to standard JPGs (scaling and format normalisation) and the operator confirms correctness before proceeding.
3. **Visia detection** — Filenames are checked against a Visia-specific regex pattern; if matched, `is_visia = True` triggers Visia-specific filename renaming.
4. **Missing file handling** — Files not matching the expected naming pattern are replaced with dummy placeholder images.
5. **Template selection** — The Excel `Modify_Template_here` sheet cell A1 is read:
   - `"*"` → Custom template
   - `"§"` → Column-name-per-row layout
   - Other → Standard or Transpose based on further configuration
6. **LaTeX generation** — The selected template module builds a `.tex` document using `openpyxl`-read metadata and image paths.
7. **PDF compilation** — `subprocess` calls the LaTeX compiler; the output folder is opened for the operator.

---

## Code Structure

```
Excel_Template_To_PDF_converter/
└── source/
    ├── main.py                            # Main pipeline orchestrator
    ├── Internal_Imports_Stable.py         # Config reader (JSON-based)
    ├── Common_Functions_Stable.py         # Shared utilities (image conversion, LaTeX helpers, file cleanup)
    ├── Templates.py                       # Template dispatcher
    ├── Template_Standard_Stable.py        # Standard layout
    ├── Template_Transpose_Stable.py       # Transposed layout
    ├── Template_Custom_Stable.py          # Custom layout
    ├── Column_Name_Per_Row_Template.py    # Per-row column header layout
    ├── Randomization_Template_Stable.py   # Randomised image ordering
    ├── Randomization_Template_Transposed_Stable.py
    ├── Create_Excel_template.py           # Excel template creator
    ├── Insert_Description_Stable.py       # Description insertion
    ├── Latex_File_Create_Stable.py        # LaTeX document assembly
    ├── File_renamers/                     # Visia-specific file renaming utilities
    ├── ImageAnalysis/                     # Shared image processing library
    └── super/                             # Archived files (excluded from git)
```

---

## Key Logic

Template selection is controlled by two sentinel values read from the Excel workbook: `"*"` in cell A1 triggers the custom template; `"§"` found anywhere in the first 20 columns triggers the column-names-per-row layout. This design means the operator controls output format directly from the Excel file without touching any Python code.

The `COLUMN_SCAN_LIMIT = 20` constant caps the column scan to avoid performance issues on wide worksheets.

---

## Results

> No benchmark metrics — output is a PDF document reviewed by the operator.

Key capabilities:
- Multiple template layouts selectable via Excel configuration
- Visia camera file detection and automated pre-renaming
- Dummy placeholder insertion for missing study images
- Draft/final PDF modes controlled via config flag

---

## Limitations

- Requires a working LaTeX installation (e.g., MiKTeX or TeX Live) on the host machine.
- Image conversion step requires operator confirmation via console prompt — not fully automated.
- Config is JSON-based; the JSON file path is expected in the working directory.

---

## Tech Stack

| Category | Tools |
|---|---|
| Language | Python 3.x |
| Excel I/O | openpyxl |
| Image processing | Custom ImageAnalysis library + Pillow (via conversion utilities) |
| Document generation | LaTeX (subprocess call to compiler) |
| File handling | os, subprocess, shutil |
| Regex | re (filename mask matching) |

---

## How to Run

```bash
# 1. Ensure a LaTeX distribution is installed (MiKTeX / TeX Live)

# 2. Place your config JSON in the working directory

# 3. Run from the source directory
cd source
python main.py

# Follow the interactive prompts to confirm image conversion and proceed.
```

---

## Business / Practical Value

Reduces the time to generate a standardised clinical image PDF report from hours of manual layout work to a single command run — while guaranteeing consistent formatting, traceability headers, and correct image ordering across all study reports.

---

## Author

Jayesh Bhat · [https://www.linkedin.com/in/jayeshbhat/] · [https://github.com/JRBhat]
