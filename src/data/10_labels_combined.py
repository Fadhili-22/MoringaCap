"""Stage 10: combined labels and next-month targets.

flood_gfd and flood_dfo share dfo_id, so they count as ONE source: flood_gfd_dfo = max(flood_gfd, flood_dfo).
n_sources = flood_desinventar + flood_emdat + flood_gfd_dfo. The *_public variants leave EM-DAT out.
Next-month targets are shifted -1 month within each county; Dec 2025 is NaN (no Jan 2026 row in the table).
"""
import pandas as pd

from common import INTERIM, log

STAGE = "10_labels_combined"
HEAVY_RAIN = 1.25


def next_month(df, col):
    """col shifted -1 month within pcode; the last month of each county becomes NA."""
    df = df.sort_values(["pcode", "year", "month"])
    t = df["year"] * 12 + df["month"] - 1
    assert (t.groupby(df["pcode"]).diff().dropna() == 1).all()
    return df.groupby("pcode")[col].shift(-1)


def run():
    key = ["pcode", "year", "month"]
    lab = pd.read_csv(INTERIM / "labels_sources.csv", dtype={"pcode": str}).sort_values(key).reset_index(drop=True)
    rain = pd.read_csv(INTERIM / "rainfall.csv", usecols=key + ["rain_pct_normal"])
    lab = lab.merge(rain, on=key, validate="one_to_one").sort_values(key).reset_index(drop=True)

    lab["flood_gfd_dfo"] = lab[["flood_gfd", "flood_dfo"]].max(axis=1)
    have_emdat = lab["flood_emdat"].notna().all()
    lab["n_sources_public"] = lab["flood_desinventar"] + lab["flood_gfd_dfo"]
    lab["flood_this_month_public"] = (lab["n_sources_public"] >= 1).astype(int)
    lab["flood_corroborated_public"] = (lab["n_sources_public"] >= 2).astype(int)
    if have_emdat:
        lab["n_sources"] = lab["n_sources_public"] + lab["flood_emdat"].astype(int)
        lab["flood_this_month"] = (lab["n_sources"] >= 1).astype(int)
        lab["flood_corroborated"] = (lab["n_sources"] >= 2).astype(int)
    else:
        log(STAGE, "EM-DAT absent: full-table label columns (n_sources, flood_this_month, ...) left NaN")
        for c in ["n_sources", "flood_this_month", "flood_corroborated"]:
            lab[c] = pd.array([pd.NA] * len(lab), dtype="Int64")

    lab["flood_next_month"] = next_month(lab, "flood_this_month").astype("Int64")
    lab["flood_next_month_public"] = next_month(lab, "flood_this_month_public").astype("Int64")
    nxt_rain = next_month(lab, "rain_pct_normal")
    lab["heavy_rain_next_month"] = (nxt_rain > HEAVY_RAIN).astype("Int64").where(nxt_rain.notna())

    last = (lab["year"] == 2025) & (lab["month"] == 12)
    assert lab.loc[last, ["flood_next_month", "flood_next_month_public", "heavy_rain_next_month"]].isna().all().all()
    assert lab.loc[~last, ["flood_next_month_public", "heavy_rain_next_month"]].notna().all().all()
    cols = ["flood_desinventar", "flood_emdat", "flood_gfd", "flood_dfo", "flood_gfd_dfo", "desinventar_no_record_year",
            "n_sources", "flood_this_month", "flood_corroborated", "flood_next_month", "heavy_rain_next_month",
            "n_sources_public", "flood_this_month_public", "flood_corroborated_public", "flood_next_month_public"]
    lab[key + cols].to_csv(INTERIM / "labels_combined.csv", index=False)
    log(STAGE, f"labels_combined.csv: flood_this_month share {lab['flood_this_month'].mean():.3f} (public {lab['flood_this_month_public'].mean():.3f}); "
               f"corroborated {lab['flood_corroborated'].mean():.4f} (public {lab['flood_corroborated_public'].mean():.4f}); "
               f"heavy_rain_next_month share {lab['heavy_rain_next_month'].mean():.3f}")


if __name__ == "__main__":
    run()
