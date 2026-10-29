"""Stage 11: county flood history feature (training years 2000-2019 only), smoothed toward the national rate.

county_flood_rate = (county_floods + m * national_rate) / (county_months + m), m = 24, where county_floods counts the
2000-2019 months with flood_this_month = 1 in that county (county_months = 240) and national_rate is the share of all
2000-2019 county-months with a flood. The value is the same on every row of a county.
county_flood_rate_public uses flood_this_month_public (no EM-DAT).
NOTE for modelling: this uses all of 2000-2019. In a rolling-origin backtest it MUST be recomputed inside each fold
from that fold's training months only (and the county's value should not use the validation period).
"""
import pandas as pd

from common import BASE_END, BASE_START, INTERIM, log

STAGE = "11_history"
M = 24


def smoothed_rate(lab, col):
    train = lab[lab["year"].between(BASE_START, BASE_END)]
    national = train[col].mean()
    g = train.groupby("pcode")[col].agg(["sum", "count"])
    rate = (g["sum"] + M * national) / (g["count"] + M)
    return rate, national


def run():
    lab = pd.read_csv(INTERIM / "labels_combined.csv", dtype={"pcode": str})
    out = lab[["pcode", "year", "month"]].copy()
    for col, name in [("flood_this_month", "county_flood_rate"), ("flood_this_month_public", "county_flood_rate_public")]:
        if lab[col].isna().all():
            out[name] = float("nan")
            continue
        rate, national = smoothed_rate(lab, col)
        out[name] = out["pcode"].map(rate)
        assert out[name].notna().all() and out.groupby("pcode")[name].nunique().max() == 1
        log(STAGE, f"{name}: national rate {national:.4f}, county range {rate.min():.4f}-{rate.max():.4f} (m={M})")
    out.to_csv(INTERIM / "history.csv", index=False)


if __name__ == "__main__":
    run()
