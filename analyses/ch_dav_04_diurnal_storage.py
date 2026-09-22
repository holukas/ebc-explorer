"""CH-Dav: diurnal cycle of the imbalance and the role of biomass storage.

Period 2019-2024 (the period of Nicolini et al. 2026, for which their
half-hourly biomass heat storage Sbio and photosynthesis term Spho exist).

Tests:
1. mean diurnal cycle per season of AE, TE, residual RES = AE - TE,
   Sbio + Spho, and RES - Sbio - Spho. A storage-driven gap peaks in the
   morning and turns negative in the evening; a gap that stays positive all
   day is not storage.
2. closure statistics with and without Sbio + Spho in AE
3. lag between AE and TE (lag of maximum cross-correlation of the mean
   diurnal cycles): storage makes TE lag AE.

Outputs: processed/CH-Dav/04_*.csv, figures/CH-Dav/04_diurnal_storage.png
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ebc_explorer.ebc import closure_stats, energy_terms
from ebc_explorer.fluxnet import load_ch_dav_hh
from ebc_explorer.nicolini import load_sbio_spho
from ebc_explorer.paths import CH_DAV_FIGURES, CH_DAV_PROCESSED

SEASONS = {12: "DJF", 1: "DJF", 2: "DJF", 3: "MAM", 4: "MAM", 5: "MAM",
           6: "JJA", 7: "JJA", 8: "JJA", 9: "SON", 10: "SON", 11: "SON"}


def lag_of_max_corr(a, b, max_lag=6):
    """Lag (in half-hours) at which b correlates best with a shifted a."""
    lags = range(-max_lag, max_lag + 1)
    corr = [np.corrcoef(np.roll(a, lag), b)[0, 1] for lag in lags]
    return list(lags)[int(np.argmax(corr))]


def main():
    df = load_ch_dav_hh()
    df = df[df.index.year >= 2019]
    terms = energy_terms(df)
    stor = load_sbio_spho("CH-Dav").reindex(terms.index)
    terms["S"] = stor["Sbio"] + stor["Spho"]
    terms["AE_S"] = terms["AE"] - terms["S"]
    terms["RES_S"] = terms["AE_S"] - terms["TE"]
    terms["season"] = terms.index.month.map(SEASONS)
    terms["hour"] = terms.index.hour + terms.index.minute / 60
    complete = terms.dropna(subset=["AE", "TE", "S"])

    diurnal = complete.groupby(["season", "hour"])[["AE", "TE", "RES", "S", "RES_S"]].mean()

    rows = {}
    for season, g in complete.groupby("season"):
        d = diurnal.loc[season]
        rows[season] = pd.concat([
            closure_stats(g["AE"], g["TE"]).add_prefix("noS_"),
            closure_stats(g["AE_S"], g["TE"]).add_prefix("withS_"),
            pd.Series({"lag_TE_vs_AE_min": 30 * lag_of_max_corr(d["AE"].to_numpy(), d["TE"].to_numpy()),
                       "max_mean_RES": d["RES"].max(), "max_mean_RES_S": d["RES_S"].max(),
                       "hour_max_RES": d["RES"].idxmax()}),
        ])
    rows["all"] = pd.concat([closure_stats(complete["AE"], complete["TE"]).add_prefix("noS_"),
                             closure_stats(complete["AE_S"], complete["TE"]).add_prefix("withS_")])
    summary = pd.DataFrame(rows).T

    CH_DAV_PROCESSED.mkdir(parents=True, exist_ok=True)
    diurnal.to_csv(CH_DAV_PROCESSED / "04_diurnal_by_season.csv")
    summary.to_csv(CH_DAV_PROCESSED / "04_storage_summary.csv")
    with pd.option_context("display.width", 220, "display.max_columns", 30):
        print(summary[["noS_n", "noS_ols_slope", "noS_ebr", "withS_ols_slope", "withS_ebr",
                       "lag_TE_vs_AE_min", "hour_max_RES", "max_mean_RES", "max_mean_RES_S"]].round(3).to_string())

    fig, axes = plt.subplots(1, 4, figsize=(18, 4.5), sharey=True)
    for ax, season in zip(axes, ["DJF", "MAM", "JJA", "SON"]):
        d = diurnal.loc[season]
        ax.plot(d.index, d["AE"], label="AE = Rn − G")
        ax.plot(d.index, d["TE"], label="TE = H + LE")
        ax.plot(d.index, d["S"], label="Sbio + Spho")
        ax.plot(d.index, d["RES"], "k-", lw=2, label="RES = AE − TE")
        ax.plot(d.index, d["RES_S"], "k--", lw=2, label="RES − S")
        ax.axhline(0, color="0.5", lw=0.8)
        ax.set_title(season)
        ax.set_xlabel("hour (local standard time)")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("W m$^{-2}$")
    axes[0].legend(fontsize=8)
    fig.suptitle("CH-Dav 2019–2024: mean diurnal cycle of measured energy balance terms")
    fig.tight_layout()
    CH_DAV_FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(CH_DAV_FIGURES / "04_diurnal_storage.png", dpi=150)


if __name__ == "__main__":
    main()
