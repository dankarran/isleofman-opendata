import os
import pandas as pd
import overpass
import csv
import json

"""
OpenStreetMap data processing

"""

data_dir = "data/openstreetmap/"


def openstreetmap():
    print("# OpenStreetMap")

    with open(data_dir + "sources/sources.json") as fp:
        sources = json.load(fp)

    data = load_data(sources)
    data = process_data(sources, data)
    write_data(sources, data)


def load_data(sources):
    print(" - Loading data")

    data = {
        "overpass": {}
    }

    update_text = input("Download updated OpenStreetMap data? (y/N) ")
    if update_text == "y":
        update_files(sources)

    for source in sources["overpass"]:
        filepath = data_dir + "sources/overpass/" + source["label"] + ".geojson"
        if os.path.isfile(filepath):
            with open(filepath) as fp:
                data["overpass"][source["label"]] = {
                    "geojson": json.load(fp)
                }

        else:
            print("    ", "WARN:", source["label"], "GeoJSON not found")

    return data


def update_files(sources):
    for source in sources["overpass"]:

        try:
            # TODO: debug why getting response_format from sources list breaks output
            response_format = "geojson"
            if "response_format" in source:
                response_format = source["response_format"]
            print("    ", "Downloading", source["label"], "in", response_format, "format")
            data = get_overpass(source["query"], response_format=response_format)
            open(data_dir + "sources/overpass/" + source["label"] + ".geojson", "w").write(json.dumps(data, indent=2))

        except Exception as error:
            print("    ", "ERROR:", error)


def get_overpass(query, response_format="geojson", verbosity="geom"):
    print("    ", "Querying Overpass API for", query, "in", response_format, "format with verbosity", verbosity)
    api = overpass.API()
    result = api.get(
        query,
        responseformat=response_format,
        verbosity=verbosity
    )

    return result


def process_data(sources, data):
    print(" - Processing OpenStreetMap data")

    for source in sources["overpass"]:
        if source["label"] in data["overpass"]:
            print("    ", "Processing", source["label"])

            rows = []
            features = data["overpass"][source["label"]]["geojson"]["features"]
            for feature in features:

                row = feature["properties"]
                row["osm_id"] = feature["id"]

                if feature["geometry"]["type"] == "Point":
                    row["lon"] = feature["geometry"]["coordinates"][0]
                    row["lat"] = feature["geometry"]["coordinates"][1]
                    row["osm_type"] = "node"
                elif feature["geometry"]["type"] == "LineString":
                    # TODO: maybe add wkt instead?
                    row["lon"] = None
                    row["lat"] = None
                    row["osm_type"] = "way"
                elif feature["geometry"]["type"] == "Polygon":
                    # TODO: maybe add wkt, and calculate centroid?
                    row["lon"] = None
                    row["lat"] = None
                    row["osm_type"] = "way"
                else:
                    row["lon"] = None
                    row["lat"] = None
                    row["osm_type"] = None

                row["osm_url"] = "https://osm.org/" + row["osm_type"] + "/" + str(row["osm_id"])

                rows.append(row)

            data["overpass"][source["label"]]["df"] = pd.DataFrame(rows)

    return data


def write_data(sources, data):
    print(" - Writing OpenStreetMap data")

    for source in sources["overpass"]:
        if source["label"] in data["overpass"]:
            print("    ", "Writing", source["label"])
            filepath_base = data_dir + "outputs/" + source["label"] + "/"

            if not os.path.isdir(filepath_base):
                os.mkdir(filepath_base)

            if "geojson" in source["output_formats"]:
                filepath = filepath_base + source["label"] + ".geojson"

                geojson = data["overpass"][source["label"]]["geojson"]
                open(filepath, "w").write(json.dumps(geojson, indent=2))

            if "csv" in source["output_formats"]:
                filepath = filepath_base + source["label"] + ".csv"

                df = data["overpass"][source["label"]]["df"]
                df_out = df
                if "csv_columns" in source:
                    csv_columns = ["osm_id", "osm_type", "osm_url", "lat", "lon"]
                    csv_columns.extend(source["csv_columns"].copy())

                    for csv_column in source["csv_columns"]:
                        if csv_column not in df.columns:
                            print("      ", "Removing", csv_column, "not in dataset")
                            csv_columns.remove(csv_column)

                    print("      ", "Writing columns", csv_columns)
                    df_out = df[csv_columns]

                df_out.to_csv(filepath, index=False, quoting=csv.QUOTE_ALL)
