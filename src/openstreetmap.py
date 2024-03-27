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
            print("    ", "Downloading", source["label"], "in", source["response_format"], "format")
            # TODO: specify responseformat if needed, debug why it breaks output
            data = get_overpass(source["query"])
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
