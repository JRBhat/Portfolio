# Site Studies Crawler for FotoStudies

> Scans clinical study directory trees for clinical photography qualification and Laufzettel documents, then exports a structured Excel report of findings.

---

## Project Overview

- **Problem**: Clinical study sites produce a large number of study folders, each containing a photography qualification sheet ("FotoQualiSheet") buried inside a `.docu` subfolder. Manually locating and cataloguing these files across dozens of studies takes hours.
- **Type**: File system crawler / automation utility
- **Approach**: Uses a PowerShell subprocess for fast native Windows directory traversal, pattern-matches study and document folders, locates the target files, and writes an Excel report with colour-coded headers via `openpyxl`.

---

## Objective

- Automatically locate photography qualification documents across all study directories under a given root.
- Output a clean Excel report showing which studies have the file and where it lives, ready for coordinator review.

---

## Dataset

| Field | Details |
|---|---|
| Source | Windows network or local clinical study directory tree |
| Structure | Study folders named `DD.DDDD-DD_*`, each containing a `.docu` subfolder |
| Target files | Files matching `foto` AND (`quali` OR `laufzettel`) in `.docu` directories |
| Output | Excel file with study number, file path, and protocol folder columns |

---

## Methodology

1. **PowerShell traversal** — A PowerShell `Get-ChildItem` command recursively finds study directories matching the `^\d{2}\.\d{4}-\d{2}_` pattern. This is significantly faster than Python's `os.walk` for large network shares.
2. **Per-study file search** — For each study directory, the script locates the `.docu` subfolder and searches for files matching the foto/quali/laufzettel naming convention.
3. **Result collection** — Matching results are returned as pipe-delimited strings (`studyNum|filePath|protocolFolder`) and parsed in Python.
4. **Protocol scanner variant** — `protocol_scanner_v2.py` extends this with PDF and Word document parsing to extract visit-specific protocol information using regex pattern matching and concurrent processing.
5. **Excel output** — `openpyxl` writes results with styled headers (blue fill, bold white font) and auto-sized columns.

---

## Code Structure

```
Site_Studies_Crawler_For_FotoStudies/
├── main.py                  # PowerShell-based fast file finder + Excel output
├── protocol_scanner_v2.py   # Extended: protocol parsing with PDF/Word support
```

---

## Key Logic

The core performance design is the PowerShell delegation: rather than walking potentially thousands of directories with Python's `os.walk`, a single `Get-ChildItem -Recurse` call runs natively and returns only matching results. Output is decoded as UTF-8 with a fallback to `cp1252` (German Windows default) to handle paths with German characters.

`PatternFill` in `main.py` uses keyword arguments (`fill_type="solid", fgColor="4472C4"`) for unambiguous openpyxl API compatibility across versions.

---

## Results

> No fixed benchmark metrics — output is a populated Excel report.

Key outputs:
- Excel file listing study numbers, FotoQualiSheet file paths, and protocol folder paths
- Console warnings for directories where PowerShell encountered errors

---

## Limitations

- Windows-only: requires PowerShell; the PowerShell command will not run on Linux or macOS.
- Assumes a specific directory naming convention (`DD.DDDD-DD_*`) and `.docu` subfolder pattern.
- Protocol scanner uses concurrent processing (thread pool); error handling for individual study failures degrades gracefully but may silently skip problems.
- Root directory is hardcoded or passed as a script argument — no config file.

---

## Tech Stack

| Category | Tools |
|---|---|
| Language | Python 3.10+ |
| Directory traversal | PowerShell via `subprocess` |
| PDF parsing | PyMuPDF (fitz) and/or pdfplumber |
| Word parsing | python-docx |
| Excel output | openpyxl |
| Concurrency | concurrent.futures (protocol scanner) |
| Logging | Python standard `logging` |

---

## How to Run

```bash
# Simple file finder
python main.py

# Protocol scanner (with PDF/Word parsing)
python protocol_scanner_v2.py
```

Edit the root directory path at the bottom of each script before running.

---

## Business / Practical Value

Turns a multi-hour manual file search across dozens of study folders into a sub-minute automated report — giving study coordinators an up-to-date overview of documentation status for audit readiness.

---

## Author

Jayesh Bhat · [https://www.linkedin.com/in/jayeshbhat/] · [https://github.com/JRBhat]
