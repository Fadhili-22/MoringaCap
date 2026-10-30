"""Stage 9a: build data/reference/place_to_county.csv from the DFO, EM-DAT Admin Units and EM-DAT Location text.

This only BUILDS the lookup and writes review files. It is not used for labels until the team confirms it.
Once confirmed, the CSV is the source of truth (edit it by hand); this script refuses to run unless --force is given,
and --force MERGES instead of overwriting:
  * an existing row whose confidence is "probable", or whose note says "user-confirmed" (hand-confirmed local
    knowledge), is PROTECTED: it is kept exactly, and any regenerated row for the same place + source is discarded;
  * every other existing row for a place the script generates again (certain / unmapped) is replaced by the new one;
  * existing rows for places the script does not generate are kept (hand-added lines are never dropped).
The previous file is copied to data/interim/<name>_before_force.csv first; protected rows whose mapping differs
from what the code would now generate are listed in the log so nobody is surprised.

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


def is_protected(df):
    """Hand-confirmed rows: confidence probable, or a note saying user-confirmed."""
    return (df["confidence"].str.strip().str.lower().isin(["probable", "user-confirmed"])
            | df["note"].str.lower().str.contains("user-confirmed", na=False))


def merge_into(path, new, label):
    """Write `new` (freshly generated rows) to `path`, keeping protected rows of the existing file. Returns merged df."""
    if not path.exists():
        new.to_csv(path, index=False)
        return new
    old = pd.read_csv(path, dtype=str).fillna("")
    old.to_csv(INTERIM / f"{path.stem}_before_force.csv", index=False)
    key = ["place_normalised", "source"]
    prot = old[is_protected(old)]
    prot_keys = set(map(tuple, prot[key].to_numpy()))
    old_keys = set(map(tuple, old[key].to_numpy()))
    new = new.fillna("")
    new_keys = new[key].apply(tuple, axis=1)
    fresh = new[~new_keys.isin(prot_keys)]
    kept_other = old[~is_protected(old) & ~old[key].apply(tuple, axis=1).isin(set(map(tuple, fresh[key].to_numpy())))]
    merged = (pd.concat([prot, kept_other, fresh], ignore_index=True)
              .drop_duplicates(LOOKUP_COLS).sort_values(["confidence", "source", "place_normalised"]).reset_index(drop=True))
    # report protected rows where the code would now say something different
    gen = new.groupby(key)["pcode"].apply(lambda x: ",".join(sorted(set(x)))).to_dict()
    differs = [(k, ",".join(sorted(set(prot[(prot[key[0]] == k[0]) & (prot[key[1]] == k[1])]["pcode"]))), gen[k])
               for k in sorted(prot_keys) if k in gen and gen[k] != ",".join(sorted(set(prot[(prot[key[0]] == k[0]) & (prot[key[1]] == k[1])]["pcode"])))]
    merged[LOOKUP_COLS].to_csv(path, index=False)
    log(STAGE, f"{label} MERGE: {len(prot)} protected rows kept ({len(prot_keys)} places), {len(fresh)} regenerated rows written, "
               f"{len(kept_other)} other existing rows kept, {len(old) - len(prot) - len(kept_other)} replaced; "
               f"{len(merged)} rows now (was {len(old)}); previous file saved as {path.stem}_before_force.csv")
    for k, was, would in differs:
        log(STAGE, f"NOTE protected {label} row {k[1]}:{k[0]!r} kept as {was or 'unmapped'}; the code would now give {would or 'unmapped'}")
    return merged


def run(force=False):
    if OUT.exists() and not force:
        raise SystemExit(f"{OUT} already exists (it may hold hand-confirmed edits). Re-run with --force to MERGE a fresh "
                         "build into it (probable / user-confirmed rows are kept as they are).")
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

    pub = merge_into(OUT, collapse(dfo_df), "DFO")
    log(STAGE, f"{OUT.name} (DFO, public): {len(pub)} rows ({(pub.pcode != '').sum()} mapped, {(pub.pcode == '').sum()} unmapped)")
    if len(em_df):
        priv = merge_into(LOOKUP_EMDAT, collapse(em_df), "EM-DAT")
        log(STAGE, f"{LOOKUP_EMDAT.name} (EM-DAT, private): {len(priv)} rows")
    for m in dropped:
        log(STAGE, "NOTE " + m)


if __name__ == "__main__":
    run(force="--force" in sys.argv)
