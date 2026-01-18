import os
import time
from datetime import datetime
import random
import urllib.parse
import pandas as pd
import bs4
import csv
import json
import re
from src.helpers import get_url, log, prompt

"""
Companies Registry data processing

"""

data_dir = "data/gov.im/companies/"
registry_url = "https://services.gov.im/ded/services/companiesregistry/"
search_page = "companysearch.iom?"

details_filepath = data_dir + "sources/details/details.json"


def companies(interactive=True):
    log("# Companies Registry - Isle of Man Government")

    with open(data_dir + "sources/sources.json") as fp:
        sources = json.load(fp)

    with open(data_dir + "sources/status.json") as fp:
        status = json.load(fp)

    # search for companies by name and write outputs
    data = load_data(sources, status, interactive)
    data = process_data(data)
    write_data(data)


def companies_unindexed(interactive=True):
    unindexed_filepath = data_dir + "outputs/company-numbers-unindexed.csv"
    if os.path.isfile(unindexed_filepath):
        unindexed = pd.read_csv(unindexed_filepath)
        log("    ", len(unindexed["Number"]), "unindexed company numbers detected")

        # exclude companies previously not found when searching by number
        not_found_filepath = data_dir + "sources/search/numbers/not-found.csv"
        if os.path.isfile(not_found_filepath):
            not_found = pd.read_csv(not_found_filepath)
            log("    ", len(not_found["Number"]), "company numbers previously not found in index")

            unindexed = unindexed[~unindexed["Number"].isin(not_found["Number"])]

        batch_count = 0
        if len(unindexed["Number"]):
            if interactive:
                batch_text = prompt("Download batch of [x] from ~" + str(len(unindexed["Number"])) + " unindexed companies? (default 0) ")
                if batch_text:
                    batch_count = int(batch_text)
            else:
                batch_count = len(unindexed["Number"])

        if batch_count > 0:
            log("    ", "Updating ", batch_count, "unindexed companies")
            unindexed_numbers = unindexed["Number"][:batch_count]
            update_companies_list_by_number(unindexed_numbers)


def load_data(sources, status, interactive=True):
    log(" - Loading Companies")

    if interactive:
        update_text = prompt("Download latest company registry details? (y/N) ")
        if update_text == "y":
            update_companies_list(sources, status)
    else:
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
    """
    Writes CSV outputs. For companies-live and companies-non-live, attempt to include
    Registered Address by reading the details.json created by update_company_details.
    """
    # load details mapping (Number -> details)
    details = load_details_file()

    # If companies-live/non-live present, augment with Registered Address column
    for record_type in data:
        df = data[record_type]

        # Only attempt to add registered address for the two company outputs
        if record_type in ("companies-live", "companies-non-live"):
            if "Number" in df.columns:
                # build a list mapping Number -> registered_address if present
                reg_addrs = []
                for _, row in df.iterrows():
                    number = str(row.get("Number", "")).strip()
                    addr = ""
                    if number in details and details[number].get("registered_address"):
                        addr = details[number].get("registered_address", "")
                    reg_addrs.append(addr)
                # add/replace Registered Address column
                df = df.copy()
                df["Registered Address"] = reg_addrs
            else:
                log("    ", "WARNING: No Number column in", record_type, "- cannot add Registered Address")

        # write the CSV file
        filename = record_type + ".csv"
        filepath = data_dir + "outputs/" + filename
        df.to_csv(filepath, index=False, quoting=csv.QUOTE_ALL)
        log("    ", len(df), "rows written to", filename)


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
                #    log("    ", "Skipping first", skip_rows, "already retrieved")
                #    data = data.iloc[1:skip_rows, :]
                #    skip_rows = 0

                write_search_page(term, page, data)

                if len(data) == 30:
                    page = page + 1
                else:
                    log("    ", "End of list")
                    break

            else:
                log("    ", "No more data")
                break

            sleep = random.randint(5, 10)
            log("    ", "... pausing for", sleep, "seconds ...")
            time.sleep(sleep)


def update_companies_list_by_number(numbers):
    for number in numbers:

        try:
            data = get_search_page(number, search_by=1)

            if not data.empty:
                write_search_by_number_page(data)

            else:
                write_search_by_number_not_found(number)
                log("    ", "Company", number, "not found")

            sleep = random.randint(1, 5)
            log("    ", "... pausing for", sleep, "seconds ...")
            time.sleep(sleep)

        except Exception as error:
            log(error)
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

    log("    ", "Downloading results for search term", term, "from", url, "page", page)
    
    index_date = datetime.now().strftime("%Y-%m-%d")

    # TODO: handle exceptions, pause and retry a few times before giving up?

    with get_url(url) as f:
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


