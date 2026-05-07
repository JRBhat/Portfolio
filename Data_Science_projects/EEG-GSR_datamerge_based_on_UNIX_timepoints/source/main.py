"""
Pipeline orchestration entry point for the EEG-GSR datamerge workflow.

This module coordinates the per-subject processing pipeline: it discovers
subject directories under ``MAIN_DIR``, merges EEG (.easy/.tsv) with GSR
(.csv) recordings via :func:`merge_data_V2.merge_device_datasets`, computes
Frontal Alpha Asymmetry (FAA), runs marker correction (clinical study only),
generates plots, and aggregates per-subject statistics into a final
collated report.

The :class:`StudyType` enum dispatches between the two supported study
designs: ``CLINICAL`` (six-trigger longitudinal protocol) and
``MASTERARBEIT`` (four-trigger pre/application/CPT/post protocol). Each
study type uses its own trigger sequence and statistics aggregator.
"""
import os
import traceback

from merge_data_V2 import merge_device_datasets
from calculate_FFA import compute_faa
from plot_data_vertical_markers_matplotlib_V4_fullyrefac import generate_plots
from extract_markers import extract_and_serialize_marker_ones
from generate_stats import generate_statistics_clinical, generate_statistics_masterarbeit
from generate_final_report_and_image import generate_final_collated_stat_file
from enum import Enum

# --- Module-level configuration constants ---
# MAIN_DIR = "data/eeg_study/current_noDownsampled"
MAIN_DIR = "data/thesis_study/03-Final--bad_subjects_rmwd--cleaned_complete_pairs_only"
FINAL_STAT_OUTPUT = os.path.join(MAIN_DIR, r"final_statistics_masterarbeit_bad_subjcts_rmwd.xlsx")
MASTERARBEIT_TRIGGER_SEQUENCE = [1, 3, 4, 2]
CLINICAL_TRIGGER_SEQUENCE = [1, 2, 3, 4, 5, 6]
MEASURED_VARIABLES = ['BPM', 'Skin_conductance_uS', 'FAA']


class StudyType(Enum):
    CLINICAL = "clinical_study"
    MASTERARBEIT = "Masterarbeit"


def main(study_type):
    for subj_name in os.listdir(MAIN_DIR):
        subject_dir = os.path.join(MAIN_DIR, subj_name)
        if not os.path.isdir(subject_dir):
            continue

        # create paths for eeg and gsr files and fft files
        subj_name = os.path.basename(subject_dir)
        eeg_path, gsr_path = r"", r""

        faa_input_path = os.path.join(subject_dir, fr"Area_{subj_name}.txt") # --- Addition: FAA input path
        faa_output_path = faa_input_path.replace(fr"Area_{subj_name}.txt", fr"Area_{subj_name}_ffa.csv") # --- Addition: FAA output path


        # Process each subject directory and handle exceptions incase of missing files or errors related
        try:
            for f in os.listdir(subject_dir):
                if f.endswith(".easy"):
                    src = os.path.join(subject_dir, f)
                    eeg_path = src.replace(".easy", ".tsv")
                    if not os.path.exists(eeg_path):
                        os.rename(src, eeg_path)

                if f.endswith("csv"):
                    gsr_path = os.path.join(subject_dir, f)

            # Merge datasets and compute BPM
            try:
                merged_path =  merge_device_datasets(eeg_path, gsr_path, subject_dir)
            except FileNotFoundError as e:
                if f.endswith(".tsv"):
                    eeg_path = os.path.join(subject_dir, f)
            ffa_output = compute_faa(faa_input_path, faa_output_path, studytype=study_type.value)
            
            if study_type == StudyType.CLINICAL:
                marker_number_corrected_outputpath = extract_and_serialize_marker_ones(merged_path)
                segments = generate_plots(marker_number_corrected_outputpath, 
                                        window_duration_mins=1,
                                        downsample_size=10, 
                                        marker_values=CLINICAL_TRIGGER_SEQUENCE)

                generate_statistics_clinical(segments, ffa_output, marker_number_corrected_outputpath)
            
            if study_type == StudyType.MASTERARBEIT:
                segments = generate_plots(merged_path, 
                        window_duration_mins=10,
                        downsample_size=5, 
                        marker_values=MASTERARBEIT_TRIGGER_SEQUENCE)
                generate_statistics_masterarbeit(segments, ffa_output, merged_path)

            
        except FileNotFoundError as e:
            traceback.print_exception(type(e), e, e.__traceback__)
            continue
        
    print("Generating final collated report...")
    generate_final_collated_stat_file(MAIN_DIR, FINAL_STAT_OUTPUT, MEASURED_VARIABLES)    
    
if __name__ == "__main__":
    main(study_type=StudyType.MASTERARBEIT)
    # main(study_type = StudyType.CLINICAL)