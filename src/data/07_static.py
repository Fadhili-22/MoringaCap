"""Stage 7: static and slowly changing county features.

Static (one row per county): elevation, elev_std, slope, pct_flat, area_km2, lc_* shares (fractions),
river/water proximity shares, and pop_density = 2019 census population / KNBS LAND area (team decision: official
land area, static 2019 value, same on every row).
Slowly changing (county-month): pct_built (GHSL, linear interpolation between 1-Jan anchors of the 5-year points,
2025 held flat to Dec 2025).
"""
import numpy as np
import pandas as pd

from common import FIRST_YEAR, INTERIM, LAST_YEAR, RAW, ee_boundary_status, load_crosswalk, log, read_ee_county_csv

STAGE = "07_static"
LC_CLASSES = ["tree", "shrub", "grass", "crop", "built", "bare", "water", "wetland", "mangrove"]
PROX_KEEP = ["pct_within_1km_river", "pct_within_5km_river", "pct_within_1km_water", "pct_water", "pct_occasional_water"]


def static_table():
    srtm = read_ee_county_csv("srtm_elevation_slope_county", STAGE)
    srtm = srtm.rename(columns={"stdDev": "elev_std"})[["pcode", "elevation", "elev_std", "slope", "pct_flat"]]

    wc = read_ee_county_csv("worldcover_landcover_county", STAGE)
    wc = wc.rename(columns={f"pct_{c}": f"lc_{c}" for c in LC_CLASSES})
    wc = wc[["pcode", "area_km2"] + [f"lc_{c}" for c in LC_CLASSES]]
    share_sum = wc[[f"lc_{c}" for c in LC_CLASSES]].sum(axis=1)
    log(STAGE, f"land-cover shares sum to {share_sum.min():.5f}-{share_sum.max():.5f} (fractions, not %)")

    prox = read_ee_county_csv("proximity_rivers_water_county", STAGE, usecols=PROX_KEEP)
    log(STAGE, "dropped river_dist_m and water_dist_m (capped at 5 km, nearly constant)")

    st = srtm.merge(wc, on="pcode").merge(prox, on="pcode")
    assert len(st) == 47 and st["pcode"].is_unique and not st.isna().any().any()
    return st


def norm_name(s):
    return s.str.lower().str.replace(r"[^a-z]", "", regex=True)


def population_density():
    """Static pop_density by pcode = 2019 census population / KNBS land area. Raises if names do not map 1:1."""
    pop_dir = RAW / "population"
    files = sorted(p.name for p in pop_dir.iterdir() if p.is_file())
    log(STAGE, f"data/raw/population/ contains: {files}")
    p = pd.read_csv(pop_dir / "county_year_population.csv")
    log(STAGE, f"population file: {len(p)} rows, columns {p.columns.tolist()}, years {p.year.min()}-{p.year.max()}, "
               f"{p.county.nunique()} counties (an annual SERIES extrapolated from the 2019 census, not a 47-row table)")
    cw = load_crosswalk()
    miss_pop = sorted(set(p["county"]) - set(cw["county"]))
    miss_cw = sorted(set(cw["county"]) - set(p["county"]))
    log(STAGE, f"population names matching the crosswalk exactly: {47 - len(miss_cw)}/47; "
               f"only in population file: {miss_pop}; only in crosswalk: {miss_cw}")
    # Accept ONLY a spelling-level difference (case/punctuation) that maps one-to-one onto all 47 counties.
    cw["key"] = norm_name(cw["county"])
    p["key"] = norm_name(p["county"])
    if set(p["key"]) != set(cw["key"]) or cw["key"].nunique() != 47:
        raise RuntimeError(f"population county names do not map to the crosswalk: {miss_pop} / {miss_cw}")
    for a in miss_pop:
        b = cw.loc[cw["key"] == norm_name(pd.Series([a])).iloc[0], "county"].iloc[0]
        log(STAGE, f"MISMATCH resolved by punctuation only: population '{a}' -> crosswalk '{b}'")
    p = p[p["year"] == 2019].merge(cw[["key", "pcode"]], on="key", how="left")
    assert len(p) == 47 and p["pcode"].is_unique and not p["pcode"].isna().any()
    p["pop_density"] = p["population"] / p["land_area_km2"]
    log(STAGE, f"pop_density = 2019 census population / KNBS land_area_km2 (static); national 2019 population "
               f"{int(p['population'].sum()):,}; density range {p['pop_density'].min():.1f}-{p['pop_density'].max():.0f} per km2")
    return p[["pcode", "pop_density"]]


def builtup_monthly():
    g = read_ee_county_csv("ghsl_builtup_county_5yr", STAGE, usecols=["year", "pct_built"])
    anchors = [0, 60, 120, 180, 240, 300]  # months since 2000-01-01 of the 1-Jan 2000, 2005, ..., 2025 anchors
    assert sorted(g["year"].unique()) == [2000, 2005, 2010, 2015, 2020, 2025]
    rows = []
    for pc, gg in g.groupby("pcode"):
        gg = gg.sort_values("year")
        for y in range(FIRST_YEAR, LAST_YEAR + 1):
            for m in range(1, 13):
                t = (y - 2000) * 12 + m - 1
                rows.append((pc, y, m, float(np.interp(t, anchors, gg["pct_built"].to_numpy()))))  # holds 2025 flat
    return pd.DataFrame(rows, columns=["pcode", "year", "month", "pct_built"])


def run():
    status = ee_boundary_status()
    log(STAGE, "Earth Engine boundary source per file: " + ", ".join(f"{k}={v}" for k, v in status.items()))
    if len(set(status.values())) > 1:
        log(STAGE, "WARNING: Earth Engine files mix COD-AB and DesInventar polygons; run all five *_cod exports so features share one boundary set")
    st = static_table().merge(population_density(), on="pcode", validate="one_to_one")
    assert len(st) == 47 and not st.isna().any().any()
    st.to_csv(INTERIM / "static_county.csv", index=False)
    grid = pd.read_csv(INTERIM / "grid.csv", usecols=["pcode", "year", "month"])
    slow = grid.merge(builtup_monthly(), on=["pcode", "year", "month"], how="left")
    assert len(slow) == 14664 and slow["pct_built"].notna().all()
    slow.to_csv(INTERIM / "slow_county_month.csv", index=False)
    log(STAGE, f"static_county.csv {st.shape}, slow_county_month.csv {slow.shape}")


if __name__ == "__main__":
    run()
