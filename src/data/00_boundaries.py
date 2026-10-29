"""Stage 0: county polygons from the OCHA COD-AB admin-1 layer, plus a LAND-ONLY version.

The DesInventar polygons (data/raw/boundaries/lev_0.*) do not follow the official boundaries for Bomet,
Murang'a, Kericho and Kiambu, so the official COD-AB layer is used. COD-AB county polygons include the Kenyan
part of Lake Victoria and Lake Turkana, so large natural lakes are cut out (Natural Earth 10m lakes v5.0.0):

    Lake Victoria, Lake Turkana, Lake Natron (a 1.4 km2 border sliver in Kajiado).

Small lakes and dams (e.g. Masinga Reservoir) stay in, so pct_water keeps its old meaning.

Outputs
  data/raw/boundaries/cod_ab/kenya_counties_cod_land.{shp,shx,dbf,prj,cpg}   fields: pcode, county   (upload to EE)
  data/reference/kenya_counties.geojson        LAND-ONLY, crosswalk fields; used by adjacency + GloFAS county max
  data/reference/kenya_counties_full.geojson   unclipped COD-AB; for the dashboard map only
"""
import json

import numpy as np
import pandas as pd
import shapefile  # pyshp
import shapely
from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.geometry.polygon import orient

from common import RAW, REFERENCE, knbs_land_area, load_crosswalk, log

STAGE = "00_boundaries"
COD_SHP = RAW / "boundaries" / "cod_ab" / "ken_admin1.shp"
LAND_SHP = RAW / "boundaries" / "cod_ab" / "kenya_counties_cod_land.shp"
LAKES_SHP = RAW / "boundaries" / "natural_earth_lakes" / "ne_10m_lakes.shp"
LAKES_REMOVED = ["Lake Victoria", "Lake Turkana", "Lake Natron"]
OUT_LAND = REFERENCE / "kenya_counties.geojson"
OUT_FULL = REFERENCE / "kenya_counties_full.geojson"
WGS84_PRJ = ('GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],'
             'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]')

_to_ea = Transformer.from_crs(4326, 6933, always_xy=True).transform  # equal-area, for km2


def area_km2(g):
    if g.is_empty:
        return 0.0
    ea = shapely.transform(g, lambda c: np.column_stack(_to_ea(c[:, 0], c[:, 1])))
    return ea.area / 1e6


def _round(coords, nd=6):
    if isinstance(coords[0], (int, float)):
        return [round(c, nd) for c in coords]
    return [_round(c, nd) for c in coords]


def _orient(g):
    if g.geom_type == "Polygon":
        return orient(g, 1.0)
    return type(g)([orient(p, 1.0) for p in g.geoms])


def load_cod():
    sf = shapefile.Reader(str(COD_SHP), encoding="utf-8")
    assert len(sf) == 47, f"expected 47 admin-1 features, found {len(sf)}"
    cw = load_crosswalk().set_index("pcode")
    out = {}
    for sr in sf.shapeRecords():
        pcode = sr.record["adm1_pcode"]
        if pcode not in cw.index or pcode in out:
            raise RuntimeError(f"COD-AB pcode {pcode!r} is not a unique crosswalk pcode")
        g = shape(sr.shape.__geo_interface__)
        if not g.is_valid:
            raise RuntimeError(f"{pcode}: invalid COD-AB geometry")
        out[pcode] = g
    assert set(out) == set(cw.index)
    return out


def load_lakes():
    sf = shapefile.Reader(str(LAKES_SHP), encoding="utf-8")
    out = {}
    for sr in sf.shapeRecords():
        name = sr.record["name"]
        if name in LAKES_REMOVED:
            assert name not in out, f"more than one polygon named {name}"
            out[name] = shapely.make_valid(shape(sr.shape.__geo_interface__))
    assert set(out) == set(LAKES_REMOVED), f"lakes not found in Natural Earth layer: {set(LAKES_REMOVED) - set(out)}"
    return out


