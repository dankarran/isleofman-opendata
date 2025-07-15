import argparse

from src.companies import companies, companies_unindexed
from src.land_transactions import land_transactions
from src.planning_applications import planning_applications
from src.openstreetmap import openstreetmap, generate_postcode_boundaries, print_datasets_markdown
from src.global_ml_building_footprints import global_ml_building_footprints
from src.helpers import log

"""
Isle of Man opendata transformation script

"""


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Isle of Man opendata transformation script")

    parser.add_argument('--companies', action='store_true', help='Run the Companies Registry update')
    parser.add_argument('--companies-unindexed', action='store_true',
                        help='Run only the Companies Registry unindexed numbers update')

    parser.add_argument('--land-transactions', action='store_true', help='Run the Land Transactions update')

    parser.add_argument('--planning-applications', action='store_true', help='Run the Planning Applications update')
    parser.add_argument('--update-weekly-planning', action='store_true',
                        help='Run only the weekly planning application files update')
    parser.add_argument('--update-annual-planning', action='store_true',
                        help='Run only the annual planning application files update')

    parser.add_argument('--openstreetmap', action='store_true', help='Run the OpenStreetMap update')
    parser.add_argument('--generate-postcode-boundaries', action='store_true',
                        help='Run only the postcode boundaries generation from OpenStreetMap data')
    parser.add_argument('--openstreetmap-markdown', action='store_true',
                        help='Run only the OpenStreetMap markdown generation')

    parser.add_argument(
        '--global-ml-building-footprints',
        action='store_true',
        help='Run the Global ML Building Footprints update'
    )

    args = parser.parse_args()

    # Determine if any specific argument was provided.
    # If no specific argument is provided, `run_all` will be True, and we run everything in interactive mode.
    # If any specific argument is provided, `run_all` will be False, and we run only the specified tasks in non-interactive mode.
    run_all = not any(vars(args).values())
    interactive = run_all

    # Companies Registry
    if args.companies or run_all:
        log('Updating Companies Registry data...')
        companies(interactive=interactive)

    if args.companies_unindexed or run_all:
        log('Updating Companies Registry unindexed numbers...')
        companies_unindexed(interactive=interactive)

    # Land Transactions
    if args.land_transactions or run_all:
        log('Updating Land Transactions data...')
        land_transactions(interactive=interactive)

    # Planning Applications
    if args.planning_applications or run_all:
        log('Updating Planning Applications data...')
        planning_applications(interactive=interactive, update_weekly=True, update_annual=True, process=True)

    if args.update_weekly_planning:
        log('Updating weekly planning application files...')
        planning_applications(interactive=interactive, update_weekly=True)

    if args.update_annual_planning:
        log('Updating annual planning application files...')
        planning_applications(interactive=interactive, update_annual=True)

    # OpenStreetMap
    if args.openstreetmap or run_all:
        log('Updating OpenStreetMap data...')
        openstreetmap(interactive=interactive)

    if args.generate_postcode_boundaries or run_all:
        log('Generating postcode boundaries...')
        generate_postcode_boundaries(interactive=interactive)

    if args.openstreetmap_markdown or run_all:
        log('Generating OpenStreetMap markdown...')
        print_datasets_markdown(interactive=interactive)

    # Global ML Building Footprints
    if args.global_ml_building_footprints or run_all:
        log('Updating Global ML Building Footprints data...')
        global_ml_building_footprints(interactive=interactive)

    log('Update complete.')
