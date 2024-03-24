import os
import requests
import pandas as pd
import csv
from src.hashing import add_md5_hash_column


"""
Land Transactions data processing

"""

source_url = 'https://www.gov.im/media/1382502/landtransactionsfeb2024.csv'
source_dir = 'data/source/gov.im/land-transactions/'
source_file = 'land-transactions.csv'

issues = []
issue_rows = []


def land_transactions(output_dir):
    print("# Land Transactions - Isle of Man Government")

    update = True
    if os.path.isfile(source_dir + source_file):
        update_text = input("Download updated land transactions file? (y/N) ")
        if update_text == "y":
            update = True
        else:
            update = False

    data = load_land_transactions(update)
    data = process_land_transactions(data, output_dir)
    write_land_transactions(data, output_dir)

    write_issues(output_dir)


def load_land_transactions(update):
    print(" - Loading Land Transactions")

    # retrieve file and save local copy in source directory
    if update:
        r = requests.get(source_url, allow_redirects=True)
        open(source_dir + source_file, 'wb').write(r.content)
        print("    ", "Land Transactions retrieved and saved to source directory")

    # read data from local file into dataframe
    data = pd.read_csv(source_dir + source_file)

    print("    ", len(data), "rows loaded")

    return data


def process_land_transactions(data, output_dir):
    print(" - Processing Land Transactions")

    data = add_hash(data)
    data = apply_corrections(data)

    data = process_parishes(data, output_dir)
    data = process_towns(data, output_dir)
    data = process_localities(data, output_dir)
    data = process_streets(data, output_dir)
    data = process_postcodes(data, output_dir)

    return data


def write_land_transactions(data, output_dir):
    print(" - Writing Land Transactions")

    data.to_csv(output_dir + 'gov.im/land-transactions/land-transactions.csv', index=False, quoting=csv.QUOTE_ALL)

    print("    ", len(data), "rows written")


def write_issues(output_dir):
    print(" - Writing issues")

    issues_df = pd.DataFrame(issues)
    issues_df = issues_df.rename(columns={0: "Hash", 1: "Description"})
    issues_df.to_csv(output_dir + 'gov.im/land-transactions/issues.csv', index=False, quoting=csv.QUOTE_ALL)

    print("    ", len(issues_df), "issues written")

    issue_rows_df = pd.DataFrame(issue_rows)
    issue_rows_df = issue_rows_df.rename(columns={0: "Hash", 1: "Description"})
    issue_rows_df.to_csv(output_dir + 'gov.im/land-transactions/issue-rows.csv', index=False, quoting=csv.QUOTE_ALL)

    print("    ", len(issue_rows_df), "issue rows written")


def add_hash(data):
    print(" - Adding hash column")

    data = add_md5_hash_column(data, 'Hash')

    # Move Hash column to start
    data = data[['Hash'] + [col for col in data.columns if col != 'Hash']]

    return data


def apply_corrections(data):
    print(" - Applying data corrections")
    print("    ", len(data), "rows passed in")

    corrections_dir = 'data/source/gov.im/land-transactions/corrections/'

    # Column renaming
    data = data.rename(columns={"Parish_": "Parish"})

    # Replace nan entries with empty string
    # see https://stackoverflow.com/questions/14162723/replacing-pandas-or-numpy-nan-with-a-none-to-use-with-mysqldb
    data = data.where(pd.notnull(data), "")

    # Town corrections - e.g. misspellings
    town_corrections_csv = corrections_dir + 'towns.csv'
    town_corrections = pd.read_csv(town_corrections_csv)
    data["Town"] = data["Town"].replace(town_corrections["From"].to_list(), town_corrections["To"].to_list())

    # Whole row corrections
    row_corrections_csv = corrections_dir + 'rows.csv'
    row_corrections = pd.read_csv(row_corrections_csv)
    row_corrections = row_corrections.where(pd.notnull(row_corrections), "")
    for index, row in row_corrections.iterrows():
        data.loc[data["Hash"] == row["Hash"], [
            "SubUnit_Name",
            "House_Number",
            "House_Name",
            "Street_Name",
            "Locality",
            "Town",
            "Postcode",
            "Parish",
            "Market_Value",
            "Consideration",
            "Acquisition_Date",
            "CompletionDate"
        ]] = [
            row["SubUnit_Name"],
            row["House_Number"],
            row["House_Name"],
            row["Street_Name"],
            row["Locality"],
            row["Town"],
            row["Postcode"],
            row["Parish"],
            row["Market_Value"],
            row["Consideration"],
            row["Acquisition_Date"],
            row["CompletionDate"]
        ]

    print("    ", len(data), "rows passed back")

    return data


def process_parishes(data, output_dir):
    # Parishes
    print(" - Parishes")

    data["Parish"] = data["Parish"].astype(str)
    data["Parish"] = data["Parish"].str.strip()

    parishes = sorted(data["Parish"].unique())

    print("    ", len(parishes), "parishes added")

    parishes_df = pd.DataFrame(parishes)
    parishes_df = parishes_df.rename(columns={0: "Name"})
    parishes_df.to_csv(output_dir + 'gov.im/land-transactions/addressing/places/parishes.csv', index=False, quoting=csv.QUOTE_ALL)

    return data


