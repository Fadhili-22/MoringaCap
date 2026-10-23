# Kenya County Flood Risk Early Warning

Moringa School Data Science capstone (DSF-PT15, Group 6), October to November 2026.

**Goal:** predict which of Kenya's 47 counties are likely to flood **next month**, using conditions observed this month: rainfall, soil moisture, vegetation, ocean climate signals and each county's terrain.

**Team:**  Fadhili, Mokeira, Frasiah, Myles

## Status

| Stage | Status |
|---|---|
| Data collection and audit | Done (22 Oct 2026) |
| County-month modelling table (47 counties x 2000-2025) | In progress |
| Models (logistic regression, random forest, XGBoost) | Not started |
| Streamlit dashboard (county risk map) | Not started |

## How it works

1. Build one table with a row per county per month, January 2000 to December 2025 (47 x 312 = 14,664 rows).
2. Each row holds that month's conditions and a label: did the county flood the **following** month?
3. Train on 2000-2019, test on 2020-2025 (plus rolling backtests), and report precision, recall and PR-AUC rather than accuracy, since floods are rare.
4. Show next month's risk per county on a map.

Flood labels combine four sources, because no single record catches every Kenyan flood: DesInventar, EM-DAT, the Global Flood Database and the Dartmouth Flood Observatory. A second target, "next month's rain above 125% of normal", is built for comparison because flood reporting is uneven over time.

## Repository layout

```
data/
  README.md          what every file is and its coverage
  DATA_NOTES.md      decisions, cleaning rules, planned columns and merge plan
  AUDIT_REPORT.md    integrity and content checks on every file (22 Oct 2026)
  raw/               original downloads, never edited
    rainfall/          CHIRPS rainfall per county (10-day)
    ndvi/              vegetation greenness per county (10-day)
    climate_indices/   ONI (El Nino) and DMI (Indian Ocean Dipole), monthly
    flood_labels/      EM-DAT (not included, see below), DesInventar, DFO, Global Flood Database
    earth_engine/      soil moisture, runoff, elevation, slope, land cover, rivers, built-up area
      scripts/           the Google Earth Engine scripts that produced them
    boundaries/        county polygons
  reference/         county code crosswalk (join key: pcode KE001-KE047) and county map
  processed/         cleaned intermediate files
  private/           team-only outputs, git-ignored
  _not_used/         files checked and rejected, kept for the record
```

Start with `data/README.md` and `data/DATA_NOTES.md`.

## EM-DAT data is not included

EM-DAT's [terms of use](https://doc.emdat.be/docs/legal/terms-of-use/) do not allow redistributing its data or databases derived from it. To reproduce the full flood labels:

1. Create a free account at [public.emdat.be](https://public.emdat.be/).
2. Make a custom request (Region: Africa, Disaster type: Flood, all years).
3. Save it as `data/raw/flood_labels/emdat/public_emdat_custom_request_2026-10-20.xlsx`.

The full modelling table, which contains EM-DAT-derived columns, stays in `data/private/`. A public version without EM-DAT columns will be published in `data/processed/`.

## Data sources

| Data | Source |
|---|---|
| Rainfall (CHIRPS, subnational) | WFP via [Humanitarian Data Exchange](https://data.humdata.org/dataset/ken-rainfall-subnational) |
| Vegetation (NDVI, subnational) | WFP via [Humanitarian Data Exchange](https://data.humdata.org/dataset/ken-ndvi-subnational) |
| Oceanic Nino Index | [NOAA Physical Sciences Laboratory](https://psl.noaa.gov/data/timeseries/month/DS/ONI/) |
| Dipole Mode Index | [NOAA Physical Sciences Laboratory](https://psl.noaa.gov/data/timeseries/month/DS/DMI/) (ERSSTv6) |
| Flood records | [DesInventar](https://www.desinventar.net/) (Kenya) |
| Major disasters | [EM-DAT](https://www.emdat.be/), CRED / UCLouvain |
| Satellite-mapped floods | [Global Flood Database](https://developers.google.com/earth-engine/datasets/catalog/GLOBAL_FLOOD_DB_MODIS_EVENTS_V1) (Cloud to Street) |
| Flood event list | [Dartmouth Flood Observatory](https://floodobservatory.colorado.edu/) |
| Soil moisture, runoff | [ERA5-Land monthly](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_MONTHLY_AGGR) (Copernicus / ECMWF) |
| Elevation, slope | [SRTM 30 m](https://developers.google.com/earth-engine/datasets/catalog/USGS_SRTMGL1_003) (NASA / USGS) |
| Land cover | [ESA WorldCover 2021](https://developers.google.com/earth-engine/datasets/catalog/ESA_WorldCover_v200) |
| Rivers | [HydroSHEDS Free Flowing Rivers](https://developers.google.com/earth-engine/datasets/catalog/WWF_HydroSHEDS_v1_FreeFlowingRivers) (WWF) |
| Surface water | [JRC Global Surface Water](https://developers.google.com/earth-engine/datasets/catalog/JRC_GSW1_4_GlobalSurfaceWater) |
| Built-up area | [GHSL Built-up Surface](https://developers.google.com/earth-engine/datasets/catalog/JRC_GHSL_P2023A_GHS_BUILT_S) (European Commission JRC) |

All data belongs to its providers; please cite each source according to its own terms.

## Known limitations

- Flood reporting is uneven: DesInventar has no records for 2004 and 2017-2019, and the Global Flood Database ends in 2018, so the test years rely more on EM-DAT, which only records large disasters.
- ERA5-Land overestimates rainfall in the western highlands (up to 2.7x CHIRPS in Elgeyo-Marakwet), so runoff is used only relative to each county's own history.
- A flood anywhere in a large county (e.g. Turkana) labels the whole county as flooded.
