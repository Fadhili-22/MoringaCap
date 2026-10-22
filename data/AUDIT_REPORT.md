# Data audit report (Group 6: Kenya County Flood Risk Early Warning)

Audit run: 22 Oct 2026. Read-only: no file in `data/` was modified, moved, renamed, re-saved or deleted. This report is the only file written into `data/`. Helper scripts live in a scratch folder outside `data/`.

## 1. Verdict

**PROBLEMS FOUND (content/documentation only; no file is corrupted).** All 37 files are present with the exact expected size and MD5 (0 mismatches, 0 extra, 0 missing). 86 of 90 content checks pass; the 4 FAILs are listed in section 4 and none of them stops the Monday build, but two (EM-DAT labels, DesInventar years) change what you should expect from the labels.

FAILs:

- [Extra checks] DATA_NOTES: of 39 level-2-only counties, 26 single-area and 13 multi-area: expected 26 / 13, actual 21 / 18 (total 39); level-2 PCODEs inside the 8 level-1 counties: 15
- [EM-DAT] of those, empty Admin Units AND Location present (2023-2024): expected 6 (all parseable from Location), actual 5 of 6; no Location text: ['2024-0892-KEN']
- [EM-DAT] empty Admin Units in any other year (informational): expected none beyond 2023-24, actual all years: 7 empty; by start year {2023: 2, 2024: 4, 2026: 1}; outside 2023-24: ['2026-0153-KEN']
- [DesInventar] years with no DesInventar records (DATA_NOTES says only 2017-2019): expected [2017, 2018, 2019], actual [2004, 2017, 2018, 2019]

## 2. File integrity

All files were already downloaded locally (no OneDrive online-only placeholders; attributes are plain Archive, none Offline/RecallOnDataAccess), so every file was hashed from its real content.

| File | Bytes | Size OK | Hash OK |
|---|---:|:---:|:---:|
| `DATA_NOTES.md` | 6366 | yes | yes |
| `README.md` | 4156 | yes | yes |
| `_not_used/DFO_3170_Precip_PERSIANN_from_20070815_to_20071031.csv` | 1076 | yes | yes |
| `_not_used/DI_Crosstab_ALL_EVENT_TYPES.xls` | 329216 | yes | yes |
| `_not_used/dmi.had.long.csv` | 39650 | yes | yes |
| `_not_used/ken-rainfall-subnat-5ytd.csv` | 1744024 | yes | yes |
| `_not_used/national_natural_disaster_inventory_UNDATED.csv` | 271474 | yes | yes |
| `_not_used/worldpop_county_year.csv` | 131895 | yes | yes |
| `processed/desinventar_floods_county_month.csv` | 9883 | yes | yes |
| `processed/era5_vs_chirps_by_county.csv` | 5506 | yes | yes |
| `raw/boundaries/lev_0.dbf` | 2856 | yes | yes |
| `raw/boundaries/lev_0.shp` | 2668132 | yes | yes |
| `raw/boundaries/lev_0.shx` | 476 | yes | yes |
| `raw/climate_indices/dmi_ersstv6.txt` | 44054 | yes | yes |
| `raw/climate_indices/oni.csv` | 19489 | yes | yes |
| `raw/earth_engine/era5land_precip_county_month.csv` | 1709129 | yes | yes |
| `raw/earth_engine/era5land_soil_runoff_county_month.csv` | 2609945 | yes | yes |
| `raw/earth_engine/ghsl_builtup_county_5yr.csv` | 31644 | yes | yes |
| `raw/earth_engine/proximity_rivers_water_county.csv` | 10443 | yes | yes |
| `raw/earth_engine/scripts/00_check_asset.js` | 318 | yes | yes |
| `raw/earth_engine/scripts/01_era5land_soil_runoff.js` | 678 | yes | yes |
| `raw/earth_engine/scripts/02_era5land_precip_check.js` | 713 | yes | yes |
| `raw/earth_engine/scripts/03_srtm_elevation_slope.js` | 638 | yes | yes |
| `raw/earth_engine/scripts/04_proximity_rivers_water.js` | 1105 | yes | yes |
| `raw/earth_engine/scripts/05_worldcover_landcover.js` | 664 | yes | yes |
| `raw/earth_engine/scripts/06_ghsl_builtup.js` | 548 | yes | yes |
| `raw/earth_engine/scripts/07_worldpop_NOT_USED.js` | 571 | yes | yes |
| `raw/earth_engine/srtm_elevation_slope_county.csv` | 7831 | yes | yes |
| `raw/earth_engine/worldcover_landcover_county.csv` | 12723 | yes | yes |
| `raw/flood_labels/desinventar/DI_Crosstab_floods_county_yearmonth.xls` | 178688 | yes | yes |
| `raw/flood_labels/dfo_master_list/wlf_nhr_fl_dfomasterlist_20190418.dbf` | 15557123 | yes | yes |
| `raw/flood_labels/emdat/public_emdat_custom_request_2026-10-20.xlsx` | 745361 | yes | yes |
| `raw/flood_labels/global_flood_database/kenya_gfd_county_floods.csv` | 31397 | yes | yes |
| `raw/ndvi/ken-ndvi-subnat-full.csv` | 4512594 | yes | yes |
| `raw/rainfall/ken-rainfall-subnat-full.csv` | 16673313 | yes | yes |
| `reference/kenya_counties.geojson` | 6986715 | yes | yes |
| `reference/kenya_county_crosswalk.csv` | 1423 | yes | yes |