def process_towns(data, output_dir):
    # Towns
    print(" - Towns")

    data["Town"] = data["Town"].astype(str)
    data["Town"] = data["Town"].str.strip()

    # exclude known non-towns not fixed in corrections file
    invalid_towns_regex = ' Road|[0-9]|Isle [oO]f Man|Part Of| And '
    invalid_towns_rows = data["Town"].str.contains(invalid_towns_regex)

    towns = data[~invalid_towns_rows]
    towns = towns.sort_values(by=["Town"])
    towns = towns[["Town"]]
    towns = towns.drop_duplicates()

    print("    ", len(towns), "towns added")

    towns_df = pd.DataFrame(towns)
    towns_df = towns_df.rename(columns={"Town": "Name"})
    towns_df.to_csv(output_dir + 'gov.im/land-transactions/addressing/places/towns.csv', index=False, quoting=csv.QUOTE_ALL)

    # handle issues
    for index, row in data[invalid_towns_rows].iterrows():
        issue = row["Town"] + " is an invalid town name"
        issues.append([row["Hash"], issue])
        row["Issue"] = issue
        issue_rows.append(row)

    print("    ", len(data[invalid_towns_rows]), "issues added")

    return data


def process_localities(data, output_dir):
    # Localities
    print(" - Localities")

    data["Locality"] = data["Locality"].astype(str)
    data["Locality"] = data["Locality"].str.strip()

    # exclude known non-localities
    invalid_localities_regex = '[0-9]|&| And |Abutting|Adjacent To|Adjoining| Road| Drive| Street|^nan$'
    invalid_localities_rows = data["Locality"].str.contains(invalid_localities_regex)

    localities = data[~invalid_localities_rows]
    localities = localities.sort_values(by=["Locality"])
    localities = localities[["Locality"]]
    localities = localities.dropna()
    localities = localities.drop_duplicates()

    print("    ", len(localities), "localities added")

    localities_df = pd.DataFrame(localities)
    localities_df = localities_df.rename(columns={"Locality": "Name"})
    localities_df.to_csv(output_dir + 'gov.im/land-transactions/addressing/places/localities.csv', index=False, quoting=csv.QUOTE_ALL)

    # handle issues
    issue_count = 0
    data[invalid_localities_rows].dropna()
    for index, row in data[invalid_localities_rows].iterrows():
        if row["Locality"] != "":
            issue = row["Locality"] + " is an invalid locality name"
            issues.append([row["Hash"], issue])
            row["Issue"] = issue
            issue_rows.append(row)
            issue_count = issue_count + 1

    print("    ", issue_count, "issues added")

    return data


def process_streets(data, output_dir):
    # Streets
    print(" - Streets")

    data["Street_Name"] = data["Street_Name"].astype(str)
    data["Street_Name"] = data["Street_Name"].str.strip()

    # exclude known non-streets
    invalid_streets_regex = '^$|[0-9]|[(]|Abutting|Adjacent |Adjoining |At |Allotment ' \
                            + '|^Land |^Lands |^Lane |^Off |Of Land |Opposite ' \
                            + '|Part Of |Pathway |Patio Area |Plot |Private |Rear Of '
    invalid_streets_rows = data["Street_Name"].str.contains(invalid_streets_regex)

    streets = data[~invalid_streets_rows]
    streets = streets[["Street_Name", "Town"]].sort_values(by=["Street_Name", "Town"])
    streets = streets.drop_duplicates()

    print("    ", len(streets), "streets added")

    streets_df = pd.DataFrame(streets)
    streets_df = streets_df.rename(columns={"Street_Name": "Name"})
    streets_df.to_csv(output_dir + 'gov.im/land-transactions/addressing/streets/streets.csv', index=False, quoting=csv.QUOTE_ALL)

    # handle issues
    issue_count = 0
    for index, row in data[invalid_streets_rows].iterrows():
        issue = row["Street_Name"] + " is an invalid street name"
        issues.append([row["Hash"], issue])
        row["Issue"] = issue
        issue_rows.append(row)
        issue_count = issue_count + 1

    print("    ", issue_count, "issues added")

    return data


def process_postcodes(data, output_dir):
    # Postcodes
    print(" - Postcodes")

    data["Postcode"] = data["Postcode"].astype(str)
    data["Postcode"] = data["Postcode"].str.strip()

    # find valid postcodes
    im_postcode_regex = '^IM[0-9]9? [0-9][A-Z]{2}$'
    valid_postcode_rows = data["Postcode"].str.contains(im_postcode_regex)

    postcodes = data[valid_postcode_rows].sort_values(by=["Postcode"])
    postcodes = postcodes[["Postcode"]]
    postcodes = postcodes.drop_duplicates()

    print("    ", len(postcodes), "postcodes added")

    postcodes_df = pd.DataFrame(postcodes)
    postcodes_df.to_csv(output_dir + 'gov.im/land-transactions/addressing/postcodes/postcodes.csv', index=False, quoting=csv.QUOTE_ALL)

    # handle issues
    issue_count = 0
    invalid_postcode_rows = data[~valid_postcode_rows]
    invalid_postcode_rows.dropna()
    for index, row in invalid_postcode_rows.iterrows():
        if row["Postcode"] != "":
            issue = row["Postcode"] + " is an invalid postcode"
            issues.append([row["Hash"], issue])
            row["Issue"] = issue
            issue_rows.append(row)
            issue_count = issue_count + 1

    print("    ", issue_count, "issues added")

    return data
