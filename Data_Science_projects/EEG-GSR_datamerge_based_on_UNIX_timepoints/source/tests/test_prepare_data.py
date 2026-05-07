"""
Tests for prepare_data_before_running_merge_func.py

Tests cover:
  - Rule matching functions (predicates) for each CleanupRule
  - apply_rules in DRY_RUN mode (no actual file changes)
  - apply_rules actually deletes / renames files
  - FileActionResult statistics are accurate
  - Invalid folder path is handled gracefully
  - Rule presets (ALL_RULES, DEFAULT_RULES, SELECTED_RULES) are defined and non-empty
"""
import os
import pytest

import prepare_data_before_running_merge_func as cleanup_mod
from prepare_data_before_running_merge_func import (
    CleanupRule,
    FileActionResult,
    apply_rules,
    delete_segments_pkl,
    delete_png,
    rename_tsv,
    delete_statistics_xlsx,
    delete_area_ffa_csv,
    delete_merged_xlsx,
    ALL_RULES,
    DEFAULT_RULES,
    SELECTED_RULES,
    TIMESTAMP_PATTERN,
)


# ---------------------------------------------------------------------------
# Predicate unit tests
# ---------------------------------------------------------------------------

class TestRulePredicates:
    """Each predicate returns True only for its intended file pattern."""

    # --- delete_segments_pkl ---
    def test_segments_pkl_matches_segments_file(self):
        assert delete_segments_pkl("/a/b", "segments.pkl") is True

    def test_segments_pkl_matches_df_temp(self):
        assert delete_segments_pkl("/a/b", "df_temp.pkl") is True

    def test_segments_pkl_rejects_other_pkl(self):
        assert delete_segments_pkl("/a/b", "data.pkl") is False

    def test_segments_pkl_rejects_non_pkl(self):
        assert delete_segments_pkl("/a/b", "segments.txt") is False

    # --- delete_png ---
    def test_png_matches_png_file(self):
        assert delete_png("/a/b", "bpm_plot.png") is True

    def test_png_rejects_jpg(self):
        assert delete_png("/a/b", "image.jpg") is False

    def test_png_rejects_png_in_path_not_name(self):
        assert delete_png("/a/png_folder", "data.xlsx") is False

    # --- rename_tsv ---
    # rename_tsv returns a re.Match object (truthy) or False/None — use bool()
    def test_rename_tsv_matches_timestamped_tsv(self):
        assert bool(rename_tsv("/a/b", "20240101120000_eeg.tsv"))

    def test_rename_tsv_rejects_tsv_without_timestamp(self):
        assert not rename_tsv("/a/b", "eeg_data.tsv")

    def test_rename_tsv_rejects_short_timestamp(self):
        assert not rename_tsv("/a/b", "2024010112.tsv")

    def test_rename_tsv_rejects_non_tsv(self):
        assert not rename_tsv("/a/b", "20240101120000_eeg.easy")

    # --- delete_statistics_xlsx ---
    def test_statistics_xlsx_matches(self):
        assert delete_statistics_xlsx("/a/b", "statistics_subject_a.xlsx") is True

    def test_statistics_xlsx_rejects_no_statistics_keyword(self):
        assert delete_statistics_xlsx("/a/b", "merged_data.xlsx") is False

    def test_statistics_xlsx_rejects_csv(self):
        assert delete_statistics_xlsx("/a/b", "statistics_subject.csv") is False

    # --- delete_area_ffa_csv ---
    def test_area_ffa_csv_matches(self):
        assert delete_area_ffa_csv("/a/b", "area_subject_ffa.csv") is True

    def test_area_ffa_csv_rejects_missing_ffa(self):
        assert delete_area_ffa_csv("/a/b", "area_subject.csv") is False

    def test_area_ffa_csv_rejects_missing_area(self):
        assert delete_area_ffa_csv("/a/b", "data_ffa.csv") is False

    def test_area_ffa_csv_rejects_xlsx(self):
        assert delete_area_ffa_csv("/a/b", "area_subject_ffa.xlsx") is False

    # --- delete_merged_xlsx ---
    def test_merged_xlsx_matches(self):
        assert delete_merged_xlsx("/a/b", "merged_highlighted_subject.xlsx") is True

    def test_merged_xlsx_rejects_non_merged(self):
        assert delete_merged_xlsx("/a/b", "statistics_subject.xlsx") is False

    def test_merged_xlsx_rejects_csv(self):
        assert delete_merged_xlsx("/a/b", "merged_data.csv") is False


# ---------------------------------------------------------------------------
# Rule preset tests
# ---------------------------------------------------------------------------

class TestRulePresets:

    def test_all_rules_contains_all_enum_members(self):
        assert ALL_RULES == set(CleanupRule)

    def test_default_rules_is_subset_of_all_rules(self):
        assert DEFAULT_RULES.issubset(ALL_RULES)

    def test_selected_rules_is_non_empty(self):
        assert len(SELECTED_RULES) > 0

    def test_selected_rules_is_subset_of_all_rules(self):
        assert SELECTED_RULES.issubset(ALL_RULES)

    def test_all_rules_has_six_members(self):
        assert len(ALL_RULES) == 6, "There should be exactly 6 CleanupRule enum members"


