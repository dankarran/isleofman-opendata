# Isle of Man open data

This project aims to take open geographic data for the Isle of Man and create new data products from it.

## Open data providers

* [Isle of Man Government](https://www.gov.im/about-the-government/government/open-data/)
  * [Land transactions](https://www.gov.im/about-the-government/government/open-data/economy/land-transactions/)
  * [Planning applications](https://www.gov.im/about-the-government/government/open-data/energy-and-environment/planning-application-data/)
* [OpenStreetMap](https://www.openstreetmap.org)

## Outputs

* Land transactions
  * Land transactions (with hash, partially cleansed with corrections)
  * Addressing (ignoring known issues)
    * Places - parishes, towns, localities
    * Streets
    * Postcodes
  * Issues noted during processing (with hash of transaction)
* Planning applications
  * Planning applications
  * Delegated decisions
  * Appeals
  * Addressing
    * Postcodes
* OpenStreetMap
  * Various datasets

## Known issues

* *Data quality* - addressing data is often messy, with information ending up in the wrong columns, and this dataset is no different
* *Incomplete data* - addressing data is incomplete as it's based on where land transactions have taken place since the process was digitised

## TODO

* License options

## Fixing issues

To fix issues in land transactions, copy row from `data/outputs/gov.im/land-transactions/issue-rows.csv` and paste 
into `data/source/gov.im/land-transactions/corrections/rows.csv` then update any fields necessary.

## Updating data

To update the data, run `python update.py` and enter `y` for each dataset you'd like to re-download from the original 
source.

For Isle of Man Government data, you will need to update the URL if there are new files available. This can be updated 
in the relevant `sources.json` file. 

## Other resources

* [Humanitarian Data Exchange (HDX)](https://data.humdata.org)
  * [Isle of Man datasets](https://data.humdata.org/group/imn)
* [OpenStreetMap](https://www.openstreetmap.org)
  * [Isle of Man OpenStreetMap exports (Geofabrik)](https://download.geofabrik.de/europe/isle-of-man.html)

## License

* Contains public sector information licensed under the [Isle of Man Open Government Licence](https://www.gov.im/about-this-site/open-government-licence/)
* Contains data from [OpenStreetMap](https://www.openstreetmap.org) licensed under the [Open Database License](https://www.openstreetmap.org/copyright).