Extra files not in the list (before this report was written): none. Missing files: none.

## 3. Content checks

`Extra checks` are additional cross-checks against claims made in README/DATA_NOTES that were not in your list.

### Reference

| Check | Expected | Actual | Result |
|---|---|---|:---:|
| crosswalk rows | 47 | 47 | **PASS** |
| crosswalk columns | ['county', 'knbs_code', 'pcode', 'desinventar_code', 'desinventar_name'] | ['county', 'knbs_code', 'pcode', 'desinventar_code', 'desinventar_name'] | **PASS** |
| crosswalk pcode = KE001-KE047, unique | 47 unique, KE001..KE047 | 47 unique, matches range: True | **PASS** |
| crosswalk desinventar_code = 1-47, unique | 47 unique, 1..47 | 47 unique, min 1, max 47 | **PASS** |
| crosswalk desinventar_code stored as zero-padded 2-char strings (matches EE/GFD/lev_0) | all length 2 (e.g. '06') | string lengths [2]; e.g. ['06', '08', '05'] | **PASS** |
| Nairobi desinventar_code = 30 (per DATA_NOTES) | 30 | [30] | **PASS** |
| geojson feature count | 47 | 47 | **PASS** |
| geojson pcode property present & matches crosswalk | 47 unique pcodes == crosswalk | key=pcode; 47 unique; equal to crosswalk: True; null: 0 | **PASS** |
| geojson attributes agree with crosswalk (county, knbs_code, desinventar_code, desinventar_name) | 0 mismatches | {'county': 0, 'knbs_code': 0, 'desinventar_code': 0, 'desinventar_name': 0} | **PASS** |

### Rainfall

| Check | Expected | Actual | Result |
|---|---|---|:---:|
| rows | 133488 | 133488 | **PASS** |
| date range | 1981-01-01 to 2026-10-01 | 1981-01-01 to 2026-10-01 | **PASS** |
| day of month only 1, 11, 21 | [1, 11, 21] | [1, 11, 21] | **PASS** |
| adm_level 1 counties | ['KE004', 'KE008', 'KE010', 'KE019', 'KE023', 'KE037', 'KE043', 'KE047'] | ['KE004', 'KE008', 'KE010', 'KE019', 'KE023', 'KE037', 'KE043', 'KE047'] | **PASS** |
| distinct level-2 PCODEs | 73 | 73 | **PASS** |
| all 47 counties covered | 47, == crosswalk | 47; equal to crosswalk: True; extra: []; missing: [] | **PASS** |
| the 8 level-1 counties also have level-2 rows (double-count risk) | ['KE004', 'KE008', 'KE010', 'KE019', 'KE023', 'KE037', 'KE043', 'KE047'] | ['KE004', 'KE008', 'KE010', 'KE019', 'KE023', 'KE037', 'KE043', 'KE047'] | **PASS** |
| no missing values 2000-2025 (all columns) | 0 nulls in every column | 0 nulls in every column | **PASS** |
| every PCODE has 936 rows in 2000-2025 | all 81 PCODEs = 936 | 81 PCODEs; min 936, max 936; not 936: 0 | **PASS** |
| prelim rows only in Sep-Oct 2026 | prelim dates within 2026-09..2026-10 | versions {'final': 133164, 'prelim': 324}; prelim 2026-09-01 to 2026-10-01 | **PASS** |
| Nairobi (KE047, level 1) Apr 2024 rfh sum | ~536.1 mm | 536.08 mm over 3 dekads | **PASS** |

