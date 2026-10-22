# Group 6 Flood Capstone: data notes and decisions

Project: Kenya County Flood Risk Early Warning (Moringa DSF-PT15, Group 6; Mokeira, Fadhili, Frasiah, Myles). Runs 19 Oct to 20 Nov 2026.
Goal: one table, one row per county per month (47 counties x 2000-2025 = 14,664 rows), key = pcode + year + month. Target = flood NEXT month. Models: logistic regression baseline, random forest, XGBoost; Streamlit dashboard.

## Decisions (22 Oct 2026)
- Target is next month: `flood_next_month` (any source records a flood in that county the following month). Keep one flag per source. Also build `heavy_rain_next_month` (next month CHIRPS rain > 125% of normal) as a comparison target.
- GFD floods count only if flooded_km2 >= 1.5. Include DFO (map district text to counties). GFD and DFO share dfo_id: count them as ONE source when checking agreement between sources.
- EM-DAT: 7 Kenyan floods have empty `Admin Units` (2023: 2, 2024: 4, 2026: 1). Parse `Location` for them. 2024-0892-KEN (Dec 2024) has no Location either: look it up manually or drop it. 2023-0721-KEN has a blank End Month. Location text needs a place-name -> county lookup (spelling variants, en dash, pre-2013 district names).
- EM-DAT licence: the terms forbid redistributing EM-DAT data or derivative databases. The raw EM-DAT file and the full modelling table (with flood_emdat) are never pushed to GitHub; the full table lives in data/private/ (git-ignored). A public table drops flood_emdat and rebuilds the combined label from DesInventar, GFD and DFO.
- Build the full grid (14,664 rows); decide at modelling time whether to drop pre-Jul-2002 rows (NDVI blank) or 2004, 2017, 2018, 2019 (no DesInventar records) for the flood target.
- "Normal" baselines (rainfall % of normal, runoff rank, county flood rate) use training years 2000-2019 only. Check what period WFP's rfh_avg covers.
- Validation (from external model reviews): keep 2020-2025 holdout but add rolling-origin backtests; report PR-AUC, recall, precision, plus a seasonal baseline. Smooth the county flood rate toward the national mean.
- All extra factors to be added except dam releases; final selection at the team meeting on Monday 26 Oct.

