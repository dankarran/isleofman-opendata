import os
import io
import time
import pandas as pd
import csv
import json
from src.helpers import get_url

"""
Planning Applications data processing

"""

data_dir = "data/gov.im/planning-applications/"
record_types = ["planning-applications", "delegated-decisions", "appeals"]
pa_base_url = "https://services.gov.im/planningapplication/services/planning/planningapplicationdetails.iom?ApplicationReferenceNumber="


def planning_applications():
    print("# Planning Applications - Isle of Man Government")

    with open(data_dir + "sources/sources.json") as fp:
        sources = json.load(fp)

    with open(data_dir + "sources/defaults.json") as fp:
        default_options = json.load(fp)

    data = load_data(sources, default_options)
    data = process_data(data)
    write_data(data)


def load_data(sources, default_options):
    print(" - Loading Planning Applications")

    data = {}

    for record_type in record_types:

        data[record_type] = {}

        # download weekly files if required
        if "weekly" in sources[record_type]:
            update_text = input("Download updated weekly " + record_type + " files? (y/N) ")
            if update_text == "y":
                update_weekly_files(sources[record_type]["weekly"], record_type)

            # load data into dataframes
            data[record_type]["weekly"] = pd.DataFrame()
            data[record_type]["weekly"] = read_weekly_files(sources[record_type]["weekly"],
                                                            record_type,
                                                            data[record_type]["weekly"])

        # download annual files if required
        update_text = input("Download updated annual " + record_type + " files? (y/N) ")
        if update_text == "y":
            update_annual_files(sources[record_type]["annual"], record_type)

        # load data into dataframes
        data[record_type]["annual"] = pd.DataFrame()
        data[record_type]["annual"] = read_annual_files(sources[record_type]["annual"],
                                                        default_options[record_type]["annual"],
                                                        record_type,
                                                        data[record_type]["annual"])

    return data


def update_weekly_files(sources, record_type):
    pub_count = 0
    for pub_date in sources:
        year = pub_date[0:4]

        year_dir = data_dir + "sources/weekly/" + year
        filename = pub_date + "-" + record_type + ".csv"
        filepath = year_dir + "/" + filename

        # only update if we don't already have the file, but always update the latest
        # few publications to check for changes
        # NOTE: future publications are subject to change until publication date
        #       and recent ones may have been checked mid-week, so need to re-check those
        pub_count = pub_count + 1
        if pub_count > 3 and os.path.isfile(filepath):
            print("    ", "Skipping", record_type, "for", pub_date)
            continue

        base_url = "https://services.gov.im/planningapplication/services/planning/applicationsearchresults.iom"
        base_url = base_url + "?PressListDate=" + pub_date + "T00%3a00%3a00.000&SearchField=PressListDate"

        pub_rows_df = pd.DataFrame(columns=["Application Number", "Details", "Local Authority", "Date"])
        page = 1
        while True:
            page_url = base_url + "&page=" + str(page)

            print("    ", "Downloading", record_type, "for", pub_date, "from", page_url, "page", page)

            r = get_url(page_url)

            html = str(r.content)

            # strip empty rows
            html = html.replace("<tr></tr>", "")

            # grab data from table
            try:
                table_df = pd.read_html(io.StringIO(html))
                if len(table_df):
                    pub_rows_df = pd.concat([pub_rows_df, table_df[0]], ignore_index=True)

                    # final page if fewer than 10 records, otherwise try and see
                    if len(table_df[0]) < 10:
                        break

            except ValueError:
                print("    ", "No more records (ValueError)")
                break

            page = page + 1
            time.sleep(1)

        # write to CSV file
        if not os.path.isdir(year_dir):
            print("    ", "Creating directory for", year)
            os.mkdir(year_dir)

        pub_rows_df.to_csv(filepath, index=False, quoting=csv.QUOTE_ALL)


def update_annual_files(sources, record_type):
    for year in sources:
        year_source = sources[year]

        year_dir = data_dir + "sources/annual/" + year
        filepath = year_dir + "/" + record_type + ".csv"

        # only update if we don't already have the file
        if os.path.isfile(filepath):
            print("    ", "Skipping", record_type, "for", year)
            continue

        if not os.path.isdir(year_dir):
            print("    ", "Creating directory for", year)
            os.mkdir(year_dir)

        print("    ", "Downloading", record_type, "for", year)

        r = get_url(year_source["url"])
        open(filepath, 'wb').write(r.content)

        # drop columns where appropriate (e.g. personal data)
        if "columns_drop" in year_source:
            print("    ", "Dropping columns", year_source["columns_drop"])

            encoding = "ISO-8859-1"
            year_data = pd.read_csv(filepath, encoding=encoding)
            year_data = year_data.drop(columns=year_source["columns_drop"])
            year_data.to_csv(filepath, index=False)


