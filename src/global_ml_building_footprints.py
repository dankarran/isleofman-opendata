import pandas as pd
import geopandas as gpd
from shapely.geometry import shape
from src.helpers import prompt


"""
Building footprints import script based on
https://github.com/microsoft/GlobalMLBuildingFootprints/blob/main/scripts/make-gis-friendly.py

"""

data_dir = "data/microsoft/global-ml-building-footprints/"


def global_ml_building_footprints(interactive=True):
    update_text = 'y'
    if interactive:
        update_text = prompt("Download updated Global ML Building Footprints data? (y/N) ")
    if update_text != "y":
        return False

    # this is the name of the geography you want to retrieve. update to meet your needs
    location = 'IsleofMan'

    dataset_links = pd.read_csv("https://minedbuildings.blob.core.windows.net/global-buildings/dataset-links.csv")
    greece_links = dataset_links[dataset_links.Location == location]
    for _, row in greece_links.iterrows():
        df = pd.read_json(row.Url, lines=True)
        df['geometry'] = df['geometry'].apply(shape)
        gdf = gpd.GeoDataFrame(df, crs=4326)
        gdf.to_file(f"{data_dir}sources/{row.QuadKey}.geojson", driver="GeoJSON")

    # TODO: merge into single GeoJSON file for outputs directory


if __name__ == "__main__":
    global_ml_building_footprints()
