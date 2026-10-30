"""Stage 8: GloFAS v4.0 river discharge -> discharge_rank, discharge_rank_lag1. SKIPPABLE / re-runnable.

Reads data/raw/glofas/glofas_kenya_<year>.nc (variable avg_dis). Each value's real date is valid_time minus
1 day. Monthly mean per grid cell, then per county the MAX cell whose centre lies inside the county polygon
(the main river). discharge_rank = mid-rank percentile among the same county + calendar month in 2000-2019;
lag computed on the full series (1999 file gives Dec 1999 for Jan 2000).
discharge_rank stays NaN for a county + calendar month unless at least MIN_BASELINE_YEARS (15) of the 20 baseline
years (2000-2019) are present: a rank against 1-3 years is meaningless (one year gives exactly 0.5 everywhere).
Daily values are averaged over the days actually present, so a month with a missing day is a mean over its remaining days.
Exactly one source gap is tolerated, listed in KNOWN_SOURCE_GAP_VALID_DATES: ECMWF has no data for the 2024-12-31 request
(valid_time 2025-01-01), so December 2024 is a 30-day mean. Any other missing day raises an error.
If no files exist yet, the columns are written as NaN and "GloFAS pending" is logged.
run(pending_only=True) writes the all-NaN file without reading any .nc (used by `build_model_table.py --skip 08_glofas`
on a fresh clone, where no interim/glofas.csv exists yet).
"""
import glob
import json
import re
import sys
from calendar import monthrange

import numpy as np
import pandas as pd
import shapely
import xarray as xr
from shapely.geometry import shape

from common import BASE_END, BASE_START, INTERIM, RAW, REFERENCE, add_lags, baseline_percentile, log

STAGE = "08_glofas"
VAR = "avg_dis"
MIN_BASELINE_YEARS = 15
# valid_time stamps that the source does not provide (the EWDS constraints list for Dec 2024 stops at the 30th). Real date = valid_time - 1 day.
# Keep in step with KNOWN_SOURCE_GAP_VALID_DATES in data/raw/glofas/scripts/download_glofas.py.
KNOWN_SOURCE_GAP_VALID_DATES = ("2025-01-01",)
GAPS_JSON = INTERIM / "glofas_gaps.json"


def county_polygons():
    gj = json.load(open(REFERENCE / "kenya_counties.geojson", encoding="utf-8"))
    return {f["properties"]["pcode"]: shapely.make_valid(shape(f["geometry"])) for f in gj["features"]}


