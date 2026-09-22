"""CH-Dav: assets for the interactive 3D landscape page.

Inputs: swisstopo tiles in raw/swisstopo_CH-Dav/ (scripts/download_ch_dav_terrain.py).
Area: 8 x 8 km, LV95 E 2781000-2789000, N 1184000-1192000.

Outputs in processed/CH-Dav/:
- 11_3d_height.bin: terrain heights on a 10 m grid (800 x 800), uint16,
  decimetres above the minimum, row 0 = north
- 11_3d_photo.jpg: SWISSIMAGE aerial photo (2025), 2560 px
- 11_3d_canopy.jpg: shaded relief with canopy height (surface - terrain) where
  the 0.5 m surface model exists (3 x 4 km), 2560 px
- 11_3d_meta.json: extent, grid size, height offset and scale
Map data © swisstopo.
"""

import json

import numpy as np
import rasterio
from matplotlib import colors
from PIL import Image
from rasterio.merge import merge

from ebc_explorer.paths import CH_DAV_PROCESSED, CH_DAV_SWISSTOPO
from ebc_explorer.terrain import hillshade, mosaic

BOUNDS = (2781000, 1184000, 2789000, 1192000)  # left, bottom, right, top
CANOPY_BOUNDS = (2783000, 1186000, 2786000, 1190000)
GRID = 10.0  # m, mesh spacing
TEX_PX = 2560
CHM_MAX = 35.0
RAMP = ["#eef1ec", "#b9d9a6", "#5fa65a", "#1f6b3a", "#0e3d22"]


def to_jpeg(rgb, name):
    img = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype("uint8"))
    img = img.resize((TEX_PX, TEX_PX), Image.LANCZOS)
    img.save(CH_DAV_PROCESSED / name, quality=82, optimize=True)


def main():
    CH_DAV_PROCESSED.mkdir(parents=True, exist_ok=True)

    # terrain heights on the mesh grid
    dtm, _ = mosaic(CH_DAV_SWISSTOPO / "alti3d_2m", GRID, bounds=BOUNDS)
    dtm = np.where(np.isfinite(dtm), dtm, np.nanmin(dtm))
    hmin = float(np.floor(np.nanmin(dtm)))
    heights = np.round((dtm - hmin) * 10).astype("<u2")
    (CH_DAV_PROCESSED / "11_3d_height.bin").write_bytes(heights.tobytes())

    # aerial photo
    files = sorted((CH_DAV_SWISSTOPO / "swissimage_2m").glob("*.tif"))
    srcs = [rasterio.open(f) for f in files]
    photo, _ = merge(srcs, bounds=BOUNDS, res=2.0)
    for s in srcs:
        s.close()
    to_jpeg(np.moveaxis(photo[:3], 0, -1) / 255.0, "11_3d_photo.jpg")

    # shaded relief everywhere, canopy height colours inside the canopy area
    dtm2, t2 = mosaic(CH_DAV_SWISSTOPO / "alti3d_2m", 2.0, bounds=BOUNDS)
    hs = np.clip(np.nan_to_num(hillshade(dtm2, 2.0), nan=1.0), 0, 1)
    shade = 0.45 + 0.55 * hs
    rgb = shade[..., None] * np.array(colors.to_rgb("#e9ecea"))
    dsm, _ = mosaic(CH_DAV_SWISSTOPO / "surface3d_0.5m", 2.0, bounds=CANOPY_BOUNDS)
    dtm_c, _ = mosaic(CH_DAV_SWISSTOPO / "alti3d_0.5m", 2.0, bounds=CANOPY_BOUNDS)
    chm = np.clip(np.nan_to_num(dsm - dtm_c, nan=0.0), 0, CHM_MAX)
    ramp = colors.LinearSegmentedColormap.from_list("chm", RAMP)
    r0 = int((BOUNDS[3] - CANOPY_BOUNDS[3]) / 2.0)
    c0 = int((CANOPY_BOUNDS[0] - BOUNDS[0]) / 2.0)
    h, w = chm.shape
    rgb[r0:r0 + h, c0:c0 + w] = ramp(chm / CHM_MAX)[..., :3] * shade[r0:r0 + h, c0:c0 + w, None]
    to_jpeg(rgb, "11_3d_canopy.jpg")

    meta = {
        "extent": [BOUNDS[0], BOUNDS[2], BOUNDS[1], BOUNDS[3]],
        "canopy_extent": [CANOPY_BOUNDS[0], CANOPY_BOUNDS[2], CANOPY_BOUNDS[1], CANOPY_BOUNDS[3]],
        "grid": GRID, "nx": int(heights.shape[1]), "ny": int(heights.shape[0]),
        "hmin": hmin, "hscale": 0.1, "chm_max": CHM_MAX, "ramp": RAMP,
    }
    (CH_DAV_PROCESSED / "11_3d_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    for name in ("11_3d_height.bin", "11_3d_photo.jpg", "11_3d_canopy.jpg"):
        print(f"{name}: {(CH_DAV_PROCESSED / name).stat().st_size / 1e3:.0f} kB")
    print(meta)


if __name__ == "__main__":
    main()
