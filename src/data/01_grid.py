"""Stage 1: empty county-month grid, 47 pcodes x every month 2000-01..2025-12 = 14,664 rows."""
import numpy as np
import pandas as pd

from common import FIRST_YEAR, INTERIM, LAST_YEAR, load_crosswalk, log

STAGE = "01_grid"
SEASON = {1: "JF", 2: "JF", 3: "MAM", 4: "MAM", 5: "MAM", 6: "JJAS", 7: "JJAS", 8: "JJAS", 9: "JJAS",
          10: "OND", 11: "OND", 12: "OND"}


def run():
    cw = load_crosswalk()
    months = pd.MultiIndex.from_product([range(FIRST_YEAR, LAST_YEAR + 1), range(1, 13)], names=["year", "month"])
    ym = months.to_frame(index=False)
    grid = cw[["pcode", "county"]].merge(ym, how="cross").sort_values(["pcode", "year", "month"], ignore_index=True)
    grid["season"] = grid["month"].map(SEASON)
    grid["month_sin"] = np.sin(2 * np.pi * grid["month"] / 12)
    grid["month_cos"] = np.cos(2 * np.pi * grid["month"] / 12)
    assert len(grid) == 14664 and not grid.duplicated(["pcode", "year", "month"]).any()
    INTERIM.mkdir(parents=True, exist_ok=True)
    grid.to_csv(INTERIM / "grid.csv", index=False)
    log(STAGE, f"grid: {len(grid)} rows, {grid['pcode'].nunique()} pcodes x {len(ym)} months")


if __name__ == "__main__":
    run()