def read_weekly_files(sources, record_type, data):
    for pub_date in sources:
        year = pub_date[0:4]
        year_dir = data_dir + "sources/weekly/" + year
        filename = pub_date + "-" + record_type + ".csv"
        filepath = year_dir + "/" + filename

        if os.path.isfile(filepath):
            try:
                print("    ", "Reading", record_type, "for", pub_date)

                week_data = pd.read_csv(filepath)

                # rename columns
                week_data = week_data.rename(columns={"Application Number": "PA Ref"})

                # strip \n from Details field
                print("      ", "Stripping newlines from addresses")
                week_data["Details"] = week_data["Details"].replace(r'\\n', ' ', regex=True)

                # add details
                week_data["Pub Date"] = pub_date
                week_data["URL"] = pa_base_url + week_data["PA Ref"]

                data = pd.concat([data, week_data])

            except UnicodeDecodeError as error:
                print("    ", "ERROR:", error)
        else:
            print("      ", "WARNING: File missing for", record_type, "for", pub_date)

    return data


def read_annual_files(sources, default_options, record_type, data):
    for year in sources:
        year_source = sources[year]

        year_dir = data_dir + "sources/annual/" + year
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

                # strip newlines from addresses
                print("      ", "Stripping newlines from addresses")
                year_data["Property Address"] = year_data["Property Address"].replace(r'\s', ' ', regex=True)

                # reorder columns (skip 2018 due to missing columns)
                if not (record_type == "appeals" and year in ["2018"]):
                    year_data = year_data[default_options["header_map"].keys()]

                # add details
                year_data["Year"] = year
                year_data["URL"] = pa_base_url + year_data["PA Ref"]

                data = pd.concat([data, year_data])

            except UnicodeDecodeError as error:
                print("    ", "ERROR:", error)
        else:
            print("      ", "WARNING: File missing for", record_type, "for", year)

    return data


def process_data(data):
    print(" - Processing Planning Applications")

    data = process_addresses(data)

    return data


def process_addresses(data):
    # Addresses
    print(" - Addresses")

    # extract all addresses
    addresses_df = pd.DataFrame()
    messy_df = pd.DataFrame()
    for record_type in record_types:
        addresses_df = pd.concat([addresses_df, data[record_type]["annual"]["Property Address"]])

        if "weekly" in data[record_type]:
            messy_df = pd.concat([messy_df, data[record_type]["weekly"]["Details"]])

    # find valid postcodes
    im_postcode_regex = '(IM[0-9]9? [0-9][A-Z]{2})'

    postcodes_df = pd.DataFrame()

    # add postcodes from annual
    postcodes_annual = addresses_df["Property Address"].str.extract(im_postcode_regex, expand=True)
    postcodes_df["Postcode"] = postcodes_annual

    # add postcodes from weekly
    postcodes_weekly = pd.DataFrame()
    postcodes_weekly["Postcode"] = messy_df["Details"].str.extract(im_postcode_regex, expand=True)
    postcodes_df = pd.concat([postcodes_df, postcodes_weekly])

    postcodes_df = postcodes_df.sort_values(by=["Postcode"])
    postcodes_df = postcodes_df[["Postcode"]]
    postcodes_df = postcodes_df.drop_duplicates()

    print("    ", len(postcodes_df), "postcodes added")

    postcodes_df.to_csv(data_dir + 'outputs/addressing/postcodes.csv', index=False, quoting=csv.QUOTE_ALL)

    return data


def write_data(data):
    print(" - Writing Planning Applications")

    for record_type in record_types:
        if "weekly" in data[record_type]:
            filename = record_type + "-weekly.csv"
            filepath = data_dir + "outputs/" + filename
            data[record_type]["weekly"].to_csv(filepath, index=False, quoting=csv.QUOTE_ALL)
            print("    ", len(data[record_type]["weekly"]), record_type, "rows written to", filename)

        filename = record_type + ".csv"
        filepath = data_dir + "outputs/" + filename
        data[record_type]["annual"].to_csv(filepath, index=False, quoting=csv.QUOTE_ALL)
        print("    ", len(data[record_type]["annual"]), record_type, "rows written to", filename)