def read_search_files(sources):
    data = pd.DataFrame()

    # company name searches
    for term in sources["search"]["names"]:
        filepath = data_dir + "sources/search/names/" + term + ".csv"
        if os.path.isfile(filepath):
            try:
                log("    ", "Reading data for", term)

                term_data = pd.read_csv(filepath)
                data = pd.concat([data, term_data])

            except UnicodeDecodeError as error:
                log("    ", "ERROR:", error)
        else:
            log("      ", "WARNING: File missing for term", term)

    # company number searches
    numbers_filepath = data_dir + "sources/search/numbers/numbers.csv"
    if os.path.isfile(numbers_filepath):
        try:
            log("    ", "Reading data for number searches")

            number_data = pd.read_csv(numbers_filepath)
            data = pd.concat([data, number_data])

        except UnicodeDecodeError as error:
            log("    ", "ERROR:", error)
    else:
        log("      ", "WARNING: File missing for number searches")

    # sort
    if not data.empty:
        # drop duplicates keeping last (so last fetched row kept)
        data = data.drop_duplicates(subset=["Number", "Registry Type", "Name"], keep="last")
        data = data.sort_values(by=["Number"])
    else:
        log("    ", "WARNING: No company search data found")

    return data


def load_details_file():
    """
    Load the details.json file which stores scraped details per company number.
    Returns dict mapping Number -> details dict.
    """
    if not os.path.isdir(os.path.dirname(details_filepath)):
        os.makedirs(os.path.dirname(details_filepath), exist_ok=True)

    if os.path.isfile(details_filepath):
        try:
            with open(details_filepath, "r", encoding="utf-8") as fp:
                return json.load(fp)
        except Exception as e:
            log("    ", "WARNING: Could not read details file:", e)
            return {}
    return {}


def save_details_file(details):
    try:
        with open(details_filepath, "w", encoding="utf-8") as fp:
            json.dump(details, fp, indent=2, ensure_ascii=False)
    except Exception as e:
        log("    ", "ERROR: Could not write details file:", e)


def _normalize_label(label: str) -> str:
    """
    Convert a label to lowercase a-z/0-9 with underscores instead of spaces and
    remove other characters. E.g. 'Registered Office Address' -> 'registered_office_address'
    """
    if not label:
        return ""
    s = label.strip().lower()
    # replace whitespace with underscore
    s = re.sub(r"\s+", "_", s)
    # remove characters other than a-z0-9 and underscore
    s = re.sub(r"[^a-z0-9_]", "", s)
    # collapse multiple underscores
    s = re.sub(r"_+", "_", s)
    # strip leading/trailing underscores
    s = s.strip("_")
    return s


def parse_main_details_table(soup: bs4.BeautifulSoup) -> dict:
    """
    Parse the main two-column details table into a dict of normalized_label => value.
    Also extract documents link/count/BusinessEntityId into a nested 'documents' key.
    Heuristic: find first table with rows where each row has a <th> and <td> pair.
    """
    tables = soup.find_all("table")
    for table in tables:
        # check for rows that contain th and td (two column descriptive table)
        rows = table.find_all("tr")
        candidate = False
        for r in rows:
            th = r.find("th")
            td = r.find("td")
            if th and td:
                candidate = True
                break
        if not candidate:
            continue

        details = {}
        for r in rows:
            th = r.find("th")
            td = r.find("td")
            if not (th and td):
                continue
            label = th.get_text(" ", strip=True)
            value = td.get_text(" ", strip=True)
            key = _normalize_label(label)
            if key:
                details[key] = value

            # special-case: documents link extraction (also set details['documents'])
            # look for an <a> inside the td pointing to the purchasefileanddocumentlist page
            a = td.find("a", href=True)
            if a:
                href = a.get("href").strip()
                # some urls are relative; make absolute against registry_url
                full_url = urllib.parse.urljoin(registry_url, href)
                link_text = a.get_text(" ", strip=True)
                # extract numeric count from label text (e.g. "540 public documents available")
                count = None
                m = re.search(r"(\d[\d,]*)", link_text)
                if m:
                    # remove commas
                    try:
                        count = int(m.group(1).replace(",", ""))
                    except Exception:
                        count = None
                # extract BusinessEntityId from query string
                parsed = urllib.parse.urlparse(full_url)
                qs = urllib.parse.parse_qs(parsed.query)
                beid = None
                if "BusinessEntityId" in qs:
                    v = qs.get("BusinessEntityId")
                    if v:
                        try:
                            beid = int(v[0])
                        except Exception:
                            # maybe it's not purely numeric
                            beid = v[0]

                # Only add documents object if the link looks like a docs link or the label contains 'document'
                if re.search(r"document", href, flags=re.I) or re.search(r"document", link_text, flags=re.I):
                    details["documents"] = {
                        "url": full_url,
                        "count": count if count is not None else 0,
                        "BusinessEntityId": beid
                    }

        if details:
            return details

    return {}


