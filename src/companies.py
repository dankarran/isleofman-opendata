import os
import requests
import time
from datetime import datetime
import random
import urllib.parse
import pandas as pd
import bs4
import csv
import json


"""
Companies Registry data processing

"""

data_dir = "data/gov.im/companies/"
registry_url = "https://services.gov.im/ded/services/companiesregistry/"
search_page = "companysearch.iom?"


def companies():
    print("# Companies Registry - Isle of Man Government")

    with open(data_dir + "sources/sources.json") as fp:
        sources = json.load(fp)

    with open(data_dir + "sources/status.json") as fp:
        status = json.load(fp)

    # retrieve a batch of previously unindexed company numbers
    companies_unindexed()

    # search for companies by name and write outputs
    data = load_data(sources, status)
    data = process_data(data)
    write_data(data)


def companies_unindexed():
    unindexed_filepath = data_dir + "outputs/company-numbers-unindexed.csv"
    if os.path.isfile(unindexed_filepath):
        unindexed = pd.read_csv(unindexed_filepath)
        print("    ", len(unindexed["Number"]), "unindexed company numbers detected")

        # exclude companies previously not found when searching by number
        not_found_filepath = data_dir + "sources/search/numbers/not-found.csv"
        if os.path.isfile(not_found_filepath):
            not_found = pd.read_csv(not_found_filepath)
            print("    ", len(not_found["Number"]), "company numbers previously not found in index")

            unindexed = unindexed[~unindexed["Number"].isin(not_found["Number"])]

        if len(unindexed["Number"]):
            batch_text = input("Download batch of [x] from ~" + str(len(unindexed["Number"])) + " unindexed companies? (default 0) ")
            if batch_text:
                batch_count = int(batch_text)
                if batch_count > 0:
                    unindexed_numbers = unindexed["Number"][:batch_count]
                    update_companies_list_by_number(unindexed_numbers)


def load_data(sources, status):
    print(" - Loading Companies")

    update_text = input("Download latest company registry details? (y/N) ")
    if update_text == "y":
        update_companies_list(sources, status)

    # load data into dataframes
    data = read_search_files(sources)

    return data


def process_data(data):
    companies_live = data[data["Status"].isin(["Live"])]
    companies_live = companies_live[companies_live["Name Status"].isin(["Current"])]
    companies_live = companies_live.drop_duplicates(subset=["Number", "Registry Type"], keep="last")

    companies_non_live = data[~data["Status"].isin(["Live"])]
    companies_non_live = companies_non_live[companies_non_live["Name Status"].isin(["Current"])]
    companies_non_live = companies_non_live.drop_duplicates(subset=["Number", "Registry Type"], keep="last")

    old_names = data[data["Name Status"].isin(["Previous"])]
    old_names = old_names.drop_duplicates(subset=["Name", "Number", "Registry Type"], keep="last")

    data["Numeric"] = pd.to_numeric(data["Number"].str.slice(start=0, stop=6))
    data["Suffix"] = data["Number"].str.slice(start=6, stop=7)

    registries = data[["Registry Type", "Numeric", "Suffix"]]
    # TODO: company count by registry
    registries = registries.drop_duplicates(subset=["Registry Type", "Suffix"], keep="last")
    registries = registries.rename(columns={"Numeric": "Latest Number"})
    registries = registries.sort_values(by=["Registry Type"])

    full_list = pd.DataFrame(columns=["Number"])
    for index, row in registries.iterrows():
        registry_list = pd.DataFrame(company_list(row["Latest Number"], row['Suffix']))
        registry_list = registry_list.rename(columns={0: "Number"})
        full_list = pd.concat([full_list, registry_list], ignore_index=True)

    full_list = full_list.sort_values(by=["Number"])

    unindexed = full_list[~full_list.Number.isin(data["Number"])]
    unindexed = unindexed.sort_values(by=["Number"])

    data = {
        "companies-live": companies_live,
        "companies-non-live": companies_non_live,
        "old-names": old_names,
        "registries": registries,
        "company-numbers-full": full_list,
        "company-numbers-unindexed": unindexed
    }

    return data


def company_list(count, suffix):
    company_numbers = list(range(1, count+1))

    formatted = []
    for company in company_numbers:
        formatted.append(str(company).zfill(6) + suffix)

    return formatted


def write_data(data):
    for record_type in data:
        filename = record_type + ".csv"
        filepath = data_dir + "outputs/" + filename
        data[record_type].to_csv(filepath, index=False, quoting=csv.QUOTE_ALL)
        print("    ", len(data[record_type]), "rows written to", filename)


