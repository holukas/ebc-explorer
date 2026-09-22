"""swisstopo open data (terrain and surface models) via the STAC API.

Data: https://data.geo.admin.ch, open government data, free use with the
source credited as "© swisstopo". Tiles are 1 x 1 km in LV95 (EPSG:2056),
named by the lower-left corner in km, e.g. 2784-1187.
"""

import json
import re
import urllib.request
from pathlib import Path

STAC = "https://data.geo.admin.ch/api/stac/v0.9/collections/{collection}/items"
ALTI3D = "ch.swisstopo.swissalti3d"  # bare-ground terrain model (DTM)
SURFACE3D = "ch.swisstopo.swisssurface3d-raster"  # surface model incl. vegetation and buildings (DSM)


def wgs84_to_lv95(lat, lon):
    """swisstopo approximate formula (accuracy ~1 m)."""
    phi = (lat * 3600 - 169028.66) / 10000
    lam = (lon * 3600 - 26782.5) / 10000
    e = (2600072.37 + 211455.93 * lam - 10938.51 * lam * phi - 0.36 * lam * phi ** 2
         - 44.54 * lam ** 3)
    n = (1200147.07 + 308807.95 * phi + 3745.25 * lam ** 2 + 76.63 * phi ** 2
         - 194.56 * lam ** 2 * phi + 119.79 * phi ** 3)
    return e, n


def list_tiles(collection, bbox_wgs84):
    """All GeoTIFF assets in a WGS84 bbox (lon_min, lat_min, lon_max, lat_max).

    Returns {(E_km, N_km): {year: {gsd: href}}}.
    """
    url = STAC.format(collection=collection) + "?bbox=" + ",".join(map(str, bbox_wgs84)) + "&limit=100"
    tiles = {}
    while url:
        with urllib.request.urlopen(url, timeout=60) as r:
            page = json.load(r)
        for item in page["features"]:
            m = re.search(r"_(\d{4})_(\d{4})-(\d{4})$", item["id"])
            if not m:
                continue
            year, e, n = int(m.group(1)), int(m.group(2)), int(m.group(3))
            for name, asset in item["assets"].items():
                if name.endswith(".tif"):
                    tiles.setdefault((e, n), {}).setdefault(year, {})[float(asset["eo:gsd"])] = asset["href"]
        url = next((link["href"] for link in page.get("links", []) if link.get("rel") == "next"), None)
    return tiles


def pick(tiles, gsd, year=None):
    """{(E, N): href} for one resolution: the given year if available, else the latest."""
    out = {}
    for key, years in tiles.items():
        candidates = [y for y in years if gsd in years[y]]
        if not candidates:
            continue
        y = year if year in candidates else max(candidates)
        out[key] = years[y][gsd]
    return out


def fetch_feature(layer, feature_id):
    """One vector feature from the geo.admin.ch API as GeoJSON (LV95 coordinates)."""
    url = (f"https://api3.geo.admin.ch/rest/services/api/MapServer/{layer}/{feature_id}"
           "?geometryFormat=geojson&sr=2056&returnGeometry=true")
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)["feature"]


def download(href, folder):
    """Download href into folder unless a complete copy exists. Returns the local path."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / href.rsplit("/", 1)[1]
    with urllib.request.urlopen(urllib.request.Request(href, method="HEAD"), timeout=60) as r:
        size = int(r.headers["Content-Length"])
    if dest.is_file() and dest.stat().st_size == size:
        return dest
    tmp = dest.with_suffix(dest.suffix + ".part")
    urllib.request.urlretrieve(href, tmp)
    if tmp.stat().st_size != size:
        raise IOError(f"incomplete download: {href}")
    tmp.replace(dest)
    return dest
