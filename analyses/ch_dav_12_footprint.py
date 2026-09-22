"""CH-Dav: ICOS footprint distances, lake and open ground in the footprint, and closure.

Data: ICOS ETC L2 fluxes 2019-2024 (raw/ICOSETC_CH-Dav_ARCHIVE_L2_2025/), which
contain per half-hour the cross-wind integrated footprint distances from the
Kljun et al. (2015) model: FETCH_OFFSET (1 %), FETCH_MAX (peak), FETCH_50/70/80/90
(cumulative 50-90 %), and FOOTPRINT_TA_CONTR (contribution of the ICOS target
area). Only FOOTPRINT_FLAG == 0 is used.

Per half-hour (daytime, measured NETRAD/G/H/LE from the FLUXNET product):
1. distance from the tower to the lake shore and to the forest edge along the
   wind direction (lake outline swissTLM3D, canopy height from swisstopo; the
   forest edge is the start of the first 50 m stretch with canopy < 2 m)
2. share of the cross-wind integrated footprint beyond those distances, from
   the cumulative distribution given by FETCH_OFFSET/50/70/80/90 (linear
   interpolation; beyond FETCH_90 an exponential tail)
3. EBR by class of lake share, open-ground share, FETCH_80 and target-area
   contribution; footprint distances per 30 deg sector for the 3D map

Result (2026-09-22): daytime FETCH_50/80/90 medians ~40-50 / 110-120 / 190-210 m.
For N wind the lake starts 350 m away and contributes ~3 % of the flux; within
the N sector EBR does not change with this share (0.42-0.47). At equal u*,
EBR decreases with FETCH_80 (u* 0.6-0.8: 0.65 within 90 m, 0.37 beyond 130 m);
FETCH ranks exactly with z/L, so closure is poorest near neutral.

Outputs: processed/CH-Dav/12_*.csv
"""

import json

import numpy as np
import pandas as pd
from matplotlib.path import Path as MplPath

from ebc_explorer.ch_dav import TOWER_LV95
from ebc_explorer.ebc import energy_terms
from ebc_explorer.fluxnet import load_ch_dav_fluxes_l2, load_ch_dav_hh
from ebc_explorer.paths import CH_DAV_PROCESSED, CH_DAV_SWISSTOPO
from ebc_explorer.terrain import mosaic, sample

SECTOR_WIDTH = 30
OPEN_CHM = 2.0
EDGE_RUN = 50  # m of continuous open ground that marks the forest edge
CANOPY_BOUNDS = (2783000, 1186000, 2786000, 1190000)


def ray_distances():
    """Per whole degree: distance to the lake shore and to the forest edge along the ray."""
    lake = json.loads((CH_DAV_SWISSTOPO / "davoser_see_swisstlm3d.geojson").read_text(encoding="utf-8"))
    rings = [MplPath(np.array(p[0])[:, :2]) for p in lake["geometry"]["coordinates"]]
    dsm, t = mosaic(CH_DAV_SWISSTOPO / "surface3d_0.5m", 1.0, bounds=CANOPY_BOUNDS)
    dtm, _ = mosaic(CH_DAV_SWISSTOPO / "alti3d_0.5m", 1.0, bounds=CANOPY_BOUNDS)
    chm = dsm - dtm
    d = np.arange(0, 3000, 2.0)
    out = []
    for deg in range(360):
        a = np.radians(deg)
        x, y = TOWER_LV95[0] + d * np.sin(a), TOWER_LV95[1] + d * np.cos(a)
        on_lake = np.zeros(d.size, bool)
        for r in rings:
            on_lake |= r.contains_points(np.column_stack([x, y]))
        c = sample(chm, t, x, y)
        is_open = (c < OPEN_CHM) | on_lake
        run = int(EDGE_RUN / 2.0)
        opened = np.convolve(is_open.astype(int), np.ones(run, int), "valid") == run
        lake_d = d[on_lake.argmax()] if on_lake.any() else np.nan
        edge_d = d[opened.argmax()] if opened.any() else np.nan
        out.append({"deg": deg, "lake_m": lake_d, "edge_m": edge_d})
    return pd.DataFrame(out).set_index("deg")


