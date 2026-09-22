"""Energy balance closure (EBC) terms and statistics.

Conventions:
- AE (available energy) = NETRAD - G
- TE (turbulent energy) = H + LE
- residual = AE - TE (positive = turbulent fluxes too small)
- "measured" = FLUXNET *_QC == 0, i.e. not gap-filled
"""

import numpy as np
import pandas as pd

STAT_NAMES = ["n", "ols_slope", "ols_intercept", "r2", "ols_slope_i0", "rma_slope", "ebr", "mean_res"]


def energy_terms(df, measured_only=True):
    """Return a DataFrame with NETRAD, G, H, LE, AE, TE, RES.

    With measured_only, gap-filled G/H/LE values are set to NaN.
    """
    out = pd.DataFrame(index=df.index)
    out["NETRAD"] = df["NETRAD"]
    for var in ("G", "H", "LE"):
        val = df[f"{var}_F_MDS"]
        if measured_only:
            val = val.where(df[f"{var}_F_MDS_QC"] == 0)
        out[var] = val
    out["AE"] = out["NETRAD"] - out["G"]
    out["TE"] = out["H"] + out["LE"]
    out["RES"] = out["AE"] - out["TE"]
    return out


def closure_stats(ae, te):
    """Closure statistics of TE against AE for complete pairs.

    Returns a Series: n, OLS slope/intercept/r2, OLS slope through origin,
    RMA slope, energy balance ratio EBR = sum(TE)/sum(AE), mean residual.
    """
    ok = ae.notna() & te.notna()
    x, y = ae[ok].to_numpy(float), te[ok].to_numpy(float)
    n = len(x)
    if n < 10:
        return pd.Series({"n": n}, index=STAT_NAMES, dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    r = np.corrcoef(x, y)[0, 1]
    return pd.Series({
        "n": n,
        "ols_slope": slope,
        "ols_intercept": intercept,
        "r2": r ** 2,
        "ols_slope_i0": (x @ y) / (x @ x),
        "rma_slope": np.sign(r) * y.std() / x.std(),
        "ebr": y.sum() / x.sum(),
        "mean_res": (x - y).mean(),
    })


def closure_by(terms, by):
    """closure_stats per group; `by` is anything accepted by DataFrame.groupby."""
    return terms.groupby(by)[["AE", "TE"]].apply(lambda g: closure_stats(g["AE"], g["TE"]))


def daily_means(terms, min_halfhours=40):
    """Daily means of the energy terms, keeping only days where every term
    has at least `min_halfhours` of 48 values."""
    cols = ["NETRAD", "G", "H", "LE"]
    counts = terms[cols].notna().groupby(terms.index.date).sum()
    means = terms[cols].groupby(terms.index.date).mean()
    means = means.where(counts >= min_halfhours).dropna()
    means.index = pd.to_datetime(means.index)
    means["AE"] = means["NETRAD"] - means["G"]
    means["TE"] = means["H"] + means["LE"]
    means["RES"] = means["AE"] - means["TE"]
    return means
