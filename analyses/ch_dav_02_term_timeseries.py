"""CH-Dav: yearly behaviour of each energy balance term and radiation consistency.

Motivation (from 01): the closure slope is low in all years, but EBR drops and
the OLS intercept shifts from ~+35 to ~0 W m-2 around 2014/2015. This looks
like a step change in one of the measured terms. Here we look at:

1. yearly mean NETRAD, G, H, LE, split into day (SW_IN_POT > 0) and night
2. radiation closure: NETRAD vs SW_IN - SW_OUT + LW_IN - LW_OUT (all measured)
3. midday albedo SW_OUT/SW_IN

Outputs: processed/CH-Dav/02_*.csv, figures/CH-Dav/02_term_timeseries.png
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ebc_explorer.ebc import energy_terms
from ebc_explorer.fluxnet import load_ch_dav_hh
from ebc_explorer.paths import CH_DAV_FIGURES, CH_DAV_PROCESSED


def main():
    df = load_ch_dav_hh()
    terms = energy_terms(df)
    year = df.index.year
    day = df["SW_IN_POT"] > 0

    # 1. yearly means per term, day/night
    means = {}
    for label, mask in (("day", day), ("night", ~day)):
        means[label] = terms.loc[mask, ["NETRAD", "G", "H", "LE"]].groupby(year[mask]).mean()
    means = pd.concat(means, axis=1)
    means.index.name = "year"

    # 2. radiation components (only half-hours where all four are measured)
    sw_in = df["SW_IN_F_MDS"].where(df["SW_IN_F_MDS_QC"] == 0)
    lw_in = df["LW_IN_F_MDS"].where(df["LW_IN_F_MDS_QC"] == 0)
    rn_comp = sw_in - df["SW_OUT"] + lw_in - df["LW_OUT"]
    diff = (df["NETRAD"] - rn_comp).dropna()
    rad = pd.DataFrame({
        "n": diff.groupby(diff.index.year).size(),
        "mean_NETRAD_minus_components": diff.groupby(diff.index.year).mean(),
        "p95_abs_diff": diff.abs().groupby(diff.index.year).quantile(0.95),
    })

    # 3. midday albedo (10-14 h local standard time, SW_IN > 200)
    midday = df.index.hour.isin([10, 11, 12, 13]) & (sw_in > 200)
    albedo = (df.loc[midday, "SW_OUT"] / sw_in[midday]).groupby(year[midday]).median()
    rad["albedo_midday_median"] = albedo
    rad["LW_OUT_night_mean"] = df.loc[~day, "LW_OUT"].groupby(year[~day]).mean()
    rad["TA_night_mean"] = df.loc[~day, "TA_F"].groupby(year[~day]).mean()

    CH_DAV_PROCESSED.mkdir(parents=True, exist_ok=True)
    means.to_csv(CH_DAV_PROCESSED / "02_yearly_term_means.csv")
    rad.to_csv(CH_DAV_PROCESSED / "02_radiation_checks.csv")
    with pd.option_context("display.width", 200, "display.max_columns", 30):
        print("yearly means (W m-2) of measured terms, day / night:")
        print(means.round(1).to_string())
        print("\nradiation checks:")
        print(rad.round(3).to_string())

    fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
    for ax, label in zip(axes[:2], ("day", "night")):
        for var in ("NETRAD", "G", "H", "LE"):
            ax.plot(means.index, means[(label, var)], "o-", label=var)
        ax.axvline(2014.5, color="r", ls=":", lw=1)
        ax.set_ylabel(f"{label} mean (W m$^{{-2}}$)")
        ax.grid(alpha=0.3)
    axes[0].legend(ncol=4)
    axes[0].set_title("CH-Dav yearly means of measured energy balance terms")
    axes[2].plot(rad.index, rad["mean_NETRAD_minus_components"], "o-", label="NETRAD − Σ components")
    axes[2].set_ylabel("W m$^{-2}$")
    ax2 = axes[2].twinx()
    ax2.plot(rad.index, rad["albedo_midday_median"], "s--", color="C3", label="midday albedo")
    ax2.set_ylabel("albedo")
    axes[2].axvline(2014.5, color="r", ls=":", lw=1)
    axes[2].grid(alpha=0.3)
    axes[2].legend(loc="upper left")
    ax2.legend(loc="upper right")
    axes[2].set_xlabel("year")
    fig.tight_layout()
    CH_DAV_FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(CH_DAV_FIGURES / "02_term_timeseries.png", dpi=150)


if __name__ == "__main__":
    main()