### Extra checks

| Check | Expected | Actual | Result |
|---|---|---|:---:|
| DATA_NOTES: of 39 level-2-only counties, 26 single-area and 13 multi-area | 26 / 13 | 21 / 18 (total 39); level-2 PCODEs inside the 8 level-1 counties: 15 | **FAIL** |
| DATA_NOTES: monthly total = sum of 3 rfh = last dekad's r1h (Nairobi Apr 2024) | r1h(2024-04-21) == 536.08 | r1h = 536.08 | **PASS** |
| DATA_NOTES: ERA5 Keiyo-Marakwet Aug 2020 rainfall | ~1,187 mm | [1187] | **PASS** |

### NDVI

| Check | Expected | Actual | Result |
|---|---|---|:---:|
| rows | 70713 | 70713 | **PASS** |
| date range | 2002-07 to 2026-09 | 2002-07 to 2026-09 | **PASS** |
| all 47 counties | 47, == crosswalk | 47; equal: True | **PASS** |

### Climate indices

| Check | Expected | Actual | Result |
|---|---|---|:---:|
| ONI monthly, starts 1950-01, no gaps | starts 1950-01, contiguous monthly | 1950-01 to 2026-12, 924 rows, 0 missing months, dup dates 0 | **PASS** |
| ONI missing coded -9999 | -9999 present; no -99.9 | -9999 count 5 (dates: ['2026-08', '2026-09', '2026-10', '2026-11', '2026-12']); -99.9 count 0 | **PASS** |
| DMI parses into Year, Month, WTIO, SETIO, DMI | 5 numeric columns | 920 rows x 5 cols; nulls 0 | **PASS** |
| DMI range 1950 to 2026-08, contiguous | 1950-01 to 2026-08 | 1950-01 to 2026-08; 0 missing months | **PASS** |
| Oct 2019 DMI | ~1.17 | [1.17] | **PASS** |

### EM-DAT

| Check | Expected | Actual | Result |
|---|---|---|:---:|
| rows x columns | 2084 x 47 | 2084 x 47 | **PASS** |
| ISO=KEN & Disaster Type=Flood rows | 56 | 56 | **PASS** |
| 2023-2024 floods with empty Admin Units | 6 | 6 | **PASS** |
| of those, empty Admin Units AND Location present (2023-2024) | 6 (all parseable from Location) | 5 of 6; no Location text: ['2024-0892-KEN'] | **FAIL** |
| empty Admin Units in any other year (informational) | none beyond 2023-24 | all years: 7 empty; by start year {2023: 2, 2024: 4, 2026: 1}; outside 2023-24: ['2026-0153-KEN'] | **FAIL** |

### DesInventar

| Check | Expected | Actual | Result |
|---|---|---|:---:|
| raw shape (rows x cols) | 78 x 185 | 78 x 185 | **PASS** |
| row 0 = county names; row 1 = sub-headers level0/DataCards/Deaths/Directly affected | 46 names, 4 sub-cols each | A1='County', A2='Year/Month', 46 county names, sub-header pattern ok after strip: True (138 of 184 sub-headers have a leading space, e.g. ' DataCards') | **PASS** |
| county names all exist in crosswalk desinventar_name | 46 of 47 found | 46 names; unmatched []; crosswalk counties absent from crosswalk-sheet ['NYAMIRA'] | **PASS** |
| README: 753 records (sum of per-county DataCards) | 753 | 753 (TOTAL row: 753) | **PASS** |
| processed rows == raw county-months with DataCards>0 | 333 | 333 | **PASS** |
| processed sum(flood_records) == raw DataCards total; deaths and affected also match | 753 / 608 / 303 | 753 / 608 / 303 | **PASS** |
| years with no DesInventar records (DATA_NOTES says only 2017-2019) | [2017, 2018, 2019] | [2004, 2017, 2018, 2019] | **FAIL** |