def share_beyond(dist, fp):
    """Share of the cross-wind integrated footprint beyond `dist` (m), per row of fp."""
    xs = fp[["FETCH_OFFSET", "FETCH_50", "FETCH_70", "FETCH_80", "FETCH_90"]].to_numpy()
    ps = np.array([0.01, 0.5, 0.7, 0.8, 0.9])
    out = np.full(len(fp), np.nan)
    for i, (x, dd) in enumerate(zip(xs, dist)):
        if not np.all(np.isfinite(x)) or not np.isfinite(dd):
            out[i] = 0.0 if np.all(np.isfinite(x)) else np.nan
            continue
        if dd <= x[-1]:
            out[i] = 1 - np.interp(dd, x, ps, left=0.0)
        else:  # exponential tail fitted through FETCH_80 and FETCH_90
            k = np.log(0.2 / 0.1) / max(x[-1] - x[-2], 1.0)
            out[i] = 0.1 * np.exp(-k * (dd - x[-1]))
    return out


def ebr_by(d, col, bins):
    d = d.assign(cls=pd.cut(d[col], bins, include_lowest=True))
    g = d.groupby("cls", observed=True)
    return pd.DataFrame({"n": g.size(), "ebr": g["TE"].sum() / g["AE"].sum(),
                         "median_" + col: g[col].median()})


def main():
    fp = load_ch_dav_fluxes_l2()
    fp = fp[fp["FOOTPRINT_FLAG"] == 0]
    hh = load_ch_dav_hh()
    terms = energy_terms(hh)
    day = hh["SW_IN_POT"] > 0
    d = terms[day].join(fp[["WD", "USTAR", "FETCH_OFFSET", "FETCH_MAX", "FETCH_50", "FETCH_70", "FETCH_80",
                             "FETCH_90", "FOOTPRINT_TA_CONTR"]], how="inner")
    d = d.dropna(subset=["AE", "TE", "WD", "FETCH_80"])
    d = d[d["AE"] >= 100]

    rays = ray_distances()
    deg = np.round(d["WD"]).astype(int) % 360
    d["lake_m"] = rays["lake_m"].reindex(deg).to_numpy()
    d["edge_m"] = rays["edge_m"].reindex(deg).to_numpy()
    d["lake_share"] = share_beyond(d["lake_m"].to_numpy(), d)
    d["open_share"] = share_beyond(d["edge_m"].to_numpy(), d)
    d["sector"] = ((d["WD"] + SECTOR_WIDTH / 2) // SECTOR_WIDTH % (360 // SECTOR_WIDTH) * SECTOR_WIDTH).astype(int)

    g = d.groupby("sector")
    sectors = pd.DataFrame({
        "n": g.size(),
        "ebr": g["TE"].sum() / g["AE"].sum(),
        **{f"{c.lower()}_median": g[c].median() for c in ["FETCH_MAX", "FETCH_50", "FETCH_70", "FETCH_80", "FETCH_90"]},
        "fetch_90_p75": g["FETCH_90"].quantile(0.75),
        "ta_contr_median": g["FOOTPRINT_TA_CONTR"].median(),
        "lake_m": rays["lake_m"].reindex(sectors_idx := g.size().index).to_numpy(),
        "edge_m": rays["edge_m"].reindex(sectors_idx).to_numpy(),
        "lake_share_mean_pct": 100 * g["lake_share"].mean(),
        "open_share_mean_pct": 100 * g["open_share"].mean(),
    })
    classes = {
        "lake_share": ebr_by(d, "lake_share", [0, 0.001, 0.02, 0.05, 0.1, 1]),
        "open_share": ebr_by(d, "open_share", [0, 0.01, 0.05, 0.1, 0.2, 1]),
        "FETCH_80": ebr_by(d, "FETCH_80", [0, 75, 100, 150, 250, 2000]),
        "FOOTPRINT_TA_CONTR": ebr_by(d, "FOOTPRINT_TA_CONTR", [0, 0.6, 0.7, 0.75, 0.8, 1]),
    }
    north = d[d["sector"].isin([0, 330])]
    classes["open_share_north"] = ebr_by(north, "open_share", [0, 0.01, 0.05, 0.1, 0.2, 1])

    CH_DAV_PROCESSED.mkdir(parents=True, exist_ok=True)
    sectors.to_csv(CH_DAV_PROCESSED / "12_footprint_by_sector.csv")
    rays.to_csv(CH_DAV_PROCESSED / "12_ray_distances.csv")
    pd.concat(classes, names=["variable", "class"]).to_csv(CH_DAV_PROCESSED / "12_ebr_by_footprint_class.csv")
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(f"daytime half-hours with valid footprint and closure data: {len(d)}")
        print(sectors.round(2).to_string())
        for k, v in classes.items():
            print(f"\nEBR by {k}:")
            print(v.round(3).to_string())


if __name__ == "__main__":
    main()
