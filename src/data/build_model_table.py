"""Run every stage in order, assemble the county-month table, run the checks and write the outputs.

    python src/data/build_model_table.py                   # everything
    python src/data/build_model_table.py --skip 08_glofas  # leave a stage out (its interim file is reused if present;
                                                           # for 08_glofas on a fresh clone an all-NaN file is written)

Stage order: 00_boundaries 01_grid 02_rainfall 03_neighbours 04_ndvi 05_climate 06_era5land 07_static 08_glofas
09_labels 10_labels_combined 11_history -> assemble -> 12_checks -> 13_outputs.
Stage 09a_place_lookup is NOT part of the build: place_to_county.csv is a confirmed, hand-editable file.
Re-run after the GloFAS files or the *_cod.csv Earth Engine exports arrive; they are picked up automatically.
"""
import argparse
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pandas as pd  # noqa: E402

from common import INTERIM, LOG_FILE, log  # noqa: E402

PRE = ["00_boundaries", "01_grid", "02_rainfall", "03_neighbours", "04_ndvi", "05_climate", "06_era5land", "07_static",
       "08_glofas", "09_labels", "10_labels_combined", "11_history"]
POST = ["12_checks", "13_outputs"]

KEYS = ["pcode", "county", "year", "month", "season", "month_sin", "month_cos"]
COLUMN_ORDER = KEYS + [
    "rain_mm", "rain_max_dekad", "rain_lag1", "rain_lag2", "rain_3mo_total", "rain_pct_normal",
    "neighbour_rain", "neighbour_rain_lag1", "ndvi", "ndvi_pct_normal",
    "oni", "oni_lag1", "oni_lag2", "oni_lag3", "dmi", "dmi_lag1", "dmi_lag2", "dmi_lag3",
    "soil_moisture_l1", "soil_moisture_l1_lag1", "soil_moisture_l2", "soil_moisture_l2_lag1", "runoff_rank",
    "discharge_rank", "discharge_rank_lag1",
    "elevation", "elev_std", "slope", "pct_flat", "area_km2",
    "lc_tree", "lc_shrub", "lc_grass", "lc_crop", "lc_built", "lc_bare", "lc_water", "lc_wetland", "lc_mangrove",
    "pct_within_1km_river", "pct_within_5km_river", "pct_within_1km_water", "pct_water", "pct_occasional_water",
    "pop_density", "pct_built", "county_flood_rate", "county_flood_rate_public",
    "flood_desinventar", "flood_emdat", "flood_gfd", "flood_dfo", "flood_gfd_dfo", "desinventar_no_record_year",
    "n_sources", "flood_this_month", "flood_corroborated",
    "n_sources_public", "flood_this_month_public", "flood_corroborated_public",
    "flood_next_month", "flood_next_month_public", "heavy_rain_next_month",
]
FEATURE_FILES = ["rainfall", "neighbour_rain", "ndvi", "climate", "era5land", "glofas", "slow_county_month", "history",
                 "labels_combined"]


def run_stage(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.run()


def assemble():
    key = ["pcode", "year", "month"]
    out = pd.read_csv(INTERIM / "grid.csv", dtype={"pcode": str})
    n = len(out)
    for f in FEATURE_FILES:
        df = pd.read_csv(INTERIM / f"{f}.csv", dtype={"pcode": str})
        assert not df.duplicated(key).any(), f"{f}: duplicate keys"
        out = out.merge(df, how="left", on=key, validate="one_to_one")
        assert len(out) == n, f"{f}: merge changed the row count"
    out = out.merge(pd.read_csv(INTERIM / "static_county.csv", dtype={"pcode": str}), how="left", on="pcode",
                    validate="many_to_one")
    missing = set(COLUMN_ORDER) - set(out.columns)
    extra = set(out.columns) - set(COLUMN_ORDER)
    assert not missing and not extra, f"column mismatch: missing {sorted(missing)}, unexpected {sorted(extra)}"
    out = out[COLUMN_ORDER].sort_values(key).reset_index(drop=True)
    assert len(out) == 14664 and not out.duplicated(key).any()
    out.to_csv(INTERIM / "model_table_full.csv", index=False)
    log("assemble", f"interim/model_table_full.csv: {out.shape[0]} rows x {out.shape[1]} columns")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip", nargs="*", default=[], help="stage names to skip, e.g. 08_glofas")
    a = ap.parse_args()
    INTERIM.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text("", encoding="utf-8")
    for s in PRE:
        if s in a.skip:
            if s == "08_glofas" and not (INTERIM / "glofas.csv").exists():
                # fresh clone: no earlier output to reuse, so write the all-NaN GloFAS file (no .nc is read)
                log("build", "skipping 08_glofas: no interim/glofas.csv yet, writing the all-NaN placeholder")
                spec = importlib.util.spec_from_file_location(s, HERE / f"{s}.py")
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                mod.run(pending_only=True)
                continue
            log("build", f"skipping {s} (its interim file from the last build is reused)")
            continue
        run_stage(s)
    assemble()
    for s in POST:
        run_stage(s)


if __name__ == "__main__":
    main()
