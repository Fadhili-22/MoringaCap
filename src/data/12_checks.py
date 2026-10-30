"""Stage 12: checks on the assembled table, written to a report.

Two reports are written so no EM-DAT-derived number leaves data/private/ by accident:
  data/processed/build_report.md     everything WITHOUT EM-DAT (public label variants, no EM-DAT event IDs)
  data/private/build_report_full.md  the same checks including EM-DAT (git-ignored)
Hard failures (structure, duplicate keys, shifted-feature mismatches) raise; everything else is reported.
"""
import numpy as np
import pandas as pd

from common import (public_label_coverage_text, FIRST_YEAR, INTERIM, LAST_YEAR, LEVEL1_PCODES, LOG_FILE, PRIVATE, PROCESSED, RAW, ee_boundary_status,
                    load_crosswalk, log, to_public)
from place_sources import load_lookup

STAGE = "12_checks"
SEASONS = {"JF": [1, 2], "MAM": [3, 4, 5], "JJAS": [6, 7, 8, 9], "OND": [10, 11, 12]}


def md(df, floatfmt=None):
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)):
                v = "" if pd.isna(v) else (floatfmt.get(c, "{:.4g}").format(v) if floatfmt else f"{v:.4g}")
            cells.append(str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


# ---------------------------------------------------------------------------------------------------- structure
def check_structure(t):
    key = ["pcode", "year", "month"]
    n_months = t.groupby("pcode").size()
    res = [("rows == 14,664", len(t) == 14664, len(t)),
           ("no duplicate (pcode, year, month)", not t.duplicated(key).any(), int(t.duplicated(key).sum())),
           ("47 pcodes", t["pcode"].nunique() == 47, t["pcode"].nunique()),
           ("pcodes == crosswalk KE001-KE047", set(t["pcode"]) == set(load_crosswalk()["pcode"]), ""),
           ("312 months per county", bool((n_months == 312).all()), f"{n_months.min()}-{n_months.max()}"),
           ("years 2000-2025", t["year"].min() == FIRST_YEAR and t["year"].max() == LAST_YEAR, f"{t['year'].min()}-{t['year'].max()}")]
    bad = [r[0] for r in res if not r[1]]
    if bad:
        raise AssertionError(f"structure checks failed: {bad}")
    return pd.DataFrame([(a, "PASS", c) for a, ok, c in res], columns=["check", "result", "value"])


def null_report(t, glofas_state, has_emdat):
    n = t.isna().sum()
    n = n[n > 0]
    expected = {
        "ndvi": (47 * 30, "NDVI record starts 2002-07 (47 counties x 30 months, Jan 2000-Jun 2002); not filled"),
        "ndvi_pct_normal": (47 * 30, "same: no NDVI before 2002-07"),
        "flood_next_month": (47, "Dec 2025 target: no Jan 2026 row in the table (47 counties)"),
        "flood_next_month_public": (47, "Dec 2025 target (47 counties)"),
        "heavy_rain_next_month": (47, "Dec 2025 target (47 counties)"),
    }
    for c in ["discharge_rank", "discharge_rank_lag1"]:
        if glofas_state == "pending":
            expected[c] = (len(t), "GloFAS pending: no files downloaded yet")
        elif glofas_state == "partial":
            expected[c] = (None, "GloFAS partial: a rank needs >= 15 of the 20 baseline years (2000-2019) for that county + calendar month")
    rows = []
    for c in t.columns:
        k = int(t[c].isna().sum())
        if k == 0:
            continue
        e = expected.get(c)
        if e and e[0] is not None:
            status = "as expected" if e[0] == k else f"UNEXPECTED count (expected {e[0]})"
            rows.append((c, k, e[1], status))
        elif e:
            rows.append((c, k, e[1], "check: is it the expected GloFAS coverage?"))
        else:
            rows.append((c, k, "none expected", "UNEXPECTED"))
    df = pd.DataFrame(rows, columns=["column", "nulls", "reason", "status"])
    return df, (df["status"].str.startswith("UNEXPECTED").any() if len(df) else False)


# ---------------------------------------------------------------------------------------------------- floods
def flood_tables(t, sources):
    cols = sources + ["flood_this_month", "flood_corroborated"]
    by_year = t.groupby("year")[cols].mean().reset_index()
    di_gap = t.groupby("year")["desinventar_no_record_year"].max()
    by_year["DI no-record yr"] = by_year["year"].map(di_gap).map({0: "", 1: "yes"})
    tot = pd.DataFrame({"source": cols, "county-months flagged": [int(t[c].sum()) for c in cols],
                        "share": [t[c].mean() for c in cols]})
    return by_year, tot


def agreement(t, groups):
    names = list(groups)
    m = pd.DataFrame(index=names, columns=names, dtype=float)
    for a in names:
        for b in names:
            m.loc[a, b] = float(((t[groups[a]] == 1) & (t[groups[b]] == 1)).sum())
    return m.astype(int).reset_index().rename(columns={"index": "(both flagged)"})


def seasonal(t, col):
    mon = t.groupby("month").agg(flood_share=(col, "mean"), mean_rain_mm=("rain_mm", "mean")).reset_index()
    seas = pd.DataFrame([(s, t[t["month"].isin(ms)][col].mean()) for s, ms in SEASONS.items()], columns=["season", "flood_share"])
    return mon, seas


def top_counties(t, col, rate_col):
    g = t.groupby(["pcode", "county"]).agg(raw_share=(col, "mean"), flood_months=(col, "sum"), county_flood_rate=(rate_col, "first")).reset_index()
    return g.sort_values("raw_share", ascending=False).head(10).drop(columns="pcode")


# ---------------------------------------------------------------------------------------------------- sanity
def rain_by_hand(t):
    """3 county-months recomputed straight from the raw CHIRPS file (independent of the pipeline code)."""
    raw = pd.read_csv(RAW / "rainfall" / "ken-rainfall-subnat-full.csv", dtype={"PCODE": str},
                      usecols=["date", "adm_level", "PCODE", "n_pixels", "rfh"])
    raw["date"] = pd.to_datetime(raw["date"])
    rng = np.random.default_rng(20261029)
    l2 = raw[raw["adm_level"] == 2].assign(pc=lambda d: d["PCODE"].str[:5])
    multi = sorted(l2[~l2["pc"].isin(LEVEL1_PCODES)].groupby("pc")["PCODE"].nunique().loc[lambda s: s > 1].index)
    picks = [(t["pcode"].iloc[i], int(t["year"].iloc[i]), int(t["month"].iloc[i])) for i in rng.integers(0, len(t), 2)]
    picks.append((multi[rng.integers(0, len(multi))], int(rng.integers(FIRST_YEAR, LAST_YEAR + 1)), int(rng.integers(1, 13))))
    rows = []
    for pc, y, mth in picks:
        win = (raw["date"].dt.year == y) & (raw["date"].dt.month == mth)
        if pc in LEVEL1_PCODES:
            d = raw[win & (raw["adm_level"] == 1) & (raw["PCODE"] == pc)]
            by_hand, kind = d["rfh"].sum(), "level-1 row"
        else:
            d = raw[win & (raw["adm_level"] == 2) & (raw["PCODE"].str[:5] == pc)]
            per = d.groupby("date").apply(lambda g: (g["rfh"] * g["n_pixels"]).sum() / g["n_pixels"].sum())
            by_hand, kind = per.sum(), f"{d['PCODE'].nunique()} level-2 area(s), n_pixels-weighted"
        got = t[(t["pcode"] == pc) & (t["year"] == y) & (t["month"] == mth)]["rain_mm"].iloc[0]
        rows.append((pc, f"{y}-{mth:02d}", kind, round(by_hand, 4), round(got, 4), f"{abs(by_hand - got):.1e}"))
        assert abs(by_hand - got) < 1e-6, f"rain_mm mismatch for {pc} {y}-{mth}"
    return pd.DataFrame(rows, columns=["pcode", "month", "raw CHIRPS rule", "by hand (mm)", "table rain_mm (mm)", "abs diff"])


def shift_checks(t):
    """Exhaustive (not spot) checks that lags look back and next-month targets look forward."""
    t = t.sort_values(["pcode", "year", "month"]).reset_index(drop=True)
    g = t.groupby("pcode")
    res = []

    def same(a, b):
        a, b = pd.Series(a), pd.Series(b)
        m = a.notna() & b.notna()
        if m.sum() == 0:
            return None, 0  # nothing to compare (e.g. GloFAS pending)
        return bool(np.allclose(a[m], b[m], rtol=0, atol=1e-9)), int(m.sum())

    for lag_col, base, k in [("rain_lag1", "rain_mm", 1), ("rain_lag2", "rain_mm", 2), ("neighbour_rain_lag1", "neighbour_rain", 1),
                             ("soil_moisture_l1_lag1", "soil_moisture_l1", 1), ("soil_moisture_l2_lag1", "soil_moisture_l2", 1),
                             ("oni_lag1", "oni", 1), ("oni_lag2", "oni", 2), ("oni_lag3", "oni", 3),
                             ("dmi_lag1", "dmi", 1), ("dmi_lag2", "dmi", 2), ("dmi_lag3", "dmi", 3),
                             ("discharge_rank_lag1", "discharge_rank", 1)]:
        ok, n = same(t[lag_col], g[base].shift(k))
        res.append((f"{lag_col} == {base} {k} month(s) earlier", ok, n))
    ok, n = same(t["rain_3mo_total"], t["rain_mm"] + g["rain_mm"].shift(1) + g["rain_mm"].shift(2))
    res.append(("rain_3mo_total == this month + 2 before", ok, n))
    pairs = [("flood_next_month_public", "flood_this_month_public")] if "flood_this_month_public" in t else []
    pairs += [("flood_next_month", "flood_this_month")]
    for tgt, base in pairs:
        if t[base].notna().any():
            ok, n = same(t[tgt].astype(float), g[base].shift(-1).astype(float))
            res.append((f"{tgt} == {base} one month LATER", ok, n))
    nxt = g["rain_pct_normal"].shift(-1)
    ok, n = same(t["heavy_rain_next_month"].astype(float), (nxt > 1.25).astype(float).where(nxt.notna()))
    res.append(("heavy_rain_next_month == (next month rain_pct_normal > 1.25)", ok, n))
    last = (t["year"] == 2025) & (t["month"] == 12)
    res.append(("Dec 2025 targets are NaN", bool(t.loc[last, [c for c in ["flood_next_month", "flood_next_month_public", "heavy_rain_next_month"] if c in t]].isna().all().all()), int(last.sum())))
    jan = t[(t["year"] == 2000) & (t["month"] == 1)]
    res.append(("Jan 2000 lags are filled (computed before trimming)",
                bool(jan[["rain_lag1", "rain_lag2", "rain_3mo_total", "neighbour_rain_lag1", "soil_moisture_l1_lag1", "oni_lag3", "dmi_lag3"]].notna().all().all()), len(jan)))
    # ONI shift against the raw file: oni at t == published ONI at t-1
    o = pd.read_csv(RAW / "climate_indices" / "oni.csv")
    o.columns = ["date", "v"]
    o["v"] = o["v"].replace(-9999, np.nan)
    d = pd.to_datetime(o["date"])
    pub = dict(zip(zip(d.dt.year, d.dt.month), o["v"]))
    one = t.drop_duplicates(["year", "month"])
    exp = [pub[(y - 1, 12)] if m == 1 else pub[(y, m - 1)] for y, m in zip(one["year"], one["month"])]
    ok, n = same(one["oni"], exp)
    res.append(("oni at month t == published ONI for month t-1 (raw oni.csv)", ok, n))
    df = pd.DataFrame([(a, "SKIPPED (no data yet)" if ok is None else ("PASS" if ok else "FAIL"), n) for a, ok, n in res],
                      columns=["check", "result", "rows compared"])
    if (df["result"] == "FAIL").any():
        raise AssertionError("shift checks failed:\n" + df[df["result"] == "FAIL"].to_string())
    return df


# ---------------------------------------------------------------------------------------------------- report
def notes_from_log(include_emdat):
    keep = ("[00_boundaries]", "[03_neighbours]", "[06_era5land]", "[07_static]", "[08_glofas]", "[09_labels]", "[02_rainfall] RESULT",
            "[05_climate]", "[10_labels_combined]", "[11_history]")
    lines = [l for l in LOG_FILE.read_text(encoding="utf-8").splitlines() if any(k in l for k in keep)]
    if not include_emdat:
        lines = [l for l in lines if "EM-DAT" not in l and "emdat" not in l.lower()]
    return lines


def emdat_drop_summary():
    """EM-DAT events dropped before labelling, as counts by reason only (event IDs stay in the private report)."""
    import re
    from collections import Counter
    reasons, total = Counter(), None
    for l in LOG_FILE.read_text(encoding="utf-8").splitlines():
        m = re.search(r"\[09_labels\] EM-DAT \d{4}-\d{4}-[A-Z]{3}: (.+?) -> (dropped|not used)", l)
        if m:
            reasons[m.group(1)] += 1
        m = re.search(r"\[09_labels\] EM-DAT: (\d+) Kenyan floods", l)
        if m:
            total = int(m.group(1))
    if not reasons:
        return "EM-DAT: no events dropped (or the file was not available in this build)."
    detail = "; ".join(f"{n} with {r}" for r, n in sorted(reasons.items()))
    return (f"EM-DAT (private source, not redistributed): {sum(reasons.values())} of {total} events dropped before labelling, by reason: {detail}. "
            "Event IDs are listed only in the private report.")


def lookup_summary():
    lk = load_lookup()
    d = lk[lk["source"].str.startswith("dfo")]
    return (f"DFO place lookup: {len(d)} rows; {int((d['pcode'] != '').sum())} mapped "
            f"({int((d['confidence'] == 'certain').sum())} certain, {int((d['confidence'] == 'probable').sum())} probable), "
            f"{int((d['pcode'] == '').sum())} unmapped (province/region names, rivers and small localities left unmapped).")


def glofas_gap_note():
    """Known GloFAS source gap read from interim/glofas_gaps.json (written by stage 8); empty if there is none."""
    import json
    p = INTERIM / "glofas_gaps.json"
    if not p.exists():
        return ""
    g = json.loads(p.read_text(encoding="utf-8"))
    if not g.get("known_gap_real_dates"):
        return ""
    return ("; known source gap: ECMWF has no GloFAS data for " + ", ".join(g["known_gap_real_dates"]) + " (valid_time "
            + ", ".join(g["known_gap_valid_dates"]) + "), so " + ", ".join(g["short_months"]) + " is a mean over the remaining days")


def glofas_coverage(t):
    """('pending' | 'partial' | 'complete', text) from the real coverage of discharge_rank, not from 'any value present'."""
    import re
    files = sorted(int(m.group(1)) for f in (RAW / "glofas").glob("glofas_kenya_*.nc")
                   if (m := re.search(r"(\d{4})\.nc$", f.name)))
    r = t["discharge_rank"]
    test = t["year"] > 2019
    base_on_disk = [y for y in files if 2000 <= y <= 2019]
    facts = (f"discharge_rank is filled for {float(r.notna().mean()):.1%} of county-months ({float(r[test].notna().mean()):.1%} of 2020-2025); "
             f"year files on disk: {files[0] if files else '-'}-{files[-1] if files else '-'} ({len(files)} files; "
             f"{len(base_on_disk)} of the 20 baseline years 2000-2019; a rank needs >= 15 per county + calendar month)")
    if r.isna().all():
        return "pending", ("PENDING (all NaN, no files yet): " if not files else
                           "NOT USABLE YET (all NaN: too few baseline years on disk to rank): ") + facts
    if r.isna().any():
        return "partial", "PARTIAL: " + facts + ". Do not model on discharge_rank until it is complete"
    return "complete", "COMPLETE: " + facts + glofas_gap_note()


def build_report(t_full, include_emdat):
    t = t_full if include_emdat else to_public(t_full)
    sources = ["flood_desinventar", "flood_gfd", "flood_dfo", "flood_gfd_dfo"] + (["flood_emdat"] if include_emdat else [])
    glofas_state, glofas_text = glofas_coverage(t)
    s = []
    title = "full (includes EM-DAT; private)" if include_emdat else "public (EM-DAT excluded)"
    s.append(f"# Build report: {title}\n")
    s.append("Generated by `src/data/12_checks.py`. " + ("" if include_emdat else
             "Every label/history number here is computed WITHOUT EM-DAT (the `_public` variants); the full version is in `data/private/`.\n"))
    s.append("## 1. Structure\n\n" + md(check_structure(t)) + "\n")
    nulls, bad_null = null_report(t, glofas_state, include_emdat)
    s.append("## 2. Null counts (columns with at least one null)\n\n" + md(nulls) + "\n")
    s.append("Every other column has zero nulls.\n")
    by_year, tot = flood_tables(t, sources)
    s.append("## 3. Flood share by source\n\nShare of all 14,664 county-months flagged. `flood_gfd_dfo` = max(GFD, DFO) because they share `dfo_id`.\n\n" + md(tot) + "\n")
    s.append("### Flood share by year (share of the year's county-months)\n\n" + md(by_year) + "\n")
    s.append("DesInventar has no records in 2000, 2001 (before its coverage), 2004, 2017, 2018 and 2019, so its zeros in those years mean "
             "'no data', not 'no flood' (`desinventar_no_record_year`).\n")
    if not include_emdat:
        s.append(f"**Warning, public labels after 2018.** {public_label_coverage_text()}\n")
    groups = {"DesInventar": "flood_desinventar", "GFD+DFO": "flood_gfd_dfo", "GFD": "flood_gfd", "DFO": "flood_dfo"}
    if include_emdat:
        groups["EM-DAT"] = "flood_emdat"
    s.append("## 4. Source agreement (county-months flagged by both)\n\nDiagonal = county-months flagged by that source.\n\n" + md(agreement(t, groups)) + "\n")
    dist = t["n_sources"].value_counts().sort_index().rename_axis("n_sources").reset_index(name="county-months")
    dist["share"] = dist["county-months"] / len(t)
    s.append("Number of independent sources agreeing (`n_sources`):\n\n" + md(dist) + "\n")
    mon, seas = seasonal(t, "flood_this_month")
    s.append("## 5. Seasonal pattern of `flood_this_month`\n\n" + md(mon) + "\n\n" + md(seas) + "\n")
    peak = mon.sort_values("flood_share", ascending=False)["month"].head(4).tolist()
    s.append(f"Highest-flood calendar months: {peak}. Expected peaks are MAM (Mar-May) and OND (Oct-Dec).\n")
    s.append("## 6. Top 10 counties by flood rate\n\n`raw_share` = share of all 312 months with `flood_this_month` = 1; "
             "`county_flood_rate` = smoothed 2000-2019 rate (m = 24).\n\n" + md(top_counties(t, "flood_this_month", "county_flood_rate")) + "\n")
    s.append("## 7. Sanity checks\n\n### rain_mm against raw CHIRPS, computed by hand (3 county-months; the 3rd is forced to a weighted multi-area county)\n\n"
             + md(rain_by_hand(t)) + "\n")
    s.append("### No feature uses next-month data (exhaustive checks, every row)\n\n" + md(shift_checks(t)) + "\n")
    s.append("## 8. Build notes\n\n"
             f"- Earth Engine boundary source per file: {ee_boundary_status()}\n"
             f"- GloFAS: {glofas_text}\n"
             f"- {lookup_summary()}\n"
             + ("" if include_emdat else f"- {emdat_drop_summary()}\n"))
    s.append("```\n" + "\n".join(notes_from_log(include_emdat)) + "\n```\n")
    s.append("## 9. Known caveats\n\n"
             "- `desinventar_no_record_year` years are unknown, not flood-free, for DesInventar.\n"
             "- `county_flood_rate*` uses all of 2000-2019; recompute inside every backtest fold.\n"
             "- `pct_built` interpolates between 5-year anchors, so months before an anchor use the next anchor (mild look-ahead).\n"
             "- `pop_density` is the static 2019 census value on every row (look-ahead for 2000-2018).\n"
             "- DMI anomalies use a 1991-2020 climatology; the rfh_avg period (1989-2018) is not used.\n"
             + ("" if include_emdat else f"- **Public labels after 2018:** {public_label_coverage_text()}\n")
             + ("- Boundary: every Earth Engine feature uses the OCHA COD-AB land-only county polygons (the `*_cod.csv` exports).\n"
                if all(v == "cod" for v in ee_boundary_status().values()) else
                f"- Boundary WARNING: these Earth Engine files still use the legacy DesInventar polygons: {ee_boundary_status()}\n")
             + "- Lake-edge caveat: the lakes are cut with the Natural Earth 10m outline, which is coarser than the true shore. "
               "Some open water stays inside the land-only polygons of Homa Bay, Siaya, Migori and Marsabit, so `lc_water` and `pct_water` there are higher "
               "than for a true-shoreline polygon (Homa Bay lc_water 5.1%, pct_water 4.4%; Siaya 3.4% / 3.0%). "
               "In Nakuru and Kajiado the extra water is real small lakes that were deliberately kept.\n")
    return "\n".join(s), bad_null


def run():
    t = pd.read_csv(INTERIM / "model_table_full.csv", dtype={"pcode": str})
    include_private = t["flood_emdat"].notna().any()
    text, bad = build_report(t, include_emdat=False)
    PROCESSED.mkdir(exist_ok=True)
    (PROCESSED / "build_report.md").write_text(text, encoding="utf-8")
    log(STAGE, "wrote data/processed/build_report.md (public, no EM-DAT)")
    if include_private:
        full, _ = build_report(t, include_emdat=True)
        notes = PRIVATE / "emdat_event_notes.csv"
        if notes.exists():
            full += "\n## 10. EM-DAT event handling (private)\n\n```\n" + notes.read_text(encoding="utf-8") + "```\n"
            full += "\n```\n" + "\n".join(l for l in LOG_FILE.read_text(encoding="utf-8").splitlines() if "EM-DAT" in l) + "\n```\n"
        (PRIVATE / "build_report_full.md").write_text(full, encoding="utf-8")
        log(STAGE, "wrote data/private/build_report_full.md (includes EM-DAT)")
    if bad:
        log(STAGE, "WARNING: unexpected nulls, see section 2 of the report")


if __name__ == "__main__":
    run()
