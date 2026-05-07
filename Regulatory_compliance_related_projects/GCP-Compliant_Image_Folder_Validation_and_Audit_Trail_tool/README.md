# 🗂️ GCP-Compliant Image Folder Validation & Audit Tool

> Automates multi-stage image folder copy workflows for clinical studies with a full Excel audit trail and bit-perfect TeraCopy verification.

---

## 🧠 Project Overview

- **Problem**: Manual folder copying in clinical image studies lacks traceability — errors can go undetected and compromise GCP (Good Clinical Practice) compliance requirements.
- **Type**: Workflow Automation / Audit Tooling
- **Approach**: TeraCopy-orchestrated file transfers with cryptographic set-equality verification, combined with an OpenPyXL-based Excel workbook that logs every copy operation with hyperlinks, timestamps, and verification report references.

---

## 🎯 Objective

- Ensure every file transfer in a multi-stage image processing pipeline is bit-perfect and verifiable.
- Maintain a GCP-compliant audit trail (source, destination, timestamp, verification report) for each copy operation — ready for regulatory review.

---

## 📊 Dataset

| Field | Details |
|---|---|
| Source | Operator-provided Windows folder structure (pre-downloaded clinical image folders) |
| Size | Not applicable — tool is agnostic to folder/file count |
| Features | Image folders at each processing stage |
| Target | Not applicable — this is a workflow tool |

> The tool expects a Windows directory where each subfolder represents one image study session. No sample data is included in the repository.

---

## ⚙️ Methodology

1. **Initialization** — Prompts operator for resume/fresh-start mode; creates `logs/` and a new (or loads existing) `Process_Validation_file.xlsx` workbook.
2. **Preliminary Copy** — Finds the first unprocessed folder, creates a `$Basic_cleaned` staging destination, and invokes TeraCopy for the initial transfer.
3. **Verification** — Reads the TeraCopy CSV report and performs set-equality against expected files; mismatch triggers a red-highlighted error row in the workbook.
4. **State Tracking** — Prefixes the active source folder with `$` so the pipeline can resume across sessions without re-processing completed stages.
5. **User-Driven Loops** — Operator creates new downstream folders; the tool copies from the `$`-marked source, shifts the `$` prefix to the new folder, and logs each hop.

---

## 🧩 Code Structure

```
AutoFotoValidation_GCPcompliant_IMG/
├── main_v1_teracopy.py   # Primary entry point — full workflow with TeraCopy verification
├── main_v0_basic.py           # Legacy variant — simplified, without report tracking
├── requirements.txt               # openpyxl (only third-party dependency)
├── .gitignore
└── README.md
```

---

## 🧠 Key Logic / Algorithm

The `$` prefix sentinel is the core state machine: any folder whose name starts with `$` is the current "active source." This allows the operator to close the script mid-session and resume exactly where they left off by answering `y` to the startup prompt.

TeraCopy report verification works by collecting all source file paths into a Python `set`, then comparing it to the set of paths extracted from the TeraCopy CSV report. If the two sets are not equal, the operation is flagged with a red Excel row rather than silently passing — this is the GCP compliance guarantee.

---

## 📈 Results

> This is a workflow automation tool

Key operational outputs per run:
- `Process_Validation_file.xlsx` — audit workbook with source/destination hyperlinks, modification timestamps, and TeraCopy report hyperlinks for every copy operation
- `logs/` — archived TeraCopy CSV verification reports
- Console log — step-by-step operator feedback

---

## ⚠️ Limitations

- **Windows-only**: Depends on TeraCopy installed at `C:\Program Files\TeraCopy\TeraCopy.exe`.
- **Hardcoded study folder**: `DEFAULT_STUDY_FOLDER` points to `D:\test_software` — must be updated before use.
- **Workbook row cap**: `MAX_LOG_ROWS = 100` silently caps the audit log at 100 operations.
- **Single-user**: No locking or concurrency handling; designed for one operator at a time.

---

## 🛠️ Tech Stack

| Category | Tools |
|---|---|
| Language | Python 3.x |
| Excel I/O | openpyxl |
| File Transfer | TeraCopy (external, Windows) |
| Standard Library | os, sys, subprocess, datetime, shutil, glob, pathlib |

---

## ▶️ How to Run

```bash
# 1. Clone the repo
git clone "repo"
cd AutoFotoValidation_GCPcompliant

# 2. Install dependencies
pip install -r requirements.txt

# 3. Update the study folder path in main_v1_teracopy.py
#    DEFAULT_STUDY_FOLDER = r"D:\your\study\folder"

# 4. Run
python main_v1_teracopy.py
```

> TeraCopy must be installed separately on Windows before running.

---

## 💡 Business / Practical Value

Clinical image studies require documented chain-of-custody for every file transfer to satisfy GCP and regulatory audit requirements. This tool replaces manual copy-and-log workflows — where operators might forget to record a step or skip verification — with an automated pipeline that produces a self-contained Excel audit package. The `$` sentinel design means operators can safely interrupt and resume without risk of double-copying or losing track of which stage is active.

---

## 👤 Author

Jayesh Bhat · [LinkedIn](https://linkedin.com/in/jayeshbhat/) · [GitHub](https://github.com/JRBhat)
