import json
import os
import requests
import pandas as pd
import csv


"""
Planning Applications data processing

"""

source_dir = "data/source/gov.im/planning-applications/"
record_types = ["planning-applications", "delegated-decisions", "appeals"]


def planning_applications(output_dir):
    print("# Planning Applications - Isle of Man Government")

    with open(source_dir + "sources.json") as fp:
        sources = json.load(fp)

    with open(source_dir + "defaults.json") as fp:
        default_options = json.load(fp)

    data = load_planning_applications(sources, default_options)
    data = process_planning_applications(data, output_dir)
    write_planning_applications(data, output_dir)


def load_planning_applications(sources, default_options):
    print(" - Loading Planning Applications")

    data = {}

    for record_type in record_types:

        # download if required
        update_text = input("Download updated " + record_type + " files? (y/N) ")
        if update_text == "y":
            update_files(sources[record_type], record_type)

        # load data into dataframes
        data[record_type] = pd.DataFrame()
        data[record_type] = read_files(sources[record_type],
                                       default_options[record_type],
                                       record_type,
                                       data[record_type])

    return data


def update_files(sources, record_type):
    for year in sources:
        year_source = sources[year]

        year_dir = source_dir + year
        filepath = year_dir + "/" + record_type + ".csv"

        if not os.path.isdir(year_dir):
            print("    ", "Creating directory for", year)
            os.mkdir(year_dir)

        print("    ", "Downloading", record_type, "for", year)
        r = requests.get(year_source["url"], allow_redirects=True)
        open(filepath, 'wb').write(r.content)

        # drop columns where appropriate (e.g. personal data)
        if "columns_drop" in year_source:
            print("    ", "Dropping columns", year_source["columns_drop"])

            encoding = "ISO-8859-1"
            year_data = pd.read_csv(filepath, encoding=encoding)
            year_data = year_data.drop(columns=year_source["columns_drop"])
            year_data.to_csv(filepath, index=False)


def read_files(sources, default_options, record_type, data):
    for year in sources:
        year_source = sources[year]

        year_dir = source_dir + year
        filepath = year_dir + "/" + record_type + ".csv"

        if os.path.isfile(filepath):
            try:
                print("    ", "Reading", record_type, "for", year)

                if "skip" in year_source and year_source["skip"]:
                    print("      ", "WARNING: Skipping", record_type, "for", year)
                    continue

                # skip header rows where appropriate
                header_skip = None
                if "header_skip" in default_options:
                    header_skip = default_options["header_skip"]
                if "header_skip" in year_source:
                    header_skip = year_source["header_skip"]

                encoding = "ISO-8859-1"
                year_data = pd.read_csv(filepath, encoding=encoding, skiprows=header_skip)

                # rename columns
                header_map = None
                if "header_map" in default_options:
                    header_map = default_options["header_map"]
                if "header_map" in year_source:
                    header_map = year_source["header_map"]
                if header_map:
                    print("      ", "Renaming columns")
                    header_map_swap = {v: k for k, v in header_map.items()}

                    year_data = year_data.rename(columns=header_map_swap)

                # reorder columns
                year_data = year_data[default_options["header_map"].keys()]

                # add year
                year_data["Year"] = year

                data = pd.concat([data, year_data])

            except UnicodeDecodeError as error:
                print("    ", "ERROR:", error)
        else:
            print("      ", "WARNING: File missing for", record_type, "for", year)

    return data


def process_planning_applications(data, output_dir):
    print(" - Processing Planning Applications")

    data = process_addresses(data, output_dir)

    return data


def process_addresses(data, output_dir):
    # Addresses
    print(" - Addresses")

    # extract all addresses
    addresses_df = pd.DataFrame()
    for record_type in record_types:
        addresses_df = pd.concat([addresses_df, data[record_type]["Property Address"]])

    # find valid postcodes
    im_postcode_regex = '(IM[0-9]9? [0-9][A-Z]{2})'

    postcodes_df = pd.DataFrame()
    postcodes_df["Postcode"] = addresses_df["Property Address"].str.extract(im_postcode_regex, expand=True)
    postcodes_df = postcodes_df.sort_values(by=["Postcode"])
    postcodes_df = postcodes_df[["Postcode"]]
    postcodes_df = postcodes_df.drop_duplicates()

    print("    ", len(postcodes_df), "postcodes added")

    postcodes_df.to_csv(output_dir + 'gov.im/planning-applications/addressing/postcodes/postcodes.csv', index=False, quoting=csv.QUOTE_ALL)

    return data


def write_planning_applications(data, output_dir):
    print(" - Writing Planning Applications")

    for record_type in record_types:
        filepath = output_dir + "gov.im/planning-applications/" + record_type + ".csv"
        data[record_type].to_csv(filepath, index=False, quoting=csv.QUOTE_ALL)
        print("    ", len(data[record_type]), record_type, "rows written")
