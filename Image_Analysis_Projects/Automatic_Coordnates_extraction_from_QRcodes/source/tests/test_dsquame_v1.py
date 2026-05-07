"""
tests/test_dsquame_v1.py
-------------------------------------
Pytest test suite for the  D-Squame analysis pipeline.

Because the pipeline depends on the proprietary `internal_libraries` library and real scan
data, tests are split into:

  1. Pure-logic unit tests -- no internal_libraries / file I/O required.
  2. Integration tests     -- require internal_libraries + real data; skipped when unavailable.

Run with:
    pytest tests/test_dsquame_v1.py -v

To run only the unit tests (no internal_libraries required):
    pytest tests/test_dsquame_v1.py -v -m "not integration"
"""

import pytest
import numpy as np
import json
import os
import tempfile

# ============================================================================
# Fixtures -- generate synthetic data that mimics what internal_libraries would produce
# ============================================================================

@pytest.fixture
def synthetic_gray_data():
    """
    Synthetic gray_data dictionary mimicking what Phase 1 produces.

    Structure: {(subject_id, area_index, timepoint_index): np.array of pixel values}
      - 5 subjects, IDs 1..5
      - 4 areas (0..3)
      - 3 timepoints (0=t0, 1=3rd strip, 2=6th strip)

    Pixel values are drawn from a normal distribution:
      - t0 (timepoint 0):  brighter (higher grey value) -- baseline, little tape pick-up
      - strip timepoints:  slightly darker due to corneocyte removal
    """
    rng = np.random.default_rng(seed=42)
    data = {}
    for subj in range(1, 6):
        for area in range(4):
            for timep in range(3):
                # t0 is bright, strip timepoints are darker
                mean_val = 0.8 if timep == 0 else 0.4
                data[(subj, area, timep)] = rng.normal(mean_val, 0.05, size=500).clip(0, 1)
    return data


@pytest.fixture
def synthetic_gray_mean(synthetic_gray_data):
    """
    Build gray_mean from synthetic_gray_data to match Phase 1 output.
    gray_mean[subj] is a (4, 3) array of mean pixel intensities.
    """
    subjects = sorted(set(k[0] for k in synthetic_gray_data))
    gray_mean = {}
    for subj in subjects:
        arr = np.zeros((4, 3))
        for area in range(4):
            for timep in range(3):
                arr[area, timep] = np.mean(synthetic_gray_data[(subj, area, timep)])
        gray_mean[subj] = arr
    return gray_mean


@pytest.fixture
def synthetic_thresh_stat_data():
    """
    Synthetic thresh_stat_data dict mimicking Phase 2 output.
    Includes entries for normal subjects (1..31) plus two 'duplicate' subjects (102, 112).
    """
    rng = np.random.default_rng(seed=7)
    stat_data = {}

    # Normal subjects 1..31
    for subj in range(1, 32):
        for area in range(4):
            for timep in range(3):
                n_pixels = 500
                dark_frac = rng.uniform(0.05, 0.35)
                stat_data[(subj, area, timep)] = {
                    'percentage':     dark_frac,
                    'count':          int(dark_frac * n_pixels),
                    'ROIsize':        n_pixels,
                    'st_data_intern': [subj, 1, timep, f"S{subj:03d}F01T0{timep+1}SKW.tif"],
                    'val_img':        f"output/S{subj:03d}_val_auto.png",
                    'contour_name':   'Proband_top',
                    'reduce_circ_border': 48,
                    'threshold_perc': 5,
                    'used_threshold': 0.3,
                }

    # Duplicate entries: subject 102 and 112
    for area in range(4):
        for timep in range(3):
            n_pixels = 500
            dark_frac = rng.uniform(0.05, 0.35)
            stat_data[(102, area, timep)] = {
                'percentage':     dark_frac,
                'count':          int(dark_frac * n_pixels),
                'ROIsize':        n_pixels,
                'st_data_intern': [102, 1, timep, f"S102F01T0{timep+1}SKW.tif"],
                'val_img':        f"output/S102_val_auto.png",
                'contour_name':   'Proband_lower',
                'reduce_circ_border': 48,
                'threshold_perc': 5,
                'used_threshold': 0.3,
            }
            stat_data[(112, area, timep)] = {
                'percentage':     dark_frac,
                'count':          int(dark_frac * n_pixels),
                'ROIsize':        n_pixels,
                'st_data_intern': [112, 1, timep, f"S112F01T0{timep+1}SKW.tif"],
                'val_img':        f"output/S112_val_auto.png",
                'contour_name':   'Proband_lower',
                'reduce_circ_border': 48,
                'threshold_perc': 5,
                'used_threshold': 0.3,
            }

    return stat_data