def write_geojson(geoms, path):
    cw = load_crosswalk().set_index("pcode")
    feats = []
    for pcode in sorted(geoms):
        geom = mapping(_orient(geoms[pcode]))
        row = cw.loc[pcode]
        feats.append({"type": "Feature",
                      "properties": {"county": row["county"], "knbs_code": int(row["knbs_code"]), "pcode": pcode,
                                     "desinventar_code": row["desinventar_code"], "desinventar_name": row["desinventar_name"]},
                      "geometry": {"type": geom["type"], "coordinates": _round(geom["coordinates"])}})
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": feats}, f, separators=(",", ":"))


def write_land_shapefile(geoms):
    cw = load_crosswalk().set_index("pcode")["county"]
    with shapefile.Writer(str(LAND_SHP), shapeType=shapefile.POLYGON, encoding="utf-8") as w:
        w.field("pcode", "C", 5)
        w.field("county", "C", 40)
        for pcode in sorted(geoms):
            w.record(pcode, cw[pcode])
            w.shape(mapping(_orient(geoms[pcode])))
    LAND_SHP.with_suffix(".prj").write_text(WGS84_PRJ, encoding="ascii")
    LAND_SHP.with_suffix(".cpg").write_text("UTF-8", encoding="ascii")


def run():
    full = load_cod()
    lakes = load_lakes()
    cw = load_crosswalk().set_index("pcode")["county"]
    knbs = knbs_land_area()

    land, lost = {}, []
    for pcode, g in full.items():
        h = g
        for lname, lake in lakes.items():
            inter = g.intersection(lake)
            a = area_km2(inter)
            if a > 0:
                lost.append((lname, cw[pcode], a))
            h = h.difference(lake)
        h = shapely.make_valid(h)
        if h.geom_type == "GeometryCollection":  # drop stray lines/points left by the difference
            h = shapely.union_all([p for p in h.geoms if p.geom_type in ("Polygon", "MultiPolygon")])
        assert not h.is_empty and h.is_valid, f"{pcode}: land-only geometry is empty/invalid"
        land[pcode] = h

    write_geojson(full, OUT_FULL)
    write_geojson(land, OUT_LAND)
    write_land_shapefile(land)

    # read the shapefile back: same features, same areas
    sf = shapefile.Reader(str(LAND_SHP), encoding="utf-8")
    assert len(sf) == 47 and [f[0] for f in sf.fields[1:]] == ["pcode", "county"]
    for sr in sf.shapeRecords():
        back = shape(sr.shape.__geo_interface__)
        assert back.is_valid and abs(area_km2(back) / area_km2(land[sr.record["pcode"]]) - 1) < 1e-6

    lost_df = pd.DataFrame(lost, columns=["lake", "county", "km2"])
    log(STAGE, "lake area cut from COD-AB polygons (km2): " +
        "; ".join(f"{r.lake} / {r.county} {r.km2:,.0f}" for r in lost_df.sort_values("km2", ascending=False).itertuples()))
    ratio = pd.DataFrame({"county": [cw[p] for p in land], "full": [area_km2(full[p]) for p in land],
                          "land": [area_km2(land[p]) for p in land], "knbs": [knbs[p] for p in land]})
    ratio["full/knbs"], ratio["land/knbs"] = ratio.full / ratio.knbs, ratio.land / ratio.knbs
    log(STAGE, f"land-only area / KNBS land area: median {ratio['land/knbs'].median():.3f}, min {ratio['land/knbs'].min():.3f}, "
               f"max {ratio['land/knbs'].max():.3f}; sum land {ratio.land.sum():,.0f} vs KNBS {ratio.knbs.sum():,.0f} km2")
    ratio.round(3).to_csv(REFERENCE.parent / "interim" / "boundary_area_check.csv", index=False)
    log(STAGE, f"wrote {LAND_SHP.name} (+shx/dbf/prj/cpg), {OUT_LAND.name} (land-only, {OUT_LAND.stat().st_size / 1e6:.1f} MB), "
               f"{OUT_FULL.name} (unclipped, for the dashboard map only)")


if __name__ == "__main__":
    run()
