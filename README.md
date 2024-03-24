# Isle of Man Opendata

This project aims to take open geographic data for the Isle of Man and create new data products from it.

## Opendata providers

* [Isle of Man Government](https://www.gov.im/about-the-government/government/open-data/)
  * [Land transactions](https://www.gov.im/about-the-government/government/open-data/economy/land-transactions/)
  * [Planning applications](https://www.gov.im/about-the-government/government/open-data/energy-and-environment/planning-application-data/)

## Outputs

* Land transactions
  * Land transactions (with hash, partially cleansed with corrections)
  * Addressing (ignoring known issues)
    * Places - parishes, towns, localities
    * Streets
    * Postcodes
  * Issues noted during processing (with hash of transaction)

## Known issues

* *Data quality* - addressing data is often messy, with information ending up in the wrong columns, and this dataset is no different
* *Incomplete data* - addressing data is incomplete as it's based on where land transactions have taken place since the process was digitised

## TODO

* License options

## Fixing issues

1. Copy row from `data/outputs/gov.im/land-transactions/issue-rows.csv` and paste into `data/source/gov.im/land-transactions/corrections/rows.csv` then update any fields necessary.

## Other resources

* [Humanitarian Data Exchange (HDX)](https://data.humdata.org)
  * [Isle of Man datasets](https://data.humdata.org/group/imn)
* [OpenStreetMap](https://www.openstreetmap.org)
  * [Isle of Man OpenStreetMap exports (Geofabrik)](https://download.geofabrik.de/europe/isle-of-man.html)

## License

Contains public sector information licensed under the [Isle of Man Open Government Licence](https://www.gov.im/about-this-site/open-government-licence/)