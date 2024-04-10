import os
import pandas as pd
import geopandas
from shapely.geometry import shape
from shapely.geometry.polygon import Polygon
from shapely.geometry.point import Point
from shapely import get_x, get_y
import overpass
import csv
import json

"""
OpenStreetMap data processing

"""

data_dir = "data/openstreetmap/"
github_url = "https://github.com/dankarran/isleofman-opendata"
github_project = "dankarran/isleofman-opendata"


def openstreetmap():
    print("# OpenStreetMap")

    with open(data_dir + "sources/sources.json") as fp:
        sources = json.load(fp)

    data = load_data(sources)
    data = process_data(sources, data)
    write_data(sources, data)

    generate_postcode_boundaries(sources, data)

    print_datasets_markdown(sources)


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
                elif feature["geometry"]["type"] in ["LineString", "Polygon"]:
                    # TODO: debug why nothing is coming through as a Polygon
                    polygon: Polygon = shape(feature["geometry"])
                    centroid: Point = polygon.centroid
                    row["lon"] = get_x(centroid)
                    row["lat"] = get_y(centroid)
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

                # limit columns in output
                if "csv_columns" in source:
                    csv_columns = ["osm_id", "osm_type", "osm_url", "lat", "lon"]
                    csv_columns.extend(source["csv_columns"].copy())

                    for csv_column in source["csv_columns"]:
                        if csv_column not in df.columns:
                            print("      ", "Removing", csv_column, "not in dataset")
                            csv_columns.remove(csv_column)

                    print("      ", "Writing columns", csv_columns)
                    df_out = df[csv_columns]

                # sort data in columns
                if "sort_columns" in source:
                    df_out = df_out.sort_values(by=source["sort_columns"])

                df_out.to_csv(filepath, index=False, quoting=csv.QUOTE_ALL)


def generate_postcode_boundaries(sources, data):
    update_text = input("Regenerate postcode boundaries from OpenStreetMap data? (y/N) ")
    if update_text != "y":
        return

    filepath = data_dir + "sources/overpass/postcodes.geojson"
    if os.path.isfile(filepath):
        gdf = geopandas.read_file(filepath)

        # find valid postcodes (exclude IM99)
        im_postcode_regex = '^IM[0-9] [0-9][A-Z]{2}$'
        valid_postcode_rows = gdf["addr:postcode"].str.contains(im_postcode_regex)
        gdf = gdf[valid_postcode_rows]

        # districts (e.g. IM1)
        gdf["district"] = gdf["addr:postcode"].str.slice(start=0, stop=3)

        districts = gdf.dissolve("district").convex_hull
        districts_filepath = data_dir + "outputs/postcodes/postcode_districts.geojson"
        districts.to_file(districts_filepath, driver="GeoJSON")

        print("    ", len(districts), "districts added")

        # sectors (e.g. IM1 1)
        gdf["sector"] = gdf["addr:postcode"].str.slice(start=0, stop=5)

        sectors = gdf.dissolve("sector").convex_hull
        sectors_filepath = data_dir + "outputs/postcodes/postcode_sectors.geojson"
        sectors.to_file(sectors_filepath, driver="GeoJSON")

        print("    ", len(sectors), "sectors added")

    else:
        print("    ", "No postcodes GeoJSON found")


def print_datasets_markdown(sources):
    update_text = input("Regenerate markdown links to OpenStreetMap datasets? (y/N) ")
    if update_text != "y":
        return

    github_outputs_dir = "/blob/main/" + data_dir + "outputs/"

    additional_sources = [
        {
            "label": "postcode_districts",
            "directory": "postcodes",
            "title": "Postcode districts (from addr:postcode)",
            "group": "Addressing",
            "output_formats": ["geojson"],
        },
        {
            "label": "postcode_sectors",
            "directory": "postcodes",
            "title": "Postcode sectors (from addr:postcode)",
            "group": "Addressing",
            "output_formats": ["geojson"],
        }
    ]

    combined_sources = sources["overpass"] + additional_sources

    groups = {}

    for source in combined_sources:
        group = "default"
        if "group" in source:
            group = source["group"]

        dataset_dir = source["label"]
        if "directory" in source:
            dataset_dir = source["directory"]

        item = source["title"]
        item = item + " :spiral_notepad:"
        if "csv" in source["output_formats"]:
            item = item + " [CSV](" + github_url + github_outputs_dir + dataset_dir + "/" + source["label"] + ".csv)"
        if "geojson" in source["output_formats"]:
            item = item + " [GeoJSON](" + github_url + github_outputs_dir + dataset_dir + "/" + source["label"] + ".geojson)"
            item = item + " :link:"
            item = item + " [view on geojson.io](http://geojson.io/#id=github:" + github_project + github_outputs_dir + dataset_dir + "/" + source["label"] + ".geojson)"

        if group not in groups:
            groups[group] = {"items": []}

        groups[group]["items"].append(item)

    # print output
    print("\n\n")

    for group in groups:
        prefix = "  * "

        # for non-default groups, print heading and indent items further
        if group != "default":
            print(prefix + group)
            prefix = "    * "

        for item in groups[group]["items"]:
            print(prefix + item)

    print("\n\n")
