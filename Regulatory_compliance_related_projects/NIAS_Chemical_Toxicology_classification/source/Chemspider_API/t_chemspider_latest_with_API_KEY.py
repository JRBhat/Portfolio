import pandas as pd
import time
from utilityFuncs.util import query_chemspider


def main(input_excel: str, output_excel: str, sheet_name: str = "NIAS_Substance"):
    # 1) Read the CAS column
    df = pd.read_excel(input_excel, sheet_name=sheet_name, usecols=["CAS"])
    cas_list = df["CAS"].dropna().astype(str).unique().tolist()

    # 2) Query ChemSpider for each
    results = []
    for cas in cas_list:
        print(f"Querying ChemSpider for {cas}…")
        info = query_chemspider(cas)
        if info:
            results.append(info)
        else:
            # if you want to keep track of misses, you could append a dict with Identifier and nulls
            results.append({"Identifier": cas, "CSID": None, "CAS": None,
                            "SMILES": None, "IUPAC": None,
                            "English": None, "German": None})
        # be polite: sleep between requests if needed
        time.sleep(0.2)

    # 3) Build a DataFrame of results
    out_df = pd.DataFrame(results)

    # 4) Save to a new Excel file
    with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
        out_df.to_excel(writer, index=False, sheet_name="ChemSpider_Results")

    print(f"Done! Results written to {output_excel}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch substance info from ChemSpider for all CAS in an Excel sheet."
    )
    parser.add_argument("input_excel", help="Path to the input .xlsx file")
    parser.add_argument("output_excel", help="Path where the output .xlsx should be saved")
    parser.add_argument(
        "--sheet", "-s", default="NIAS_Substance",
        help="Name of the sheet containing the 'CAS' column"
    )
    args = parser.parse_args()

    main(args.input_excel, args.output_excel, sheet_name=args.sheet)
