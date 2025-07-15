import argparse

from src.companies import companies
from src.land_transactions import land_transactions
from src.planning_applications import planning_applications
from src.openstreetmap import openstreetmap
from src.global_ml_building_footprints import global_ml_building_footprints

"""
Isle of Man opendata transformation script

"""


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Isle of Man opendata transformation script")
    parser.add_argument('--companies', action='store_true', help='Run the Companies Registry update')
    parser.add_argument('--land-transactions', action='store_true', help='Run the Land Transactions update')
    parser.add_argument('--planning-applications', action='store_true', help='Run the Planning Applications update')
    parser.add_argument('--openstreetmap', action='store_true', help='Run the OpenStreetMap update')
    parser.add_argument(
        '--global-ml-building-footprints',
        action='store_true',
        help='Run the Global ML Building Footprints update'
    )
    # New arguments for granular control
    parser.add_argument('--companies-unindexed', action='store_true',
                        help='Run only the Companies Registry unindexed numbers update')
    parser.add_argument('--update-weekly-planning', action='store_true',
                        help='Run only the weekly planning application files update')
    parser.add_argument('--update-annual-planning', action='store_true',
                        help='Run only the annual planning application files update')
    parser.add_argument('--generate-postcode-boundaries', action='store_true',
                        help='Run only the postcode boundaries generation from OpenStreetMap data')


    args = parser.parse_args()

    # Determine if any specific argument was provided.
    # If no specific argument is provided, `run_all` will be True, and we run everything in interactive mode.
    # If any specific argument is provided, `run_all` will be False, and we run only the specified tasks in non-interactive mode.
    run_all = not any(vars(args).values())
    interactive = run_all

    # Companies Registry
    # If --companies-unindexed is specified, we only run that specific task, not the general companies update.
    # Otherwise, if --companies or run_all, we run the general companies update.
    if args.companies_unindexed:
        print('Updating Companies Registry unindexed numbers...')
        companies(interactive=interactive, run_unindexed_only=True)
    elif args.companies or run_all:
        print('Updating Companies Registry data...')
        # Pass a flag to companies() to indicate if companies_unindexed should be run internally
        # If --companies-unindexed was NOT specified, then companies() should run its internal unindexed update.
        companies(interactive=interactive, run_unindexed_only=False) # Default behavior

    # Land Transactions
    if args.land_transactions or run_all:
        print('Updating Land Transactions data...')
        land_transactions(interactive=interactive)

    # Planning Applications
    # If any specific planning argument is specified, we only run that specific task.
    # Otherwise, if --planning-applications or run_all, we run the general planning applications update.
    if args.update_weekly_planning:
        print('Updating weekly planning application files...')
        planning_applications(interactive=interactive, run_weekly_only=True)
    elif args.update_annual_planning:
        print('Updating annual planning application files...')
        planning_applications(interactive=interactive, run_annual_only=True)
    elif args.planning_applications or run_all:
        print('Updating Planning Applications data...')
        # Default behavior for planning_applications()
        planning_applications(interactive=interactive)

    # OpenStreetMap
    # If --generate-postcode-boundaries is specified, we only run that specific task.
    # Otherwise, if --openstreetmap or run_all, we run the general openstreetmap update.
    if args.generate_postcode_boundaries:
        print('Generating postcode boundaries...')
        openstreetmap(interactive=interactive, run_postcode_boundaries_only=True)
    elif args.openstreetmap or run_all:
        print('Updating OpenStreetMap data...')
        # Default behavior for openstreetmap()
        openstreetmap(interactive=interactive)

    # Global ML Building Footprints
    if args.global_ml_building_footprints or run_all:
        print('Updating Global ML Building Footprints data...')
        global_ml_building_footprints(interactive=interactive)

    print('Update complete.')
