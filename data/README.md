# Data folder: Kenya County Flood Risk Early Warning (Group 6)

Last updated 22 Oct 2026. Full notes, decisions and the merge plan are in `DATA_NOTES.md`.

Join key for everything is `pcode` (KE001-KE047). Files that use `COUNTYCO` or `county_code` (DesInventar alphabetical codes) are mapped to `pcode` with `reference/kenya_county_crosswalk.csv` (`desinventar_code`).

## raw/  (original downloads, never edit these)
| Folder | File | Role | Coverage |
|---|---|---|---|
| rainfall | ken-rainfall-subnat-full.csv | Main input: CHIRPS 10-day rainfall + anomalies (WFP/HDX) | 1981-01 to 2026-10, all 47 counties |
| ndvi | ken-ndvi-subnat-full.csv | Input: vegetation greenness | 2002-07 to 2026-09 |
| climate_indices | oni.csv | Input: El Nino index (NOAA PSL). Missing = -9999 | 1950 to 2026-07 |
| climate_indices | dmi_ersstv6.txt | Input: Indian Ocean Dipole index (ERSSTv6) | 1950 to 2026-08 |
| flood_labels/emdat | public_emdat_custom_request_2026-10-20.xlsx | Label: large floods; filter ISO=KEN, Disaster Type=Flood | 2000 to 2026 (56 Kenyan floods) |
| flood_labels/desinventar | DI_Crosstab_floods_county_yearmonth.xls | Label: national flood records, county x year/month (753 records) | 2002 to 2025 |
| flood_labels/dfo_master_list | wlf_nhr_fl_dfomasterlist_20190418.dbf | Label: Dartmouth Flood Observatory events (free-text locations) | 1988 to 2010 (41 Kenyan floods) |
| flood_labels/global_flood_database | kenya_gfd_county_floods.csv | Label: satellite flood area per event per county (GEE export) | 2002 to 2018 (33 floods) |
| boundaries | lev_0.shp / .shx / .dbf | Kenya county polygons (DesInventar codes) | 47 counties |
| earth_engine | era5land_soil_runoff_county_month.csv | Input: soil moisture + runoff (ERA5-Land). Use runoff only as a within-county rank | 1999-10 to 2025-12 |
| earth_engine | era5land_precip_county_month.csv | Diagnostic only: ERA5 rainfall, shows why ERA5 runoff is inflated | 1999-10 to 2025-12 |
| earth_engine | srtm_elevation_slope_county.csv | Input (static): elevation, slope, share of flat land | 47 counties |
| earth_engine | worldcover_landcover_county.csv | Input (static): land-cover shares + county area | 2021 snapshot |
| earth_engine | proximity_rivers_water_county.csv | Input (static): share of county near major rivers / water. Drop the two *_dist_m columns | 47 counties |
| earth_engine | ghsl_builtup_county_5yr.csv | Input: built-up share every 5 years (interpolate) | 2000 to 2025 |
| earth_engine/scripts | 00-07 *.js | The Earth Engine scripts that produced these files (asset: projects/grounded-pager-478418-p6/assets/kenyan_counties) | |

## reference/
- kenya_county_crosswalk.csv: links official county codes (pcode KE001-KE047), DesInventar codes and name spellings.
- kenya_counties.geojson: county polygons with pcode, for maps/dashboard (~7 MB, simplify before Streamlit).

## processed/
- desinventar_floods_county_month.csv: DesInventar crosstab reshaped to one row per flooded county-month (333 rows).
- era5_vs_chirps_by_county.csv: per-county comparison of ERA5 vs CHIRPS rainfall and ERA5 runoff, 2000-2025 (for the limitations section).

## Still to add (Monday 26 Oct)
- raw/population/: KNBS 2019 census population and density per county (47 rows: county, population_2019, area_km2, density_per_km2).
- raw/glofas/: GloFAS river discharge from the Copernicus Climate Data Store (needs account + API key; download script to be written).
- Neighbour/upstream rainfall is built in code from CHIRPS + the county map; nothing to download.

## _not_used/  (kept for the record, do not use)
- ken-rainfall-subnat-5ytd.csv: only 2022-2026; replaced by the full file.
- national_natural_disaster_inventory_UNDATED.csv: HDX inventory, date column empty.
- DI_Crosstab_ALL_EVENT_TYPES.xls: includes droughts, epidemics etc., not just floods.
- DFO_3170_Precip_...csv: rainfall for a single 2007 event, not a label.
- dmi.had.long.csv: older DMI (HadISST, to 2026-05); replaced by dmi_ersstv6.txt.
- worldpop_county_year.csv: WorldPop 2000-2020; counts badly off vs the 2019 census (Mandera 2.16 M vs ~0.87 M, national total 52 M vs ~47.6 M). Replaced by census density.
