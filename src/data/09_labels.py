"""Stage 9: flood labels, one flag per source per county-month.

(a) DesInventar  (b) Global Flood Database  (c) DFO via the place lookup  (d) EM-DAT (private; skipped if the file is absent)
Place -> county comes from the confirmed lookup files (data/reference/place_to_county.csv + data/private/place_to_county_emdat.csv).
"""
import pandas as pd

from common import FIRST_YEAR, INTERIM, LAST_YEAR, PRIVATE, PROCESSED, RAW, codes_to_pcode, load_crosswalk, log
from place_sources import (EMDAT_XLSX, LOOKUP_EMDAT, admin_unit_names, load_dfo_candidates, load_emdat_floods, load_lookup,
                           lookup_dict)
from placenames import fragments, norm

STAGE = "09_labels"
NO_RECORD_YEARS = [2000, 2001, 2004, 2017, 2018, 2019]  # DesInventar has no records (2000-01 predate its coverage)
GFD_MIN_KM2 = 1.5
GRID_START, GRID_END = pd.Timestamp(f"{FIRST_YEAR}-01-01"), pd.Timestamp(f"{LAST_YEAR}-12-31")


def flag_months(grid, rows, name):
    """rows: iterable of (pcode, Period start, Period end) -> 0/1 column on the grid."""
    flagged = set()
    for pcode, start, end in rows:
        for p in pd.period_range(start, end, freq="M"):
            if FIRST_YEAR <= p.year <= LAST_YEAR:
                flagged.add((pcode, p.year, p.month))
    f = pd.DataFrame(sorted(flagged), columns=["pcode", "year", "month"]).assign(**{name: 1})
    out = grid.merge(f, how="left", on=["pcode", "year", "month"])
    out[name] = out[name].fillna(0).astype(int)
    return out[["pcode", "year", "month", name]]


def label_desinventar(grid):
    di = pd.read_csv(PROCESSED / "desinventar_floods_county_month.csv", dtype={"pcode": str})
    assert not di.duplicated(["pcode", "year", "month"]).any()
    assert ((di["flood_records"] > 0) == (di["flood_occurred"] == 1)).all()
    flagged = di[di["flood_occurred"] == 1][["pcode", "year", "month"]].assign(flood_desinventar=1)
    out = grid.merge(flagged, how="left", on=["pcode", "year", "month"])
    out["flood_desinventar"] = out["flood_desinventar"].fillna(0).astype(int)
    out["desinventar_no_record_year"] = out["year"].isin(NO_RECORD_YEARS).astype(int)
    empty = [y for y in range(FIRST_YEAR, LAST_YEAR + 1) if y not in set(di["year"])]
    assert empty == NO_RECORD_YEARS, f"no-record years in the data {empty} differ from the agreed list {NO_RECORD_YEARS}"
    log(STAGE, f"DesInventar: {len(flagged)} county-months flagged; no-record years {NO_RECORD_YEARS} flagged")
    return out[["pcode", "year", "month", "flood_desinventar", "desinventar_no_record_year"]]


def label_gfd(grid):
    g = pd.read_csv(RAW / "flood_labels" / "global_flood_database" / "kenya_gfd_county_floods.csv",
                    dtype={"county_code": str})
    n_all = len(g)
    g = g[g["flooded_km2"] >= GFD_MIN_KM2].copy()
    g["pcode"] = codes_to_pcode(g["county_code"], load_crosswalk())
    out = flag_months(grid, [(r.pcode, pd.Period(r.began, "M"), pd.Period(r.ended, "M")) for r in g.itertuples()], "flood_gfd")
    log(STAGE, f"GFD: {len(g)} of {n_all} county-event rows have flooded_km2 >= {GFD_MIN_KM2}; "
               f"{g['dfo_id'].nunique()} events; {int(out['flood_gfd'].sum())} county-months flagged")
    return out


def dfo_event_counties(lookup):
    """DFO events inside 2000-2025 -> (event table with mapped pcodes). Uses the confirmed lookup only."""
    m = lookup_dict(lookup, "dfo")
    rows, unmapped_frags = [], []
    for r in load_dfo_candidates().itertuples():
        if r.Ended < GRID_START or r.Began > GRID_END:
            continue
        pcodes = set()
        for _, n in fragments(r.Detailed_L):
            hit = m.get(("dfo_detailed_l", n))
            if hit:
                pcodes |= hit
            else:
                unmapped_frags.append((int(r.Register__), n))
        rows.append(dict(dfo_id=int(r.Register__), began=r.Began, ended=r.Ended, pcodes=sorted(pcodes)))
    return pd.DataFrame(rows), unmapped_frags


