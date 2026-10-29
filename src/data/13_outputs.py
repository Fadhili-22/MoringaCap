"""Stage 13: write the final tables and the data dictionary.

  data/private/model_table_full.csv      all columns incl. EM-DAT-derived ones (git-ignored)
  data/processed/model_table_public.csv  EM-DAT columns dropped, *_public columns renamed to the standard names
  data/DATA_DICTIONARY.md                every column: role, unit, source, how it was built (generated; asserts full coverage)
"""
import shutil
import subprocess

import pandas as pd

from common import (INTERIM, PRIVATE, PROCESSED, PUBLIC_DROP, PUBLIC_RENAME, ROOT, ee_boundary_status, log,
                    to_public)

STAGE = "13_outputs"

KEY, FEATURE, TARGET, LABEL = "KEY", "FEATURE", "TARGET", "LABEL (not a feature)"
CHIRPS = "CHIRPS rainfall via WFP/HDX subnational file ken-rainfall-subnat-full.csv, column `rfh`"
RAIN_RULE = ("8 level-1 counties (KE004, KE008, KE010, KE019, KE023, KE037, KE043, KE047) use their level-1 row only; the other "
             "39 use level-2 rows matched by the first 5 characters of PCODE, n_pixels-weighted mean per dekad")
ERA5 = "ERA5-Land monthly aggregates (ECMWF/ERA5_LAND/MONTHLY_AGGR) via Earth Engine, county mean at 1 km"
WC = "ESA WorldCover 2021 v200 via Earth Engine, county mean at 100 m"
EE_NOTE = "polygons: OCHA COD-AB land-only (see Boundaries in the header)"
FULL_ONLY = " (private table only)"

