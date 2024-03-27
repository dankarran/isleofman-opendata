import os
import requests
import json
import csv
import pandas as pd
import overpass


"""
OpenStreetMap data processing

"""

source_dir = "data/source/openstreetmap/"
bbox = "54,-5,54.5,-4"


def openstreetmap(output_dir):
    print("# OpenStreetMap")

    with open(source_dir + "sources.json") as fp:
        sources = json.load(fp)

    data = load_data(sources)
    write_data(data, output_dir)


def load_data(sources):
    print(" - Loading data")

    data = {}

    update_text = input("Download updated data? (y/N) ")
    if update_text == "y":
        update_files(sources)

    return data


def update_files(sources):
    for source in sources["overpass"]:

        try:
            print("    ", "Downloading", source["label"])
            data = get_overpass(source["query"], responseformat=source["response_format"])
            open(source_dir + source["label"] + '.geojson', 'w').write(json.dumps(data))

        except Exception as error:
            print("    ", "ERROR:", error)


def get_overpass(query, responseformat="geojson", verbosity="geom"):
    api = overpass.API()
    result = api.get(
        query,
        responseformat=responseformat,
        verbosity=verbosity
    )

    return result


def write_data(data, output_dir):
    for key in data["geojson"]:
        open(source_dir + key + '.geojson', 'w').write(json.dumps(data[key]))
