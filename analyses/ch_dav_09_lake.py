"""CH-Dav: the Davoser See next to the tower.

The lake outline comes from swisstopo swissTLM3D (layer
ch.swisstopo.swisstlm3d-gewaessernetz, feature 1256805, "Davoser See",
water body ID CH0095340000, surface 1558 m a.s.l. per swissTLMRegio). It is
fetched once and stored in raw/swisstopo_CH-Dav/davoser_see_swisstlm3d.geojson.

Outputs:
- lake dimensions: area, perimeter, extent, length and width along the main axis
- position relative to the tower: centroid distance and bearing, nearest shore,
  angular range of the lake as seen from the tower
- share of lake surface per 30 deg wind sector and distance band, joined with
  the sector EBR from 07
processed/CH-Dav/09_lake_*.csv, figures/CH-Dav/09_lake_map.png
"""

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.path import Path as MplPath

from ebc_explorer.paths import CH_DAV_FIGURES, CH_DAV_PROCESSED, CH_DAV_SWISSTOPO
from ebc_explorer.swisstopo import fetch_feature

TOWER = np.array([2784453.0, 1187750.0])
LAKE_FILE = CH_DAV_SWISSTOPO / "davoser_see_swisstlm3d.geojson"
SECTOR_WIDTH = 30
BANDS = [(0, 500), (500, 1000), (1000, 2000), (2000, 3000)]


def load_lake():
    if not LAKE_FILE.is_file():
        feature = fetch_feature("ch.swisstopo.swisstlm3d-gewaessernetz", 1256805)
        LAKE_FILE.parent.mkdir(parents=True, exist_ok=True)
        LAKE_FILE.write_text(json.dumps(feature), encoding="utf-8")
    feature = json.loads(LAKE_FILE.read_text(encoding="utf-8"))
    polys = feature["geometry"]["coordinates"]  # MultiPolygon: [polygon][ring][point]
    return [np.array(ring)[:, :2] for poly in polys for ring in poly[:1]], feature


def ring_area(xy):
    x, y = xy[:, 0], xy[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def bearing(dx, dy):
    return (np.degrees(np.arctan2(dx, dy)) + 360) % 360


def main():
    rings, feature = load_lake()
    ring = max(rings, key=ring_area)  # outer shore of the main lake body
    area = sum(ring_area(r) for r in rings)
    perimeter = np.sum(np.hypot(*np.diff(ring, axis=0).T))
    centroid = ring.mean(axis=0)

    # main axis from principal components of the shoreline points
    pts = ring - centroid
    _, _, vt = np.linalg.svd(pts, full_matrices=False)
    along, across = pts @ vt[0], pts @ vt[1]
    axis_bearing = bearing(*vt[0]) % 180

    rel = ring - TOWER
    dist = np.hypot(rel[:, 0], rel[:, 1])
    brg = bearing(rel[:, 0], rel[:, 1])
    c = centroid - TOWER
    dims = pd.Series({
        "area_km2": area / 1e6,
        "perimeter_km": perimeter / 1e3,
        "length_km": (along.max() - along.min()) / 1e3,
        "max_width_km": (across.max() - across.min()) / 1e3,
        "main_axis_bearing_deg": axis_bearing,
        "E_min": ring[:, 0].min(), "E_max": ring[:, 0].max(), "N_min": ring[:, 1].min(), "N_max": ring[:, 1].max(),
        "centroid_E": centroid[0], "centroid_N": centroid[1],
        "centroid_distance_km": np.hypot(*c) / 1e3,
        "centroid_bearing_deg": bearing(*c),
        "nearest_shore_m": dist.min(),
        "nearest_shore_bearing_deg": brg[dist.argmin()],
        "farthest_shore_km": dist.max() / 1e3,
    })

    # share of lake surface per sector and distance band (5 m grid)
    step = 5.0
    gx, gy = np.meshgrid(np.arange(TOWER[0] - 3000, TOWER[0] + 3000, step) + step / 2,
                         np.arange(TOWER[1] - 3000, TOWER[1] + 3000, step) + step / 2)
    xy = np.column_stack([gx.ravel(), gy.ravel()])
    water = np.zeros(len(xy), bool)
    for r in rings:
        water |= MplPath(r).contains_points(xy)
    d = np.hypot(xy[:, 0] - TOWER[0], xy[:, 1] - TOWER[1])
    s = ((bearing(xy[:, 0] - TOWER[0], xy[:, 1] - TOWER[1]) + SECTOR_WIDTH / 2) // SECTOR_WIDTH
         % (360 // SECTOR_WIDTH) * SECTOR_WIDTH).astype(int)
    rows = []
    for sec in range(0, 360, SECTOR_WIDTH):
        row = {"sector_centre_deg": sec}
        for lo, hi in BANDS:
            m = (s == sec) & (d >= lo) & (d < hi)
            row[f"lake_pct_{lo}_{hi}"] = 100 * water[m].mean()
        rows.append(row)
    sectors = pd.DataFrame(rows).set_index("sector_centre_deg")
    ebr = pd.read_csv(CH_DAV_PROCESSED / "07_sector_diagnostics.csv", index_col=0)
    sectors = sectors.join(ebr[["share_pct", "ebr_all", "ebr_unstable"]])

    CH_DAV_PROCESSED.mkdir(parents=True, exist_ok=True)
    dims.to_frame("value").to_csv(CH_DAV_PROCESSED / "09_lake_dimensions.csv")
    sectors.to_csv(CH_DAV_PROCESSED / "09_lake_by_sector.csv")
    print(f"{feature['properties'].get('name')} ({feature['properties'].get('gwl_nr')}), {len(rings)} polygon(s)")
    print(dims.round(3).to_string())
    print()
    print(sectors.round(2).to_string())

    fig, ax = plt.subplots(figsize=(7, 7))
    for r in rings:
        ax.fill(r[:, 0], r[:, 1], color="#2a78d6", alpha=0.35, lw=0)
        ax.plot(r[:, 0], r[:, 1], color="#2a78d6", lw=1)
    for sec in np.arange(0, 360, SECTOR_WIDTH) - SECTOR_WIDTH / 2:
        a = np.radians(sec)
        ax.plot([TOWER[0], TOWER[0] + 3000 * np.sin(a)], [TOWER[1], TOWER[1] + 3000 * np.cos(a)], color="0.6", lw=0.6)
    th = np.linspace(0, 2 * np.pi, 200)
    for rr in (500, 1000, 2000):
        ax.plot(TOWER[0] + rr * np.sin(th), TOWER[1] + rr * np.cos(th), color="0.6", lw=0.6, ls=":")
    ax.plot(*TOWER, marker="^", color="#eb6834", ms=11, mec="k")
    ax.set_aspect("equal")
    ax.set_xlim(TOWER[0] - 2500, TOWER[0] + 2500)
    ax.set_ylim(TOWER[1] - 2000, TOWER[1] + 3000)
    ax.set_title(f"Davoser See (swissTLM3D, © swisstopo): {dims.area_km2:.2f} km², "
                 f"nearest shore {dims.nearest_shore_m:.0f} m from the tower")
    ax.set_xlabel("E (LV95, m)"); ax.set_ylabel("N (LV95, m)")
    fig.tight_layout()
    CH_DAV_FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(CH_DAV_FIGURES / "09_lake_map.png", dpi=150)


if __name__ == "__main__":
    main()
