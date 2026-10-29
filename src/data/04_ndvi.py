"""Stage 4: WFP NDVI (vim) -> county-month. Monthly value = mean of the 3 dekads.

Data starts 2002-07; earlier months are left blank (not filled).
ndvi_pct_normal = ndvi / mean ndvi of the same county + calendar month over the available
2002-07..2019-12 months (a RATIO, 1.0 = normal).
"""
import pandas as pd

from common import BASE_END, INTERIM, RAW, dekads_to_months, log, wfp_county_dekads

STAGE = "04_ndvi"
SRC = RAW / "ndvi" / "ken-ndvi-subnat-full.csv"


def run():
    dek = wfp_county_dekads(SRC, "vim", STAGE)
    mon = dekads_to_months(dek, "vim", "mean", STAGE).rename(columns={"vim": "ndvi"})
    first = mon.sort_values(["year", "month"]).iloc[0]
    log(STAGE, f"NDVI series starts {int(first.year)}-{int(first.month):02d}")
    normal = mon[mon["year"] <= BASE_END].groupby(["pcode", "month"])["ndvi"].mean().rename("_normal")
    mon = mon.join(normal, on=["pcode", "month"])
    mon["ndvi_pct_normal"] = mon["ndvi"] / mon["_normal"].where(mon["_normal"] > 0)
    grid = pd.read_csv(INTERIM / "grid.csv", usecols=["pcode", "year", "month"])
    out = grid.merge(mon[["pcode", "year", "month", "ndvi", "ndvi_pct_normal"]], how="left", on=["pcode", "year", "month"])
    ym = out["year"] * 100 + out["month"]
    assert out.loc[ym < 200207, ["ndvi", "ndvi_pct_normal"]].isna().all().all()
    assert out.loc[ym >= 200207, ["ndvi", "ndvi_pct_normal"]].notna().all().all()
    out.to_csv(INTERIM / "ndvi.csv", index=False)
    log(STAGE, f"ndvi.csv: {len(out)} rows, {out['ndvi'].isna().sum()} blank (all before 2002-07)")


if __name__ == "__main__":
    run()
