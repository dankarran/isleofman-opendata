# Isle of Man Companies Registry

Information about companies registered on the Isle of Man.

## Datasets

(Incomplete, work in progress...)

  * Live companies index :spiral_notepad: [CSV](https://github.com/dankarran/isleofman-opendata/blob/main/data/gov.im/companies/outputs/companies-live.csv)
  * Non-live companies index :spiral_notepad: [CSV](https://github.com/dankarran/isleofman-opendata/blob/main/data/gov.im/companies/outputs/companies-non-live.csv)
  * Old company names index :spiral_notepad: [CSV](https://github.com/dankarran/isleofman-opendata/blob/main/data/gov.im/companies/outputs/old-names.csv)
  * Registries :spiral_notepad: [CSV](https://github.com/dankarran/isleofman-opendata/blob/main/data/gov.im/companies/outputs/registries.csv)

## Open data provider

  * [Isle of Man Government](https://www.gov.im/about-the-government/government/open-data/)
    * [Companies Registry](https://www.gov.im/about-the-government/departments/enterprise/central-registry/companies-registry/)

## Known issues

  * *Incomplete data* - there isn't a consolidated published list, so the list here is based on searching using common terms and combining them. Some companies may fall through the net.

## Data retrieval

The companies index is built up by searching for common terms in the Companies Registry which should cover the majority of company names.

Current search terms:
  * *L* (includes Ltd, Limited, LLC, PLC, LP, etc.)
  * *INC*
  * *FOUNDATION*
  * *PARTNER*
  * *CORP*
  * *A*, *E*, *I*, *O*, *U*

TODO:
  * consider most effective and efficient way of covering company names that aren't captured 
    * numbers, all letters
    * searching for company numbers missing from sequence
    * requesting a complete list from the Companies Registry, ideally including details that would otherwise require crawling individual company pages

## Other resources

  * [Company search](https://services.gov.im/ded/services/companiesregistry/welcome.iom)
  * [General statistics report](https://app.powerbi.com/view?r=eyJrIjoiZWU4NzI5MGUtMGUxYS00ZDVkLThkYmYtNjFhMzU5ZGQ2N2EzIiwidCI6IjM5YzAwODM2LWVkMTItNDhkYS05Yjk3LTU5NGQ4MDhmMDNlNSIsImMiOjl9)

## License

Contains public sector information licensed under the [Isle of Man Open Government Licence](https://www.gov.im/about-this-site/open-government-licence/).
