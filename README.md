# Isle of Man open data

This project aims to take open geographic data for the Isle of Man and create new data products from it.

## Open data providers

* [Isle of Man Government](https://www.gov.im/about-the-government/government/open-data/)
* [OpenStreetMap](https://www.openstreetmap.org/#map=10/54.2283/-4.5792)

## Datasets

* :file_folder: [Land transactions](https://github.com/dankarran/isleofman-opendata/tree/main/data/gov.im/land-transactions/)
* :file_folder: [Planning applications](https://github.com/dankarran/isleofman-opendata/tree/main/data/gov.im/planning-applications/)
* :file_folder: [OpenStreetMap](https://github.com/dankarran/isleofman-opendata/tree/main/data/openstreetmap/)

See individual README files in relevant part of `data` directory for further details.

## TODO

* License options
  * No additional rights claimed on data beyond original license
  * Code probably opensource MIT license

## Updating data

To update the data, run `python update.py` and enter `y` for each dataset you'd like to re-download from the original 
source.

## Other resources

* [Humanitarian Data Exchange (HDX)](https://data.humdata.org)
  * [Isle of Man datasets](https://data.humdata.org/group/imn)

## License

* Contains public sector information licensed under the [Isle of Man Open Government Licence](https://www.gov.im/about-this-site/open-government-licence/).
* Contains data from [OpenStreetMap](https://www.openstreetmap.org/#map=10/54.2283/-4.5792) licensed under the [Open Database License](https://www.openstreetmap.org/copyright).