def label_dfo(grid, lookup):
    ev, _ = dfo_event_counties(lookup)
    kept = ev[ev["pcodes"].map(len) > 0]
    dropped = ev[ev["pcodes"].map(len) == 0]
    rows = [(p, pd.Period(r.began, "M"), pd.Period(r.ended, "M")) for r in kept.itertuples() for p in r.pcodes]
    out = flag_months(grid, rows, "flood_dfo")
    log(STAGE, f"DFO: {len(ev)} Kenyan events in 2000-2025; {len(kept)} kept (>=1 place mapped), {len(dropped)} dropped "
               f"{sorted(dropped['dfo_id'].tolist())}; {int(out['flood_dfo'].sum())} county-months flagged")
    return out


def label_emdat(grid, lookup):
    em = load_emdat_floods()
    if em is None:
        log(STAGE, "EM-DAT file not on this machine: flood_emdat left NaN (public variants are unaffected)")
        return grid[["pcode", "year", "month"]].assign(flood_emdat=pd.array([pd.NA] * len(grid), dtype="Int64")), {}
    m = lookup_dict(lookup, "emdat")
    if not LOOKUP_EMDAT.exists() or not m:
        # The EM-DAT file is on this machine but its place -> county lookup is not: every event would map to no
        # county and flood_emdat would silently be all zero (and flood_this_month would lose EM-DAT with no warning).
        raise RuntimeError(
            f"EM-DAT file is present ({EMDAT_XLSX.name}) but the private place lookup is missing or has no EM-DAT rows: "
            f"{LOOKUP_EMDAT}. Restore it, or rebuild it with `python src/data/09a_place_lookup.py --force` and review it. "
            "If you do not have the EM-DAT file, remove it from data/raw/flood_labels/emdat/ to build the public table only.")
    cw = load_crosswalk()
    rows, notes = [], {"dropped_no_location": [], "end_month_fixed": [], "outside_grid": [], "no_county": [], "location_parsed": []}
    for _, r in em.iterrows():
        eid, sy, sm = r["DisNo."], int(r["Start Year"]), int(r["Start Month"])
        if pd.isna(r["End Month"]):  # team decision for the one event with a blank End Month = single month, the Start Month
            ey, emon = sy, sm
            notes["end_month_fixed"].append(eid)
            log(STAGE, f"EM-DAT {eid}: blank End Month -> set to Start Month; span collapsed to {sy}-{sm:02d} (team decision)")
        else:
            ey, emon = int(r["End Year"]), int(r["End Month"])
        names = admin_unit_names(r["Admin Units"])
        if names:
            pcodes = set().union(*[m.get(("emdat_admin_units", norm(n)), set()) for n in names])
        else:
            loc = r["Location"]
            if not isinstance(loc, str) or not loc.strip():
                notes["dropped_no_location"].append(eid)
                log(STAGE, f"EM-DAT {eid}: empty Admin Units and empty Location -> dropped")
                continue
            pcodes = set().union(*[m.get(("emdat_location", n), set()) for _, n in fragments(loc)])
            notes["location_parsed"].append(eid)
        if sy > LAST_YEAR or ey < FIRST_YEAR:
            notes["outside_grid"].append(eid)
            log(STAGE, f"EM-DAT {eid}: outside 2000-2025 -> not used")
            continue
        if not pcodes:
            notes["no_county"].append(eid)
            log(STAGE, f"EM-DAT {eid}: no place mapped to a county -> dropped")
            continue
        rows += [(p, pd.Period(f"{sy}-{sm:02d}", "M"), pd.Period(f"{ey}-{emon:02d}", "M")) for p in pcodes]
    out = flag_months(grid, rows, "flood_emdat")
    if int(out["flood_emdat"].sum()) == 0:
        raise RuntimeError(f"EM-DAT labelling produced 0 flagged county-months from {len(em)} events: the lookup does not match "
                           "the file. Refusing to write an all-zero flood_emdat.")
    log(STAGE, f"EM-DAT: {len(em)} Kenyan floods; {int(out['flood_emdat'].sum())} county-months flagged "
               f"({len(notes['location_parsed'])} events parsed from Location text)")
    return out, notes


def run():
    grid = pd.read_csv(INTERIM / "grid.csv", usecols=["pcode", "year", "month"])
    lookup = load_lookup()
    key = ["pcode", "year", "month"]
    emdat, notes = label_emdat(grid, lookup)
    lab = (label_desinventar(grid).merge(label_gfd(grid), on=key).merge(label_dfo(grid, lookup), on=key)
           .merge(emdat, on=key))
    assert len(lab) == 14664 and not lab.duplicated(key).any()
    lab.to_csv(INTERIM / "labels_sources.csv", index=False)
    pd.Series({k: ",".join(v) for k, v in notes.items()}).to_csv(PRIVATE / "emdat_event_notes.csv", header=["events"])
    log(STAGE, "labels_sources.csv written")


if __name__ == "__main__":
    run()
