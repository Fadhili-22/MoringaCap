"""Stage 3: county adjacency from the county polygons, then neighbour rainfall.

Counties are adjacent if their polygons touch after a tiny buffer (absorbs slivers between polygons).
neighbour_rain = mean rain_mm of the neighbours in the same month; neighbour_rain_lag1 = previous month's
value (computed on the full series before trimming to 2000-2025).
"""
import json

import pandas as pd
import shapely
from shapely.geometry import shape
from shapely.strtree import STRtree

from common import FIRST_YEAR, INTERIM, REFERENCE, add_lags, load_crosswalk, log

STAGE = "03_neighbours"
BUFFER_DEG = 0.001  # ~110 m
KM_PER_DEG = 111.32


def build_adjacency():
    gj = json.load(open(REFERENCE / "kenya_counties.geojson", encoding="utf-8"))
    geoms = {f["properties"]["pcode"]: shapely.make_valid(shape(f["geometry"])) for f in gj["features"]}
    assert len(geoms) == 47
    pcodes = sorted(geoms)
    buffered = [geoms[p].buffer(BUFFER_DEG) for p in pcodes]
    tree = STRtree(buffered)
    rows = []
    for i, p in enumerate(pcodes):
        for j in tree.query(buffered[i], predicate="intersects"):
            if j == i:
                continue
            border_km = geoms[p].boundary.intersection(buffered[j]).length * KM_PER_DEG
            rows.append((p, pcodes[j], round(border_km, 1)))
    adj = pd.DataFrame(rows, columns=["pcode", "neighbour_pcode", "approx_shared_border_km"])
    return adj, pcodes


def run():
    adj, pcodes = build_adjacency()
    cw = load_crosswalk().set_index("pcode")["county"]
    counts = adj.groupby("pcode").size().reindex(pcodes).fillna(0).astype(int)
    zero = counts[counts == 0]
    if len(zero):
        raise RuntimeError(f"counties with 0 neighbours: {[f'{p} {cw[p]}' for p in zero.index]}")
    pairs = set(zip(adj.pcode, adj.neighbour_pcode))
    assert all((b, a) in pairs for a, b in pairs), "adjacency is not symmetric"
    adj.to_csv(REFERENCE / "county_adjacency.csv", index=False)
    log(STAGE, f"county_adjacency.csv: {len(adj)} directed pairs ({len(adj) // 2} borders)")
    log(STAGE, "neighbour counts: " + ", ".join(f"{cw[p]}={counts[p]}" for p in pcodes))
    short = adj[(adj.approx_shared_border_km < 2) & (adj.pcode < adj.neighbour_pcode)]
    if len(short):
        log(STAGE, "NOTE borders < 2 km (possible corner touches, still counted as neighbours): " +
            "; ".join(f"{cw[a]}-{cw[b]} {km} km" for a, b, km in short.itertuples(index=False)))

    rain = pd.read_csv(INTERIM / "rainfall_monthly_full.csv")
    wide = rain.pivot(index=["year", "month"], columns="pcode", values="rain_mm").sort_index()
    assert not wide.isna().any().any()
    A = pd.crosstab(adj.pcode, adj.neighbour_pcode).reindex(index=wide.columns, columns=wide.columns, fill_value=0)
    A = A.div(A.sum(axis=1), axis=0)
    nr = pd.DataFrame(wide.to_numpy() @ A.to_numpy().T, index=wide.index, columns=wide.columns)
    long = nr.stack().rename("neighbour_rain").reset_index()
    long = add_lags(long, ["neighbour_rain"], [1])
    out = long[long["year"] >= FIRST_YEAR][["pcode", "year", "month", "neighbour_rain", "neighbour_rain_lag1"]]
    assert len(out) == 14664 and out.notna().all().all()
    out.to_csv(INTERIM / "neighbour_rain.csv", index=False)
    log(STAGE, f"neighbour_rain.csv: {len(out)} rows")


if __name__ == "__main__":
    run()