## raw/ details
- rainfall/ken-rainfall-subnat-full.csv: 133,488 rows, 10-day rows (dates on day 1/11/21 = dekad start). 8 counties (KE004, KE008, KE010, KE019, KE023, KE037, KE043, KE047) have BOTH a level-1 county row and level-2 rows: use the level-1 row only for those (else double-counting). Other 39 counties: level-2 only (21 have a single area; 18 need n_pixels-weighted mean). The 8 level-1 counties contain 15 level-2 PCODEs, which must be ignored. No nulls 2000-2025; prelim rows only Sep-Oct 2026. Monthly total = sum of 3 rfh values (= last dekad's r1h).
- ndvi/ken-ndvi-subnat-full.csv: 70,713 rows, dekadal, columns vim, vim_avg, viq. Same level-1/level-2 rule.
- climate_indices/oni.csv: missing coded -9999 (header wrongly says -99.9).
- flood_labels/desinventar: crosstab, 78 rows x 185 cols; 4 cols per county (level0, DataCards, Deaths, Directly affected). No records in 2004, 2017, 2018, 2019. Use DataCards as the record count (level0 is not a count). Strip leading spaces from the sub-headers. Nyamira has no records.
- flood_labels/dfo_master_list: 4,029 global floods; 41 Kenyan 1988-2010; location free text in Detailed_L (old district names).
- flood_labels/global_flood_database: county_code = DesInventar alphabetical code (30 = Nairobi), NOT official.
- boundaries/lev_0: fields COUNTYCO (DesInventar code), COUNT, FIRST_COUN. (.prj missing.) Uploaded to Earth Engine as projects/grounded-pager-478418-p6/assets/kenyan_counties.

## raw/earth_engine/ details (exported 22 Oct 2026)
All keyed by COUNTYCO (string with leading zero) -> pcode via crosswalk.desinventar_code. All 47 counties present, codes verified. Read all COUNTYCO / county_code / desinventar_code columns with dtype=str (zero-padded, e.g. '08').
- era5land_soil_runoff_county_month.csv: 315 months x 47 = 14,805 rows, no gaps. volumetric_soil_water_layer_1/_2 (m3/m3), surface_runoff_sum, runoff_sum (metres). Soil moisture plausible (Turkana ~0.08, Vihiga ~0.43). RUNOFF ABSOLUTE VALUES UNUSABLE. Use `runoff_rank` = percentile of this month's runoff among the same county + calendar month in 2000-2019 (0-1). Do not use % of normal (22% of county-months have normal < 1 mm; ratios reach 6,000%).
- era5land_precip_county_month.csv: ERA5-Land rainfall (column `mean`, metres). Diagnostic only. ERA5 rain is 2.7x CHIRPS in Elgeyo-Marakwet, 2.3x West Pokot, 1.7-1.8x Uasin Gishu/Trans Nzoia; 0.56-0.67x in Tana River, Marsabit, Kilifi, Garissa, Turkana. Elgeyo-Marakwet Aug 2020: ERA5 1,187 mm vs CHIRPS 288 mm. Month-to-month correlation 0.63-0.92, so within-county ranks stay informative. Summary in processed/era5_vs_chirps_by_county.csv.
- srtm_elevation_slope_county.csv: elevation (mean m), min, max, stdDev, slope (mean deg), pct_flat (slope < 2 deg).
- worldcover_landcover_county.csv: area_km2 + pct_tree, shrub, grass, crop, built, bare, water, wetland, mangrove. Areas match official (Nairobi 696 km2, Turkana 68,603 km2).
- proximity_rivers_water_county.csv: pct_within_1km_river, pct_within_5km_river (rivers with upstream area >= 1,000 km2), pct_within_1km_water, pct_water, pct_occasional_water. DROP river_dist_m and water_dist_m (capped at 5 km, nearly constant). County polygons exclude Lake Victoria / Lake Turkana, so pct_water = small lakes and dams only. pct_occasional_water is tiny (max 0.5%) and uses 1984-2021 data (slight overlap with test years).
- ghsl_builtup_county_5yr.csv: pct_built for 2000, 2005, ..., 2025 (282 rows); rises in all counties (Nairobi 11.9% -> 14.9%). Building footprint only, so lower than WorldCover built-up (correlation 0.83). Interpolate linearly to each month.

## Final table columns (planned)
- Keys: pcode, county, year, month, season.
- Rainfall: rain_mm, rain_pct_normal, lags 1-2, rain_3mo_total; neighbour_rain (+ lag).
- NDVI: ndvi, ndvi_pct_normal (blank before Jul 2002).
- Climate: oni, dmi, lags 1-3.
- Hydrology: soil_moisture (layer 1, maybe layer 2), runoff_rank, river discharge (GloFAS, if obtained).
- Static: elevation, slope, pct_flat, pct_within_1km/5km_river, pct_within_1km_water, land-cover shares, population density (census).
- Slowly changing: built-up share (GHSL, interpolated).
- History: county_flood_rate (training years, smoothed).
- Labels: flood_desinventar, flood_emdat, flood_gfd, flood_dfo, n_sources, flood_corroborated, flood_next_month, heavy_rain_next_month.

## Merge plan
1. Empty grid: 47 counties x every month 2000-2025.
2. Rainfall -> county-month (rules above).
3. NDVI -> county-month.
4. ONI, DMI on year-month; replace -9999.
5. ERA5 soil moisture + runoff_rank; static and GHSL tables via COUNTYCO -> pcode.
6. Each flood source -> flooded county-months (EM-DAT Admin Units or Location text, span start-end months; GFD >= 1.5 km2, span began-ended; DFO via place-to-county mapping).
7. Labels shifted to next month; per-source flags kept.
8. Features: lags, rolling totals, neighbour rain, season, smoothed historical flood rate (training years only).
9. Checks: 14,664 rows, no duplicate keys, 47 counties, flood share by year and source, seasonal pattern.