### DFO

| Check | Expected | Actual | Result |
|---|---|---|:---:|
| rows | 4029 | 4029 | **PASS** |
| rows mentioning Kenya (any text field) | 41 | 41 | **PASS** |

### GFD

| Check | Expected | Actual | Result |
|---|---|---|:---:|
| rows | 358 | 358 | **PASS** |
| distinct dfo_id | 33 | 33 | **PASS** |
| began range | 2002 to 2018 | 2002-04-26 to 2018-04-28 | **PASS** |
| county_code all exist in crosswalk desinventar_code | all in 1..47 crosswalk | 42 distinct codes; not in crosswalk: [] | **PASS** |
| county_name agrees with crosswalk name for that code | 0 mismatches | 0 mismatches [] | **PASS** |

### Processed

| Check | Expected | Actual | Result |
|---|---|---|:---:|
| DI processed rows | 333 | 333 | **PASS** |
| DI processed counties | 46 | 46 | **PASS** |
| DI processed years | 2002-2025 | 2002-2025 | **PASS** |
| DI processed duplicate pcode+year+month | 0 | 0 | **PASS** |
| DI processed pcodes all in crosswalk | subset | not in crosswalk: [] | **PASS** |
| era5_vs_chirps_by_county rows | 47 | 47 | **PASS** |

### EE soil/runoff

| Check | Expected | Actual | Result |
|---|---|---|:---:|
| rows = 47 x 315 | 14805 | 14805 | **PASS** |
| months | 315, 1999-10 to 2025-12 | 315, 1999-10 to 2025-12 | **PASS** |
| 315 months per county, no gaps | 47 x 315 | 47 counties; min 315, max 315 | **PASS** |
| no duplicates (COUNTYCO,year,month) | 0 | 0 | **PASS** |
| no nulls (all columns except .geo) | 0 | 0 | **PASS** |
| soil water layer 1 range | ~0.05 to ~0.48 | 0.0306 (TURKANA 2023-02) to 0.4735 (NYAMIRA 2018-04); 88 rows < 0.05, all in ['TURKANA'] | **PASS** |
| COUNTYCO maps to crosswalk (47 codes, names agree) | 47 codes == crosswalk; 0 name mismatches | 47 codes, equal: True; code string lengths [2]; name mismatches [] | **PASS** |

### EE precip

| Check | Expected | Actual | Result |
|---|---|---|:---:|
| rows = 47 x 315 | 14805 | 14805 | **PASS** |
| value column named `mean` | mean | True | **PASS** |
| months / per county | 315 months 1999-10..2025-12; 47 x 315 | 315 months 1999-10..2025-12; per county min 315 max 315 | **PASS** |
| no duplicates / no nulls | 0 / 0 | 0 / 0 | **PASS** |
| `mean` plausible as metres of monthly rain | 0 <= mean < ~1.5 m | min 0.00004, max 1.1865 | **PASS** |
| COUNTYCO maps to crosswalk (47 codes, names agree) | 47 codes == crosswalk; 0 name mismatches | 47 codes, equal: True; code string lengths [2]; name mismatches [] | **PASS** |
| same county-month grid as soil/runoff file | True | True | **PASS** |

### EE SRTM

| Check | Expected | Actual | Result |
|---|---|---|:---:|
| rows | 47 | 47 | **PASS** |
| Mombasa mean elevation | ~29 m | [28.67551651494105] | **PASS** |
| Nyandarua mean elevation | ~2,537 m | [2537.233027677982] | **PASS** |
| COUNTYCO maps to crosswalk (47 codes, names agree) | 47 codes == crosswalk; 0 name mismatches | 47 codes, equal: True; code string lengths [2]; name mismatches [] | **PASS** |

