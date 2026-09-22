"""Download swisstopo terrain and surface models around the CH-Dav tower.

1. Valley context: swissALTI3D 2 m (latest year), 8 x 8 km, E 2781-2788, N 1184-1191.
2. Footprint north of the tower: swissSURFACE3D Raster 0.5 m and swissALTI3D
   0.5 m (year 2019, closest to the 2020 surface model), 3 x 4 km,
   E 2783-2785, N 1186-1189.

Tower: 46.81533 N, 9.85591 E = LV95 E 2784453, N 1187750 (tile 2784-1187).
Files go to raw/swisstopo_CH-Dav/<product>/; a README records source and licence.
Re-running skips complete files.

    uv run python scripts/download_ch_dav_terrain.py
"""

from datetime import date

from ebc_explorer.paths import CH_DAV_SWISSTOPO
from ebc_explorer.swisstopo import ALTI3D, SURFACE3D, download, list_tiles, pick

BBOX_WGS84 = (9.78, 46.76, 9.93, 46.87)  # covers both areas with margin
CONTEXT = {"e": range(2781, 2789), "n": range(1184, 1192)}
FOOTPRINT = {"e": range(2783, 2786), "n": range(1186, 1190)}

README = """# swisstopo terrain and surface models around CH-Dav

Source: Federal Office of Topography swisstopo, https://data.geo.admin.ch (STAC API).
Licence: open government data, free use; credit the source as "© swisstopo".
Downloaded: {today} with ebc-explorer scripts/download_ch_dav_terrain.py.

Tower: 46.81533 N, 9.85591 E = LV95 (EPSG:2056) E 2784453, N 1187750, tile 2784-1187.
Tiles are 1 x 1 km GeoTIFFs named <product>_<year>_<E km>-<N km>_<resolution>_2056_5728.tif
(heights in m a.s.l., LN02 height system).

- alti3d_2m/: swissALTI3D, bare-ground terrain, 2 m, E 2781-2788, N 1184-1191 (valley context)
- alti3d_0.5m/: swissALTI3D, bare-ground terrain, 0.5 m, E 2783-2785, N 1186-1189
- surface3d_0.5m/: swissSURFACE3D Raster, surface incl. trees and buildings, 0.5 m, same tiles
  (canopy height = surface - terrain)
"""


def in_area(key, area):
    return key[0] in area["e"] and key[1] in area["n"]


def main():
    alti = list_tiles(ALTI3D, BBOX_WGS84)
    surf = list_tiles(SURFACE3D, BBOX_WGS84)
    jobs = []
    jobs += [("alti3d_2m", h) for k, h in pick(alti, 2.0).items() if in_area(k, CONTEXT)]
    jobs += [("alti3d_0.5m", h) for k, h in pick(alti, 0.5, year=2019).items() if in_area(k, FOOTPRINT)]
    jobs += [("surface3d_0.5m", h) for k, h in pick(surf, 0.5).items() if in_area(k, FOOTPRINT)]
    expected = len(CONTEXT["e"]) * len(CONTEXT["n"]) + 2 * len(FOOTPRINT["e"]) * len(FOOTPRINT["n"])
    print(f"{len(jobs)} tiles to fetch (expected {expected})")

    total = 0
    for i, (product, href) in enumerate(sorted(jobs), 1):
        path = download(href, CH_DAV_SWISSTOPO / product)
        total += path.stat().st_size
        print(f"[{i}/{len(jobs)}] {product}/{path.name}")
    (CH_DAV_SWISSTOPO / "README.md").write_text(README.format(today=date.today().isoformat()), encoding="utf-8")
    print(f"done: {total / 1e6:.0f} MB in {CH_DAV_SWISSTOPO}")


if __name__ == "__main__":
    main()
