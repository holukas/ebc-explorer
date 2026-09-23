"""CH-Dav: water balance check of measured and closure-corrected LE.

Question: the FLUXNET product provides H_CORR and LE_CORR, i.e. H and LE
scaled by the energy balance closure factor (Rn - G) / (H + LE) of a moving
window, with the Bowen ratio kept. At CH-Dav this roughly doubles both fluxes.
Is the doubled evapotranspiration (ET) compatible with precipitation?
Over several years, ET cannot exceed precipitation P minus runoff Q, and Q is
clearly positive in this Alpine area.

Data: FLUXNET half-hourly product, 1998-2024 (1997 has a flux calculation
error). ET = LE * 1800 s / lambda, lambda = (2.501 - 0.00237 Ta) 1e6 J kg-1.
- ET_meas from LE_F_MDS (measured + MDS gap-filled; annual sums need gap-filled data)
- ET_corr from LE_CORR
- P_F: site precipitation gauge (gap-filled with ERA5); P_ERA: downscaled ERA5
- implied runoff ratio 1 - ET/P (soil and snow storage cancel over several years)
- Budyko expectation (Fu equation, w = 2.6) with Priestley-Taylor potential ET
  (alpha = 1.26) from measured Rn - G, for years with >= 95 % AE coverage.

Caveats: the gauge probably underestimates snowfall (undercatch); P_ERA is a
model value for a grid cell. ET_meas depends on gap filling, which is large
after 2019 (measured LE in only ~45 % of half-hours in 2020-2024).

Result (2026-09-23): ET_corr exceeds site P in 16 of 27 years (1998-2024); over
1998-2024 ET_corr/P is 1.01 with both the gauge and ERA5, which leaves no runoff.
ET_meas/P is 0.62, i.e. a runoff ratio of ~0.4. The Budyko curve gives ET/P ~0.73.
For 2019-2024 alone, ET_corr/P is 0.80 (runoff ratio 0.2) and ET_meas/P 0.40;
ET_meas dropped from ~590 mm (1998-2018) to ~405 mm (2019-2024).
The water balance does not support doubling LE; at most a part of the missing
energy can be latent heat. Runoff data for the catchment would make this test
quantitative.

Outputs: processed/CH-Dav/14_water_balance_yearly.csv, 14_water_balance_periods.csv,
figures/CH-Dav/14_water_balance.png
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ebc_explorer.fluxnet import load_ch_dav_hh
from ebc_explorer.paths import CH_DAV_FIGURES, CH_DAV_PROCESSED

FIRST_YEAR = 1998
PERIODS = {"1998-2024": (1998, 2024), "1998-2018": (1998, 2018), "2019-2024": (2019, 2024)}
FU_W = 2.6
PT_ALPHA = 1.26


def fu_ratio(phi, w=FU_W):
    """Budyko curve after Fu (1981): ET/P as a function of aridity PET/P."""
    return 1 + phi - (1 + phi ** w) ** (1 / w)


def main():
    hh = load_ch_dav_hh()
    hh = hh[hh.index.year >= FIRST_YEAR]
    year = hh.index.year
    lam = (2.501 - 0.00237 * hh.TA_F) * 1e6
    to_mm = 1800 / lam

    ta = hh.TA_F
    es = 0.6108 * np.exp(17.27 * ta / (ta + 237.3))
    slope = 4098 * es / (ta + 237.3) ** 2
    gamma = 0.000665 * hh.PA_F
    ae = (hh.NETRAD - hh.G_F_MDS).clip(lower=0)

    t = pd.DataFrame({
        "P_F": hh.P_F.groupby(year).sum(),
        "P_ERA": hh.P_ERA.groupby(year).sum(),
        "ET_meas": (hh.LE_F_MDS * to_mm).groupby(year).sum(),
        "ET_corr": (hh.LE_CORR * to_mm).groupby(year).sum(),
        "PET_PT": (PT_ALPHA * slope / (slope + gamma) * ae * to_mm).groupby(year).sum(),
        "LE_measured_share": hh.LE_F_MDS_QC.eq(0).groupby(year).mean(),
        "AE_coverage": ae.notna().groupby(year).mean(),
    })
    t.loc[t.AE_coverage < 0.95, "PET_PT"] = np.nan
    t["ET_budyko"] = fu_ratio(t.PET_PT / t.P_F) * t.P_F
    for et in ("ET_meas", "ET_corr"):
        t[f"{et}/P_F"] = t[et] / t.P_F
        t[f"{et}/P_ERA"] = t[et] / t.P_ERA
    t.index.name = "year"

    rows = {}
    for name, (a, b) in PERIODS.items():
        s = t.loc[a:b]
        tot = s[["P_F", "P_ERA", "ET_meas", "ET_corr"]].sum()
        b_years = s.dropna(subset=["ET_budyko"])
        rows[name] = {
            "n_years": len(s),
            **(tot / len(s)).rename(lambda c: f"{c}_mean_mm").to_dict(),
            "ET_meas/P_F": tot.ET_meas / tot.P_F, "ET_corr/P_F": tot.ET_corr / tot.P_F,
            "ET_meas/P_ERA": tot.ET_meas / tot.P_ERA, "ET_corr/P_ERA": tot.ET_corr / tot.P_ERA,
            "runoff_ratio_meas_P_F": 1 - tot.ET_meas / tot.P_F, "runoff_ratio_corr_P_F": 1 - tot.ET_corr / tot.P_F,
            "years_ET_corr_gt_P_F": int((s.ET_corr > s.P_F).sum()),
            "years_ET_meas_gt_P_F": int((s.ET_meas > s.P_F).sum()),
            "ET_budyko/P_F": b_years.ET_budyko.sum() / b_years.P_F.sum(),
            "LE_measured_share": s.LE_measured_share.mean(),
        }
    periods = pd.DataFrame(rows).T
    periods.index.name = "period"

    CH_DAV_PROCESSED.mkdir(parents=True, exist_ok=True)
    t.to_csv(CH_DAV_PROCESSED / "14_water_balance_yearly.csv")
    periods.to_csv(CH_DAV_PROCESSED / "14_water_balance_periods.csv")
    with pd.option_context("display.width", 220, "display.max_columns", 30):
        print(t.round(2).to_string())
        print()
        print(periods.T.round(2).to_string())

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(t.index, t.P_F, "o-", color="tab:blue", label="P, site gauge")
    ax.plot(t.index, t.P_ERA, "o--", color="tab:blue", alpha=0.5, label="P, ERA5")
    ax.plot(t.index, t.ET_corr, "s-", color="tab:red", label="ET from LE_CORR")
    ax.plot(t.index, t.ET_meas, "s-", color="tab:green", label="ET from LE (measured + gap-filled)")
    ax.set_ylabel("mm per year")
    ax.set_ylim(0, None)
    ax.grid(alpha=0.3)
    ax.legend(ncol=2, loc="lower left")
    ax.set_title("CH-Dav: yearly precipitation and evapotranspiration")
    fig.tight_layout()
    CH_DAV_FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(CH_DAV_FIGURES / "14_water_balance.png", dpi=150)


if __name__ == "__main__":
    main()
