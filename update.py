from src.companies import companies
from src.land_transactions import land_transactions
from src.planning_applications import planning_applications
from src.openstreetmap import openstreetmap

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