def parse_previous_names_table(soup: bs4.BeautifulSoup) -> list:
    """
    Parse the previous names table. Heuristics:
      - Look for an h2 with id or text 'names' / 'previous names' and then next table
      - Otherwise, find a table whose header contains 'name' and 'status'
    Returns a list of { 'name': <name>, 'status': <status> }.
    """
    # 1) look for heading
    for h in soup.find_all(re.compile("^h[1-6]$")):
        hid = (h.get("id") or "").lower()
        if hid == "names" or re.search(r"previous\s+names", h.get_text(strip=True), flags=re.I):
            nxt = h.find_next("table")
            if nxt:
                return _parse_names_table(nxt)

    # 2) find table by header row
    for table in soup.find_all("table"):
        header_cells = [c.get_text(strip=True).lower() for c in table.find_all("th")]
        if any("name" in h for h in header_cells) and any("status" in h for h in header_cells):
            return _parse_names_table(table)

    return []


def _parse_names_table(table_tag: bs4.Tag) -> list:
    rows = []
    trs = table_tag.find_all("tr")
    # find header to know which column is name/status
    headers = [th.get_text(strip=True).lower() for th in table_tag.find_all("th")]
    # if headers present, skip header row
    for r in trs:
        tds = r.find_all("td")
        if not tds:
            continue
        # name is first td, status second if available
        name = tds[0].get_text(" ", strip=True) if len(tds) >= 1 else ""
        status = tds[1].get_text(" ", strip=True) if len(tds) >= 2 else ""
        if name:
            rows.append({"name": name, "status": status})
    return rows


def parse_agents_table(soup: bs4.BeautifulSoup) -> list:
    """
    Parse the Registered Agents table. Heuristics:
      - Look for an h2 with id or text 'agents' / 'registered agents' then next table
      - Otherwise find a table whose header contains 'agent' and 'address'
    Returns list of { 'agent': <name>, 'address': <address> }
    """
    for h in soup.find_all(re.compile("^h[1-6]$")):
        hid = (h.get("id") or "").lower()
        if hid == "agents" or re.search(r"registered\s+agents?", h.get_text(strip=True), flags=re.I):
            nxt = h.find_next("table")
            if nxt:
                return _parse_agents_table(nxt)

    for table in soup.find_all("table"):
        header_cells = [c.get_text(strip=True).lower() for c in table.find_all("th")]
        if any("agent" in h for h in header_cells) and any("address" in h for h in header_cells):
            return _parse_agents_table(table)

    return []


def _parse_agents_table(table_tag: bs4.Tag) -> list:
    rows = []
    trs = table_tag.find_all("tr")
    for r in trs:
        tds = r.find_all("td")
        if not tds:
            continue
        agent = tds[0].get_text(" ", strip=True) if len(tds) >= 1 else ""
        address = tds[1].get_text(" ", strip=True) if len(tds) >= 2 else ""
        if agent or address:
            rows.append({"agent": agent, "address": address})
    return rows


def parse_company_page(soup: bs4.BeautifulSoup) -> dict:
    """
    High-level parser that returns a dict:
      {
        "main": { normalized_key: value, ... },
        "previous_names": [ {name, status}, ... ],
        "agents": [ {agent, address}, ... ]
      }
    """
    main = parse_main_details_table(soup)
    previous_names = parse_previous_names_table(soup)
    agents = parse_agents_table(soup)

    return {"main": main, "previous_names": previous_names, "agents": agents}


