import os
import requests
import time
from datetime import datetime
import pandas as pd
import bs4
import csv
import json


"""
Companies Registry data processing

"""

data_dir = "data/gov.im/companies/"
registry_url = "https://services.gov.im/ded/services/companiesregistry/"
search_page = "companysearch.iom?SortBy=IncorporationDate&SortDirection=0&search=Search&searchtext="


def companies():
    print("# Companies Registry - Isle of Man Government")

    with open(data_dir + "sources/sources.json") as fp:
        sources = json.load(fp)

    with open(data_dir + "sources/status.json") as fp:
        status = json.load(fp)

    data = load_data(sources, status)
    data = process_data(data)
    write_data(data)


def load_data(sources, status):
    print(" - Loading Companies")

    update_text = input("Download latest company registry details? (y/N) ")
    if update_text == "y":
        update_companies_list(sources, status)

    # load data into dataframes
    data = read_terms_files(sources)

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

    data = {
        "companies-live": companies_live,
        "companies-non-live": companies_non_live,
        "old-names": old_names
    }

    return data


def write_data(data):
    for record_type in data:
        filename = record_type + ".csv"
        filepath = data_dir + "outputs/" + filename
        data[record_type].to_csv(filepath, index=False, quoting=csv.QUOTE_ALL)
        print("    ", len(data[record_type]), "rows written to", filename)


def update_companies_list(sources, status):
    for term in sources["search"]["terms"]:

        page = 1
        skip_rows = 0
        if term in status["search"]["terms"]:
            term_status = status["search"]["terms"][term]["latest"]

            if term_status["rows"] == 30:
                # start on next page after full page retrieved
                page = term_status["page"] + 1
            else:
                # start on final page again, but skip the rows we've already seen
                # TODO: may want to check contents as well, to ensure sort order is the same
                page = term_status["page"]
                skip_rows = term_status["rows"]

        while True:
            data = get_search_page(term, page)

            if not data.empty:
                if skip_rows:
                    print("    ", "Skipping first", skip_rows, "already retrieved")
                    data = data.iloc[1:skip_rows, :]
                    skip_rows = 0

                write_search_page(term, page, data)

                if len(data) == 30:
                    page = page + 1
                else:
                    print("    ", "End of list")
                    break

            else:
                print("    ", "No more data")
                break

            sleep = 5 # TODO: back off if server responding slower?
            print("    ", "... pausing for", sleep, "seconds ...")
            time.sleep(sleep)


def get_search_page(term, page):
    url = registry_url + search_page + term + "&page=" + str(page)

    print("    ", "Downloading results for", term, "from", url, "page", page)
    
    index_date = datetime.now().strftime("%Y-%m-%d")

    # TODO: handle exceptions, pause and retry a few times before giving up?

    with requests.get(url) as f:
        soup = bs4.BeautifulSoup(f.content, "lxml")

        table = soup.find_all("table")[0]
        table_rows = table.find_all("tr")

        rows = []
        for row in table_rows:
            name_link = row.find_all("td")[0].find_all("a")[0]
            name = str(name_link.contents[0])
            url = registry_url + str(name_link.get("href")).strip()

            rows.append({
                "Name": name,
                "Number": str(row.find_all("td")[1].contents[0]),
                "Inc/Reg Date": str(row.find_all("td")[2].contents[0]),
                "Status": str(row.find_all("td")[3].contents[0]),
                "Registry Type": str(row.find_all("td")[4].contents[0]),
                "Name Status": str(row.find_all("td")[5].contents[0]),
                "URL": url,
                "Index Date": index_date
            })

        df = pd.DataFrame(rows)

        return df


def write_search_page(term, page, data):
    filepath = data_dir + "sources/terms/" + term + ".csv"

    file_exists = os.path.isfile(filepath)
    add_header = not file_exists

    data.to_csv(filepath, mode="a", index=False, header=add_header, quoting=csv.QUOTE_ALL)

    update_search_status(term, page, data)


def update_search_status(term, page, data):
    with open(data_dir + "sources/status.json", "r+") as fp:
        status = json.load(fp)

        if term not in status["search"]["terms"]:
            status["search"]["terms"][term] = {}

        records = data.to_dict("records")

        status["search"]["terms"][term]["latest"] = {
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "page": page,
            "rows": len(records),
            "last_row": records.pop()
        }

        # overwrite file with latest details
        fp.seek(0)
        fp.write(json.dumps(status, indent=2))
        fp.truncate()


def read_terms_files(sources):
    data = pd.DataFrame()

    for term in sources["search"]["terms"]:
        filepath = data_dir + "sources/terms/" + term + ".csv"

        if os.path.isfile(filepath):
            try:
                print("    ", "Reading data for", term)

                term_data = pd.read_csv(filepath)

                data = pd.concat([data, term_data])

            except UnicodeDecodeError as error:
                print("    ", "ERROR:", error)
        else:
            print("      ", "WARNING: File missing for", term)

    data = data.sort_values(by=["Number"])

    return data