# name: (role, unit, source, how it was built)
SPEC = [
    ("pcode", KEY, "text", "OCHA/HDX county code", "KE001-KE047, join key everywhere (data/reference/kenya_county_crosswalk.csv)"),
    ("county", KEY, "text", "crosswalk", "County name"),
    ("year", KEY, "year", "-", "2000-2025"),
    ("month", KEY, "month 1-12", "-", "Calendar month"),
    ("season", FEATURE, "JF / MAM / JJAS / OND", "derived from month", "JF = Jan-Feb, MAM = Mar-May, JJAS = Jun-Sep, OND = Oct-Dec"),
    ("month_sin", FEATURE, "-1..1", "derived from month", "sin(2*pi*month/12)"),
    ("month_cos", FEATURE, "-1..1", "derived from month", "cos(2*pi*month/12)"),
    ("rain_mm", FEATURE, "mm / month", CHIRPS, f"Sum of the 3 dekads of the month. {RAIN_RULE}"),
    ("rain_max_dekad", FEATURE, "mm / dekad", CHIRPS, "Largest of the month's 3 dekadal county values"),
    ("rain_lag1", FEATURE, "mm / month", CHIRPS, "rain_mm of the previous month (computed on the full 1981-2025 series before trimming)"),
    ("rain_lag2", FEATURE, "mm / month", CHIRPS, "rain_mm two months earlier"),
    ("rain_3mo_total", FEATURE, "mm / 3 months", CHIRPS, "rain_mm + rain_lag1 + rain_lag2"),
    ("rain_pct_normal", FEATURE, "ratio (1.0 = normal)", CHIRPS, "rain_mm / mean rain_mm of the same county + calendar month over 2000-2019 (training years). "
     "A ratio, not a percentage. WFP's own `rfh_avg` (period 1989-2018) is NOT used"),
    ("neighbour_rain", FEATURE, "mm / month", CHIRPS + "; data/reference/county_adjacency.csv", "Mean rain_mm of the counties whose polygons touch (0.001 deg buffer; land-only COD-AB polygons)"),
    ("neighbour_rain_lag1", FEATURE, "mm / month", "as neighbour_rain", "Previous month's neighbour_rain (full series before trimming)"),
    ("ndvi", FEATURE, "NDVI (dimensionless)", "WFP/HDX subnational vegetation index, column `vim` (ken-ndvi-subnat-full.csv)",
     f"Mean of the month's 3 dekads; same level-1/level-2 rule as rainfall. Blank before 2002-07 (not filled)"),
    ("ndvi_pct_normal", FEATURE, "ratio (1.0 = normal)", "as ndvi", "ndvi / mean ndvi of the same county + calendar month over the available 2002-07..2019-12 months. Blank before 2002-07"),
    ("oni", FEATURE, "deg C (index)", "NOAA PSL ONI (CPC), oni.csv", "SHIFTED: value at month t = published ONI for month t-1 (the published value is centred on its month and would otherwise include t+1). "
     "-9999 -> NaN. Same for every county"),
    ("oni_lag1", FEATURE, "deg C (index)", "as oni", "oni one month earlier (published t-2)"),
    ("oni_lag2", FEATURE, "deg C (index)", "as oni", "oni two months earlier (published t-3)"),
    ("oni_lag3", FEATURE, "deg C (index)", "as oni", "oni three months earlier (published t-4)"),
    ("dmi", FEATURE, "deg C (index)", "Dipole Mode Index, ERSSTv6 (dmi_ersstv6.txt); anomalies vs a 1991-2020 climatology", "DMI = WTIO - SETIO for the month. Same for every county"),
    ("dmi_lag1", FEATURE, "deg C (index)", "as dmi", "dmi one month earlier"),
    ("dmi_lag2", FEATURE, "deg C (index)", "as dmi", "dmi two months earlier"),
    ("dmi_lag3", FEATURE, "deg C (index)", "as dmi", "dmi three months earlier"),
    ("soil_moisture_l1", FEATURE, "m3/m3", ERA5 + ", volumetric_soil_water_layer_1 (0-7 cm)", f"County mean; {EE_NOTE}"),
    ("soil_moisture_l1_lag1", FEATURE, "m3/m3", "as soil_moisture_l1", "Previous month (series starts 1999-10 so Jan 2000 is filled)"),
    ("soil_moisture_l2", FEATURE, "m3/m3", ERA5 + ", volumetric_soil_water_layer_2 (7-28 cm)", "County mean"),
    ("soil_moisture_l2_lag1", FEATURE, "m3/m3", "as soil_moisture_l2", "Previous month"),
    ("runoff_rank", FEATURE, "0-1 percentile", ERA5 + ", runoff_sum", "Mid-rank percentile of this month's runoff among the same county + calendar month in 2000-2019. "
     "Absolute runoff and % of normal are deliberately not used (ERA5 runoff is unusable in absolute terms). Values outside the 2000-2019 range are 0 or 1"),
    ("discharge_rank", FEATURE, "0-1 percentile", "GloFAS v4.0 consolidated river discharge (DOI 10.24381/cds.a4fdd6b9), `avg_dis`",
     "Real date = valid_time minus 1 day; monthly mean per grid cell; per county the MAX cell centre inside the land-only polygon (the main river); mid-rank percentile among the same county + calendar month in 2000-2019. "
     "NaN until the glofas_kenya_<year>.nc files are present. Dec 2025 is a 30-day mean (1 Jan 2026 not downloaded)"),
    ("discharge_rank_lag1", FEATURE, "0-1 percentile", "as discharge_rank", "Previous month's discharge_rank (full series; the 1999 file provides Dec 1999)"),
    ("elevation", FEATURE, "m", "SRTM GL1 v003 (USGS/SRTMGL1_003) via Earth Engine, 90 m scale", f"County mean elevation; static. {EE_NOTE}"),
    ("elev_std", FEATURE, "m", "as elevation", "Standard deviation of elevation within the county (renamed from stdDev); static"),
    ("slope", FEATURE, "degrees", "as elevation", "County mean slope; static"),
    ("pct_flat", FEATURE, "fraction 0-1", "as elevation", "Share of the county with slope < 2 degrees (named pct_ but a fraction); static"),
    ("area_km2", FEATURE, "km2", WC.replace("county mean at 100 m", "geometry area"), "Area of the land-only OCHA COD-AB county polygon used for the Earth Engine exports; static"),
    ("lc_tree", FEATURE, "fraction 0-1", WC, "Share of county pixels of class 10 (renamed from pct_tree; fractions, not %); static"),
    ("lc_shrub", FEATURE, "fraction 0-1", WC, "Class 20; static"),
    ("lc_grass", FEATURE, "fraction 0-1", WC, "Class 30; static"),
    ("lc_crop", FEATURE, "fraction 0-1", WC, "Class 40; static"),
    ("lc_built", FEATURE, "fraction 0-1", WC, "Class 50 (built-up); static"),
    ("lc_bare", FEATURE, "fraction 0-1", WC, "Class 60; static"),
    ("lc_water", FEATURE, "fraction 0-1", WC, "Class 80 (permanent water). Big lakes are cut out, so this is small lakes, dams, rivers and the strip of open water left along the cut lake shores; static. Lake-edge caveat: in Homa Bay, Siaya, Migori and Marsabit it is inflated by roughly 2-5 points because the Natural Earth lake outline is coarser than the real shoreline (see the build report)"),
    ("lc_wetland", FEATURE, "fraction 0-1", WC, "Class 90; static"),
    ("lc_mangrove", FEATURE, "fraction 0-1", WC, "Class 95; static"),
    ("pct_within_1km_river", FEATURE, "fraction 0-1", "WWF HydroSHEDS Free Flowing Rivers (upstream area >= 1,000 km2) via Earth Engine", "Share of the county within 1 km of such a river; static (river_dist_m dropped)"),
    ("pct_within_5km_river", FEATURE, "fraction 0-1", "as above", "Share of the county within 5 km of such a river; static"),
    ("pct_within_1km_water", FEATURE, "fraction 0-1", "JRC Global Surface Water v1.4 (occurrence >= 50%) via Earth Engine", "Share of the county within 1 km of permanent water; static (water_dist_m dropped)"),
    ("pct_water", FEATURE, "fraction 0-1", "JRC Global Surface Water v1.4", "Share of the county that is permanent water (occurrence >= 50%); static. Same lake-edge caveat as lc_water"),
    ("pct_occasional_water", FEATURE, "fraction 0-1", "JRC Global Surface Water v1.4 (1984-2021)", "Share with occurrence 1-49%; static. Uses data overlapping the test years (small)"),
    ("pop_density", FEATURE, "people / km2", "KNBS 2019 Kenya Population and Housing Census (population) and KNBS county land area (`land_area_km2`), data/raw/population/county_year_population.csv",
     "2019 census population / KNBS land area. STATIC: the same 2019 value on every row (look-ahead for 2000-2018). The file is a 2000-2025 series extrapolated from the 2019 census; only the 2019 row is used. Area source: KNBS land area, not the polygon area"),
    ("pct_built", FEATURE, "fraction 0-1", "JRC GHSL GHS-BUILT-S R2023A (built_surface) via Earth Engine, 100 m", "Linear interpolation between the 1-Jan anchors 2000, 2005, ..., 2025; 2025 held flat to Dec 2025 (months before an anchor use the next anchor: mild look-ahead)"),
    ("county_flood_rate", FEATURE, "fraction 0-1" + FULL_ONLY, "derived from flood_this_month", "(county_floods + 24*national_rate)/(county_months + 24) over 2000-2019, same on every row of a county. "
     "MODELLING CODE MUST RECOMPUTE THIS INSIDE EACH BACKTEST FOLD from that fold's training months only"),
    ("county_flood_rate_public", FEATURE, "fraction 0-1", "derived from flood_this_month_public", "Same as county_flood_rate from the label without EM-DAT (becomes `county_flood_rate` in the public table). Recompute inside each fold"),
    ("flood_desinventar", LABEL, "0/1", "DesInventar (data/processed/desinventar_floods_county_month.csv)", "1 if DesInventar has >= 1 flood record for the county-month. Zero is 'no data' in desinventar_no_record_year years"),
    ("flood_emdat", LABEL, "0/1" + FULL_ONLY, "EM-DAT custom request 2026-10-20 (not redistributed)", "Kenyan floods (ISO KEN, Disaster Type Flood): every month from Start Month to End Month flagged for the event's counties (Admin Units; Location text for the 6 events lacking Admin Units). Province-only events dropped; one event with a blank End Month collapsed to its start month"),
    ("flood_gfd", LABEL, "0/1", "Global Flood Database (Cloud to Street / DFO), kenya_gfd_county_floods.csv", "1 for every month from `began` to `ended` of events with flooded_km2 >= 1.5 in the county"),
    ("flood_dfo", LABEL, "0/1", "Dartmouth Flood Observatory Global Active Archive of Large Flood Events (master list 2019-04-18)", "41 Kenya rows; counties parsed from `Detailed_L` with the confirmed place lookup (data/reference/place_to_county.csv); every month from Began to Ended flagged"),
    ("flood_gfd_dfo", LABEL, "0/1", "max(flood_gfd, flood_dfo)", "GFD and DFO share dfo_id, so they count as ONE source"),
    ("desinventar_no_record_year", LABEL, "0/1", "derived", "1 for 2000, 2001 (before DesInventar coverage), 2004, 2017, 2018, 2019: DesInventar holds no records those years, so flood_desinventar = 0 there is unknown, not 'no flood'. Use to mask, not as a feature"),
    ("n_sources", LABEL, "0-3" + FULL_ONLY, "derived", "flood_desinventar + flood_emdat + flood_gfd_dfo (in the public table: without EM-DAT, 0-2)"),
    ("flood_this_month", LABEL, "0/1" + FULL_ONLY, "derived", "1 if n_sources >= 1 (public table: without EM-DAT). A label for month t; not a feature"),
    ("flood_corroborated", LABEL, "0/1" + FULL_ONLY, "derived", "1 if n_sources >= 2"),
    ("n_sources_public", LABEL, "0-2", "derived", "flood_desinventar + flood_gfd_dfo (no EM-DAT); becomes `n_sources` in the public table"),
    ("flood_this_month_public", LABEL, "0/1", "derived", "1 if n_sources_public >= 1; becomes `flood_this_month` in the public table"),
    ("flood_corroborated_public", LABEL, "0/1", "derived", "1 if n_sources_public >= 2; becomes `flood_corroborated` in the public table"),
    ("flood_next_month", TARGET, "0/1" + FULL_ONLY, "derived", "flood_this_month shifted -1 month within the county. NaN for Dec 2025 (no Jan 2026 row). Public table: from the label without EM-DAT"),
    ("flood_next_month_public", TARGET, "0/1", "derived", "As flood_next_month from flood_this_month_public; becomes `flood_next_month` in the public table"),
    ("heavy_rain_next_month", TARGET, "0/1", "derived from rain_pct_normal", "1 if NEXT month's rain_pct_normal > 1.25 (comparison target). NaN for Dec 2025"),
]


