# Commodity and Macro Data Sources

Reference sheet for external data feeds that could power future indicators and dashboards. No pipelines are wired yet; this is scoping only.

## Future dashboard concepts
- Commodity Indicator (broad supply/demand and positioning context)
- Fuel Indicator (oil and gas inventories plus short/medium-term trend)
- Agriculture Indicator (crop progress, yield, exports)
- Macro Overlay (rates, USD, inflation versus commodities)

## Source assessment
| Source Name | URL | Data Type | Access Method (API / CSV / scrape / manual) | Auth Required (Yes/No) | Update Frequency | Ease of Ingestion (Easy / Moderate / Hard) | Status (Not Tried / Tested / Ingested) | Notes / Constraints |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| World Bank / IMF commodity data | https://www.worldbank.org/en/research/commodity-markets | Commodity prices (macro) | API or CSV downloads via World Bank open data; IMF series via CSV/Excel | No | Monthly | Moderate | Not Tried | World Bank “Pink Sheet” offers open CSV/API; IMF series terms allow research use but review attribution requirements; schema changes periodically. |
| CFTC Commitments of Traders (COT) | https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm | Positioning | CSV/Excel files; HTML summary pages | No | Weekly (published Friday for Tuesday data) | Moderate | Not Tried | Public CSVs zipped by market category; occasional format updates; need contract code mapping for consistent symbols. |
| FRED (St. Louis Fed) | https://fred.stlouisfed.org/ | Macro rates, FX, CPI, commodities | API or CSV | Yes (free API key) | Daily/Weekly/Monthly (series dependent) | Easy | Not Tried | Stable JSON/CSV API with per-key rate limits; wide library of macro drivers and some commodity series. |
| CME Group public pages | https://www.cmegroup.com/ | Futures quotes, settlements, volumes | HTML pages; limited CSV on product pages | No | Daily (settlements) / Intraday (quotes) | Hard | Not Tried | No official free API; scraping subject to terms of use and robots rules; data licensing may be required for systematic use. |
| USDA NASS QuickStats | https://quickstats.nass.usda.gov/ | Agriculture (acreage, yields, progress) | API or CSV extracts | Yes (API key) | Weekly/Seasonal/Annual (by series) | Moderate | Not Tried | API enforces query size/time limits; datasets can be large—may need paging and caching; metadata lookup required to frame queries. |
| EIA Open Data | https://www.eia.gov/opendata/ | Energy (inventories, production, prices) | API or CSV | Yes (API key) | Weekly/Daily (series dependent) | Easy | Not Tried | JSON API with straightforward series codes; rate limits apply; some historical revisions require periodic backfill. |

## Output expectations
- Modify only files you create.
- Keep tone technical and neutral.
- Assume this will later feed an AWS-based pipeline and dashboard.
- Write clean Markdown suitable for a real engineering repo.
