"""Loaders for the two place-based flood sources (DFO, EM-DAT) and for the place -> county lookup files.

The lookup is split for licensing: DFO rows live in data/reference/place_to_county.csv (public); EM-DAT rows
live in data/private/place_to_county_emdat.csv (git-ignored). load_lookup() reads both when present.
"""
import json

import pandas as pd
from dbfread import DBF

from common import PRIVATE, RAW, REFERENCE
from placenames import repair_text

DFO_DBF = RAW / "flood_labels" / "dfo_master_list" / "wlf_nhr_fl_dfomasterlist_20190418.dbf"
EMDAT_XLSX = RAW / "flood_labels" / "emdat" / "public_emdat_custom_request_2026-10-20.xlsx"
LOOKUP_PUBLIC = REFERENCE / "place_to_county.csv"
LOOKUP_EMDAT = PRIVATE / "place_to_county_emdat.csv"
LOOKUP_COLS = ["place_raw", "place_normalised", "pcode", "source", "note", "confidence"]


def load_dfo_candidates():
    """The 41 DFO rows that mention Kenya in any column."""
    d = pd.DataFrame(iter(DBF(str(DFO_DBF), load=True, encoding="latin-1")))
    is_ken = d.apply(lambda r: r.astype(str).str.contains("kenya", case=False).any(), axis=1)
    k = d[is_ken].copy()
    assert len(k) == 41, f"expected 41 DFO rows mentioning Kenya, found {len(k)}"
    k["Began"] = pd.to_datetime(k["Began"])
    k["Ended"] = pd.to_datetime(k["Ended"])
    k["Detailed_L"] = k["Detailed_L"].map(repair_text)
    return k


def load_emdat_floods():
    """The 56 Kenyan flood events, or None if the (git-ignored) EM-DAT file is not on this machine."""
    if not EMDAT_XLSX.exists():
        return None
    x = pd.read_excel(EMDAT_XLSX)
    k = x[(x["ISO"] == "KEN") & (x["Disaster Type"] == "Flood")].copy()
    assert len(k) == 56, f"expected 56 Kenyan EM-DAT floods, found {len(k)}"
    return k


def admin_unit_names(s):
    if not isinstance(s, str) or not s.strip():
        return []
    return [v for o in json.loads(s) for kk, v in o.items() if kk.endswith("_name")]


def load_lookup():
    """Public + private lookup rows. EM-DAT rows are simply absent on a machine without data/private/."""
    parts = [pd.read_csv(LOOKUP_PUBLIC, dtype=str).fillna("")]
    if LOOKUP_EMDAT.exists():
        parts.append(pd.read_csv(LOOKUP_EMDAT, dtype=str).fillna(""))
    return pd.concat(parts, ignore_index=True)


def lookup_dict(lookup, source_prefix):
    """{(source, place_normalised): set(pcode)} for mapped rows whose source starts with source_prefix."""
    m = lookup[(lookup["pcode"] != "") & lookup["source"].str.startswith(source_prefix)]
    out = {}
    for r in m.itertuples():
        out.setdefault((r.source, r.place_normalised), set()).add(r.pcode)
    return out
