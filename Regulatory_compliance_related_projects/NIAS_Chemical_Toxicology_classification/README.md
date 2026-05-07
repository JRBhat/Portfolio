# NIAS Standalone Reporter

> A desktop GUI application that identifies and classifies Non-Intentionally Added Substances (NIAS) in food contact materials, classification follows EU regulations and CAS/SMILES codes are automatically extracted from trusted databases such as PubCHEM and Chemspider. In the end, it generates a structured compliance Word report.

---

## Project Overview

- **Problem**: Analytical labs generating NIAS compliance reports for food contact materials must cross-reference instrument/analysis output (GC-MS peak lists) against EU regulatory databases, resolve missing CAS numbers via PubChem, apply Cramer toxicological classification, and produce formatted Word documents — a process that takes hours per sample when done manually.
- **Type**: Regulatory compliance automation / desktop application
- **Approach**: Reads a laboratory "Auswertung" Excel file and a NIAS substance database, merges them by CAS number, queries PubChem for any substance not found in the DB, applies EU FCM regulation checks, and exports a six-table Word report. All heavy processing runs in a QThread to keep the PySide6 GUI responsive.

---

## Objective

- Reduce manual reporting time for NIAS compliance submissions by automating the data merge, regulatory lookup, and document generation pipeline.
- Provide a GUI that guides analysts through the workflow and surfaces errors in real time.

---

## Dataset

| Field | Details |
|---|---|
| Source 1 | Laboratory Excel "Auswertung" sheet (GC-MS peak list with retention times, areas, CAS numbers) |
| Source 2 | NIAS substance database (internal Excel file with EU FCM classification, SML values) |
| External API | PubChem REST API (for substances not in the internal DB) |
| Output | Word `.docx` report with six compliance tables |

---

## Methodology

1. **Config loading** — INI config file provides file paths, ISD list, and pass/fail label text; GUI-set parameters (uncertainty factors, specimen mass) override config values.
2. **Database parsing** — `parsing.parse_db` loads all substance records from the NIAS DB Excel file into `Substance` dataclass instances.
3. **Excel parsing** — The lab Auswertung sheet is read and each row is categorised as: identified (has CAS), unidentified (no CAS/name), or alkane.
4. **Missing substance handling** — Substances absent from the DB are flagged; PubChem is queried using a rotating deque of identifier types (CAS → name → IUPAC → SMILES) until resolved.
5. **Merge** — `merge_db_and_excel_substances` applies DB or PubChem data to every substance object in priority order: direct CAS match → bad CAS remapping → manual follow-up record.
6. **EU regulation check** — `eu_regulation.py` applies FCM-specific rules (SML, Cramer class, FCM identifier).
7. **Chemical classification** — Cramer and Toxtree classification values are applied from the database.
8. **Export** — `exports.export_document` generates the final Word report with formatted compliance tables.

---

## Code Structure

```
NIAS_Chemical_Toxicology_classification/
└── source/
    ├── main.py                          # Qt app entry point
    ├── substance.py                     # Substance dataclass (CAS, SMILES, SML, classifications...)
    ├── parsing.py                       # Lab Excel and DB Excel parsers
    ├── merging.py                       # DB + PubChem merge logic
    ├── merge_helper_container.py        # TemporaryBucket helper for merge state
    ├── reporting.py                     # QThread orchestrating the full pipeline
    ├── exports.py                       # Word document generation
    ├── eu_regulation.py                 # EU FCM regulation rules
    ├── chemical_classification.py       # Cramer / Toxtree classification
    ├── missing_substances_and_bad_cas_handling.py
    ├── rounding.py                      # Regulatory rounding rules
    ├── excel_config_sheet.py            # Config sheet reader
    ├── get_all_classification.py        # Classification aggregator
    ├── autofill_db_to_update_missing.py # DB maintenance utility
    ├── add_missing_fcm_for_groups.py    # FCM group autofill
    ├── GUI_logic/                       # PySide6 window and dialog logic
    │   ├── gui_mainwindow.py
    │   ├── gui_autofill.py
    │   ├── gui_logging.py
    │   └── gui_reporting.py
    ├── GUI_utils/                       # GUI helper functions
    ├── Chemspider_API/                  # ChemSpider API client (supplementary lookups)
    ├── DB_manipulation_code/            # One-off DB maintenance scripts
    ├── utilityFuncs/                    # PubChem query + CAS validation utilities
    └── Tests/                           # Unit tests
```

---

## Key Logic

The PubChem enrichment loop uses a `collections.deque` to rotate through identifier types (CAS, name, IUPAC, SMILES). For each substance, it tries each available identifier in turn until all three target fields (CAS, IUPAC name, SMILES) are resolved or all options are exhausted. This avoids hammering PubChem with the same failing query type repeatedly.

The `Substance` dataclass stores all analytical and regulatory fields (retention time, area, CAS, SML, Cramer class, FCM number, INCI name, Toxtree, classifications in DE/EN) in one place — making it straightforward to pass the full substance context to any stage of the pipeline.

---

## Results

Output quality depends on the coverage of the internal NIAS database and PubChem's substance records.

Key outputs:
- Word report with six compliance tables
- Debug Excel file listing substances not found in the DB
- `cas_merge_errors.log` for tracing failed CAS resolutions

---

## Limitations

- SSL verification is disabled for PubChem queries in restricted network environments — this is a known configuration constraint, not a security oversight.
- PubChem API availability affects report completeness; substances unresolvable via API are flagged for manual follow-up.
- ChemSpider API services have been discontinued ever since it has been commercialized. Not open-sourced anymore. Lookup mus tbe done manually through their web application.

---

## Tech Stack

| Category | Tools |
|---|---|
| Language | Python 3.10+ |
| GUI | PySide6 (Qt) |
| Excel I/O | pandas, openpyxl |
| Word export | python-docx |
| External API | PubChem REST API, ChemSpider API |
| Data model | Python dataclasses |
| Logging | Python standard `logging` |

---

## How to Run

```bash
# Install dependencies
pip install PySide6 pandas openpyxl python-docx requests urllib3

# Run the GUI application
cd source
python main.py
```

Configure file paths and parameters via the GUI before triggering the reporting pipeline.

---

## Business / Practical Value

Compresses a multi-hour manual compliance reporting workflow into minutes — analysts load the instrument output, configure a few parameters, and receive a publication-ready Word document with all regulatory cross-references resolved and classified.

---

## Author

Jayesh Bhat · [https://www.linkedin.com/in/jayeshbhat/] · [https://github.com/JRBhat]
