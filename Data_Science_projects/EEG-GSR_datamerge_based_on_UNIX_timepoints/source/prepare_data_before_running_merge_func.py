import os
import re
import logging
from enum import Enum, auto
from dataclasses import dataclass
from typing import Callable, Dict, Tuple, Set


# -----------------------------
# CONFIGURATION
# -----------------------------

DRY_RUN = False  # 🔴 Change to False to ACTUALLY delete/rename files

LOG_FILE = "cleanup.log"

# Regex to detect timestamp at the beginning of filename (YYYYMMDDHHMMSS)
TIMESTAMP_PATTERN = re.compile(r'^\d{14}')


# -----------------------------
# LOGGING SETUP
# -----------------------------

# Configure logging to file and console; logs both to a file and the console for better traceability using standard logging module
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("SmartCleanup")


# -----------------------------
# ENUM FOR RULES
# -----------------------------

# Enum to define cleanup rules- using Enum for clarity and type safety - auto() for automatic value assignment
class CleanupRule(Enum):
    SEGMENTS_PKL = auto()
    PNG_IMAGES = auto()
    TSV_TO_EASY = auto()
    STATISTICS_XLSX = auto()
    AREA_FFA_CSV = auto()
    MERGED_XLSX = auto()


# -----------------------------
# RULE FUNCTIONS
# -----------------------------


# Individual rule functions that determine if a file matches the rule
def delete_segments_pkl(path: str, name: str) -> bool:
    return name.endswith(".pkl") and ("segments" in name or "df_temp" in name)

def delete_png(path: str, name: str) -> bool:
    return name.endswith(".png")

def rename_tsv(path: str, name: str) -> bool:
    return name.endswith(".tsv") and TIMESTAMP_PATTERN.match(name)

def delete_statistics_xlsx(path: str, name: str) -> bool:
    return name.endswith(".xlsx") and "statistics" in name

def delete_area_ffa_csv(path: str, name: str) -> bool:
    return name.endswith(".csv") and "area" in name and "ffa" in name

def delete_merged_xlsx(path: str, name: str) -> bool:
    return name.endswith(".xlsx") and "merged" in name


# -----------------------------
# DISPATCH TABLE
# -----------------------------

# Rule dispatch table mapping rules to their actions and functions; used for dynamic rule application; strategy pattern implementation
# Each entry maps a CleanupRule to a tuple of (action_type, function)
# action_type is either "delete" or "rename"
RULE_DISPATCH: Dict[CleanupRule, Tuple[str, Callable[[str, str], bool]]] = {
    CleanupRule.SEGMENTS_PKL:   ("delete", delete_segments_pkl),
    CleanupRule.PNG_IMAGES:     ("delete", delete_png),
    CleanupRule.TSV_TO_EASY:    ("rename", rename_tsv),
    CleanupRule.STATISTICS_XLSX:("delete", delete_statistics_xlsx),
    CleanupRule.AREA_FFA_CSV:   ("delete", delete_area_ffa_csv),
    CleanupRule.MERGED_XLSX:   ("delete", delete_merged_xlsx),
}


# -----------------------------
# CORE ENGINE
# -----------------------------

# dataclass to hold statistics- dataclass used due to its simplicity and built-in features; could be replaced with a simple dict if preferred
@dataclass
class FileActionResult:
    deleted: int = 0
    renamed: int = 0
    scanned: int = 0


def _delete_file(path: str):
    if DRY_RUN:
        logger.info(f"[DRY-RUN] Would delete: {path}")
    else:
        os.remove(path)
        logger.info(f"Deleted: {path}")


def _rename_file(old_path: str):
    new_path = os.path.splitext(old_path)[0] + ".easy"

    if DRY_RUN:
        logger.info(f"[DRY-RUN] Would rename: {old_path} -> {new_path}")
    else:
        os.rename(old_path, new_path)
        logger.info(f"Renamed: {old_path} -> {new_path}")


def apply_rules(root_folder: str, selected_rules: Set[CleanupRule]) -> FileActionResult:
    stats = FileActionResult()

    if not os.path.isdir(root_folder):
        logger.error(f"Invalid folder: {root_folder}")
        return stats

    for root, _, files in os.walk(root_folder):
        for file in files:
            stats.scanned += 1
            normalized_name = file.lower()
            full_path = os.path.join(root, file)

            for rule in selected_rules:
                action, rule_fn = RULE_DISPATCH[rule]

                if rule_fn(full_path, normalized_name):
                    if action == "delete":
                        _delete_file(full_path)
                        stats.deleted += 1

                    elif action == "rename":
                        _rename_file(full_path)
                        stats.renamed += 1

                    break  # One rule per file

    return stats


# -----------------------------
# RULE PRESETS (SWITCH-LIKE)
# -----------------------------

# Set of all rules for easy reference and presets- allowing inclusion/exclusion simply by subtracting from the set
ALL_RULES = set(CleanupRule)

DEFAULT_RULES = {
    CleanupRule.SEGMENTS_PKL,
    CleanupRule.PNG_IMAGES,
    CleanupRule.TSV_TO_EASY,
    CleanupRule.STATISTICS_XLSX,
    CleanupRule.AREA_FFA_CSV,
    CleanupRule.MERGED_XLSX
}

#  Custom selection of rules (like a switch) to enable/disable specific rules simply by adding/removing them here
SELECTED_RULES = ALL_RULES - {
    # Exclude AREA_FFA_CSV deletion
    CleanupRule.AREA_FFA_CSV,
    # Exclude MERGED_XLSX deletion
    CleanupRule.MERGED_XLSX
}
    
# -----------------------------
# MAIN
# -----------------------------

def main():
    print("\n--- SMART CLEANUP TOOL ---")
    print(f"DRY_RUN = {DRY_RUN}")
    print(f"Logs saved to: {LOG_FILE}")

    folder_path = "data/thesis_study/test"

    # Edit this set to choose what runs (like a switch)
    selected_rules = DEFAULT_RULES # Use DEFAULT_RULES to run all rules

    logger.info(f"Starting scan in: {folder_path}")
    logger.info(f"Active rules: {[r.name for r in selected_rules]}")

    stats = apply_rules(folder_path, selected_rules)

    logger.info("=" * 50)
    logger.info("PROCESS COMPLETE")
    logger.info(f"Files scanned : {stats.scanned}")
    logger.info(f"Files deleted : {stats.deleted}")
    logger.info(f"Files renamed : {stats.renamed}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
