import json
import overpass


"""
OpenStreetMap data processing

"""

source_dir = "data/source/openstreetmap/"


def openstreetmap(output_dir):
    print("# OpenStreetMap")

    with open(source_dir + "sources.json") as fp:
        sources = json.load(fp)

    data = load_data(sources)


def load_data(sources):
    print(" - Loading data")

    data = {}

    update_text = input("Download updated OpenStreetMap data? (y/N) ")
    if update_text == "y":
        update_files(sources)

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
            open(source_dir + "overpass/" + source["label"] + ".geojson", "w").write(json.dumps(data, indent=2))

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
