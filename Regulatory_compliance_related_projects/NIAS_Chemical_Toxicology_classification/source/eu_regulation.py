import requests
import pandas as pd
from bs4 import BeautifulSoup
import os

def extract_EURegs_from_html_to_ExcelorCsv(url: str, output_prefix: str = "eu_regulation",
                                            output_dir: str = "."):
    """
    Extract Annex I table data from a EUR-Lex HTML regulation page and save it to an Excel file.

    Parameters:
        url (str): URL of the EUR-Lex regulation HTML content.
        output_prefix (str): Prefix for output files (default: 'eu_regulation').
        output_dir (str): Directory where the output file will be saved (default: current directory).
    """
    # Fetch the page
    r = requests.get(url)
    r.encoding = 'utf-8'  # Ensure proper character decoding
    bs = BeautifulSoup(r.text, features='html.parser')

    # Locate the Annex I section
    anx_I = bs.find('div', {'id': 'anx_I'})
    if anx_I is None:
        raise ValueError("Annex I (id='anx_I') not found in the HTML document.")

    table1 = anx_I.find('table')
    if table1 is None:
        raise ValueError("No table found inside Annex I section.")

    rows_csv = []
    rows_xslx = []

    for i, tr in enumerate(table1.find_all('tr')):
        if i < 2:  # Skip header rows
            continue

        td = tr.find_all('td')
        if len(td) >= 7:  # or >= the number of expected fields
            fcm = td[0].text.strip()
            ref = td[1].text.strip()
            cas = td[2].text.strip()
            if len(cas) < 5:
                cas = ''
            if "\n" in cas:
                cas = cas.split("\n")[0]
            cas = cas.lstrip('0')
            name = td[3].text.strip()
            plastic = td[4].text.strip()
            monomer = td[5].text.strip()
            frf = td[6].text.strip()
            sml = td[7].text.strip()
            sml_gr = td[8].text.strip()
            restr = td[9].text.strip()
            conf = td[10].text.strip()

            print(f"Row {i}: FCM={fcm}")
            row_xlsx = {
                'FCM': fcm, 'Ref': ref, 'CAS': cas, 'Name': name, 'Plastic': plastic,
                'Monomer': monomer, 'FRF': frf, 'SML': sml, "SML_Group": sml_gr,
                'Restr': restr, 'Conf': conf
            }
            row_csv = {
                'FCM': fcm, 'Ref': ref, 'CAS': cas, 'Name': name, 'Plastic': plastic,
                'Monomer': monomer, 'FRF': frf, 'SML': sml
            }
            rows_xslx.append(row_xlsx)
            rows_csv.append(row_csv)

    # Output file names
    excel_filename = f'{output_prefix}.xlsx'

    # Save files
    pd.DataFrame(rows_xslx).to_excel(os.path.join(output_dir, excel_filename), index=False)

    print(f"Data extracted and saved as:\n-  {excel_filename}")


def extract_Group_restrictions(url: str, output_prefix: str = "eu_group_restrictions",
                               output_dir: str = "."):
    # Fetch the page
    r = requests.get(url)
    r.encoding = 'utf-8'  # Ensure proper character decoding
    bs = BeautifulSoup(r.text, features='html.parser')

    # Locate the Annex I section
    anx_I = bs.find('div', {'id': 'anx_I'})
    if anx_I is None:
        raise ValueError("Annex I (id='anx_I') not found in the HTML document.")

    tables = anx_I.find_all('table')
    if tables is None:
        raise ValueError("No table found inside Annex I section.")

    rows_csv = []
    rows_xslx = []
    for n, table in enumerate(tables, start=1):
        if n == 2:
            print(table)
            for i, tr in enumerate(table.find_all('tr')):
                if i < 2:  # Skip header rows
                    continue

                td = tr.find_all('td')
                if len(td) == 4:  # or >= the number of expected fields
                    grp_nr = td[0].text.strip()
                    fcm = ", \n".join(td[1].text.strip().split("\n"))
                    sml = td[2].text.strip()
                    grp_descp = td[3].text.strip()

                    print(f"Row {i}: FCM={fcm}")

                    row_xlsx = {
                        'Group_nr': grp_nr, 'FCM': fcm, 'SML': sml, 'Group Description': grp_descp
                    }
                    rows_xslx.append(row_xlsx)

    excel_filename = f'{output_prefix}.xlsx'

    # Save files
    pd.DataFrame(rows_xslx).to_excel(os.path.join(output_dir, excel_filename), index=False)

    print(f"Data extracted and saved as:\n-  {excel_filename}")

def extract_fcm_from_eureg_xlsx(EUreg_xlsx_path, db_path):

    # Load the first Excel file (FCM mapping)
    df_fcm = pd.read_excel(EUreg_xlsx_path,  engine="openpyxl")

    # Load the second Excel file (Target file for FCM updates)
    df_target = pd.read_excel(db_path,  engine="openpyxl")

    # Remove leading zeros from CAS in both DataFrames
    df_fcm["CAS"] = df_fcm["CAS"].astype(str).str.lstrip("0")
    df_target["CAS"] = df_target["CAS"].astype(str).str.lstrip("0")

    # Convert CAS to string to ensure correct mapping
    df_fcm["CAS"] = df_fcm["CAS"].astype(str)
    df_target["CAS"] = df_target["CAS"].astype(str)

    # Create a dictionary mapping CAS -> FCM from the first file
    cas_to_fcm = dict(zip(df_fcm["CAS"], df_fcm["FCM"]))

    # Update FCM in the second file only if it's missing
    df_target["FCM"] = df_target.apply(
        lambda row: cas_to_fcm[row["CAS"]] if row["CAS"] in cas_to_fcm and pd.isna(row["FCM"]) else row["FCM"],
        axis=1
    )

    # Save the updated second file
    df_target.to_excel("updated_second_file_test.xlsx", index=False)

    print("FCM values updated successfully and saved as 'updated_second_file.xlsx'.")


def main():
    # Update these paths to point to your local EU regulation Excel files if using extract_fcm_from_eureg_xlsx.
    # eureg_path = r"path\to\eu_regulation.xlsx"
    # db_path = r"path\to\updated_chemical_data.xlsx"

    # Scrape EU regulation data from EUR-Lex and save to current directory
    extract_EURegs_from_html_to_ExcelorCsv(
        "https://eur-lex.europa.eu/legal-content/DE/TXT/HTML/?uri=CELEX:02011R0010-20250316#anx_I",
        output_prefix="eu_regulation_10_2025_de",
        output_dir="."
    )
    # extract_fcm_from_eureg_xlsx(eureg_path, db_path)
    # extract_Group_restrictions("https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:02011R0010-20250316#anx_I",
    # output_prefix="eu_regulation_10_2025_en_groups")

if __name__ == "__main__":
    main()