# ---------------------------------------------------------------------------
# apply_rules integration tests (using tmp_path)
# ---------------------------------------------------------------------------

class TestApplyRules:

    def _set_dry_run(self, value: bool):
        """Monkeypatch the module-level DRY_RUN flag."""
        cleanup_mod.DRY_RUN = value

    def teardown_method(self):
        """Always reset DRY_RUN to False after each test."""
        cleanup_mod.DRY_RUN = False

    def test_returns_file_action_result(self, tmp_path):
        result = apply_rules(str(tmp_path), set())
        assert isinstance(result, FileActionResult)

    def test_invalid_folder_returns_zero_stats(self):
        result = apply_rules("/this/path/does/not/exist", ALL_RULES)
        assert result.deleted == 0
        assert result.renamed == 0
        assert result.scanned == 0

    def test_dry_run_does_not_delete_png(self, tmp_path):
        png_file = tmp_path / "bpm_plot.png"
        png_file.write_bytes(b"\x89PNG\r\n")  # minimal PNG header

        self._set_dry_run(True)
        apply_rules(str(tmp_path), {CleanupRule.PNG_IMAGES})

        assert png_file.exists(), "DRY_RUN should not actually delete the PNG"

    def test_actual_delete_removes_png(self, tmp_path):
        png_file = tmp_path / "bpm_plot.png"
        png_file.write_bytes(b"\x89PNG\r\n")

        self._set_dry_run(False)
        result = apply_rules(str(tmp_path), {CleanupRule.PNG_IMAGES})

        assert not png_file.exists(), "PNG file should be deleted"
        assert result.deleted == 1

    def test_actual_delete_removes_statistics_xlsx(self, tmp_path):
        stats_file = tmp_path / "statistics_subject_a.xlsx"
        stats_file.write_bytes(b"PK")  # minimal ZIP/xlsx header

        self._set_dry_run(False)
        result = apply_rules(str(tmp_path), {CleanupRule.STATISTICS_XLSX})

        assert not stats_file.exists()
        assert result.deleted == 1

    def test_rename_tsv_to_easy(self, tmp_path):
        tsv_file = tmp_path / "20240101120000_eeg.tsv"
        tsv_file.write_text("dummy")

        self._set_dry_run(False)
        result = apply_rules(str(tmp_path), {CleanupRule.TSV_TO_EASY})

        expected_easy = tmp_path / "20240101120000_eeg.easy"
        assert expected_easy.exists(), ".tsv file should be renamed to .easy"
        assert not tsv_file.exists(), "Original .tsv file should no longer exist"
        assert result.renamed == 1

    def test_dry_run_rename_does_not_rename(self, tmp_path):
        tsv_file = tmp_path / "20240101120000_eeg.tsv"
        tsv_file.write_text("dummy")

        self._set_dry_run(True)
        apply_rules(str(tmp_path), {CleanupRule.TSV_TO_EASY})

        assert tsv_file.exists(), "DRY_RUN should not rename the file"

    def test_scanned_count_equals_total_files(self, tmp_path):
        for name in ["a.png", "b.txt", "c.xlsx"]:
            (tmp_path / name).write_text("x")

        result = apply_rules(str(tmp_path), set())
        assert result.scanned == 3

    def test_one_rule_per_file(self, tmp_path):
        """A file matching multiple rules should only be acted on once (first matching rule)."""
        # This file matches both PNG_IMAGES and potentially others
        png_file = tmp_path / "statistics_bpm.png"
        png_file.write_bytes(b"\x89PNG\r\n")

        self._set_dry_run(False)
        result = apply_rules(str(tmp_path), {CleanupRule.PNG_IMAGES, CleanupRule.STATISTICS_XLSX})

        # File should be deleted once, not twice
        assert result.deleted == 1

    def test_segments_pkl_deleted(self, tmp_path):
        pkl_file = tmp_path / "segments.pkl"
        pkl_file.write_bytes(b"\x80\x05")  # pickle header

        self._set_dry_run(False)
        result = apply_rules(str(tmp_path), {CleanupRule.SEGMENTS_PKL})

        assert not pkl_file.exists()
        assert result.deleted == 1

    def test_df_temp_pkl_deleted(self, tmp_path):
        pkl_file = tmp_path / "df_temp.pkl"
        pkl_file.write_bytes(b"\x80\x05")

        self._set_dry_run(False)
        result = apply_rules(str(tmp_path), {CleanupRule.SEGMENTS_PKL})

        assert not pkl_file.exists()
        assert result.deleted == 1

    def test_empty_folder_returns_zero_stats(self, tmp_path):
        result = apply_rules(str(tmp_path), ALL_RULES)
        assert result.scanned == 0
        assert result.deleted == 0
        assert result.renamed == 0

    def test_subdirectory_files_are_scanned(self, tmp_path):
        """apply_rules should recurse into subdirectories."""
        subdir = tmp_path / "subject_01"
        subdir.mkdir()
        png = subdir / "bpm.png"
        png.write_bytes(b"\x89PNG")

        self._set_dry_run(False)
        result = apply_rules(str(tmp_path), {CleanupRule.PNG_IMAGES})

        assert not png.exists(), "PNG in subdirectory should be deleted"
        assert result.deleted == 1
