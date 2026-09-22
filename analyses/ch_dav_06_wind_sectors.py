"""CH-Dav: closure by wind direction and friction velocity.

Motivation:
- the EC boom points west (fieldbook 2002-01-09: boom re-aligned to the west
  after being found loose and rotated south), so easterly winds reach the
  sonic through the tower lattice (flow distortion, tower shadow)
- the site is on a WNW-facing slope in the NE-SW oriented Davos valley:
  up-/down-slope and valley winds may carry advection
- low u* (weak turbulence) is where closure is usually worst

Daytime (SW_IN_POT > 0), AE >= 100 W m-2, measured data only.
EBR = sum(TE) / sum(AE) per 30 deg sector, per sensor era (before / after
the 2014-07 sonic change to Gill HS).

Also EBR by quadrant (N/E/S/W) within u* classes, to separate a direction
effect from a turbulence effect (winds from some directions are windier).

Result (2026-09-22): EBR rises strongly with u* (0.2 -> 0.8), and at the same
u* northerly winds close much worse (~0.5) than S/W winds (0.75-1.0). N is the
dominant daytime direction. The N deficit is present in all six instrument
periods (N 0.44-0.62 vs S 0.68-0.82, W 0.74-1.03 at u* 0.4-1.0), i.e. it is
not tied to a sonic or gas analyser model.

Outputs: processed/CH-Dav/06_*.csv, figures/CH-Dav/06_wind_sectors.png
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ebc_explorer.ch_dav import instrument_period
from ebc_explorer.ebc import energy_terms
from ebc_explorer.fluxnet import load_ch_dav_hh
from ebc_explorer.paths import CH_DAV_FIGURES, CH_DAV_PROCESSED

SECTOR_WIDTH = 30
USTAR_BINS = [0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.5, 3.0]
USTAR_BINS_COARSE = [0, 0.3, 0.5, 0.7, 1.0, 3.0]
HS_SONIC_START = pd.Timestamp("2014-07-16 12:00")


def ebr_table(d, by):
    g = d.groupby(by, observed=True)
    out = pd.DataFrame({"n": g.size(), "ebr": g["TE"].sum() / g["AE"].sum(),
                        "H_over_AE": g["H"].sum() / g["AE"].sum(),
                        "LE_over_AE": g["LE"].sum() / g["AE"].sum()})
    return out


def main():
    df = load_ch_dav_hh()
    terms = energy_terms(df)
    terms["WD"] = df["WD"]
    terms["USTAR"] = df["USTAR"]
    terms["era"] = np.where(df.index >= HS_SONIC_START, "2014-07+ (Gill HS)", "<2014-07 (Gill R2/R3)")
    d = terms[(df["SW_IN_POT"] > 0) & (terms["AE"] >= 100)].dropna(subset=["AE", "TE", "WD", "USTAR"])
    d = d[d.index.year >= 1998]  # 1997: flux calculation bug (fieldbook 1997-08-12)

    edges = np.arange(0, 360 + SECTOR_WIDTH, SECTOR_WIDTH)
    d["sector"] = pd.cut((d["WD"] + SECTOR_WIDTH / 2) % 360, edges, right=False,
                         labels=[int(e) for e in edges[:-1]])  # label = sector centre
    d["ustar_class"] = pd.cut(d["USTAR"], USTAR_BINS, right=False)

    d["quadrant"] = pd.cut((d["WD"] + 45) % 360, [0, 90, 180, 270, 360], right=False,
                           labels=["N", "E", "S", "W"])
    d["ustar_coarse"] = pd.cut(d["USTAR"], USTAR_BINS_COARSE, right=False)

    sectors = ebr_table(d, ["era", "sector"])
    ustar = ebr_table(d, ["era", "ustar_class"])
    quad_ustar = ebr_table(d, ["ustar_coarse", "quadrant"])
    # same, per instrument period, for moderate-to-strong turbulence only
    d["period"] = instrument_period(d.index)
    mid_ustar = d[(d["USTAR"] >= 0.4) & (d["USTAR"] < 1.0)]
    quad_period = ebr_table(mid_ustar, ["period", "quadrant"])

    CH_DAV_PROCESSED.mkdir(parents=True, exist_ok=True)
    sectors.to_csv(CH_DAV_PROCESSED / "06_ebr_by_wind_sector.csv")
    ustar.to_csv(CH_DAV_PROCESSED / "06_ebr_by_ustar.csv")
    quad_ustar.to_csv(CH_DAV_PROCESSED / "06_ebr_by_quadrant_and_ustar.csv")
    quad_period.to_csv(CH_DAV_PROCESSED / "06_ebr_by_quadrant_and_period.csv")
    with pd.option_context("display.width", 200):
        print("EBR by wind sector (centre, deg):")
        print(sectors.round(3).unstack("era").to_string())
        print("\nEBR by u* class (m s-1):")
        print(ustar.round(3).unstack("era").to_string())
        print("\nEBR by u* class and wind quadrant (all years):")
        print(quad_ustar["ebr"].unstack("quadrant").round(2).to_string())
        print(quad_ustar["n"].unstack("quadrant").to_string())
        print("\nEBR by instrument period and wind quadrant (u* 0.4-1.0):")
        print(quad_period["ebr"].unstack("quadrant").round(2).to_string())

    fig = plt.figure(figsize=(13, 5.5))
    ax1 = fig.add_subplot(1, 2, 1, projection="polar")
    ax1.set_theta_zero_location("N")
    ax1.set_theta_direction(-1)
    for era, s in sectors.groupby(level="era"):
        s = s.droplevel("era")
        theta = np.deg2rad(np.append(s.index.astype(float), s.index[0]))
        ax1.plot(theta, np.append(s["ebr"], s["ebr"].iloc[0]), "o-", label=era)
    ax1.set_ylim(0, 1)
    ax1.set_title("daytime EBR by wind direction (AE ≥ 100 W m$^{-2}$)")
    ax1.legend(loc="lower left", bbox_to_anchor=(-0.15, -0.15), fontsize=8)
    ax2 = fig.add_subplot(1, 2, 2)
    for era, s in ustar.groupby(level="era"):
        s = s.droplevel("era")
        ax2.plot([iv.mid for iv in s.index], s["ebr"], "o-", label=era)
    ax2.set_xlabel("u* (m s$^{-1}$)")
    ax2.set_ylabel("daytime EBR")
    ax2.set_ylim(0, 1)
    ax2.grid(alpha=0.3)
    ax2.legend()
    fig.tight_layout()
    CH_DAV_FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(CH_DAV_FIGURES / "06_wind_sectors.png", dpi=150)


if __name__ == "__main__":
    main()
