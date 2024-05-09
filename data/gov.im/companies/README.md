# Isle of Man Companies Registry

Information about companies registered on the Isle of Man.

## Datasets

  * Live companies index :spiral_notepad: [CSV](https://github.com/dankarran/isleofman-opendata/blob/main/data/gov.im/companies/outputs/companies-live.csv)
  * Non-live companies index :spiral_notepad: [CSV](https://github.com/dankarran/isleofman-opendata/blob/main/data/gov.im/companies/outputs/companies-non-live.csv)
  * Old company names index :spiral_notepad: [CSV](https://github.com/dankarran/isleofman-opendata/blob/main/data/gov.im/companies/outputs/old-names.csv)
  * Registries :spiral_notepad: [CSV](https://github.com/dankarran/isleofman-opendata/blob/main/data/gov.im/companies/outputs/registries.csv)

## Open data provider

  * [Isle of Man Government](https://www.gov.im/about-the-government/government/open-data/)
    * [Companies Registry](https://www.gov.im/about-the-government/departments/enterprise/central-registry/companies-registry/)

## Known issues

  * *Incomplete data* - there isn't a consolidated published list, so the list here is based on searching using common terms and then any companies missing from the sequence. Some companies may fall through the net.

## Data retrieval

The Companies Registry doesn't currently publish a complete list of companies, though they note they may look into this in the future.

The companies index is built up by searching for common terms in the Companies Registry which should cover the majority 
of company names. Any company numbers in the sequence that haven't been seen are then searched for using company number.

Current search terms:
  * *L* (includes Ltd, Limited, LLC, PLC, LP, etc.)
  * *INC*
  * *FOUNDATION*
  * *PARTNER*
  * *CORP*
  * *A*, *E*, *I*, *O*, *U*

## Other resources

  * [Company search](https://services.gov.im/ded/services/companiesregistry/welcome.iom)
  * [General statistics report](https://app.powerbi.com/view?r=eyJrIjoiZWU4NzI5MGUtMGUxYS00ZDVkLThkYmYtNjFhMzU5ZGQ2N2EzIiwidCI6IjM5YzAwODM2LWVkMTItNDhkYS05Yjk3LTU5NGQ4MDhmMDNlNSIsImMiOjl9)
  * [Public Records Office - registered dissolved company files](https://archives.gov.im/TreeBrowse.aspx?src=CalmView.Catalog&field=RefNo&key=S2)

## License

Contains public sector information licensed under the [Isle of Man Open Government Licence](https://www.gov.im/about-this-site/open-government-licence/).