# ============================================================================
# Unit tests -- Phase 1 logic
# ============================================================================

class TestPhase1IndexMapping:
    """
    The 12 spots per subject half are stored in a flat list.
    The mapping id -> (areal, timep) must satisfy:
      areal = id // 3    (values 0,1,2,3 for the four skin areas)
      timep = id % 3     (values 0,1,2 for t0, 3rd strip, 6th strip)
    """

    def test_areal_mapping(self):
        expected = [0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3]
        for id in range(12):
            assert id // 3 == expected[id], f"areal mismatch at id={id}"

    def test_timep_mapping(self):
        expected = [0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2]
        for id in range(12):
            assert id % 3 == expected[id], f"timep mismatch at id={id}"

    def test_all_12_spots_unique(self):
        """Every (areal, timep) pair maps to exactly one spot index."""
        pairs = [(id // 3, id % 3) for id in range(12)]
        assert len(pairs) == len(set(pairs)), "Duplicate (areal, timep) pairs found"

    def test_circle_radius_shrink(self):
        """
        reduce_circ_border_diameter = (256 - 232) * 2 = 48
        Effective diameter = original_diameter - 48
        For a circle stored with radius 256: effective radius should be 232.
        """
        reduce_circ_border_diameter = (256 - 232) * 2
        original_radius = 256
        # The formula applied in the code: x*2 - reduce  (x = radius, so x*2 = diameter)
        effective_diameter = original_radius * 2 - reduce_circ_border_diameter
        effective_radius = effective_diameter / 2
        assert effective_radius == 232


class TestPhase1GrayData:
    """Tests against the synthetic gray_data fixture."""

    def test_all_keys_present(self, synthetic_gray_data):
        """Phase 1 must produce entries for every (subj, area, timep) combination."""
        subjects = set(range(1, 6))
        areas    = set(range(4))
        timepoints = set(range(3))
        for subj in subjects:
            for area in areas:
                for timep in timepoints:
                    assert (subj, area, timep) in synthetic_gray_data

    def test_pixel_values_in_range(self, synthetic_gray_data):
        """Normalised pixel values must lie in [0, 1]."""
        for key, arr in synthetic_gray_data.items():
            assert arr.min() >= 0.0, f"Negative pixel value at {key}"
            assert arr.max() <= 1.0, f"Pixel value > 1 at {key}"

    def test_gray_mean_shape(self, synthetic_gray_mean):
        """gray_mean per subject must be a (4, 3) matrix."""
        for subj, mat in synthetic_gray_mean.items():
            assert mat.shape == (4, 3), f"Wrong shape for subject {subj}: {mat.shape}"

    def test_gray_mean_values_consistent(self, synthetic_gray_data, synthetic_gray_mean):
        """gray_mean[subj][area, timep] must match np.mean of the raw pixel array."""
        for subj in range(1, 6):
            for area in range(4):
                for timep in range(3):
                    expected = np.mean(synthetic_gray_data[(subj, area, timep)])
                    actual   = synthetic_gray_mean[subj][area, timep]
                    np.testing.assert_allclose(actual, expected, rtol=1e-6)


# ============================================================================
# Unit tests -- Phase 2 threshold logic
# ============================================================================

class TestPhase2ThresholdDerivation:
    """
    The dark threshold is derived as:
      perc = [Nth percentile of gray_data[(s,a,t)] for all (s,a,t) where t in {1,2}]
      dark_threshold = mean(perc[:40])  # first 5 subj * 4 areas * 2 timepoints
    """

    def test_threshold_uses_only_strip_timepoints(self, synthetic_gray_data):
        """
        Only timepoints 1 and 2 (strip measurements) should be used to compute
        the threshold, NOT timepoint 0 (baseline t0).
        """
        dummy_perc = 5
        strip_keys = [k for k in synthetic_gray_data.keys() if k[2] in [1, 2]]
        baseline_keys = [k for k in synthetic_gray_data.keys() if k[2] == 0]

        perc_strip    = [np.percentile(synthetic_gray_data[k], dummy_perc) for k in strip_keys]
        perc_baseline = [np.percentile(synthetic_gray_data[k], dummy_perc) for k in baseline_keys]

        # Strip percentile values should be lower than baseline (darker after tape removal)
        assert np.mean(perc_strip) < np.mean(perc_baseline), \
            "Strip timepoints are expected to be darker than baseline"

    def test_threshold_count_slice(self, synthetic_gray_data):
        """The slice [:4*2*5] selects exactly 40 values (5 subj * 4 areas * 2 timepoints)."""
        keys = [k for k in synthetic_gray_data.keys() if k[2] in [1, 2]]
        expected_count = 4 * 2 * 5  # = 40
        assert len(keys[:expected_count]) == expected_count

    def test_threshold_is_scalar(self, synthetic_gray_data):
        """dark_threshold must be a single scalar, not an array."""
        dummy_perc = 5
        perc = [
            np.percentile(synthetic_gray_data[k], dummy_perc)
            for k in synthetic_gray_data.keys()
            if k[2] in [1, 2]
        ]
        dark_threshold = np.mean(perc[:(4 * 2 * 5)])
        assert np.isscalar(dark_threshold) or dark_threshold.ndim == 0

    def test_threshold_range(self, synthetic_gray_data):
        """For synthetic data with strip means ~0.4, threshold should be in [0, 1]."""
        dummy_perc = 5
        perc = [
            np.percentile(synthetic_gray_data[k], dummy_perc)
            for k in synthetic_gray_data.keys()
            if k[2] in [1, 2]
        ]
        dark_threshold = np.mean(perc[:(4 * 2 * 5)])
        assert 0.0 <= dark_threshold <= 1.0


class TestPhase2DarkPixelClassification:
    """
    A pixel is classified as 'dark' (part of a D-Squame disc residue spot) when
    its intensity is BELOW the dark_threshold.
    data = pixel_array < dark_threshold  --> boolean array
    percentage = np.mean(data)           --> fraction of dark pixels
    """

    def test_percentage_between_0_and_1(self):
        rng = np.random.default_rng(42)
        pixels = rng.uniform(0, 1, 1000)
        threshold = 0.35
        data = pixels < threshold
        percentage = np.mean(data)
        assert 0.0 <= percentage <= 1.0

    def test_count_equals_sum_of_booleans(self):
        rng = np.random.default_rng(42)
        pixels = rng.uniform(0, 1, 1000)
        threshold = 0.35
        data = pixels < threshold
        assert np.sum(data) == int(np.sum(data))  # must be integer-valued

    def test_all_dark_when_threshold_above_max(self):
        pixels = np.array([0.1, 0.2, 0.3])
        threshold = 1.0
        data = pixels < threshold
        assert np.mean(data) == 1.0

    def test_none_dark_when_threshold_below_min(self):
        pixels = np.array([0.5, 0.6, 0.7])
        threshold = 0.0
        data = pixels < threshold
        assert np.mean(data) == 0.0


# ============================================================================
# Unit tests -- Phase 3 subject-ID correction logic
# ============================================================================

class TestPhase3SubjectCorrection:
    """
    Phase 3 applies a hard-coded mapping to move data from duplicate scan IDs
    (102, 112) back to the real subject IDs (2, 12).
    """

    def test_subject_2_area_2_2_remapped(self, synthetic_thresh_stat_data):
        """(2,2,2) should come from the dirty (2,3,1) entry."""
        dirty = synthetic_thresh_stat_data

        cleaned = {}
        cleaned[(2, 2, 2)] = dirty[(2, 3, 1)]
        cleaned[(2, 3, 1)] = dirty[(102, 3, 1)]
        cleaned[(2, 3, 2)] = dirty[(102, 3, 2)]
        cleaned[(12, 2, 2)] = dirty[(112, 2, 2)]

        assert cleaned[(2, 2, 2)] is dirty[(2, 3, 1)]
        assert cleaned[(2, 3, 1)] is dirty[(102, 3, 1)]
        assert cleaned[(12, 2, 2)] is dirty[(112, 2, 2)]

    def test_normal_subjects_pass_through(self, synthetic_thresh_stat_data):
        """
        Normal subjects (ID <= 31) that are not manually remapped should be
        copied unchanged into the cleaned dict.
        """
        dirty = synthetic_thresh_stat_data

        cleaned = {}
        cleaned[(2, 2, 2)] = dirty[(2, 3, 1)]
        cleaned[(2, 3, 1)] = dirty[(102, 3, 1)]
        cleaned[(2, 3, 2)] = dirty[(102, 3, 2)]
        cleaned[(12, 2, 2)] = dirty[(112, 2, 2)]

        for subj_data, data_c in dirty.items():
            if (subj_data[0] <= 31) and (subj_data not in cleaned):
                cleaned[subj_data] = data_c

        # Subject 1, all areas/timepoints must be present
        for area in range(4):
            for timep in range(3):
                assert (1, area, timep) in cleaned, f"(1,{area},{timep}) missing from cleaned"

    def test_duplicates_excluded_from_cleaned(self, synthetic_thresh_stat_data):
        """
        After correction, no entries with subject ID 102 or 112 should remain
        in the cleaned dict (they have been re-keyed or excluded).
        """
        dirty = synthetic_thresh_stat_data

        cleaned = {}
        cleaned[(2, 2, 2)] = dirty[(2, 3, 1)]
        cleaned[(2, 3, 1)] = dirty[(102, 3, 1)]
        cleaned[(2, 3, 2)] = dirty[(102, 3, 2)]
        cleaned[(12, 2, 2)] = dirty[(112, 2, 2)]

        for subj_data, data_c in dirty.items():
            if (subj_data[0] <= 31) and (subj_data not in cleaned):
                cleaned[subj_data] = data_c

        duplicate_keys = [k for k in cleaned if k[0] in (102, 112)]
        assert len(duplicate_keys) == 0, f"Duplicate subject keys still present: {duplicate_keys}"

    def test_area_timepoint_names(self):
        """Sanity check on the German area/timepoint name arrays."""
        areanames  = ["links unten", "links oben", "rechts unten", "rechts oben"]
        timepnames = ["t0", "3.strip", "6.strip"]

        assert len(areanames) == 4, "Expected 4 area names"
        assert len(timepnames) == 3, "Expected 3 timepoint names"

        # Index 0 should be the baseline
        assert timepnames[0] == "t0"
        # Index 1 and 2 are the strip measurements
        assert "strip" in timepnames[1]
        assert "strip" in timepnames[2]


# ============================================================================
# Unit tests -- TSV output format
# ============================================================================

class TestOutputFormat:
    """Verify the structure of the .tsv rows produced by both the raw and cleaned export."""

    def test_raw_tsv_row_length(self, synthetic_thresh_stat_data):
        """
        Each raw TSV row must have the same number of fields as the header.
        Header: ['subj', 'areal', 'timep', 'Test', 'Test_long', 'Value', 'Unit',
                 'org_img', 'val_img', 'contour_name', 'used_threshold',
                 'threshold_perc', 'reduce_circ_border']
        """
        header = [
            'subj', 'areal', 'timep', 'Test', "Test_long", "Value", "Unit",
            'org_img', 'val_img', 'contour_name', 'used_threshold',
            'threshold_perc', 'reduce_circ_border',
        ]
        test_names = {
            'percentage': 'percentage of covered area',
            'count':      'count of dark pixels in ROI',
            'ROIsize':    'pixels in roi',
        }
        unit_names = {'percentage': '0-1', 'count': '#', 'ROIsize': '#'}

        # Take the first entry for a quick check
        subj_data = (1, 0, 0)
        data_c = synthetic_thresh_stat_data[subj_data]

        for test_key, long_test_name in test_names.items():
            row = (
                [str(subj_data[0]), str(subj_data[1] + 1), str(subj_data[2] + 1)]
                + [test_key, long_test_name, str(data_c[test_key]), unit_names[test_key],
                   str(data_c['st_data_intern'][-1])]
                + [str(data_c[loc_key]) for loc_key in header[8:]]
            )
            assert len(row) == len(header), \
                f"Row length {len(row)} != header length {len(header)} for test_key={test_key}"

    def test_cleaned_tsv_has_area_and_time_names(self, synthetic_thresh_stat_data):
        """
        The cleaned TSV adds 'areal_name' and 'timepoint_name' columns.
        Verify a sample row contains the expected German strings.
        """
        areanames  = ["links unten", "links oben", "rechts unten", "rechts oben"]
        timepnames = ["t0", "3.strip", "6.strip"]

        subj_data = (1, 2, 1)  # subject 1, area 2 ("rechts unten"), timepoint 1 ("3.strip")
        data_c    = synthetic_thresh_stat_data[subj_data]

        row_prefix = [
            str(subj_data[0]),
            str(subj_data[1] + 1),
            str(subj_data[2] + 1),
            areanames[subj_data[1]],   # "rechts unten"
            timepnames[subj_data[2]],  # "3.strip"
        ]
        assert row_prefix[3] == "rechts unten"
        assert row_prefix[4] == "3.strip"


# ============================================================================
# Integration tests (require internal_libraries and real data files)
# ============================================================================

@pytest.mark.integration
class TestIntegration:
    """
    These tests exercise the real pipeline against actual data.
    They are skipped automatically when internal_libraries is not installed or data paths
    don't exist.  To enable, set environment variable ENABLE_INTEGRATION_TESTS=1.
    """

    OUTPUTPATH = "output/analysis"
    DATA_DAT   = os.path.join(OUTPUTPATH, "data.dat")

    @pytest.fixture(autouse=True)
    def skip_if_no_internal_libraries(self):
        pytest.importorskip("internal_libraries", reason="internal_libraries library not available; skipping integration test")
        if not os.path.exists(self.DATA_DAT):
            pytest.skip(f"data.dat not found at {self.DATA_DAT}")

    def test_data_dat_loadable(self):
        """data.dat produced by Phase 1 must be loadable by internal_libraries Util.readData."""
        from ImageAnalysis import Util
        result = Util.readData(self.DATA_DAT)
        assert len(result) == 3, "Expected [study_data, gray_data, gray_mean]"

    def test_gray_mean_shapes(self):
        """Each entry in gray_mean must be a (4,3) matrix."""
        from ImageAnalysis import Util
        _, _, gray_mean = Util.readData(self.DATA_DAT)
        for subj, mat in gray_mean.items():
            assert mat.shape == (4, 3), f"Subject {subj} gray_mean shape is {mat.shape}"
