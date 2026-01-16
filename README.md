# Isle of Man open data

This project aims to take open data for the Isle of Man and create new data products from it.

## Datasets

  * :file_folder: [Companies](https://github.com/dankarran/isleofman-opendata/tree/main/data/gov.im/companies/)
  * :file_folder: [Land transactions](https://github.com/dankarran/isleofman-opendata/tree/main/data/gov.im/land-transactions/)
  * :file_folder: [Planning applications](https://github.com/dankarran/isleofman-opendata/tree/main/data/gov.im/planning-applications/)
  * :file_folder: [Registered Buildings](https://github.com/dankarran/isleofman-opendata/tree/main/data/gov.im/registered-buildings/)
  * :file_folder: [OpenStreetMap](https://github.com/dankarran/isleofman-opendata/tree/main/data/openstreetmap/)
  * :file_folder: [Microsoft Global ML Building Footprints](https://github.com/dankarran/isleofman-opendata/tree/main/data/microsoft/global-ml-building-footprints/)

See individual README files in relevant part of `data` directory for further details.

## Open data providers

  * [Isle of Man Government](https://www.gov.im/about-the-government/government/open-data/)
  * [OpenStreetMap](https://www.openstreetmap.org/#map=10/54.2283/-4.5792)
  * [Microsoft](https://github.com/microsoft/GlobalMLBuildingFootprints)

## TODO

  * License options
    * No additional rights claimed on data beyond original license
    * Code probably opensource MIT license

## Updating data

The update script (`update.py`) can be run in two modes: interactive or argument-driven.

### Interactive Mode

To run in interactive mode, which will prompt you for each major data category, simply run the script without any arguments:

```bash
python update.py
```

The script will ask whether you want to update each dataset (Companies, Land Transactions, etc.).

### Argument-driven Mode

To run specific updates without interactive prompts, you can use command-line arguments. This is useful for automated or targeted updates. Providing any argument will disable interactive mode.

**General dataset updates:**

*   `--companies`: Run the full Companies Registry update.
*   `--land-transactions`: Run the Land Transactions update.
*   `--planning-applications`: Run the full Planning Applications update.
*   `--openstreetmap`: Run the full OpenStreetMap update.
*   `--global-ml-building-footprints`: Run the Global ML Building Footprints update.

**Granular task updates:**

*   `--companies-unindexed`: Run only the unindexed company number search.
*   `--update-weekly-planning`: Run only the weekly planning application list update.
*   `--update-annual-planning`: Run only the annual planning application list update.
*   `--generate-postcode-boundaries`: Run only the postcode boundary generation from OpenStreetMap data.
*   `--openstreetmap-markdown`: Run only the OpenStreetMap markdown generation.

You can combine multiple arguments. For example, to run a weekly/monthly update:

```bash
python update.py --companies --companies-unindexed --land-transactions --openstreetmap --generate-postcode-boundaries
```

## Other resources

  * [Humanitarian Data Exchange (HDX)](https://data.humdata.org)
    * [Isle of Man datasets](https://data.humdata.org/group/imn)
  * [Traveline National Dataset (TNDS)](https://www.travelinedata.org.uk/traveline-open-data/traveline-national-dataset/) - bus timetable data

## License

  * Contains public sector information licensed under the [Isle of Man Open Government Licence](https://www.gov.im/about-this-site/open-government-licence/).
  * Contains data from [OpenStreetMap](https://www.openstreetmap.org/#map=10/54.2283/-4.5792) licensed under the [Open Database License](https://www.openstreetmap.org/copyright).
  * Contains data from Microsoft licensed under the Open Data Commons [Open Database License](https://opendatacommons.org/licenses/odbl/) (ODbL).