def update_companies_list(sources, status):
    for term in sources["search"]["names"]:

        page = 1
        skip_rows = 0
        if term in status["search"]["names"]:
            term_status = status["search"]["names"][term]["latest"]

            if term_status["rows"] == 30:
                # start on next page after full page retrieved
                page = term_status["page"] + 1
            else:
                # start on final page again
                # TODO: skip the rows we've already seen
                #       ... may want to check contents as well, to ensure sort order is the same
                page = term_status["page"]
                skip_rows = term_status["rows"]

        while True:
            data = get_search_page(term, page=page)

            if not data.empty:
                # TODO: fix stats recording if skipping rows
                #if skip_rows:
                #    print("    ", "Skipping first", skip_rows, "already retrieved")
                #    data = data.iloc[1:skip_rows, :]
                #    skip_rows = 0

                write_search_page(term, page, data)

                if len(data) == 30:
                    page = page + 1
                else:
                    print("    ", "End of list")
                    break

            else:
                print("    ", "No more data")
                break

            sleep = random.randint(5, 10)
            print("    ", "... pausing for", sleep, "seconds ...")
            time.sleep(sleep)


def update_companies_list_by_number(numbers):
    for number in numbers:

        try:
            data = get_search_page(number, search_by=1)

            if not data.empty:
                write_search_by_number_page(data)

            else:
                write_search_by_number_not_found(number)
                print("    ", "Company", number, "not found")

            sleep = random.randint(1, 5)
            print("    ", "... pausing for", sleep, "seconds ...")
            time.sleep(sleep)

        except Exception as error:
            print(error)
            return False


def get_search_page(term, search_by=0, sort_by="IncorporationDate", sort_direction=0, page=1):
    params = {
        "SearchBy": search_by,
        "SortBy": sort_by,
        "SortDirection": sort_direction,
        "searchtext": term,
        "page": page,
        "Search": "Search"
    }
    url = registry_url + search_page + urllib.parse.urlencode(params)

    print("    ", "Downloading results for search term", term, "from", url, "page", page)
    
    index_date = datetime.now().strftime("%Y-%m-%d")

    # TODO: handle exceptions, pause and retry a few times before giving up?

    with requests.get(url) as f:
        soup = bs4.BeautifulSoup(f.content, "lxml")

        table = soup.find_all("table")[0]
        table_rows = table.find_all("tr")

        rows = []
        for row in table_rows:
            tds = row.find_all("td")

            name_link = tds[0].find_all("a")[0]
            name = str(name_link.contents[0])
            url = registry_url + str(name_link.get("href")).strip()

            rows.append({
                "Name": name,
                "Number": str(tds[1].contents[0]),
                "Inc/Reg Date": str(tds[2].contents[0]),
                "Status": str(tds[3].contents[0]),
                "Registry Type": str(tds[4].contents[0]),
                "Name Status": str(tds[5].contents[0]),
                "URL": url,
                "Index Date": index_date
            })

        df = pd.DataFrame(rows)

        return df


def write_search_page(term, page, data):
    filepath = data_dir + "sources/search/names/" + term + ".csv"

    file_exists = os.path.isfile(filepath)
    add_header = not file_exists

    data.to_csv(filepath, mode="a", index=False, header=add_header, quoting=csv.QUOTE_ALL)

    update_search_status(term, page, data)


def write_search_by_number_page(data):
    filepath = data_dir + "sources/search/numbers/numbers.csv"

    file_exists = os.path.isfile(filepath)
    add_header = not file_exists

    data.to_csv(filepath, mode="a", index=False, header=add_header, quoting=csv.QUOTE_ALL)


def write_search_by_number_not_found(number):
    filepath = data_dir + "sources/search/numbers/not-found.csv"

    file_exists = os.path.isfile(filepath)
    add_header = not file_exists

    rows = [{
        "Number": number,
        "Index Date": datetime.now().strftime("%Y-%m-%d")
    }]
    data = pd.DataFrame(rows)

    data.to_csv(filepath, mode="a", index=False, header=add_header, quoting=csv.QUOTE_ALL)


def update_search_status(term, page, data):
    with open(data_dir + "sources/status.json", "r+") as fp:
        status = json.load(fp)

        if term not in status["search"]["names"]:
            status["search"]["names"][term] = {}

        records = data.to_dict("records")

        status["search"]["names"][term]["latest"] = {
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "page": page,
            "rows": len(records),
            "last_row": records.pop()
        }

        # overwrite file with latest details
        fp.seek(0)
        fp.write(json.dumps(status, indent=2))
        fp.truncate()


def read_search_files(sources):
    data = pd.DataFrame()

    # company name searches
    for term in sources["search"]["names"]:
        filepath = data_dir + "sources/search/names/" + term + ".csv"
        if os.path.isfile(filepath):
            try:
                print("    ", "Reading data for", term)

                term_data = pd.read_csv(filepath)
                data = pd.concat([data, term_data])

            except UnicodeDecodeError as error:
                print("    ", "ERROR:", error)
        else:
            print("      ", "WARNING: File missing for term", term)

    # company number searches
    numbers_filepath = data_dir + "sources/search/numbers/numbers.csv"
    if os.path.isfile(numbers_filepath):
        try:
            print("    ", "Reading data for number searches")

            number_data = pd.read_csv(numbers_filepath)
            data = pd.concat([data, number_data])

        except UnicodeDecodeError as error:
            print("    ", "ERROR:", error)
    else:
        print("      ", "WARNING: File missing for number searches")

    # sort
    data = data.sort_values(by=["Number", "Name", "Index Date"])

    return data
