# Kenya County Flood Risk Early Warning

Moringa School Data Science capstone (DSF-PT15, Group 6), October to November 2026.

**Goal:** predict which of Kenya's 47 counties are likely to flood in the **coming month**, using conditions observed in the month before: rainfall, soil moisture, vegetation, ocean climate signals and each county's terrain.

**Team:** Fadhili, Mokeira, Frasiah, Myles

**This repository is the data, cleaning and exploration part** (EDA). The models, the monthly forecast job and the Streamlit app are in the second repository: [ElNinoEngine](https://github.com/Fadhili-22/ElNinoEngine) (private).

## Status

| Stage | Status |
|---|---|
| Data collection and audit | Done (22 Oct 2026) |
| County-month modelling table (47 counties x 2000-2025) | Done (`python src/data/build_model_table.py` rebuilds it; public and private versions) |
| Combining notebooks (`notebooks/1_combining_datasets`) and EDA notebooks (`notebooks/2_eda`) | Done and run top to bottom; the EDA ends with `data/processed/selected_features.csv` |
| Models (logistic regression, decision tree, random forest, XGBoost), monthly forecast and Streamlit app | Done, in the [ElNinoEngine](https://github.com/Fadhili-22/ElNinoEngine) repository |

## How it works

1. Build one table with a row per county per month, January 2000 to December 2025 (47 x 312 = 14,664 rows).
2. Each row holds that month's conditions and a label: did the county flood the **following** month?
3. Train on 2002-07 to 2019-12, test on 2020-2024 (plus rolling backtests), and report precision, recall and PR-AUC rather than accuracy, since floods are rare. See the agreed decisions below.
4. Show the coming month's risk per county in an app (in the ElNinoEngine repository).

Flood labels combine four sources, because no single record catches every Kenyan flood: DesInventar, EM-DAT, the Global Flood Database and the Dartmouth Flood Observatory. A second target, "next month's rain above 125% of normal", is built for comparison because flood reporting is uneven over time.

## Agreed modelling decisions (2 Nov 2026)

- **Target:** `flood_next_month` from the **full label** (DesInventar, EM-DAT, Global Flood Database, DFO combined). The public table (no EM-DAT) is for sharing only; its test years are almost empty of floods.
- **Rows:** modelling starts at **2002-07**, when NDVI begins (earlier rows have blank NDVI and almost no flood labels).
- **Split:** train 2002-07 to 2019-12, test **2020-2024**, reported separately from the training era because the mix of label sources changes after 2018 (the test years rely mostly on EM-DAT). **2025 is excluded** from scoring: its flood labels are almost empty.
- **Baseline to beat:** persistence ("it flooded this month, so it will flood next month"). Floods last across months, so this baseline is far better than chance. `flood_this_month` is therefore a baseline, not a feature.
- **Never features:** `flood_this_month` and every other label or source column, `desinventar_no_record_year` (it marks missing label coverage, not climate) and `heavy_rain_next_month` (a comparison target built from next month's rain).
- **`county_flood_rate`** uses labels up to 2019 on every row, so it must be recomputed inside each training fold.
- **Feature analysis uses training rows only**, so the test years stay unseen.
- **Rainfall limitation:** the WFP sub-county rows put some sub-counties under the wrong county (Kiambu / Murang'a, Kericho / Bomet). Their rainfall, and `neighbour_rain` of 16 neighbouring counties, is mixed. It is reported as a limitation, not fixed.

## Repository layout

```
data/
  README.md            what every file is and its coverage
  DATA_DICTIONARY.md   every column of the model table
  raw/                 original downloads, never edited
    rainfall/            CHIRPS rainfall per county (10-day)
    ndvi/                vegetation greenness per county (10-day)
    climate_indices/     ONI (El Nino) and DMI (Indian Ocean Dipole), monthly
    flood_labels/        EM-DAT (not in git, see below), DesInventar, DFO, Global Flood Database
    earth_engine/        soil moisture, runoff, elevation, slope, land cover, rivers, built-up area
      scripts/             the Google Earth Engine scripts that produced them
    glofas/              GloFAS river discharge, one .nc per year (not in git)
    population/          KNBS population and land area per county
    boundaries/          county polygons
  reference/           county code crosswalk (join key: pcode KE001-KE047), county map, adjacency, DFO place lookup
  processed/           cleaned files and the public model table (model_table_public.csv)
  interim/             build intermediates (git-ignored, created by the build)
  private/             full model table with EM-DAT columns and full build report (git-ignored, created by the build)
src/data/            the build pipeline (stages 00-13), run with python src/data/build_model_table.py
notebooks/
  1_combining_datasets/  four notebooks that rebuild the merge step by step in plain pandas
  2_eda/                 four notebooks: data quality and target, rain/vegetation/climate, soil/rivers/land, feature overlap and selection
  archive/               earlier notebooks kept for the record
docs/
  PIPELINE_EXPLAINED.md  long guide to how the pipeline works
  AUDIT_REPORT.md        integrity and content checks on the raw files (22 Oct 2026)
```

Start with the notebooks, in this order:

1. `notebooks/1_combining_datasets/` : `01_grid_and_county_keys`, `02_rainfall_vegetation_climate`, `03_land_soil_and_rivers`, `04_flood_labels_and_final_table`
2. `notebooks/2_eda/` : `01_data_quality_and_target`, `02_rain_vegetation_climate_vs_target`, `03_soil_rivers_land_vs_target`, `04_feature_overlap_and_selection`

For the background read `data/README.md` and `docs/PIPELINE_EXPLAINED.md`. Run `python src/data/build_model_table.py` first so that `data/interim/` and `data/private/` exist. The notebooks use the `flood` conda environment (kernel "Python (flood)") and `requirements.txt`.

## EM-DAT data is not included

EM-DAT's [terms of use](https://doc.emdat.be/docs/legal/terms-of-use/) do not allow redistributing its data or databases derived from it. To reproduce the full flood labels:

1. Create a free account at [public.emdat.be](https://public.emdat.be/).
2. Make a custom request (Region: Africa, Disaster type: Flood, all years).
3. Save it as `data/raw/flood_labels/emdat/public_emdat_custom_request_2026-10-20.xlsx`.

The full modelling table, which contains EM-DAT-derived columns, stays in `data/private/` and is never committed. The public version without EM-DAT columns is `data/processed/model_table_public.csv`.

**Running the notebooks:** the combining notebooks need only the public files. The EDA notebooks (`notebooks/2_eda`) and the last combining notebook read `data/private/model_table_full.csv`, so they need your own EM-DAT download and a run of `python src/data/build_model_table.py` first. Their saved outputs are kept in the notebooks, and they print only counts and rates, never EM-DAT records.

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
