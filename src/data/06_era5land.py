"""Stage 6: ERA5-Land soil moisture (layers 1, 2) and runoff rank. Lags on the full 1999-10..2025-12 series.

runoff_rank = mid-rank percentile (0-1) of this month's runoff_sum among the same county + calendar month
in 2000-2019. Absolute runoff and % of normal are NOT used. era5land_precip_county_month.csv is ignored.
"""
from common import FIRST_YEAR, INTERIM, add_lags, baseline_percentile, log, read_ee_county_csv

STAGE = "06_era5land"


def run():
    e = read_ee_county_csv("era5land_soil_runoff_county_month", STAGE,
                           usecols=["year", "month", "volumetric_soil_water_layer_1",
                                    "volumetric_soil_water_layer_2", "runoff_sum"])
    assert not e.duplicated(["pcode", "year", "month"]).any()
    e = e.rename(columns={"volumetric_soil_water_layer_1": "soil_moisture_l1",
                          "volumetric_soil_water_layer_2": "soil_moisture_l2"})
    e = add_lags(e, ["soil_moisture_l1", "soil_moisture_l2"], [1])
    e["runoff_rank"] = baseline_percentile(e, "runoff_sum")
    cols = ["soil_moisture_l1", "soil_moisture_l1_lag1", "soil_moisture_l2", "soil_moisture_l2_lag1", "runoff_rank"]
    out = e[e["year"] >= FIRST_YEAR][["pcode", "year", "month"] + cols]
    assert len(out) == 14664 and out[cols].notna().all().all()
    out.to_csv(INTERIM / "era5land.csv", index=False)
    log(STAGE, f"era5land.csv: {len(out)} rows; runoff_rank min {out['runoff_rank'].min():.3f} "
               f"max {out['runoff_rank'].max():.3f}")


if __name__ == "__main__":
    run()
