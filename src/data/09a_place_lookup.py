"""Stage 9a: build data/reference/place_to_county.csv from the DFO, EM-DAT Admin Units and EM-DAT Location text.

This only BUILDS the lookup and writes review files. It is not used for labels until the team confirms it.
Once confirmed, the CSV is the source of truth (edit it by hand); this script refuses to overwrite it unless
run with --force.

Outputs
  data/reference/place_to_county.csv       DFO rows only: place_raw, place_normalised, pcode, source, note, confidence
  data/private/place_to_county_emdat.csv   the EM-DAT rows (licence: never leaves data/private/)
  data/interim/place_review_dfo.csv        per DFO event x fragment (what the labels would use)
  data/private/place_review_emdat.csv      same for EM-DAT (private: derived from EM-DAT rows)
"""
import sys

import pandas as pd

from common import INTERIM, PRIVATE, load_crosswalk, log
from place_sources import (LOOKUP_COLS, LOOKUP_EMDAT, LOOKUP_PUBLIC, admin_unit_names, load_dfo_candidates,
                           load_emdat_floods)
from placenames import fragments, map_fragment, norm

STAGE = "09a_place_lookup"
OUT = LOOKUP_PUBLIC
GRID_START = pd.Timestamp("2000-01-01")
GRID_END = pd.Timestamp("2025-12-31")


def event_rows(source, event_id, items, cw):
    """items = list of (raw, normalised). Returns review rows."""
    name_to_pcode = dict(zip(cw["county"], cw["pcode"]))
    rows = []
    for raw, n in items:
        for county, conf, note in map_fragment(n):
            rows.append(dict(event=event_id, source=source, place_raw=raw, place_normalised=n,
                             pcode=name_to_pcode[county] if county else "", county=county or "",
                             confidence=conf, note=note))
    return rows


def run(force=False):
    if OUT.exists() and not force:
        raise SystemExit(f"{OUT} already exists (it may hold hand-confirmed edits). Re-run with --force to rebuild it.")
    cw = load_crosswalk()
    dfo_rows, em_rows, dropped = [], [], []

    dfo = load_dfo_candidates()
    for r in dfo.itertuples():
        if r.Ended < GRID_START or r.Began > GRID_END:
            dropped.append(f"DFO {int(r.Register__)} ({r.Began:%Y-%m}..{r.Ended:%Y-%m}) outside 2000-2025: not parsed")
            continue
        items = fragments(r.Detailed_L)
        if not items:
            dropped.append(f"DFO {int(r.Register__)} ({r.Began:%Y-%m}): Detailed_L empty after removing non-Kenya text")
        for row in event_rows("dfo_detailed_l", f"DFO-{int(r.Register__)}", items, cw):
            row.update(began=r.Began.date(), ended=r.Ended.date())
            dfo_rows.append(row)

    em = load_emdat_floods()
    for _, r in (em if em is not None else pd.DataFrame()).iterrows():
        eid = r["DisNo."]
        end_year = r["End Year"] if pd.notna(r["End Year"]) else r["Start Year"]
        if int(end_year) < 2000 or int(r["Start Year"]) > 2025:
            dropped.append(f"EM-DAT {eid} outside 2000-2025: not parsed")
            continue
        names = admin_unit_names(r["Admin Units"])
        if names:
            items, source = [(n, norm(n)) for n in names], "emdat_admin_units"
        else:
            loc = r["Location"]
            if not isinstance(loc, str) or not loc.strip():
                dropped.append(f"EM-DAT {eid}: empty Admin Units AND empty Location -> cannot be mapped (to be dropped)")
                continue
            items, source = fragments(loc), "emdat_location"
        em_rows += event_rows(source, eid, items, cw)

    dfo_df, em_df = pd.DataFrame(dfo_rows), pd.DataFrame(em_rows)
    PRIVATE.mkdir(exist_ok=True)
    dfo_df.to_csv(INTERIM / "place_review_dfo.csv", index=False)
    em_df.to_csv(PRIVATE / "place_review_emdat.csv", index=False)

    def collapse(df):
        out = (df.groupby(["place_normalised", "pcode", "source"], as_index=False, dropna=False)
               .agg(place_raw=("place_raw", "first"), note=("note", "first"), confidence=("confidence", "first")))
        return out[LOOKUP_COLS].sort_values(["confidence", "source", "place_normalised"]).reset_index(drop=True)

    pub = collapse(dfo_df)
    pub.to_csv(OUT, index=False)
    log(STAGE, f"{OUT.name} (DFO, public): {len(pub)} rows ({(pub.pcode != '').sum()} mapped, {(pub.pcode == '').sum()} unmapped)")
    if len(em_df):
        priv = collapse(em_df)
        priv.to_csv(LOOKUP_EMDAT, index=False)
        log(STAGE, f"{LOOKUP_EMDAT.name} (EM-DAT, private): {len(priv)} rows")
    for m in dropped:
        log(STAGE, "NOTE " + m)


if __name__ == "__main__":
    run(force="--force" in sys.argv)
