from src.companies import companies
from src.land_transactions import land_transactions
from src.planning_applications import planning_applications
from src.openstreetmap import openstreetmap
from src.global_ml_building_footprints import global_ml_building_footprints

"""
Isle of Man opendata transformation script

"""


if __name__ == '__main__':

    # Isle of Man Companies Registry
    companies()

    # Isle of Man Government Land Transactions data
    land_transactions()

    # Isle of Man Government Planning Applications data
    planning_applications()

    # OpenStreetMap
    openstreetmap()

    # Global ML Building Footprints
    global_ml_building_footprints()
