"""CH-Dav: base map images for the overview report.

Renders two plain raster images without axes; the report draws the tower,
wind sectors, distance rings and the lake outline on top as vector graphics.

1. valley: shaded relief of the terrain (swissALTI3D 2 m), 6 x 6 km around the tower
2. canopy: canopy height (swissSURFACE3D 2020 minus swissALTI3D 2019, 1 m) over
   shaded relief, 3 x 4 km (E 2783-2786, N 1186-1190)

Outputs: processed/CH-Dav/10_map_valley.jpg, 10_map_canopy.jpg and
10_maps.json with the LV95 extent [left, right, bottom, top] of each image.
Map data © swisstopo.
"""

import json

import matplotlib.image
import numpy as np
from matplotlib import colors

from ebc_explorer.paths import CH_DAV_PROCESSED, CH_DAV_SWISSTOPO
from ebc_explorer.terrain import extent, hillshade, mosaic

VALLEY_BOUNDS = (2781500, 1185000, 2787500, 1191000)  # left, bottom, right, top (LV95)
CANOPY_BOUNDS = (2783000, 1186000, 2786000, 1190000)
MAX_PX = 1100  # longest image side
CHM_MAX = 35.0


def save_rgb(rgb, name):
    """Downsample by block averaging to at most MAX_PX and save as JPEG."""
    k = max(1, int(np.ceil(max(rgb.shape[:2]) / MAX_PX)))
    h, w = (rgb.shape[0] // k) * k, (rgb.shape[1] // k) * k
    small = rgb[:h, :w].reshape(h // k, k, w // k, k, 3).mean(axis=(1, 3))
    matplotlib.image.imsave(CH_DAV_PROCESSED / name, np.clip(small, 0, 1), format="jpg", pil_kwargs={"quality": 84})
    return small.shape[:2]


def main():
    CH_DAV_PROCESSED.mkdir(parents=True, exist_ok=True)
    meta = {}

    dtm2, t2 = mosaic(CH_DAV_SWISSTOPO / "alti3d_2m", 2.0, bounds=VALLEY_BOUNDS)
    hs = np.nan_to_num(hillshade(dtm2, 2.0), nan=1.0)
    shade = 0.35 + 0.65 * np.clip(hs, 0, 1)
    base = np.array(colors.to_rgb("#e9ecea"))
    rgb = shade[..., None] * base
    shape = save_rgb(rgb, "10_map_valley.jpg")
    meta["valley"] = {"file": "10_map_valley.jpg", "extent": extent(dtm2, t2), "px": list(shape)}

    dsm, t1 = mosaic(CH_DAV_SWISSTOPO / "surface3d_0.5m", 1.0, bounds=CANOPY_BOUNDS)
    dtm, _ = mosaic(CH_DAV_SWISSTOPO / "alti3d_0.5m", 1.0, bounds=CANOPY_BOUNDS)
    chm = np.clip(np.nan_to_num(dsm - dtm, nan=0.0), 0, CHM_MAX)
    hs = np.clip(np.nan_to_num(hillshade(dtm, 1.0), nan=1.0), 0, 1)
    # one-hue sequential ramp: open ground light, tall forest dark green
    ramp = colors.LinearSegmentedColormap.from_list("chm", ["#eef1ec", "#b9d9a6", "#5fa65a", "#1f6b3a", "#0e3d22"])
    rgb = ramp(chm / CHM_MAX)[..., :3] * (0.55 + 0.45 * hs)[..., None]
    shape = save_rgb(rgb, "10_map_canopy.jpg")
    meta["canopy"] = {"file": "10_map_canopy.jpg", "extent": extent(dtm, t1), "px": list(shape),
                      "chm_max": CHM_MAX, "ramp": ["#eef1ec", "#b9d9a6", "#5fa65a", "#1f6b3a", "#0e3d22"]}

    (CH_DAV_PROCESSED / "10_maps.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    for k, v in meta.items():
        size = (CH_DAV_PROCESSED / v["file"]).stat().st_size / 1e3
        print(f"{k}: {v['px']} px, extent {v['extent']}, {size:.0f} kB")


if __name__ == "__main__":
    main()
