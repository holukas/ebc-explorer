"""CH-Dav: terrain and canopy around the tower, per wind sector.

Motivation (06, 07): daytime winds from N/NNE close at ~0.5, S/SW/W at
0.75-1.0, at the same u*. Is the terrain or the canopy different to the north?

Data: swisstopo swissALTI3D (terrain, 2 m, 8 x 8 km) and swissSURFACE3D
Raster (surface incl. trees, read at 1 m from the 0.5 m tiles, 3 x 4 km),
downloaded with scripts/download_ch_dav_terrain.py. Canopy height model
CHM = surface - terrain.

Per 30 deg wind sector (same sectors as 06/07):
1. terrain: height along the sector centre line relative to the tower base,
   and the mean terrain gradient along the wind direction (positive = the
   ground rises towards where the wind comes from, i.e. the air flows downhill
   to the tower)
2. canopy: mean canopy height and share of open ground (CHM < 2 m) in
   distance bands 0-250, 250-500, 500-1000, 1000-1400 m
3. join with EBR per sector from 07

Result (2026-09-22): local slope 18 deg (250 m) / 15 deg (500 m), facing
WNW. The tower stands at the foot of the forested slope, ~80 m above the flat,
open valley floor to the N, NW and W. North of the tower the forest ends after
~250-300 m (open ground: 36 % at 0-250 m, 74 % at 250-500 m, 97 % at
500-1000 m); northerly air crosses the valley floor and rises ~18 % over the
last 500 m to the tower. W/NW are equally open but rare (< 1 % of data).

Outputs: processed/CH-Dav/08_*.csv, figures/CH-Dav/08_terrain_map.png,
08_canopy_map.png, 08_sector_profiles.png
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling
from rasterio.merge import merge

from ebc_explorer.paths import CH_DAV_FIGURES, CH_DAV_PROCESSED, CH_DAV_SWISSTOPO

TOWER = (2784453.0, 1187750.0)  # LV95
SECTOR_WIDTH = 30
BANDS = [(0, 250), (250, 500), (500, 1000), (1000, 1400)]
OPEN_CHM = 2.0  # m, canopy height below which ground counts as open


def mosaic(folder, res):
    files = sorted(Path(folder).glob("*.tif"))
    srcs = [rasterio.open(f) for f in files]
    arr, transform = merge(srcs, res=res, resampling=Resampling.average, nodata=-9999)
    for s in srcs:
        s.close()
    a = arr[0].astype("float64")
    a[a == -9999] = np.nan
    return a, transform


def grid_coords(shape, transform):
    rows, cols = np.indices(shape)
    x = transform.c + (cols + 0.5) * transform.a
    y = transform.f + (rows + 0.5) * transform.e
    return x, y


def polar(x, y):
    dx, dy = x - TOWER[0], y - TOWER[1]
    dist = np.hypot(dx, dy)
    az = (np.degrees(np.arctan2(dx, dy)) + 360) % 360  # 0 = north, clockwise
    sector = ((az + SECTOR_WIDTH / 2) // SECTOR_WIDTH % (360 // SECTOR_WIDTH) * SECTOR_WIDTH).astype(int)
    return dist, sector


def sample(a, transform, x, y):
    col = ((x - transform.c) / transform.a).astype(int)
    row = ((y - transform.f) / transform.e).astype(int)
    ok = (row >= 0) & (row < a.shape[0]) & (col >= 0) & (col < a.shape[1])
    out = np.full(np.shape(x), np.nan)
    out[ok] = a[row[ok], col[ok]]
    return out


def hillshade(z, res, az=315, alt=45):
    gy, gx = np.gradient(z, res)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    a, b = np.radians(az), np.radians(alt)
    return np.sin(b) * np.cos(slope) + np.cos(b) * np.sin(slope) * np.cos(a - aspect)


def main():
    dtm2, t2 = mosaic(CH_DAV_SWISSTOPO / "alti3d_2m", 2.0)
    dsm1, t1 = mosaic(CH_DAV_SWISSTOPO / "surface3d_0.5m", 1.0)
    dtm1, _ = mosaic(CH_DAV_SWISSTOPO / "alti3d_0.5m", 1.0)
    chm = np.clip(dsm1 - dtm1, 0, 60)
    z0 = float(sample(dtm2, t2, np.array([TOWER[0]]), np.array([TOWER[1]]))[0])

    # local plane fit within 250 m and 1000 m: slope and aspect
    x2, y2 = grid_coords(dtm2.shape, t2)
    d2, s2 = polar(x2, y2)
    local = []
    for r in (250, 500, 1000):
        m = (d2 <= r) & np.isfinite(dtm2)
        A = np.column_stack([x2[m] - TOWER[0], y2[m] - TOWER[1], np.ones(m.sum())])
        (gx, gy, _), *_ = np.linalg.lstsq(A, dtm2[m], rcond=None)
        slope = np.degrees(np.arctan(np.hypot(gx, gy)))
        aspect = (np.degrees(np.arctan2(-gx, -gy)) + 360) % 360  # direction the slope faces (downhill)
        local.append({"radius_m": r, "slope_deg": slope, "aspect_deg": aspect})
    local = pd.DataFrame(local)

    # per sector: terrain profile and gradient along the wind direction, canopy by band
    sectors = np.arange(0, 360, SECTOR_WIDTH)
    dist = np.arange(0, 3001, 20.0)
    profiles, rows = {}, []
    x1, y1 = grid_coords(chm.shape, t1)
    d1, s1 = polar(x1, y1)
    for sec in sectors:
        az = np.radians(sec)
        px, py = TOWER[0] + dist * np.sin(az), TOWER[1] + dist * np.cos(az)
        prof = sample(dtm2, t2, px, py) - z0
        profiles[sec] = prof
        row = {"sector_centre_deg": int(sec)}
        for lo, hi in [(0, 500), (0, 1000), (0, 2000)]:
            m = (dist >= lo) & (dist <= hi) & np.isfinite(prof)
            # rise of the ground per metre towards the wind source (upwind)
            row[f"upwind_gradient_pct_{lo}_{hi}"] = 100 * np.polyfit(dist[m], prof[m], 1)[0]
        row["height_at_1km_m"] = prof[dist == 1000][0]
        for lo, hi in BANDS:
            m = (s1 == sec) & (d1 >= lo) & (d1 < hi) & np.isfinite(chm)
            c = chm[m]
            row[f"chm_mean_{lo}_{hi}"] = c.mean() if c.size else np.nan
            row[f"open_pct_{lo}_{hi}"] = 100 * (c < OPEN_CHM).mean() if c.size else np.nan
        rows.append(row)
    table = pd.DataFrame(rows).set_index("sector_centre_deg")
    ebr = pd.read_csv(CH_DAV_PROCESSED / "07_sector_diagnostics.csv", index_col=0)
    table = table.join(ebr[["share_pct", "ebr_all", "ebr_unstable"]])

    CH_DAV_PROCESSED.mkdir(parents=True, exist_ok=True)
    local.to_csv(CH_DAV_PROCESSED / "08_local_terrain.csv", index=False)
    table.to_csv(CH_DAV_PROCESSED / "08_sector_terrain_canopy.csv")
    pd.DataFrame(profiles, index=dist).rename_axis("distance_m").to_csv(CH_DAV_PROCESSED / "08_sector_profiles.csv")
    with pd.option_context("display.width", 250, "display.max_columns", 40):
        print(f"tower ground elevation {z0:.1f} m a.s.l.")
        print(local.round(1).to_string(index=False))
        cols = ["share_pct", "ebr_all", "upwind_gradient_pct_0_500", "upwind_gradient_pct_0_2000", "height_at_1km_m",
                "chm_mean_0_250", "chm_mean_250_500", "chm_mean_500_1000", "open_pct_0_250", "open_pct_250_500",
                "open_pct_500_1000", "open_pct_1000_1400"]
        print(table[cols].round(2).to_string())

    CH_DAV_FIGURES.mkdir(parents=True, exist_ok=True)
    ext2 = [t2.c, t2.c + dtm2.shape[1] * t2.a, t2.f + dtm2.shape[0] * t2.e, t2.f]
    ext1 = [t1.c, t1.c + chm.shape[1] * t1.a, t1.f + chm.shape[0] * t1.e, t1.f]

    def sector_lines(ax, r):
        for sec in sectors - SECTOR_WIDTH / 2:
            a = np.radians(sec)
            ax.plot([TOWER[0], TOWER[0] + r * np.sin(a)], [TOWER[1], TOWER[1] + r * np.cos(a)], color="w", lw=0.6, alpha=0.7)
        for rr in (500, 1000, 2000):
            if rr <= r:
                th = np.linspace(0, 2 * np.pi, 200)
                ax.plot(TOWER[0] + rr * np.sin(th), TOWER[1] + rr * np.cos(th), color="w", lw=0.6, ls=":", alpha=0.9)
        ax.plot(*TOWER, marker="^", color="#eb6834", ms=10, mec="k")

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(hillshade(dtm2, 2.0), extent=ext2, cmap="gray", vmin=0, vmax=1)
    cs = ax.contour(np.flipud(dtm2), levels=np.arange(1400, 2800, 100), extent=ext2, colors="k", linewidths=0.4, alpha=0.6)
    ax.clabel(cs, fmt="%d", fontsize=6)
    sector_lines(ax, 3000)
    ax.add_patch(plt.Rectangle((ext1[0], ext1[2]), ext1[1] - ext1[0], ext1[3] - ext1[2], fill=False, ec="#2a78d6", lw=1.5))
    ax.set_title("CH-Dav terrain (swissALTI3D 2 m, © swisstopo)\n30° wind sectors, rings at 0.5, 1, 2 km; blue: canopy map area")
    ax.set_xlabel("E (LV95, m)"); ax.set_ylabel("N (LV95, m)")
    fig.tight_layout(); fig.savefig(CH_DAV_FIGURES / "08_terrain_map.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 8.5))
    im = ax.imshow(chm, extent=ext1, cmap="YlGn", vmin=0, vmax=40)
    sector_lines(ax, 2200)
    fig.colorbar(im, ax=ax, shrink=0.7, label="canopy height (m)")
    ax.set_title("Canopy height = surface − terrain (swissSURFACE3D 2020, swissALTI3D 2019, © swisstopo)", fontsize=9)
    ax.set_xlabel("E (LV95, m)"); ax.set_ylabel("N (LV95, m)")
    fig.tight_layout(); fig.savefig(CH_DAV_FIGURES / "08_canopy_map.png", dpi=150); plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    for sec, color in [(0, "C0"), (30, "C1"), (180, "C2"), (210, "C3"), (270, "C4"), (90, "C5")]:
        axes[0].plot(dist, profiles[sec], color=color, label=f"{sec}° (EBR {table.loc[sec, 'ebr_all']:.2f})")
    axes[0].axhline(0, color="k", lw=0.6)
    axes[0].axhline(35, color="0.5", lw=0.6, ls=":")
    axes[0].text(2990, 37, "EC height", ha="right", fontsize=8, color="0.4")
    axes[0].set_xlabel("distance from tower along the wind direction (m)")
    axes[0].set_ylabel("ground height relative to tower base (m)")
    axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3)
    x = table.index.to_numpy()
    axes[1].bar(x - 6, table["open_pct_250_500"], 12, label="open ground 250–500 m (%)")
    axes[1].bar(x + 6, table["open_pct_500_1000"], 12, label="open ground 500–1000 m (%)")
    ax2 = axes[1].twinx()
    ax2.plot(x, table["ebr_all"], "ko-", label="EBR")
    ax2.set_ylim(0, 1)
    axes[1].set_xticks(x); axes[1].set_xlabel("wind sector centre (°)")
    axes[1].set_ylabel("share of open ground (CHM < 2 m, %)"); ax2.set_ylabel("EBR")
    axes[1].legend(loc="upper left", fontsize=8); ax2.legend(loc="upper right", fontsize=8)
    fig.tight_layout(); fig.savefig(CH_DAV_FIGURES / "08_sector_profiles.png", dpi=150); plt.close(fig)


if __name__ == "__main__":
    main()
