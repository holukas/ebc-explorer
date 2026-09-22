"""CH-Dav: sector diagnostics following McGloin et al. (2018).

Motivation (06): at equal u*, daytime northerly winds close at ~0.5 while S/W
winds close at 0.75-1.0. McGloin et al. (2018) found a similar sector-specific
deficit at a slope forest (0.48-0.55 vs 0.80), which persisted for unstable
conditions only, and which coincided with low measured u* relative to the
flow (terrain-induced advection). Kidston et al. (2010) found low closure for
winds passing through the tower before reaching a west-mounted EC system.

Per 30 deg wind sector (daytime, AE >= 100 W m-2, measured data, 1998+):
1. EBR for all conditions and for unstable conditions only (z/L < -0.1)
2. median u*/WS (turbulence intensity proxy; low values = weakly turbulent or
   distorted flow at the sensor) and median WS
3. share of daytime data per sector

Stability: L = -u*^3 * T_K / (k * g * H / (rho * cp)), z = 35 m - d,
d = 2/3 * canopy height (19 m). Air density from pressure and temperature.

Result (2026-09-22): N and NNE carry 62 % of daytime data and close at
0.47-0.52 also for z/L < -0.1 (S/SW rise to 0.64-0.75, W/WNW ~0.8-0.9).
Northerly flow is the fastest (median WS ~3 m s-1) with the lowest u*/WS
(0.17, about the log-law value for z-d ~22 m over a rough forest), i.e. a
well-developed along-valley flow, not weak turbulence.

Outputs: processed/CH-Dav/07_sector_diagnostics.csv, figures/CH-Dav/07_sector_diagnostics.png
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ebc_explorer.ebc import energy_terms
from ebc_explorer.fluxnet import load_ch_dav_hh
from ebc_explorer.paths import CH_DAV_FIGURES, CH_DAV_PROCESSED

Z_MEAS = 35.0
CANOPY_HEIGHT = 19.0
D = 2 / 3 * CANOPY_HEIGHT
KARMAN, G, CP, R_DRY = 0.4, 9.81, 1005.0, 287.05
SECTOR_WIDTH = 30


def obukhov_zeta(df):
    """z/L from USTAR, H, TA_F and PA_F (kPa)."""
    t_k = df["TA_F"] + 273.15
    rho = df["PA_F"] * 1000 / (R_DRY * t_k)
    kin_h = df["H_F_MDS"].where(df["H_F_MDS_QC"] == 0) / (rho * CP)
    L = -df["USTAR"] ** 3 * t_k / (KARMAN * G * kin_h)
    return (Z_MEAS - D) / L


def main():
    df = load_ch_dav_hh()
    terms = energy_terms(df)
    terms["zeta"] = obukhov_zeta(df)
    terms["ustar_ws"] = df["USTAR"] / df["WS"]
    terms["WS"] = df["WS"]
    terms["WD"] = df["WD"]
    d = terms[(df["SW_IN_POT"] > 0) & (terms["AE"] >= 100) & (terms.index.year >= 1998)]
    d = d.dropna(subset=["AE", "TE", "WD", "zeta"])
    edges = np.arange(0, 360 + SECTOR_WIDTH, SECTOR_WIDTH)
    d["sector"] = pd.cut((d["WD"] + SECTOR_WIDTH / 2) % 360, edges, right=False,
                         labels=[int(e) for e in edges[:-1]])

    def ebr(g):
        return g["TE"].sum() / g["AE"].sum()

    g_all = d.groupby("sector", observed=True)
    unstable = d[d["zeta"] < -0.1].groupby("sector", observed=True)
    table = pd.DataFrame({
        "share_pct": 100 * g_all.size() / len(d),
        "ebr_all": g_all[["AE", "TE"]].apply(ebr),
        "ebr_unstable": unstable[["AE", "TE"]].apply(ebr),
        "n_unstable": unstable.size(),
        "median_ustar_ws": g_all["ustar_ws"].median(),
        "median_ws": g_all["WS"].median(),
        "median_zeta": g_all["zeta"].median(),
    })
    table.index.name = "sector_centre_deg"

    CH_DAV_PROCESSED.mkdir(parents=True, exist_ok=True)
    table.to_csv(CH_DAV_PROCESSED / "07_sector_diagnostics.csv")
    with pd.option_context("display.width", 200):
        print(table.round(3).to_string())

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    x = table.index.astype(int)
    axes[0].bar(x - 4, table["ebr_all"], 8, label="all daytime")
    axes[0].bar(x + 4, table["ebr_unstable"], 8, label="z/L < −0.1")
    axes[0].set_ylabel("EBR")
    axes[0].legend()
    axes[1].bar(x, table["median_ustar_ws"], 10)
    axes[1].set_ylabel("median u*/WS")
    axes[2].bar(x, table["share_pct"], 10)
    axes[2].set_ylabel("share of daytime data (%)")
    for ax in axes:
        ax.set_xlabel("wind sector centre (deg)")
        ax.set_xticks(x)
        ax.grid(alpha=0.3, axis="y")
    fig.suptitle("CH-Dav daytime sector diagnostics (1998–2024, AE ≥ 100 W m$^{-2}$)")
    fig.tight_layout()
    CH_DAV_FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(CH_DAV_FIGURES / "07_sector_diagnostics.png", dpi=150)


if __name__ == "__main__":
    main()
