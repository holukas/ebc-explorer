"""CH-Dav: heterogeneity and uncertainty of the available-energy terms (error budget).

Question: how much of the missing energy could come from spatial heterogeneity
or measurement uncertainty of a single available-energy term, in particular
the soil heat flux G, which varies strongly in space under a forest canopy?

Data 2020-2024 (sensor-level data start with ICOS labelling, Nov 2019):
- 5 soil plots, each with a self-calibrating heat flux plate at 5-6 cm
  (G_<plot>_1_1), soil temperature at 2-3 cm and 5 cm and soil water content at
  5 cm (METEOSENS, scripts/extract_ch_dav_meteosens.py)
- air heat and water vapour storage below the EC system from the profile
  (SH, SLE, with uncertainty SH_UNC, SLE_UNC) and from one point (SH_1P,
  SLE_1P) in the ICOS L2 fluxes
- biomass heat storage and photosynthesis (Sbio, Spho, Nicolini et al. 2026)
- radiation: two pyranometers at 35 m (SW_IN_1_1_1, SW_IN_1_1_2) and the net
  radiation corrections of Nicolini et al. (2026)
- measured NETRAD, H, LE from the FLUXNET product

Soil heat storage above each plate: S_G = C * dT/dt * dz, with dz = plate depth,
T = mean of the 2-3 cm and 5 cm soil temperatures (centred difference over
1 h), C = rho_b * c_solid + theta * rho_w * c_w. The bulk density of the
organic-rich topsoil is not measured; a range of 500 to 1200 kg m-3 is used
(800 as central value), c_solid = 1000 J kg-1 K-1.

Result (2026-09-23): G is small under the dense canopy (summer midday mean of
5 plates 6 W m-2, storage above the plates 8 W m-2). The plot-to-plot range of
G + S_G is ~20 W m-2 at summer midday, i.e. ~7 % of the residual (294 W m-2);
using the highest plot instead of the mean raises the slope only from 0.51 to
0.52. Even with every plausible error of all available-energy terms in the same
direction (~150 W m-2 at summer midday), about half of the residual remains.

Outputs: processed/CH-Dav/13_*.csv, figures/CH-Dav/13_soil_plates.png
"""

import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ebc_explorer.ebc import closure_stats
from ebc_explorer.fluxnet import load_ch_dav_fluxes_l2, load_ch_dav_hh
from ebc_explorer.nicolini import load_sbio_spho
from ebc_explorer.paths import CH_DAV_FIGURES, CH_DAV_METEOSENS_PARQUET, CH_DAV_PROCESSED

PLOTS = [1, 2, 3, 4, 5]
PLATE_DEPTH = {1: 0.06, 2: 0.06, 3: 0.05, 4: 0.05, 5: 0.05}  # m, from VARINFO_METEOSENS
RHO_B = {"low": 500.0, "mid": 800.0, "high": 1200.0}  # kg m-3, assumed range for the topsoil
C_SOLID = 1000.0  # J kg-1 K-1
C_WATER = 4.18e6  # J m-3 K-1
MIDDAY = [11.0, 11.5, 12.0, 12.5, 13.0]  # local standard time, start of half-hour


def cols(df, pattern):
    return [c for c in df.columns if re.fullmatch(pattern, c)]


def soil_storage(ms, plot, rho_b):
    """Heat storage change in the soil layer above plate `plot` (W m-2)."""
    t = ms[cols(ms, rf"TS_{plot}_1_\d") + cols(ms, rf"TS_{plot}_2_\d")].mean(axis=1)
    theta = ms[cols(ms, rf"SWC_{plot}_1_\d")].mean(axis=1)
    if theta.median() > 1:  # ICOS reports SWC in %
        theta = theta / 100
    heat_capacity = rho_b * C_SOLID + theta * C_WATER
    dtdt = (t.shift(-1) - t.shift(1)) / 3600.0
    return heat_capacity * PLATE_DEPTH[plot] * dtdt