def dictionary_md(full_cols, public_cols):
    spec_names = [s[0] for s in SPEC]
    assert set(spec_names) == set(full_cols), f"dictionary out of sync: undocumented {sorted(set(full_cols) - set(spec_names))}, stale {sorted(set(spec_names) - set(full_cols))}"
    status = ee_boundary_status()
    cod = all(v == "cod" for v in status.values())
    out = ["# Data dictionary: county-month modelling table\n",
           "Generated by `src/data/13_outputs.py` (it fails if a column is undocumented). One row per county per month, 47 counties x 2000-01..2025-12 = 14,664 rows; key = `pcode` + `year` + `month`.\n",
           "Two tables are written. `data/processed/model_table_public.csv` has no EM-DAT-derived column: `flood_emdat` and every label/history column that used EM-DAT are dropped and the `*_public` columns are renamed to the standard names "
           "(`n_sources`, `flood_this_month`, `flood_corroborated`, `flood_next_month`, `county_flood_rate`). "
           "`data/private/model_table_full.csv` (git-ignored; EM-DAT licence) has all columns.\n",
           "**Roles:** KEY = identifier; FEATURE = usable as a model input; LABEL (not a feature) = flood outcome for the same month or label metadata; TARGET = what we predict (next month).\n",
           "**Baselines:** every 'normal', percentile and flood-rate uses training years 2000-2019 only. Lags/rolling windows were computed on the full available series before trimming to 2000-2025.\n",
           "**Boundaries:** " + ("all Earth Engine features were computed on the OCHA COD-AB land-only county polygons (Lake Victoria, Lake Turkana and Lake Natron removed; Natural Earth 10m lakes v5.0.0). "
                               if cod else "THIS BUILD still used the legacy DesInventar polygons for these Earth Engine files: "
                               f"{ {k: v for k, v in status.items() if v != 'cod'} }. Re-run the `*_cod.js` exports and rebuild to switch to the official land-only COD-AB polygons. ")
           + "County adjacency and the GloFAS county maximum use the land-only COD-AB polygons (`data/reference/kenya_counties.geojson`); "
             "`kenya_counties_full.geojson` (lakes included) is for the dashboard map only.\n",
           "**Area sources:** `area_km2` = polygon area from the Earth Engine export; `pop_density` uses KNBS county land area (`land_area_km2` in data/raw/population/county_year_population.csv). "
           "Land-only COD-AB areas agree with KNBS land areas within 7% for all 47 counties (median ratio 1.000).\n",
           "| column | in public table | role | unit | source | how it was built |", "|---|---|---|---|---|---|"]
    for name, role, unit, src, how in SPEC:
        if name in PUBLIC_RENAME:
            where = f"as `{PUBLIC_RENAME[name]}`"
        elif name in PUBLIC_DROP:
            where = "yes, rebuilt without EM-DAT" if name in public_cols else "no (private only)"
        else:
            where = "yes" if name in public_cols else "no"
        out.append(f"| `{name}` | {where} | {role} | {unit} | {src} | {how} |")
    return "\n".join(out) + "\n"


