# Isle of Man Land Transactions data

Information about land transactions from ~2001 onwards, including address and pricing details.

## Datasets

  * Land transactions (with hash, partially cleansed with corrections) :spiral_notepad: [CSV](https://github.com/dankarran/isleofman-opendata/blob/main/data/gov.im/land-transactions/outputs/land-transactions.csv)
  * Addressing (some known issues filtered out)
    * Addresses (unfiltered) :spiral_notepad: [CSV](https://github.com/dankarran/isleofman-opendata/blob/main/data/gov.im/land-transactions/outputs/addressing/addresses.csv)
    * Streets :spiral_notepad: [CSV](https://github.com/dankarran/isleofman-opendata/blob/main/data/gov.im/land-transactions/outputs/addressing/streets.csv)
    * Localities :spiral_notepad: [CSV](https://github.com/dankarran/isleofman-opendata/blob/main/data/gov.im/land-transactions/outputs/addressing/localities.csv)
    * Towns :spiral_notepad: [CSV](https://github.com/dankarran/isleofman-opendata/blob/main/data/gov.im/land-transactions/outputs/addressing/towns.csv)
    * Postcodes :spiral_notepad: [CSV](https://github.com/dankarran/isleofman-opendata/blob/main/data/gov.im/land-transactions/outputs/addressing/postcodes.csv)
    * Parishes :spiral_notepad: [CSV](https://github.com/dankarran/isleofman-opendata/blob/main/data/gov.im/land-transactions/outputs/addressing/parishes.csv)
  * Issues noted during processing (with hash of transaction) :spiral_notepad: [CSV](https://github.com/dankarran/isleofman-opendata/blob/main/data/gov.im/land-transactions/outputs/issues.csv)

## Open data provider

  * [Isle of Man Government](https://www.gov.im/about-the-government/government/open-data/)
    * [Land transactions](https://www.gov.im/about-the-government/government/open-data/economy/land-transactions/)

## Known issues

  * *Data quality* - addressing data is often messy, with information ending up in the wrong columns, and this dataset is no different
  * *Incomplete data* - addressing data is incomplete as it's based on where land transactions have taken place since the process began to be digitised

## Fixing issues

To fix issues in land transactions, copy row from [outputs/issue-rows.csv](https://github.com/dankarran/isleofman-opendata/blob/main/data/gov.im/land-transactions/outputs/issue-rows.csv) and paste 
into [sources/corrections/rows.csv](https://github.com/dankarran/isleofman-opendata/blob/main/data/gov.im/land-transactions/sources/corrections/rows.csv) then update any fields necessary.

## Updating data

Before running the `update.py` script, you will need to update the land transactions source URL if there is a new file
available. This can be updated in the [sources/sources.json](https://github.com/dankarran/isleofman-opendata/blob/main/data/gov.im/land-transactions/sources/sources.json) file. 

## License

Contains public sector information licensed under the [Isle of Man Open Government Licence](https://www.gov.im/about-this-site/open-government-licence/).
