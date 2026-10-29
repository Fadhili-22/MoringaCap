"""Stage 5: ONI and DMI, same value for every county in a month. Lags computed on the full 1950+ series.

ONI is SHIFTED one month (team decision): oni at month t = the published ONI value for month t-1. NOAA PSL labels
each 3-month running mean by its CENTRE month, so the published value for t averages t-1, t and t+1 and would leak
month t+1. The published value for t-1 averages t-2, t-1 and t, all known by the end of month t.
oni_lag1..3 are lags of this shifted series (published t-2, t-3, t-4).
"""
import pandas as pd

from common import FIRST_YEAR, INTERIM, LAST_YEAR, RAW, log

STAGE = "05_climate"


def with_lags(df, col):
    df = df.sort_values(["year", "month"]).reset_index(drop=True)
    t = df["year"] * 12 + df["month"] - 1
    assert (t.diff().dropna() == 1).all(), f"{col}: months not contiguous"
    for k in (1, 2, 3):
        df[f"{col}_lag{k}"] = df[col].shift(k)
    return df


def run():
    oni = pd.read_csv(RAW / "climate_indices" / "oni.csv")
    oni.columns = ["date", "oni"]  # the long header text becomes `oni`
    n_missing = int((oni["oni"] == -9999).sum())
    oni["oni"] = oni["oni"].replace(-9999, float("nan"))
    d = pd.to_datetime(oni["date"])
    oni = oni.assign(year=d.dt.year, month=d.dt.month)[["year", "month", "oni"]].sort_values(["year", "month"]).reset_index(drop=True)
    published = oni.set_index(["year", "month"])["oni"]
    oni["oni"] = oni["oni"].shift(1)  # month t now carries the published value for t-1 (rows are contiguous months)
    chk = oni.set_index(["year", "month"])["oni"]
    assert chk.loc[(2015, 12)] == published.loc[(2015, 11)] and chk.loc[(2016, 1)] == published.loc[(2015, 12)]
    log(STAGE, f"ONI: {n_missing} values of -9999 set to NaN (all after the 2026-07 last valid month)")

    dmi = pd.read_csv(RAW / "climate_indices" / "dmi_ersstv6.txt", sep=r"\s+", skiprows=13, header=None,
                      names=["year", "month", "wtio", "setio", "dmi"])
    assert dmi.iloc[0][["year", "month", "dmi"]].tolist() == [1950, 1, 0.23], "DMI header skip is off"
    dmi = dmi[["year", "month", "dmi"]].astype({"year": int, "month": int})

    clim = with_lags(oni, "oni").merge(with_lags(dmi, "dmi"), on=["year", "month"], how="outer")
    clim = clim[clim["year"].between(FIRST_YEAR, LAST_YEAR)]
    grid = pd.read_csv(INTERIM / "grid.csv", usecols=["pcode", "year", "month"])
    out = grid.merge(clim, how="left", on=["year", "month"])
    cols = ["oni", "oni_lag1", "oni_lag2", "oni_lag3", "dmi", "dmi_lag1", "dmi_lag2", "dmi_lag3"]
    out = out[["pcode", "year", "month"] + cols]
    assert len(out) == 14664 and out[cols].notna().all().all()
    out.to_csv(INTERIM / "climate.csv", index=False)
    log(STAGE, f"climate.csv: {len(out)} rows, no nulls")


if __name__ == "__main__":
    run()
