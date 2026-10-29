"""Shared paths, constants and helpers for the county-month model-table build."""
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
REFERENCE = DATA / "reference"
PROCESSED = DATA / "processed"
PRIVATE = DATA / "private"

FIRST_YEAR, LAST_YEAR = 2000, 2025
BASE_START, BASE_END = 2000, 2019  # "normal" / rank baseline = training years only

# Counties that have BOTH a level-1 row and level-2 rows in the WFP files: use level 1 only.
LEVEL1_PCODES = ["KE004", "KE008", "KE010", "KE019", "KE023", "KE037", "KE043", "KE047"]

LOG_FILE = INTERIM / "build_log.txt"


# Public table: drop every column that used EM-DAT, then rename the *_public ones to the standard names.
PUBLIC_DROP = ["flood_emdat", "n_sources", "flood_this_month", "flood_corroborated", "flood_next_month",
               "county_flood_rate"]
PUBLIC_RENAME = {"n_sources_public": "n_sources", "flood_this_month_public": "flood_this_month",
                 "flood_corroborated_public": "flood_corroborated", "flood_next_month_public": "flood_next_month",
                 "county_flood_rate_public": "county_flood_rate"}


def to_public(df):
    return df.drop(columns=PUBLIC_DROP).rename(columns=PUBLIC_RENAME)