def parse_registered_address(soup: bs4.BeautifulSoup) -> str:
    """
    Attempt to find a registered address on a company details page.
    Preferentially return:
      1) main['registered_office_address'] or main['registered_address'] or main['place_of_business']
      2) first agent address (if agents table present and agent looks like an address)
      3) heuristics (previous behavior)
    """
    parsed = parse_company_page(soup)
    main = parsed.get("main", {})
    if main:
        # prefer normalized keys
        for key in ("registered_office_address", "registered_address", "registered_office", "address", "place_of_business"):
            if key in main and main[key]:
                return main[key]

    # fallback: use first agent address if present
    agents = parsed.get("agents", [])
    if agents:
        first = agents[0]
        if first.get("address"):
            return first.get("address")

    # old heuristic fallback: search for elements with 'address' in class/id
    addr_candidates = []
    for tag in soup.find_all(True):
        cid = " ".join(filter(None, [tag.get("class") and " ".join(tag.get("class")), tag.get("id") or ""]))
        if cid and re.search(r"\baddress\b", cid, flags=re.I):
            text = tag.get_text(separator=" ", strip=True)
            if text:
                addr_candidates.append(text)

    if addr_candidates:
        return ", ".join(addr_candidates)

    full_text = soup.get_text("\n", strip=True)
    # TODO: Place of Business if needed
    m = re.search(r"(Registered (Office|Address)[^\n]*\n)([\s\S]{0,300})", full_text, flags=re.I)
    if m:
        candidate = m.group(3).split("\n")
        lines = [l.strip() for l in candidate if l.strip()][:3]
        return ", ".join(lines)

    return ""


def fetch_details_for_list(number_url_pairs, max_requests=None, min_sleep=1.0, max_sleep=3.0, force=False):
    """
    number_url_pairs: list of (Number, URL)
    """
    if max_requests is not None:
        try:
            max_requests = int(max_requests)
        except Exception:
            max_requests = None

    details = load_details_file()
    count = 0

    for number, url in number_url_pairs:
        if max_requests is not None and count >= max_requests:
            log("    ", f"Reached max_requests limit ({max_requests}). Stopping.")
            break

        if not url:
            log("    ", f"Skipping {number}: no details URL available")
            continue

        # skip if already fetched and not forcing
        if not force and number in details and details[number].get("fetched"):
            log("    ", f"Skipping {number}: details already fetched (use force to re-fetch)")
            continue

        try:
            log("    ", f"Fetching details for {number} -> {url}")
            r = get_url(url)
            if getattr(r, "status_code", None) is not None and r.status_code != 200:
                log("    ", f"Warning: received status {r.status_code} for {url}")
                # store metadata that we attempted
                details[number] = {
                    "url": url,
                    "fetched": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "http_status": r.status_code
                }
                save_details_file(details)
                continue

            # Use text if requests.Response-like, or .content if a file-like was returned
            content = getattr(r, "text", None) or getattr(r, "content", None) or ""
            soup = bs4.BeautifulSoup(content, "html.parser")

            parsed = parse_company_page(soup)
            main = parsed.get("main", {})
            prev_names = parsed.get("previous_names", [])
            agents = parsed.get("agents", [])

            # prefer normalized main fields for registered address
            reg_addr = ""
            if main:
                reg_addr = main.get("registered_office_address") \
                           or main.get("registered_address") \
                           or main.get("place_of_business") \
                           or ""

            # fallback to parse_registered_address heuristics if still empty
            if not reg_addr:
                reg_addr = parse_registered_address(soup)

            # agent: collapse first agent into a single string (name + address)
            agent_str = ""
            if agents:
                first_agent = agents[0]
                agent_str = first_agent.get("agent", "") or ""
                if first_agent.get("address"):
                    if agent_str:
                        agent_str = f"{agent_str} - {first_agent.get('address')}"
                    else:
                        agent_str = first_agent.get("address")

            # documents: prefer structured documents from main if present
            docs = None
            if main and main.get("documents"):
                docs = main.get("documents")
            else:
                # try to find purchase link anywhere on the page as fallback
                a = soup.find("a", href=re.compile(r"purchasefileanddocumentlist", flags=re.I))
                if a:
                    href = a.get("href").strip()
                    full_url = urllib.parse.urljoin(registry_url, href)
                    text = a.get_text(" ", strip=True)
                    m = re.search(r"(\d[\d,]*)", text)
                    count = int(m.group(1).replace(",", "")) if m else 0
                    parsed = urllib.parse.urlparse(full_url)
                    qs = urllib.parse.parse_qs(parsed.query)
                    beid = None
                    if "BusinessEntityId" in qs:
                        v = qs.get("BusinessEntityId")
                        if v:
                            try:
                                beid = int(v[0])
                            except Exception:
                                beid = v[0]
                    docs = {"url": full_url, "count": count, "BusinessEntityId": beid}

            details[number] = {
                "url": url,
                "fetched": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "http_status": getattr(r, "status_code", None) or "",
                "registered_address": reg_addr,
                "previous_names": prev_names,
                "agent": agent_str,
                "main": main,
                "agents": agents,
                "documents": docs
            }

            save_details_file(details)
            count += 1

            # polite sleep
            sleep = random.uniform(min_sleep, max_sleep)
            log("    ", f"... pausing for {sleep:.2f} seconds ...")
            time.sleep(sleep)

        except Exception as e:
            log("    ", f"Error fetching details for {number}: {e}")

    log("    ", f"Finished fetching details. Total fetched this run: {count}")
    return details