### EE WorldCover

| Check | Expected | Actual | Result |
|---|---|---|:---:|
| rows | 47 | 47 | **PASS** |
| land-cover shares sum per county (9 pct_ cols) | ~1 | min 0.99996, max 1.00000; cols ['pct_bare', 'pct_built', 'pct_crop', 'pct_grass', 'pct_mangrove', 'pct_shrub', 'pct_tree', 'pct_water', 'pct_wetland'] | **PASS** |
| Nairobi area | ~696 km2 | [696.3] | **PASS** |
| COUNTYCO maps to crosswalk (47 codes, names agree) | 47 codes == crosswalk; 0 name mismatches | 47 codes, equal: True; code string lengths [2]; name mismatches [] | **PASS** |

### EE proximity

| Check | Expected | Actual | Result |
|---|---|---|:---:|
| rows | 47 | 47 | **PASS** |
| all pct_ columns between 0 and 1 | [0,1] | 5 cols ['pct_occasional_water', 'pct_water', 'pct_within_1km_river', 'pct_within_1km_water', 'pct_within_5km_river']; min 0.000e+00, max 0.4679; nulls 0 | **PASS** |
| COUNTYCO maps to crosswalk (47 codes, names agree) | 47 codes == crosswalk; 0 name mismatches | 47 codes, equal: True; code string lengths [2]; name mismatches [] | **PASS** |

### EE GHSL

| Check | Expected | Actual | Result |
|---|---|---|:---:|
| rows = 47 x 6 | 282 | 282 | **PASS** |
| years | [2000, 2005, 2010, 2015, 2020, 2025] | [2000, 2005, 2010, 2015, 2020, 2025] | **PASS** |
| 6 rows per county, no duplicates | 47 x 6 | 47 counties, min 6 max 6, dups 0 | **PASS** |
| pct_built never decreases over time (any county) | 0 counties decrease | 0 counties decrease [] | **PASS** |
| COUNTYCO maps to crosswalk (47 codes, names agree) | 47 codes == crosswalk; 0 name mismatches | 47 codes, equal: True; code string lengths [2]; name mismatches [] | **PASS** |

### Boundaries

| Check | Expected | Actual | Result |
|---|---|---|:---:|
| lev_0 shape count | 47 | 47 | **PASS** |
| lev_0 fields | ['COUNTYCO', 'COUNT', 'FIRST_COUN'] | ['COUNTYCO', 'COUNT', 'FIRST_COUN'] | **PASS** |
| lev_0 COUNTYCO maps to crosswalk | 47 unique codes == crosswalk | 47 unique; equal: True; samples ['01', '02', '03'] | **PASS** |
| lev_0.prj missing (known) | missing | missing | **PASS** |

## 4. Problems, extra/missing files and other observations

### FAILs (details)

1. **EM-DAT: only 5 of the 6 empty-`Admin Units` floods in 2023-2024 have a `Location` to parse.** There are exactly 6 floods in 2023-2024 with empty `Admin Units` (matches DATA_NOTES), but `2024-0892-KEN` (Dec 2024) has `Location` empty as well (and `GADM Admin Units` is empty too), so it cannot be mapped to counties from the file. The other five (`2023-0721-KEN`, `2023-0187-KEN`, `2024-0150-KEN`, `2024-0210-KEN`, `2024-0247-KEN`) have usable `Location` text. Decide how to treat `2024-0892-KEN` (drop it, or look it up manually). Separately, `2023-0721-KEN` starts Oct 2023 and ends in 2024 with a blank `End Month`, so its span end must be assumed.
2. **EM-DAT: one more empty-`Admin Units` flood outside 2023-2024.** `2026-0153-KEN` (Mar 2026) has empty `Admin Units`; its `Location` lists all 47 counties. It falls outside the 2000-2025 grid, so it has no effect on the 14,664-row table, but the note "6 of the 2023-2024 ones" is not the whole story (7 empties in total, 56 Kenyan floods, 1 of them in 2026).
3. **DesInventar: 2004 also has no records, not just 2017-2019.** Years with at least one flood record: 2002-2003, 2005-2016, 2020-2025 (20 of 24 years). The notes only mention the 2017-2019 gap. If you drop or flag no-data years at modelling time, add 2004.
4. **Rainfall area counts in DATA_NOTES are wrong.** Of the 39 counties with level-2 rows only, 21 have a single area and 18 (not 13) have several areas needing the n_pixels-weighted mean (the notes say 26 and 13). The rule itself is unaffected, but do not hard-code 13 anywhere; update the note.

