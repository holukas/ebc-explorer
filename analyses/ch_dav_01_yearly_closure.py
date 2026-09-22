"""CH-Dav: energy balance closure per year, 1997-2024.

Question: is the low closure found by Nicolini et al. (2026) for the ICOS
period (2019+) also present in the older record, or did it appear later?

Uses measured (not gap-filled) NETRAD, G, H, LE only.
- half-hourly: OLS slope of TE vs AE, EBR = sum(TE)/sum(AE)
- daily: same on daily means (days with >= 40/48 values of every term);
  storage terms largely cancel at daily scale.

Outputs: processed/CH-Dav/01_yearly_closure.csv, figures/CH-Dav/01_yearly_closure.png
"""

import matplotlib.pyplot as plt
import pandas as pd

from ebc_explorer.ebc import closure_by, daily_means, energy_terms
from ebc_explorer.fluxnet import load_ch_dav_hh
from ebc_explorer.paths import CH_DAV_FIGURES, CH_DAV_PROCESSED

ICOS_START = 2019


def main():
    terms = energy_terms(load_ch_dav_hh())
    hh = closure_by(terms, terms.index.year)
    daily = daily_means(terms)
    dd = closure_by(daily, daily.index.year)

    table = pd.concat({"hh": hh, "daily": dd}, axis=1)
    table.index.name = "year"
    CH_DAV_PROCESSED.mkdir(parents=True, exist_ok=True)
    table.to_csv(CH_DAV_PROCESSED / "01_yearly_closure.csv")

    with pd.option_context("display.width", 200, "display.max_columns", 30):
        print(table.loc[:, [("hh", "n"), ("hh", "ols_slope"), ("hh", "ols_intercept"), ("hh", "r2"),
                            ("hh", "ebr"), ("hh", "mean_res"),
                            ("daily", "n"), ("daily", "ols_slope"), ("daily", "ebr")]].round(3).to_string())
        pre, post = terms[terms.index.year < ICOS_START], terms[terms.index.year >= ICOS_START]
        print("\nperiod summary (half-hourly):")
        print(pd.DataFrame({f"<{ICOS_START}": closure_by(pre, lambda _: 0).iloc[0],
                            f">={ICOS_START}": closure_by(post, lambda _: 0).iloc[0]}).round(3).to_string())

    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    for ax, col, label in ((axes[0], "ols_slope", "OLS slope TE vs AE"), (axes[1], "ebr", "EBR = ΣTE / ΣAE")):
        ax.plot(hh.index, hh[col], "o-", label="half-hourly")
        ax.plot(dd.index, dd[col], "s--", label="daily means")
        ax.axvspan(ICOS_START - 0.5, table.index.max() + 0.5, color="0.9", zorder=0, label="ICOS period")
        ax.axhline(1, color="k", lw=0.8)
        ax.set_ylabel(label)
        ax.set_ylim(0, 1.1)
        ax.grid(alpha=0.3)
    axes[0].legend(loc="lower left")
    axes[0].set_title("CH-Dav energy balance closure per year (measured NETRAD, G, H, LE)")
    axes[1].set_xlabel("year")
    fig.tight_layout()
    CH_DAV_FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(CH_DAV_FIGURES / "01_yearly_closure.png", dpi=150)


if __name__ == "__main__":
    main()