def build_number_url_pairs_from_outputs(targets):
    """
    Build a list of (Number, URL) pairs from existing outputs.
    targets: list containing any of 'live', 'non-live', 'new', or 'all'
    For 'new', we look for numbers present in outputs which are not yet in details.json.
    """
    pairs = []
    # load outputs if present
    live_path = data_dir + "outputs/companies-live.csv"
    non_live_path = data_dir + "outputs/companies-non-live.csv"

    live_df = pd.read_csv(live_path, dtype=str) if os.path.isfile(live_path) else pd.DataFrame()
    non_live_df = pd.read_csv(non_live_path, dtype=str) if os.path.isfile(non_live_path) else pd.DataFrame()

    # helper to extract pairs from df
    def pairs_from_df(df):
        out = []
        if df.empty:
            return out
        if "Number" not in df.columns:
            log("    ", "WARNING: Dataframe has no Number column - skipping")
            return out
        # 'URL' column expected; if absent, try other columns that look like urls/details
        url_cols = [c for c in df.columns if c.lower() == "url" or "details" in c.lower()]
        url_col = url_cols[0] if url_cols else None

        for _, row in df.iterrows():
            num = str(row.get("Number", "")).strip()
            url = ""
            if url_col:
                url = str(row.get(url_col, "")).strip()
            out.append((num, url))
        return out

    if "live" in targets:
        pairs.extend(pairs_from_df(live_df))
    if "non-live" in targets:
        pairs.extend(pairs_from_df(non_live_df))

    # deduplicate by Number keeping first seen
    dedup = {}
    for num, url in pairs:
        if num not in dedup:
            dedup[num] = url

    # handle 'new' target: produce pairs that are not in details file
    if "new" in targets:
        details = load_details_file()
        new_pairs = []
        for num, url in dedup.items():
            if num not in details:
                new_pairs.append((num, url))
        # return only new pairs
        return new_pairs

    # otherwise return dedup pairs as list
    return list(dedup.items())


def update_company_details(targets=("new",), max_requests=None, min_sleep=1.0, max_sleep=3.0, force=False, interactive=True):
    """
    Public function invoked by update.py

    targets: list-like of 'live', 'non-live', 'new' (or mix), default ('new',)
    max_requests: optional int limit
    min_sleep/max_sleep: seconds between requests
    force: if True, re-fetch company details even if present in details.json
    interactive: if True, prompt user to confirm
    """
    if isinstance(targets, str):
        targets = [targets]

    # build pairs of Number/URL to fetch
    pairs = build_number_url_pairs_from_outputs(targets)

    if not len(pairs):
        log("    ", "No company numbers/URLs found for requested targets.")
        return

    to_fetch_count = len(pairs)
    if max_requests is not None:
        to_fetch_count = min(len(pairs), int(max_requests))

    if interactive:
        confirm = prompt(f"Fetch details for {to_fetch_count} companies? (y/N) ")
        if confirm.lower() != "y":
            log("    ", "Aborting details fetch.")
            return

    # perform the fetches
    fetch_details_for_list(pairs, max_requests=max_requests, min_sleep=min_sleep, max_sleep=max_sleep, force=force)
