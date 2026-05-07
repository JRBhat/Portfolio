import logging
import pandas as pd
import numpy as np
import argparse
import os

logger = logging.getLogger(__name__)

# Default column separator for whitespace-delimited input files.
DEFAULT_SEPARATOR = r'\s+'


def compute_faa(input_path: str, output_path: str, studytype: str, sep: str = DEFAULT_SEPARATOR):
    """
    Reads an EEG alpha values file, computes Frontal Alpha Asymmetry (FAA),
    and writes the augmented data to a CSV.

    Parameters:
    - input_path: Path to the input data file (e.g., .txt or .csv)
    - output_path: Path where the output CSV with FAA will be saved
    - studytype: Study design identifier. Accepted values:
        - ``"Masterarbeit"`` — computes FAA_pre and FAA_post from pre/post
          columns and returns a dict with those two keys.
        - ``"clinical"`` — computes six FAA timepoints (baseline, applk,
          5 min, 10 min, 15 min, 20 min) and returns a dict with six keys.
    - sep: Column separator regex for pandas.read_csv (default: whitespace)
    """
    if studytype == "Masterarbeit":
        if not os.path.exists(output_path):
            # Load data
            df = pd.read_csv(input_path, sep=sep, decimal=',')

            # Compute FAA for pre and post
            df['FAA_pre'] = np.log(df['F4-Average_pre']) - np.log(df['F3-Average_pre'])
            df['FAA_post'] = np.log(df['F4-Average_post']) - np.log(df['F3-Average_post'])

            # Save augmented data
            df.to_csv(output_path, index=False)
            logger.info("Saved FAA-augmented data to %s", output_path)
            return {'FAA_pre': df['FAA_pre'][0], 'FAA_post': df['FAA_post'][0]}

        else:
            logger.info("FAA output already exists at %s", output_path)
            logger.info("Skipping FFA calculation and proceeding to plotting...")
            df = pd.read_csv(output_path)
            return {'FAA_pre': df['FAA_pre'][0], 'FAA_post': df['FAA_post'][0]}

    elif studytype == "clinical":
        if not os.path.exists(output_path):
            # Load data
            df = pd.read_csv(input_path, sep=sep)

            # Compute FAA for pre and post
            df['FAA_baseline'] = np.log(df['F4-Average_baseline']) - np.log(df['F3-Average_baseline'])
            df['FAA_applk'] = np.log(df['F4-Average_applk']) - np.log(df['F3-Average_applk'])
            df['FAA_5min'] = np.log(df['F4-Average_5min']) - np.log(df['F3-Average_5min'])
            df['FAA_10min'] = np.log(df['F4-Average_10min']) - np.log(df['F3-Average_10min'])
            df['FAA_15min'] = np.log(df['F4-Average_15min']) - np.log(df['F3-Average_15min'])
            df['FAA_20min'] = np.log(df['F4-Average_20min']) - np.log(df['F3-Average_20min'])

            # Save augmented data
            df.to_csv(output_path, index=False)
            logger.info("Saved FAA-augmented data to %s", output_path)
            return {'FAA_baseline': df['FAA_baseline'][0],
                    'FAA_applk': df['FAA_applk'][0],
                    'FAA_5min': df['FAA_5min'][0],
                    'FAA_10min': df['FAA_10min'][0],
                    'FAA_15min': df['FAA_15min'][0],
                    'FAA_20min': df['FAA_20min'][0],
                    }

        else:
            logger.info("FAA output already exists at %s", output_path)
            logger.info("Skipping FFA calculation and proceeding to marker correction...")
            df = pd.read_csv(output_path)
            return {'FAA_baseline': df['FAA_baseline'][0],
                    'FAA_applk': df['FAA_applk'][0],
                    'FAA_5min': df['FAA_5min'][0],
                    'FAA_10min': df['FAA_10min'][0],
                    'FAA_15min': df['FAA_15min'][0],
                    'FAA_20min': df['FAA_20min'][0],
                    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compute Frontal Alpha Asymmetry (FAA) from EEG alpha values."
    )
    parser.add_argument(
        "input_file",
        help="Path to the input whitespace-separated file (e.g., alpha_data.txt)"
    )
    parser.add_argument(
        "output_file",
        help="Path for the output CSV file (e.g., alpha_with_faa.csv)"
    )
    parser.add_argument(
        "studytype",
        help="Type of data processing (e.g. Masterarbeit or clinical)"
    )
    parser.add_argument(
        "--sep",
        default=DEFAULT_SEPARATOR,
        help="Column separator regex for pandas.read_csv (default: whitespace)"
    )

    args = parser.parse_args()
    compute_faa(args.input_file, args.output_file, args.studytype, sep=args.sep)
