import os
import pandas as pd
from Tests.t_chemspider_api_secure import query_chemspider
from Tests.t_pubchem_api_secure import query_pubchem
import logging
import pandas as pd
import logging


# Configure logging
logging.basicConfig(filename='query_errors.log', level=logging.ERROR, 
                    format='%(asctime)s - %(levelname)s - %(message)s')


def update_excel_with_queries(input_file, output_file):
    # Load the Excel file
    df = pd.read_excel(input_file)
    
    # Iterate over rows and check missing values
    for index, row in df.iterrows():
        cas = str(row['CAS']).strip()
        
        if pd.isna(row['SMILES']) or pd.isna(row['IUPAC_DE']) or pd.isna(row['IUPAC_EN']):
            print(f"Querying for CAS: {cas}")
            try:
                if pd.isna(row['IUPAC_DE']) or pd.isna(row['IUPAC_EN']):
                    # Query ChemSpider first
                    chemspider_data = query_chemspider(cas)

                    if "Error" in chemspider_data:
                        logging.error(f"{chemspider_data}")
                        
                    elif chemspider_data and ('iupac_name_de' in chemspider_data or 'iupac_name_en' in chemspider_data):
                        df.at[index, 'IUPAC_DE'] = chemspider_data.get('iupac_name_de', row['IUPAC_DE'])
                        df.at[index, 'IUPAC_EN'] = chemspider_data.get('iupac_name_en', row['IUPAC_EN'])
                    else:
                        logging.warning(f"Empty response from ChemSpider for CAS {cas}")
                        
                if pd.isna(row['SMILES']):
                # Query PubChem for SMILES and missing IUPAC names
                    pubchem_data = query_pubchem(cas)
                    if "Error" in pubchem_data:
                        logging.error(f"{pubchem_data}")
                    elif pubchem_data:
                        df.at[index, 'SMILES'] = pubchem_data.get('CanonicalSMILES', row['SMILES'])
                    else:
                        logging.warning(f"Empty response from PubChem for CAS {cas}")
                        
            except Exception as e:
                logging.error(f"Failed to query CAS {cas}: {e}")
                print(f"Error querying CAS {cas}: {e}")
                
    # Save the updated file
    df.to_excel(output_file, index=False)
    print(f"Updated Excel file saved as: {output_file}")



def update_missing_cas(file_path):
    """Update missing CAS values using available IUPAC or SMILES information."""
    df = pd.read_excel(file_path)
    
    for index, row in df.iterrows():
        cas = row["CAS"]
        iupac = row["IUPAC_EN"] or row["IUPAC_DE"]
        smiles = row["SMILES"]
        
        if pd.isna(cas) or cas == "-":

            if str(iupac).lower != 'nan':
                result_pub = query_pubchem(iupac, "iupac")
                result_cs = query_chemspider(iupac, "iupac")
                if result_pub:
                    if result_pub["CAS"]:
                        df.at[index, "CAS"] = result_pub["CAS"]
                    if str(smiles).lower() == 'nan' and result_pub["SMILES"]:
                        df.at[index, "SMILES"] = result_pub["SMILES"]
                elif result_cs:
                    if (df.at[index, "CAS"] == "-" or df.at[index, "SMILES"] == "") : 
                        if result_cs["CAS"]:
                            df.at[index, "CAS"] = result_cs["CAS"]
                        if str(smiles).lower() == 'nan' and result_cs["SMILES"]:
                            df.at[index, "SMILES"] = result_cs["SMILES"]
            elif  not str(iupac).lower == 'nan' and str(smiles).lower() != 'nan':
                result = query_pubchem(smiles, "smiles")
                if result and result["CAS"]:
                    df.at[index, "CAS"] = result["CAS"]
                        
                        
    new_file_path = file_path.replace(".xlsx", "_updated.xlsx")
    df.to_excel(new_file_path, index=False)
    print(f"Updated file saved as {new_file_path}")



def get_cas_and_iupac_with_smiles_from_pubchem(input_path):
    
    df = pd.read_excel(input_path)

    for index, row in df.iterrows():
        cas = row["CAS"]
        iupac = row["IUPAC_EN"] or row["IUPAC_DE"]
        smiles = row["SMILES"]

        # if pd.isna(cas) or cas == "-":
        if iupac == "" or str(iupac).lower() == "nan":
            if str(smiles).lower() != 'nan':
                result_pub = query_pubchem(smiles, "smiles")
                    
                if result_pub and cas == "-":
                    print(result_pub)
                    if result_pub["CAS"]:
                        df.at[index, "CAS"] = result_pub["CAS"]
                        
                if result_pub and str(row["IUPAC_EN"]).lower() =="nan":
                    df.at[index, "IUPAC_EN"] = result_pub["IUPAC"]
        if (str(cas).lower() != "nan" or str(cas).lower() != "-") and str(iupac).lower() != "nan" and  str(smiles).lower() == "nan":
            try:
                result_pub = query_pubchem(iupac, "name")
                print(result_pub)
                if result_pub:
                    if result_pub["SMILES"]:
                        df.at[index, "SMILES"] = result_pub["SMILES"]
            except Exception as e:
                print(e)
                
                
    new_file_path = input_path.replace(".xlsx", "_updated.xlsx")
    df.to_excel(new_file_path, index=False)
    print(f"Updated file saved as {new_file_path}")       




if __name__ == "__main__":
    input_file = os.environ.get("NIAS_DB_PATH", "data/NIAS_ZDB.xlsx")  # Change to your actual file name
    # update_excel_with_queries(input_file, output_file)
    # update_missing_cas(input_file)
    # get_cas_and_iupac_with_smiles_from_pubchem(input_file)
    get_cas_and_iupac_with_smiles_from_pubchem(input_file)