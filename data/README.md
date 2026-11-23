# Data folder: Kenya County Flood Risk Early Warning (Group 6)

Last updated 2 Nov 2026. How the files are turned into the county-month table is explained in `../docs/PIPELINE_EXPLAINED.md`; the column-by-column description is in `DATA_DICTIONARY.md`.

Join key for everything is `pcode` (KE001-KE047). Files that use `COUNTYCO` or `county_code` (DesInventar alphabetical codes) are mapped to `pcode` with `reference/kenya_county_crosswalk.csv` (`desinventar_code`). Always read code columns with `dtype=str` (DesInventar code `06` must not become `6`).

**WFP rainfall and NDVI files (changed 1 Nov 2026):** only the `adm_level` 2 rows are used, for all 47 counties. They are grouped by the first 5 characters of `PCODE` and combined as an `n_pixels`-weighted mean. The `adm_level` 1 rows (KE004, KE008, KE010, KE019, KE023, KE037, KE043, KE047) are former provinces that reuse a county code. For example, KE023 covers ~172,600 km2 (Rift Valley), not Turkana's 68,111 km2. So they are dropped. The previous rule used them for those 8 counties and gave them province rainfall.

**Known limitation of the WFP level-2 rows:** a few sub-counties sit under the wrong county, so the rainfall of Kiambu / Murang'a and of Kericho / Bomet is mixed. Judged by `n_pixels`, the rainfall of Kiambu covers about 51% of its area, Murang'a about 145%, Kericho about 82% and Bomet about 120%. This also feeds `neighbour_rain` of 16 other counties. It is not fixed; it is reported as a limitation.

## What is committed and what is rebuilt
- `raw/`, `reference/`, `processed/` are in git, except the EM-DAT file and the GloFAS `.nc` files (see below).
- `interim/` (build intermediates) and `private/` (the full modelling table with EM-DAT-derived columns, the full build report, the EM-DAT place lookup) do not exist in a fresh clone. They are created by `python src/data/build_model_table.py` and are git-ignored.

## raw/  (original downloads, never edit these)
| Folder | File | Role | Coverage |
|---|---|---|---|
| rainfall | ken-rainfall-subnat-full.csv | Main input: CHIRPS 10-day rainfall + anomalies (WFP/HDX). Use adm_level 2 rows only | 1981-01 to 2026-10, all 47 counties |
| ndvi | ken-ndvi-subnat-full.csv | Input: vegetation greenness. Use adm_level 2 rows only | 2002-07 to 2026-09 |
| climate_indices | oni.csv | Input: El Nino index (NOAA PSL). Missing = -9999. The pipeline shifts it back one month | 1950 to 2026-07 |
| climate_indices | dmi_ersstv6.txt | Input: Indian Ocean Dipole index (ERSSTv6), 13 header lines | 1950 to 2026-08 |
| flood_labels/emdat | public_emdat_custom_request_2026-10-20.xlsx | Label: large floods; filter ISO=KEN, Disaster Type=Flood. NOT in git | 2000 to 2026 (56 Kenyan floods) |
| flood_labels/desinventar | DI_Crosstab_floods_county_yearmonth.xls | Label: national flood records, county x year/month (753 records). Reading it needs `xlrd` | 2002 to 2025 |
| flood_labels/dfo_master_list | wlf_nhr_fl_dfomasterlist_20190418.dbf | Label: Dartmouth Flood Observatory events (free-text locations) | 1988 to 2010 (41 Kenyan floods) |
| flood_labels/global_flood_database | kenya_gfd_county_floods.csv | Label: satellite flood area per event per county (GEE export) | 2002 to 2018 (33 floods) |
| boundaries/cod_ab | kenya_counties_cod_land.* (and ken_admin1.*) | County polygons used by the pipeline: OCHA COD-AB admin-1 with Lakes Victoria, Turkana and Natron removed (stage 00). The other COD-AB layers are git-ignored | 47 counties |
| boundaries | lev_0.shp / .shx / .dbf | Old DesInventar county polygons (DesInventar codes). Only used by the legacy non-`_cod` Earth Engine files | 47 counties |
| boundaries/natural_earth_lakes | ne_10m_lakes.* | Lake outlines used to cut the lakes out of the county polygons | |
| earth_engine | era5land_soil_runoff_county_month_cod.csv | Input: soil moisture + runoff (ERA5-Land). Use runoff only as a within-county rank | 1999-10 to 2025-12 |
| earth_engine | era5land_precip_county_month.csv | Diagnostic only: ERA5 rainfall (legacy polygons, metres), shows why ERA5 runoff is inflated | 1999-10 to 2025-12 |
| earth_engine | srtm_elevation_slope_county_cod.csv | Input (static): elevation, slope, share of flat land | 47 counties |
| earth_engine | worldcover_landcover_county_cod.csv | Input (static): land-cover shares + county area | 2021 snapshot |
| earth_engine | proximity_rivers_water_county_cod.csv | Input (static): share of county near major rivers / water. Drop the two *_dist_m columns | 47 counties |
| earth_engine | ghsl_builtup_county_5yr_cod.csv | Input: built-up share every 5 years (interpolated to months) | 2000 to 2025 |
| earth_engine | the same files without `_cod` | Earlier exports on the old DesInventar polygons; used only if the `_cod` file is missing | |
| earth_engine/scripts | 00-07 *.js | The Earth Engine scripts that produced these files (`*_cod.js` = the ones in use; `07_worldpop_NOT_USED.js` was rejected) | |
| population | county_year_population.csv | Input: KNBS population series per county 2000-2025 (extrapolated from the 2019 census) and KNBS land area. Only the 2019 rows are used | 47 counties |
| glofas | glofas_kenya_1999.nc ... 2025.nc (27 files) | Input: GloFAS v4.0 daily river discharge. NOT in git (about 240 MB); see `glofas/README.md` | 1999-01 to 2025-12 |

## reference/
- kenya_county_crosswalk.csv: links official county codes (pcode KE001-KE047), DesInventar codes and name spellings.
- kenya_counties.geojson: land-only county polygons with pcode (lakes removed), for maps and the GloFAS cell lookup.
- kenya_counties_full.geojson: the same counties without the lake cut, for the dashboard map only.
- county_adjacency.csv: pairs of neighbouring counties (244 directed pairs, 122 borders) for `neighbour_rain`.
- place_to_county.csv: the confirmed DFO free-text place to county lookup (public; the EM-DAT lookup is private).

## processed/
- model_table_public.csv: the county-month table without EM-DAT columns (14,664 rows x 64 columns). Shareable.
- build_report.md: PASS/FAIL checks and label statistics for the public table.
- desinventar_floods_county_month.csv: DesInventar crosstab reshaped to one row per flooded county-month (333 rows). Notebook `1_combining_datasets/04_...` reproduces it from the raw `.xls`.
- desinventar_floods_with_pcode_and_date.csv: the same with a date column, written by the archived flood-history notebook.
- climate_indices_month.csv: ONI and DMI as published, written by the archived climate notebook. The pipeline does not read it.
- era5_vs_chirps_by_county.csv: per-county comparison of ERA5 vs CHIRPS rainfall, 2000-2025. Made before the 1 Nov province-row fix, so the `chirps` column is out of date for 7 counties (Turkana, Tana River, Marsabit, Homa Bay, Kakamega, Wajir, Nyeri).
- selected_features.csv: feature names kept after the EDA (written by `notebooks/2_eda/04_...`).