def log(stage, msg):
    """Print and append to data/interim/build_log.txt."""
    INTERIM.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.now():%H:%M:%S} [{stage}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def pad2(s):
    return s.astype(str).str.strip().str.zfill(2)


def load_crosswalk():
    cw = pd.read_csv(REFERENCE / "kenya_county_crosswalk.csv", dtype=str)
    cw["desinventar_code"] = pad2(cw["desinventar_code"])
    assert len(cw) == 47 and cw["pcode"].is_unique and cw["desinventar_code"].is_unique
    return cw


def codes_to_pcode(codes, cw=None):
    """Map DesInventar-style 2-char county codes to pcode; raise on anything unmapped."""
    cw = load_crosswalk() if cw is None else cw
    m = dict(zip(cw["desinventar_code"], cw["pcode"]))
    out = pad2(codes).map(m)
    if out.isna().any():
        raise ValueError(f"unmapped county codes: {sorted(set(pad2(codes)[out.isna()]))}")
    return out


def read_county_code_csv(path, code_col, **kw):
    """Read a county-level CSV whose code column is a DesInventar code; add pcode."""
    df = pd.read_csv(path, dtype={code_col: str}, **kw)
    df["pcode"] = codes_to_pcode(df[code_col])
    return df


def knbs_land_area():
    """pcode -> official KNBS land area (km2), from land_area_km2 in data/raw/population/county_year_population.csv."""
    p = pd.read_csv(RAW / "population" / "county_year_population.csv")
    cw = load_crosswalk()
    key = lambda x: x.str.lower().str.replace(r"[^a-z]", "", regex=True)
    p["key"], cw["key"] = key(p["county"]), key(cw["county"])
    a = p.groupby("key")["land_area_km2"].agg(["min", "max"])
    assert (a["min"] == a["max"]).all(), "land_area_km2 varies within a county"
    m = cw.merge(a["min"].rename("km2"), left_on="key", right_index=True, how="left")
    if m["km2"].isna().any():
        raise ValueError(f"counties without a KNBS area: {m.loc[m['km2'].isna(), 'county'].tolist()}")
    return dict(zip(m["pcode"], m["km2"]))


EE_DIR = RAW / "earth_engine"
EE_STEMS = ["era5land_soil_runoff_county_month", "srtm_elevation_slope_county", "worldcover_landcover_county",
            "proximity_rivers_water_county", "ghsl_builtup_county_5yr"]


def ee_boundary_status():
    """For each Earth Engine county file: 'cod' if <stem>_cod.csv exists (OCHA COD-AB polygons), else 'desinventar'."""
    return {s: "cod" if (EE_DIR / f"{s}_cod.csv").exists() else "desinventar" for s in EE_STEMS}


def read_ee_county_csv(stem, stage, usecols=None):
    """Read an Earth Engine county export, preferring <stem>_cod.csv (keyed by pcode) over <stem>.csv (COUNTYCO).

    Returns pcode + the requested columns. The COD file's pcodes (and county names, if present) are checked
    against the crosswalk; nothing is guessed.
    """
    cod = EE_DIR / f"{stem}_cod.csv"
    if cod.exists():
        df = pd.read_csv(cod, dtype={"pcode": str})
        cw = load_crosswalk()
        if set(df["pcode"]) != set(cw["pcode"]):
            raise ValueError(f"{cod.name}: pcodes differ from the crosswalk "
                             f"(extra {sorted(set(df['pcode']) - set(cw['pcode']))}, missing {sorted(set(cw['pcode']) - set(df['pcode']))})")
        if "county" in df.columns:
            key = lambda x: x.str.lower().str.replace(r"[^a-z]", "", regex=True)
            m = df[["pcode", "county"]].drop_duplicates().merge(cw[["pcode", "county"]], on="pcode", suffixes=("", "_cw"))
            bad = m[key(m["county"]) != key(m["county_cw"])]
            if len(bad):
                raise ValueError(f"{cod.name}: county names disagree with the crosswalk: {bad.values.tolist()}")
        log(stage, f"{stem}: using {cod.name} (OCHA COD-AB polygons, keyed by pcode)")
    else:
        df = read_county_code_csv(EE_DIR / f"{stem}.csv", "COUNTYCO")
        log(stage, f"{stem}: {stem}_cod.csv not found, falling back to {stem}.csv (DesInventar polygons, COUNTYCO)")
    return df if usecols is None else df[["pcode"] + list(usecols)]


def add_lags(df, cols, lags):
    """Add <col>_lag<k> within pcode. df must hold every month of a contiguous series per pcode."""
    df = df.sort_values(["pcode", "year", "month"]).reset_index(drop=True)
    t = df["year"] * 12 + df["month"] - 1
    step = t.groupby(df["pcode"]).diff().dropna()
    assert (step == 1).all(), "months are not contiguous within pcode; lags would be wrong"
    for c in cols:
        for k in lags:
            df[f"{c}_lag{k}"] = df.groupby("pcode")[c].shift(k)
    return df


def baseline_mean(df, col):
    """Mean of col per (pcode, calendar month) over BASE_START-BASE_END, aligned to df's rows."""
    base = df[df["year"].between(BASE_START, BASE_END)]
    m = base.groupby(["pcode", "month"])[col].mean().rename("_normal")
    return df.join(m, on=["pcode", "month"])["_normal"]


def baseline_percentile(df, col):
    """Mid-rank percentile (0-1) of col among the same pcode + calendar month in BASE years.

    Ties get the average rank, so a block of identical values (e.g. zero runoff) maps to its middle.
    """
    out = pd.Series(np.nan, index=df.index)
    for _, g in df.groupby(["pcode", "month"]):
        base = np.sort(g.loc[g["year"].between(BASE_START, BASE_END), col].dropna().to_numpy())
        if len(base) == 0:
            continue
        x = g[col].to_numpy()
        lo = np.searchsorted(base, x, side="left")
        hi = np.searchsorted(base, x, side="right")
        r = (lo + hi) / 2 / len(base)
        r[np.isnan(x)] = np.nan
        out.loc[g.index] = r
    return out


def wfp_county_dekads(path, value_col, stage):
    """WFP/HDX subnational file -> one row per (pcode, dekad date) for the 47 counties.

    Level-1 counties use their level-1 row only; all others use their level-2 rows (matched by
    the first 5 characters of PCODE) combined as the n_pixels-weighted mean. 2026 rows dropped.
    """
    d = pd.read_csv(path, dtype={"PCODE": str}, usecols=["date", "adm_level", "PCODE", "n_pixels", value_col])
    d["date"] = pd.to_datetime(d["date"])
    assert set(d["adm_level"]) <= {1, 2}
    d = d[d["date"].dt.year <= LAST_YEAR]
    l1 = d[d["adm_level"] == 1]
    assert sorted(l1["PCODE"].unique()) == LEVEL1_PCODES, "level-1 county set differs from the agreed list"
    l1 = l1.rename(columns={"PCODE": "pcode"})[["pcode", "date", value_col]]
    l2 = d[d["adm_level"] == 2].copy()
    l2["pcode"] = l2["PCODE"].str[:5]
    ignored = l2.loc[l2["pcode"].isin(LEVEL1_PCODES), "PCODE"].nunique()
    l2 = l2[~l2["pcode"].isin(LEVEL1_PCODES)]
    l2["w"] = l2[value_col] * l2["n_pixels"]
    g = l2.groupby(["pcode", "date"]).agg(w=("w", "sum"), n=("n_pixels", "sum"))
    l2c = (g["w"] / g["n"]).rename(value_col).reset_index()
    areas = l2.groupby("pcode")["PCODE"].nunique()
    log(stage, f"{Path(path).name}: {len(LEVEL1_PCODES)} level-1 counties; {ignored} level-2 PCODEs inside them ignored; "
               f"{len(areas)} level-2-only counties ({(areas == 1).sum()} single-area, {(areas > 1).sum()} weighted)")
    out = pd.concat([l1, l2c], ignore_index=True)
    assert out["pcode"].nunique() == 47 and not out.duplicated(["pcode", "date"]).any()
    assert not out[value_col].isna().any()
    return out


def dekads_to_months(d, value_col, how, stage):
    """Aggregate dekads to months, asserting exactly 3 dekads per county-month."""
    d = d.assign(year=d["date"].dt.year, month=d["date"].dt.month)
    g = d.groupby(["pcode", "year", "month"])[value_col]
    n = g.size()
    assert (n == 3).all(), f"{stage}: {(n != 3).sum()} county-months do not have exactly 3 dekads"
    agg = g.agg(how)
    if isinstance(agg, pd.Series):
        agg = agg.rename(value_col)
    return agg.reset_index()
