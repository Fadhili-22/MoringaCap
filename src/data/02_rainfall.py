"""Stage 2: CHIRPS rainfall (WFP rfh) -> county-month features.

Lags and rolling totals are computed on the full 1981-2025 series BEFORE trimming to 2000-2025.
Normal = mean rain_mm for the same county + calendar month over 2000-2019 (training years only).
rain_pct_normal is a RATIO (1.0 = normal, 1.25 = 125% of normal).
"""
import numpy as np
import pandas as pd

from common import (FIRST_YEAR, INTERIM, LEVEL1_PCODES, RAW, add_lags, baseline_mean, dekads_to_months, log,
                    wfp_county_dekads)

STAGE = "02_rainfall"
SRC = RAW / "rainfall" / "ken-rainfall-subnat-full.csv"


def report_rfh_avg_period():
    """Find which year window WFP's rfh_avg equals (we do NOT use rfh_avg as a feature)."""
    d = pd.read_csv(SRC, dtype={"PCODE": str}, usecols=["date", "adm_level", "PCODE", "rfh", "rfh_avg"])
    d["date"] = pd.to_datetime(d["date"])
    best = None
    for pc in ("KE047", "KE004", "KE019"):
        k = d[(d["PCODE"] == pc) & (d["adm_level"] == 1) & (d["date"].dt.year <= 2025)].copy()
        k["dk"] = k["date"].dt.month * 100 + k["date"].dt.day // 10
        avg = k.groupby("dk")["rfh_avg"].first()
        assert k.groupby("dk")["rfh_avg"].nunique().max() == 1, "rfh_avg varies within a dekad of the year"
        res = []
        for a in range(1981, 2012):
            for b in range(a + 9, 2026):
                m = k[k["date"].dt.year.between(a, b)].groupby("dk")["rfh"].mean()
                res.append((float((m - avg).abs().max()), a, b))
        res.sort()
        log(STAGE, f"rfh_avg check {pc}: best-matching window {res[0][1]}-{res[0][2]} (max abs diff {res[0][0]:.2g} mm); "
                   f"next best {res[1][1]}-{res[1][2]} ({res[1][0]:.2g} mm)")
        best = best or res[0]
    log(STAGE, f"RESULT: WFP rfh_avg covers {best[1]}-{best[2]} (long-term mean of rfh per dekad). Not used as a feature.")


def run():
    report_rfh_avg_period()
    dek = wfp_county_dekads(SRC, "rfh", STAGE)
    mon = dekads_to_months(dek, "rfh", ["sum", "max"], STAGE).rename(columns={"sum": "rain_mm", "max": "rain_max_dekad"})
    mon = add_lags(mon, ["rain_mm"], [1, 2])
    mon = mon.rename(columns={"rain_mm_lag1": "rain_lag1", "rain_mm_lag2": "rain_lag2"})
    mon["rain_3mo_total"] = mon["rain_mm"] + mon["rain_lag1"] + mon["rain_lag2"]
    log(STAGE, f"full monthly series: {mon['year'].min()}-{mon['year'].max()}, {len(mon)} rows")
    mon[["pcode", "year", "month", "rain_mm"]].to_csv(INTERIM / "rainfall_monthly_full.csv", index=False)

    normal = baseline_mean(mon, "rain_mm")
    zero = (normal == 0).sum()
    if zero:
        log(STAGE, f"WARNING: {zero} county-months have normal rain == 0; rain_pct_normal set to NaN there")
    mon["rain_pct_normal"] = mon["rain_mm"] / normal.where(normal > 0)

    out = mon[mon["year"] >= FIRST_YEAR]
    cols = ["pcode", "year", "month", "rain_mm", "rain_max_dekad", "rain_lag1", "rain_lag2", "rain_3mo_total",
            "rain_pct_normal"]
    out = out[cols]
    assert len(out) == 14664 and out[cols].notna().all().all()
    out.to_csv(INTERIM / "rainfall.csv", index=False)
    log(STAGE, f"rainfall.csv: {len(out)} rows; rain_pct_normal range {out['rain_pct_normal'].min():.3f}-"
               f"{out['rain_pct_normal'].max():.3f}, share > 1.25: {(out['rain_pct_normal'] > 1.25).mean():.3f}")


if __name__ == "__main__":
    run()
