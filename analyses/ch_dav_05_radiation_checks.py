"""CH-Dav: independent checks of the radiation measurements.

Motivation (from 04): the residual is ~50 % of AE at every hour of the day,
i.e. multiplicative. Either AE is overestimated by a constant factor
(radiation calibration) or H + LE are underestimated by a constant factor.
NETRAD equals the sum of its components (02), so only an error common to the
radiometer would remain. Independent references available in the product:

1. SW_IN vs ERA5 SW_IN (downscaled to the site), daily means
2. SW_IN vs PPFD_IN (separate quantum sensor): SW_IN / PPFD_IN is ~0.45-0.5
   J umol-1 for global radiation; drifts or steps point at a sensor problem
3. SW_IN vs potential radiation SW_IN_POT on clear days (upper envelope)
4. midday Rn / SW_IN ratio per year

Outputs: processed/CH-Dav/05_radiation_checks.csv, figures/CH-Dav/05_radiation_checks.png
"""

import matplotlib.pyplot as plt
import pandas as pd

from ebc_explorer.fluxnet import load_ch_dav_hh
from ebc_explorer.paths import CH_DAV_FIGURES, CH_DAV_PROCESSED


def main():
    df = load_ch_dav_hh()
    sw_in = df["SW_IN_F_MDS"].where(df["SW_IN_F_MDS_QC"] == 0)
    year = df.index.year

    # 1. daily means, only days with all 48 measured SW_IN values
    daily = pd.DataFrame({"SW_IN": sw_in, "SW_IN_ERA": df["SW_IN_ERA"], "SW_IN_POT": df["SW_IN_POT"]})
    counts = daily["SW_IN"].notna().groupby(df.index.date).sum()
    daily = daily.groupby(df.index.date).mean()[counts == 48]
    daily.index = pd.to_datetime(daily.index)
    by_year = pd.DataFrame({
        "SW_IN_over_ERA5": daily.groupby(daily.index.year)["SW_IN"].sum()
                           / daily.groupby(daily.index.year)["SW_IN_ERA"].sum(),
        # clear-sky envelope: 95th percentile of daily SW_IN / SW_IN_POT
        "clearsky_SW_IN_over_POT_p95": (daily["SW_IN"] / daily["SW_IN_POT"])
                                       .groupby(daily.index.year).quantile(0.95),
    })

    # 2. SW_IN / PPFD_IN, daytime half-hours with SW_IN > 100
    ok = (sw_in > 100) & (df["PPFD_IN"] > 0)
    by_year["SW_IN_over_PPFD"] = (sw_in[ok] / df.loc[ok, "PPFD_IN"]).groupby(year[ok]).median()

    # 4. midday Rn / SW_IN
    midday = df.index.hour.isin([11, 12]) & (sw_in > 300)
    by_year["Rn_over_SW_IN_midday"] = (df.loc[midday, "NETRAD"] / sw_in[midday]).groupby(year[midday]).median()

    by_year.index.name = "year"
    CH_DAV_PROCESSED.mkdir(parents=True, exist_ok=True)
    by_year.to_csv(CH_DAV_PROCESSED / "05_radiation_checks.csv")
    print(by_year.round(3).to_string())

    fig, axes = plt.subplots(len(by_year.columns), 1, figsize=(10, 9), sharex=True)
    for ax, col in zip(axes, by_year.columns):
        ax.plot(by_year.index, by_year[col], "o-")
        ax.set_ylabel(col, fontsize=8)
        ax.grid(alpha=0.3)
        ax.axvline(2014.5, color="r", ls=":", lw=1)
    axes[0].set_title("CH-Dav radiation consistency checks per year")
    axes[-1].set_xlabel("year")
    fig.tight_layout()
    CH_DAV_FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(CH_DAV_FIGURES / "05_radiation_checks.png", dpi=150)


if __name__ == "__main__":
    main()
