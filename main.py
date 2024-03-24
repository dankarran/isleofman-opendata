from src.land_transactions import land_transactions

"""
Isle of Man opendata transformation script

"""

output_dir = 'data/outputs/'


if __name__ == '__main__':

    # Isle of Man Government Land Transactions data
    land_transactions(output_dir)