def run():
    full = pd.read_csv(INTERIM / "model_table_full.csv", dtype={"pcode": str})
    PRIVATE.mkdir(exist_ok=True)
    PROCESSED.mkdir(exist_ok=True)
    shutil.copyfile(INTERIM / "model_table_full.csv", PRIVATE / "model_table_full.csv")
    pub = to_public(full)
    assert not [c for c in pub.columns if "emdat" in c.lower()]
    pub.to_csv(PROCESSED / "model_table_public.csv", index=False)
    (ROOT / "data" / "DATA_DICTIONARY.md").write_text(dictionary_md(list(full.columns), list(pub.columns)), encoding="utf-8")
    log(STAGE, f"model_table_full.csv {full.shape} -> data/private/; model_table_public.csv {pub.shape} -> data/processed/; DATA_DICTIONARY.md written")
    # confirm git would not pick up anything EM-DAT
    try:
        paths = ["data/private/model_table_full.csv", "data/private/build_report_full.md", "data/private/place_to_county_emdat.csv",
                 "data/raw/flood_labels/emdat/public_emdat_custom_request_2026-10-20.xlsx", "data/interim/model_table_full.csv"]
        for p in paths:
            r = subprocess.run(["git", "check-ignore", "-q", p], cwd=ROOT)
            log(STAGE, f"git check-ignore {p}: {'IGNORED' if r.returncode == 0 else 'NOT IGNORED  <-- problem'}")
    except FileNotFoundError:
        log(STAGE, "git not found: skipped the check-ignore confirmation")


if __name__ == "__main__":
    run()