def monthly_cell_means(files):
    """Return (months, lat, lon, array[month, lat, lon]) of per-cell monthly mean discharge."""
    sums, counts, seen, lat, lon = {}, {}, set(), None, None
    for f in files:
        with xr.open_dataset(f) as ds:
            if VAR not in ds.variables:
                raise RuntimeError(f"{f}: variable '{VAR}' not found; variables are {list(ds.variables)}")
            if "valid_time" not in ds.variables:
                raise RuntimeError(f"{f}: no 'valid_time' coordinate; coordinates are {list(ds.coords)}")
            da = ds[VAR].squeeze(drop=True)
            if set(da.dims) != {"valid_time", "latitude", "longitude"}:
                raise RuntimeError(f"{f}: unexpected dims {da.dims} for {VAR}")
            da = da.transpose("valid_time", "latitude", "longitude")
            real = pd.DatetimeIndex(ds["valid_time"].values) - pd.Timedelta(days=1)
            vals = da.values.astype("float64")
            la, lo = ds["latitude"].values, ds["longitude"].values
            if lat is None:
                lat, lon = la, lo
            elif not (np.allclose(lat, la) and np.allclose(lon, lo)):
                raise RuntimeError(f"{f}: grid differs from the first file")
            dup = seen & set(real.normalize())
            if dup:
                raise RuntimeError(f"{f}: dates already read from another file: {sorted(dup)[:3]}")
            seen |= set(real.normalize())
            ym = real.year * 100 + real.month
            for key in np.unique(ym):
                sub = vals[ym == key]
                sums[key] = sums.get(key, 0) + np.nansum(sub, axis=0)
                counts[key] = counts.get(key, 0) + np.sum(~np.isnan(sub), axis=0)
    keys = sorted(sums)
    expected = set()
    for y in {d.year for d in seen}:
        expected |= set(pd.date_range(f"{y}-01-01", f"{y}-12-31"))
    known = {pd.Timestamp(v) - pd.Timedelta(days=1) for v in KNOWN_SOURCE_GAP_VALID_DATES}
    missing = sorted(expected - seen)
    unexpected = [d for d in missing if d not in known]
    if unexpected:
        raise RuntimeError(f"GloFAS files are missing {len(unexpected)} day(s) that are not a known source gap: "
                           f"{[d.strftime('%Y-%m-%d') for d in unexpected[:10]]}")
    gaps = [d for d in missing if d in known]
    if gaps:
        log(STAGE, "known source gap, not an error: no GloFAS data for " + ", ".join(d.strftime("%Y-%m-%d") for d in gaps)
            + " (valid_time " + ", ".join(KNOWN_SOURCE_GAP_VALID_DATES) + "); those months are means over their remaining days")
    days = {k: sum(1 for d in seen if d.year * 100 + d.month == k) for k in keys}
    short = [(k, days[k], monthrange(k // 100, k % 100)[1]) for k in keys if days[k] != monthrange(k // 100, k % 100)[1]]
    if short:
        log(STAGE, "months with fewer days than the calendar (mean over available days): " +
            ", ".join(f"{k // 100}-{k % 100:02d} ({n}/{N})" for k, n, N in short))
    arr = np.stack([np.where(counts[k] > 0, sums[k] / np.maximum(counts[k], 1), np.nan) for k in keys])
    GAPS_JSON.write_text(json.dumps({"known_gap_real_dates": [d.strftime("%Y-%m-%d") for d in gaps],
                                     "known_gap_valid_dates": list(KNOWN_SOURCE_GAP_VALID_DATES),
                                     "short_months": [f"{k // 100}-{k % 100:02d} ({n}/{N} days)" for k, n, N in short]}), encoding="utf-8")
    return keys, lat, lon, arr


def run(glofas_dir=RAW / "glofas", out_path=INTERIM / "glofas.csv", pending_only=False):
    grid = pd.read_csv(INTERIM / "grid.csv", usecols=["pcode", "year", "month"])
    cols = ["discharge_rank", "discharge_rank_lag1"]
    files = [] if pending_only else sorted(
        f for f in glob.glob(str(glofas_dir / "glofas_kenya_*.nc")) if re.search(r"glofas_kenya_\d{4}\.nc$", f))
    if not files:
        log(STAGE, "GloFAS pending: " + ("stage skipped and no earlier glofas.csv" if pending_only else "no glofas_kenya_<year>.nc files found")
            + "; discharge columns left as NaN")
        GAPS_JSON.unlink(missing_ok=True)
        out = grid.assign(discharge_rank=np.nan, discharge_rank_lag1=np.nan)
        out.to_csv(out_path, index=False)
        return
    years = [int(re.search(r"(\d{4})\.nc$", f).group(1)) for f in files]
    missing = sorted(set(range(min(years), max(years) + 1)) - set(years))
    log(STAGE, f"{len(files)} GloFAS files, years {min(years)}-{max(years)}; missing years inside range: {missing or 'none'}")
    if min(years) > 1999 or max(years) < 2025:
        log(STAGE, f"WARNING: coverage {min(years)}-{max(years)} does not span 1999-2025; unfilled months stay NaN")

    keys, lat, lon, arr = monthly_cell_means(files)
    lon2, lat2 = np.meshgrid(lon, lat)
    rows = []
    for pc, geom in county_polygons().items():
        inside = shapely.contains_xy(geom, lon2.ravel(), lat2.ravel()).reshape(lon2.shape)
        n = int(inside.sum())
        if n == 0:
            log(STAGE, f"WARNING: no GloFAS cell centre inside {pc}; discharge left NaN for this county")
            mx = np.full(len(keys), np.nan)
        else:
            cells = arr[:, inside]
            mx = np.where(np.isnan(cells).all(axis=1), np.nan, np.nanmax(np.where(np.isnan(cells), -np.inf, cells), axis=1))
        rows.append(pd.DataFrame({"pcode": pc, "year": [k // 100 for k in keys], "month": [k % 100 for k in keys],
                                  "discharge_max_cell": mx, "n_cells": n}))
    d = pd.concat(rows, ignore_index=True)
    # make every county's series contiguous so lags are exact
    full = pd.period_range(f"{keys[0] // 100}-{keys[0] % 100:02d}", f"{keys[-1] // 100}-{keys[-1] % 100:02d}", freq="M")
    ym = pd.DataFrame({"year": full.year, "month": full.month})
    d = pd.DataFrame({"pcode": sorted(d["pcode"].unique())}).merge(ym, how="cross").merge(d, how="left", on=["pcode", "year", "month"])
    d["discharge_rank"] = baseline_percentile(d, "discharge_max_cell", min_years=MIN_BASELINE_YEARS)
    base_years = (d[d["year"].between(BASE_START, BASE_END)].dropna(subset=["discharge_max_cell"])
                  .groupby(["pcode", "month"]).size().reindex(pd.MultiIndex.from_product([sorted(d["pcode"].unique()), range(1, 13)]), fill_value=0))
    enough = int((base_years >= MIN_BASELINE_YEARS).sum())
    log(STAGE, f"baseline years present per county+month: min {int(base_years.min())}, max {int(base_years.max())}; "
               f"{enough}/{len(base_years)} county+calendar-months have >= {MIN_BASELINE_YEARS} of 20, the rest stay NaN")
    d = add_lags(d, ["discharge_rank"], [1])
    d.to_csv(INTERIM / "glofas_county_month_max.csv", index=False)
    out = grid.merge(d[["pcode", "year", "month"] + cols], how="left", on=["pcode", "year", "month"])
    out.to_csv(out_path, index=False)
    log(STAGE, f"glofas.csv: {len(out)} rows; {out['discharge_rank'].isna().sum()} NaN discharge_rank")


if __name__ == "__main__":
    run()
