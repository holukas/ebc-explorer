"""Raster helpers for the swisstopo terrain and surface tiles (LV95)."""

from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.merge import merge


def mosaic(folder, res, bounds=None):
    """Merge all GeoTIFF tiles in folder at resolution res (m). Returns (array, transform); nodata -> NaN."""
    files = sorted(Path(folder).glob("*.tif"))
    srcs = [rasterio.open(f) for f in files]
    arr, transform = merge(srcs, bounds=bounds, res=res, resampling=Resampling.average, nodata=-9999)
    for s in srcs:
        s.close()
    a = arr[0].astype("float64")
    a[a == -9999] = np.nan
    return a, transform


def extent(a, transform):
    """[left, right, bottom, top] of an array for imshow."""
    return [transform.c, transform.c + a.shape[1] * transform.a, transform.f + a.shape[0] * transform.e, transform.f]


def grid_coords(shape, transform):
    rows, cols = np.indices(shape)
    return transform.c + (cols + 0.5) * transform.a, transform.f + (rows + 0.5) * transform.e


def sample(a, transform, x, y):
    col = ((np.asarray(x) - transform.c) / transform.a).astype(int)
    row = ((np.asarray(y) - transform.f) / transform.e).astype(int)
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