def main():
    hh = load_ch_dav_hh()
    hh = hh[hh.index.year >= 2020]
    ms = pd.read_parquet(CH_DAV_METEOSENS_PARQUET).reindex(hh.index)
    l2 = load_ch_dav_fluxes_l2().reindex(hh.index)
    bio = load_sbio_spho("CH-Dav").reindex(hh.index)

    d = pd.DataFrame(index=hh.index)
    d["NETRAD"] = hh["NETRAD"]
    d["H"] = hh["H_F_MDS"].where(hh["H_F_MDS_QC"] == 0)
    d["LE"] = hh["LE_F_MDS"].where(hh["LE_F_MDS_QC"] == 0)
    d["TE"] = d["H"] + d["LE"]
    d["G_fluxnet"] = hh["G_F_MDS"].where(hh["G_F_MDS_QC"] == 0)
    for p in PLOTS:
        d[f"G{p}"] = ms[f"G_{p}_1_1"]
        for k, rho in RHO_B.items():
            d[f"SG{p}_{k}"] = soil_storage(ms, p, rho)
        d[f"Gs{p}"] = d[f"G{p}"] + d[f"SG{p}_mid"]  # heat flux at the soil surface
    g = d[[f"G{p}" for p in PLOTS]]
    gs = d[[f"Gs{p}" for p in PLOTS]]
    d["G_mean"], d["G_sd"] = g.mean(axis=1), g.std(axis=1)
    d["Gs_mean"], d["Gs_sd"] = gs.mean(axis=1), gs.std(axis=1)
    d["Gs_max"], d["Gs_min"] = gs.max(axis=1), gs.min(axis=1)
    for k in RHO_B:
        d[f"SG_{k}"] = d[[f"SG{p}_{k}" for p in PLOTS]].mean(axis=1)
    d["S_air"] = l2["SH"] + l2["SLE"]
    d["S_air_unc"] = np.hypot(l2["SH_UNC"], l2["SLE_UNC"])
    d["S_air_1p"] = l2["SH_1P"] + l2["SLE_1P"]
    d["S_bio"] = bio["Sbio"] + bio["Spho"]
    d["NETRAD_fullcorr"] = bio["NETRAD_fullcorr"]
    d["SW_IN_diff"] = ms["SW_IN_1_1_2"] - ms["SW_IN_1_1_1"]
    d["day"] = hh["SW_IN_POT"] > 0
    d["hour"] = d.index.hour + d.index.minute / 60
    d["summer"] = d.index.month.isin([6, 7, 8])

    # 1. closure with each G variant, on one common sample (daytime, all terms available)
    need = ["NETRAD", "TE", "G_fluxnet", "Gs_mean", "Gs_max", "Gs_min", "S_air", "S_bio"] + [f"Gs{p}" for p in PLOTS]
    c = d[d["day"]].dropna(subset=need)
    full = c["S_air"] + c["S_bio"]
    variants = {
        "Rn - G (FLUXNET)": c["NETRAD"] - c["G_fluxnet"],
        "Rn - mean G (5 plates)": c["NETRAD"] - c[[f"G{p}" for p in PLOTS]].mean(axis=1),
        "Rn - mean (G + S_G)": c["NETRAD"] - c["Gs_mean"],
        **{f"Rn - (G + S_G), plot {p}": c["NETRAD"] - c[f"Gs{p}"] for p in PLOTS},
        "Rn - highest plot (G + S_G)": c["NETRAD"] - c["Gs_max"],
        "Rn - lowest plot (G + S_G)": c["NETRAD"] - c["Gs_min"],
        "all terms, mean (G + S_G)": c["NETRAD"] - c["Gs_mean"] - full,
        "all terms, highest plot": c["NETRAD"] - c["Gs_max"] - full,
    }
    closure = pd.DataFrame({k: closure_stats(ae, c["TE"]) for k, ae in variants.items()}).T

    # 2. error budget: midday in summer and all daytime, on the same common sample
    rows = {}
    for label, sel in (("summer midday", c["summer"] & c["hour"].isin(MIDDAY)), ("daytime, all year", slice(None))):
        s = c.loc[sel]
        res = (s["NETRAD"] - s["Gs_mean"] - s["S_air"] - s["S_bio"] - s["TE"]).mean()
        sw = d.loc[s.index, "SW_IN_diff"]
        rows[label] = {
            "residual AE - TE (all terms)": res,
            "NETRAD mean": s["NETRAD"].mean(),
            "G mean of 5 plates": s[[f"G{p}" for p in PLOTS]].mean(axis=1).mean(),
            "G spatial SD between plates": s[[f"G{p}" for p in PLOTS]].std(axis=1).mean(),
            "G standard error of the 5-plate mean": (s[[f"G{p}" for p in PLOTS]].std(axis=1) / np.sqrt(5)).mean(),
            "G highest minus lowest plate": (s[[f"G{p}" for p in PLOTS]].max(axis=1) - s[[f"G{p}" for p in PLOTS]].min(axis=1)).mean(),
            "S_G mean (bulk density 800)": d.loc[s.index, "SG_mid"].mean(),
            "S_G range for bulk density 500 to 1200": (d.loc[s.index, "SG_high"] - d.loc[s.index, "SG_low"]).mean(),
            "G + S_G highest minus lowest plot": (s["Gs_max"] - s["Gs_min"]).mean(),
            "S_air mean (profile)": s["S_air"].mean(),
            "S_air uncertainty (ICOS)": d.loc[s.index, "S_air_unc"].mean(),
            "S_air profile minus one point": (s["S_air"] - d.loc[s.index, "S_air_1p"]).abs().mean(),
            "S_bio + S_pho mean": s["S_bio"].mean(),
            "S_bio + S_pho: extra if twice as large": s["S_bio"].mean(),
            "SW_IN difference between 2 pyranometers": sw.abs().mean(),
            "NETRAD corrected minus measured (Nicolini)": (d.loc[s.index, "NETRAD_fullcorr"] - s["NETRAD"]).mean(),
            "n half-hours": float(len(s)),
        }
        r = rows[label]
        # upper bound: every plausible error of the available-energy terms in the same direction;
        # a SW_IN error changes Rn by (1 - albedo) ~ 0.94 of it
        r["upper bound: all errors in the same direction"] = (
            r["G + S_G highest minus lowest plot"] + r["S_G range for bulk density 500 to 1200"]
            + r["S_air profile minus one point"] + r["S_bio + S_pho: extra if twice as large"]
            + 0.94 * r["SW_IN difference between 2 pyranometers"]
            + abs(r["NETRAD corrected minus measured (Nicolini)"]))
    budget = pd.DataFrame(rows)
    for col in budget.columns:
        budget[f"{col}, % of residual"] = 100 * budget[col].abs() / budget.loc["residual AE - TE (all terms)", col]
    budget.loc["n half-hours", [c2 for c2 in budget.columns if "%" in c2]] = np.nan
    budget.loc["residual AE - TE (all terms)", [c2 for c2 in budget.columns if "%" in c2]] = 100.0

    # 3. mean diurnal cycle per plot in summer
    summer = d[d["summer"]]
    diurnal = summer.groupby("hour")[[f"G{p}" for p in PLOTS] + [f"Gs{p}" for p in PLOTS] + ["SG_mid"]].mean()

    CH_DAV_PROCESSED.mkdir(parents=True, exist_ok=True)
    closure.to_csv(CH_DAV_PROCESSED / "13_closure_by_G_variant.csv")
    budget.to_csv(CH_DAV_PROCESSED / "13_error_budget.csv")
    diurnal.to_csv(CH_DAV_PROCESSED / "13_soil_plates_diurnal_summer.csv")
    with pd.option_context("display.width", 220, "display.max_columns", 20):
        print(f"common daytime sample: {len(c)} half-hours")
        print(closure[["n", "ols_slope", "ebr", "mean_res"]].round(3).to_string())
        print()
        print(budget.round(1).to_string())
        print()
        print("summer mean diurnal G per plate (W m-2), selected hours:")
        print(diurnal.loc[[0.0, 6.0, 9.0, 12.0, 15.0, 18.0, 21.0]].round(1).to_string())

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    for p in PLOTS:
        axes[0].plot(diurnal.index, diurnal[f"G{p}"], label=f"plot {p} (G at {PLATE_DEPTH[p] * 100:.0f} cm)")
        axes[1].plot(diurnal.index, diurnal[f"Gs{p}"], label=f"plot {p}")
    for ax, t in zip(axes, ["heat flux plate G", "G + storage above plate (surface flux)"]):
        ax.axhline(0, color="k", lw=0.6)
        ax.set_title(f"CH-Dav, summer 2020-2024: {t}")
        ax.set_xlabel("hour (local standard time)"); ax.set_ylabel("W m$^{-2}$"); ax.grid(alpha=0.3)
    axes[0].legend(fontsize=8)
    fig.tight_layout()
    CH_DAV_FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(CH_DAV_FIGURES / "13_soil_plates.png", dpi=150)


if __name__ == "__main__":
    main()