### Things that passed but need care in the merge

- **Leading zeros must survive.** The crosswalk, Earth Engine files, GFD and `lev_0` all store `desinventar_code` / `COUNTYCO` / `county_code` as zero-padded 2-character strings (`'08'`), so they join cleanly as strings. Read them with `dtype=str`: pandas defaults would turn `'08'` into `8` and break the join. All 47 codes map one-to-one, and the county names agree with the crosswalk in every EE file, GFD and the geojson (`lev_0` was checked on codes only).
- **DesInventar crosstab details.** The sub-headers in row 1 have a leading space (`' DataCards'`, `' Deaths'`, `' Directly affected'`); strip them. The `level0` columns sum to 7,789 and are NOT a record count: the 753 records in README are the `DataCards` columns (the processed file correctly uses `DataCards`; its rows, records 753, deaths 608 and affected 303 all reconcile to the raw crosstab). `Directly affected` is non-zero in only 2 county-months (303 people in total), so it is nearly useless as a feature. Nyamira has no flood records at all (46 of 47 counties).
- **EM-DAT `Location` text needs normalising.** It contains an en dash (U+2013) in one 2019 row (`Taita-Taveta`) and spelling variants (`Muranga`, `Trans Nzoia`, `Tarkana`, `WAjir`, "and Kitui", "Keiyo/Marakwet" as separate districts). The old-district `Admin Units` JSON also uses pre-2013 districts (Nyando, Koibatek, Keiyo, Marakwet, Malindi...), so mapping to the 47 counties needs a lookup table.
- **ONI file runs to 2026-12.** The last 5 rows (2026-08 to 2026-12) are `-9999`; the last valid month is 2026-07 as README says. DMI ends 2026-08. Both are beyond the 2000-2025 grid, so only lags near the end of 2025 matter. The `oni.csv` header still wrongly says -99.9; no -99.9 values exist.
- **Soil water layer 1 minimum is 0.031**, below the "~0.05" quoted, but it is Turkana in dry months (Turkana mean 0.082; all 88 values under 0.05 are Turkana, lowest Feb 2023), so it is plausible, not an error.
- **Rainfall.** `prelim` rows (324) are Sep-Oct 2026 only; the last `final` dekad is 2026-08-21. The period behind `rfh_avg` is still undocumented (an open item in DATA_NOTES).
- **GFD.** 42 distinct counties, 177 of the 358 rows have `flooded_km2 >= 1.5` (the agreed threshold); no duplicate (dfo_id, county) pairs and no null values.
- **Boundaries.** `lev_0.prj` is missing as expected (only `.dbf`, `.shp`, `.shx` present); coordinates are in plain lon/lat degrees (bbox 33.91 to 41.90, -4.65 to 5.48), so it is almost certainly WGS84 but that is an assumption.

### Extra / missing files

- Extra files: none. Missing files: none.
- Not present yet, by plan (README "Still to add", Monday 26 Oct): `raw/population/` and `raw/glofas/`.

### Method notes

- Scripts were run from a scratch folder outside `data/`; `xlrd`, `dbfread` and `pyshp` were not installed on this machine and were installed into that scratch folder only (no change to the Python environment).
- Files were opened read-only. After the report was written the integrity script was re-run to confirm that no hash or size changed and that `AUDIT_REPORT.md` is the only new file.

Post-audit: DATA_NOTES.md corrected for the 4 FAILs above (its MD5 now differs from the manifest by design).
