"""CH-Dav: closure per instrument period, and is H or LE the missing flux?

Tests (daytime, SW_IN_POT > 0, measured data only):
1. closure statistics per instrument period (sonic + gas analyser)
2. multiple regression AE = a*H + b*LE + c per period: with perfect closure
   a = b = 1; a coefficient much larger than 1 points at that flux being
   underestimated (caveat: H and LE are correlated)
3. EBR by relative humidity class per period, within classes of AE: high-
   frequency attenuation of H2O in closed/enclosed-path systems grows with RH
   (Ibrom 2007, Mammarella 2009, Fratini 2012). If LE is underestimated this
   way, EBR should decrease with RH in closed/enclosed periods but not in
   open-path periods. AE classes are needed because humid daytime conditions
   are mostly low-energy (cloudy, morning), where ratios behave differently.
4. evaporative fraction LE/(H+LE) per period

Result (2026-09-22): within AE classes EBR decreases with RH in all periods
incl. open-path (not a closed-path-only artefact); at AE 450-900 and RH < 50 %
EBR is only 0.45-0.59 in every period.

Outputs: processed/CH-Dav/03_*.csv, figures/CH-Dav/03_instrument_periods.png
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ebc_explorer.ch_dav import INSTRUMENT_PERIODS, instrument_period
from ebc_explorer.ebc import closure_by, energy_terms
from ebc_explorer.fluxnet import load_ch_dav_hh
from ebc_explorer.paths import CH_DAV_FIGURES, CH_DAV_PROCESSED

RH_BINS = [0, 50, 70, 80, 90, 100.1]
AE_BINS = [100, 250, 450, 900]


def partial_coefficients(g):
    """Fit AE = a*H + b*LE + c by least squares."""
    g = g.dropna(subset=["AE", "H", "LE"])
    if len(g) < 100:
        return pd.Series({"a_H": np.nan, "b_LE": np.nan, "c": np.nan, "n": len(g)})
    X = np.column_stack([g["H"], g["LE"], np.ones(len(g))])
    (a, b, c), *_ = np.linalg.lstsq(X, g["AE"].to_numpy(), rcond=None)
    return pd.Series({"a_H": a, "b_LE": b, "c": c, "n": len(g)})


def main():
    df = load_ch_dav_hh()
    terms = energy_terms(df)
    terms["period"] = instrument_period(df.index)
    terms["RH"] = df["RH"]
    day = terms[df["SW_IN_POT"] > 0].dropna(subset=["AE", "TE"])

    stats = closure_by(day, "period")
    coefs = day.groupby("period", observed=True)[["AE", "H", "LE"]].apply(partial_coefficients)
    ef = (day.groupby("period", observed=True)["LE"].sum()
          / day.groupby("period", observed=True)["TE"].sum()).rename("evap_fraction")
    summary = stats.join(coefs.drop(columns="n")).join(ef)
    summary.insert(0, "ga_type", INSTRUMENT_PERIODS.set_index("label")["ga_type"])

    day["RH_class"] = pd.cut(day["RH"], RH_BINS, right=False)
    day["AE_class"] = pd.cut(day["AE"], AE_BINS, right=False)
    keys = ["AE_class", "period", "RH_class"]
    rh = day.groupby(keys, observed=True)[["AE", "H", "LE", "TE"]].sum()
    rh["ebr"] = rh["TE"] / rh["AE"]
    rh["H_over_AE"] = rh["H"] / rh["AE"]
    rh["LE_over_AE"] = rh["LE"] / rh["AE"]
    rh["n"] = day.groupby(keys, observed=True).size()
    rh_table = rh["ebr"].unstack("RH_class")

    CH_DAV_PROCESSED.mkdir(parents=True, exist_ok=True)
    summary.to_csv(CH_DAV_PROCESSED / "03_period_summary.csv")
    rh.to_csv(CH_DAV_PROCESSED / "03_ebr_by_rh.csv")
    with pd.option_context("display.width", 220, "display.max_columns", 30):
        print("daytime closure per instrument period:")
        print(summary[["ga_type", "n", "ols_slope", "ols_intercept", "r2", "ebr", "mean_res",
                       "a_H", "b_LE", "c", "evap_fraction"]].round(3).to_string())
        print("\ndaytime EBR by AE class (W m-2) and RH class (%):")
        print(rh_table.round(2).to_string())
        print("\nn:")
        print(rh["n"].unstack("RH_class").to_string())

    ae_classes = rh_table.index.get_level_values("AE_class").unique()
    fig, axes = plt.subplots(1, len(ae_classes) + 1, figsize=(5 * (len(ae_classes) + 1), 5))
    centers = [(b.left + min(b.right, 100)) / 2 for b in rh_table.columns]
    for ax, ae_class in zip(axes, ae_classes):
        for label, row in rh_table.loc[ae_class].iterrows():
            ga = INSTRUMENT_PERIODS.set_index("label").loc[label, "ga_type"]
            ax.plot(centers, row.values, "s--" if ga == "open" else "o-", label=label)
        ax.set_title(f"AE {ae_class} W m$^{{-2}}$")
        ax.set_xlabel("RH (%)")
        ax.set_ylim(0, 1.3)
        ax.axhline(1, color="k", lw=0.8)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("daytime EBR = ΣTE / ΣAE (dashed = open path)")
    axes[0].legend(fontsize=7)
    x = np.arange(len(summary))
    axes[-1].bar(x - 0.2, summary["a_H"], 0.4, label="a (H)")
    axes[-1].bar(x + 0.2, summary["b_LE"], 0.4, label="b (LE)")
    axes[-1].axhline(1, color="k", lw=0.8)
    axes[-1].set_xticks(x, summary.index, rotation=30, ha="right", fontsize=8)
    axes[-1].set_title("AE = a·H + b·LE + c (daytime)")
    axes[-1].legend()
    axes[-1].grid(alpha=0.3, axis="y")
    fig.tight_layout()
    CH_DAV_FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(CH_DAV_FIGURES / "03_instrument_periods.png", dpi=150)


if __name__ == "__main__":
    main()
