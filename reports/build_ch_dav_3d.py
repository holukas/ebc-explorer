"""Build the interactive 3D landscape page for CH-Dav.

Inputs (run first): analyses/ch_dav_07 (sector EBR), ch_dav_09 (lake),
ch_dav_11 (terrain heights and textures), ch_dav_12 (ICOS footprint per sector).

    uv run python reports/build_ch_dav_3d.py [--fragment PATH]

Output: reports/ch_dav_3d.html (self-contained; three.js from jsdelivr, fonts
from Google Fonts). Map data © swisstopo.
"""

import argparse
import base64
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from build_ch_dav_overview import AUTHOR, STANDALONE_HEAD, clean, records
from ebc_explorer.ch_dav import TOWER_LV95
from ebc_explorer.paths import CH_DAV_PROCESSED, CH_DAV_SWISSTOPO

HERE = Path(__file__).parent
TEMPLATE = HERE / "templates" / "ch_dav_3d.html"
OUTPUT = HERE / "ch_dav_3d.html"


def b64(path):
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def payload():
    p = CH_DAV_PROCESSED
    meta = json.loads((p / "11_3d_meta.json").read_text(encoding="utf-8"))
    lake = json.loads((CH_DAV_SWISSTOPO / "davoser_see_swisstlm3d.geojson").read_text(encoding="utf-8"))
    ring = np.array(max((poly[0] for poly in lake["geometry"]["coordinates"]), key=len))[:, :2]
    ring = ring[:: max(1, len(ring) // 500)]
    dims = pd.read_csv(p / "09_lake_dimensions.csv", index_col=0)["value"]
    fp = pd.read_csv(p / "12_footprint_by_sector.csv")
    sectors = pd.read_csv(p / "07_sector_diagnostics.csv")[["sector_centre_deg", "share_pct", "ebr_all"]]
    today = date.today()
    return {
        "generated": f"{today.day} {today:%B %Y}",
        "author": AUTHOR,
        "tower": list(TOWER_LV95),
        "terrain3d": {
            **{k: meta[k] for k in ("extent", "grid", "nx", "ny", "hmin", "hscale", "chm_max", "ramp")},
            "heights": b64(p / "11_3d_height.bin"),
            "textures": {"photo": "data:image/jpeg;base64," + b64(p / "11_3d_photo.jpg"),
                         "canopy": "data:image/jpeg;base64," + b64(p / "11_3d_canopy.jpg")},
        },
        "lake": {"outline": [[round(float(e), 1), round(float(n), 1)] for e, n in ring], "level": 1558.0,
                 "centroid": [clean(dims["centroid_E"]), clean(dims["centroid_N"])]},
        "footprint": records(fp),
        "sectors": records(sectors),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fragment", type=Path, help="also write the page without html/head wrapper")
    args = parser.parse_args(argv)
    text = json.dumps(payload(), ensure_ascii=False, separators=(",", ":"))
    body = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", text)
    OUTPUT.write_text(STANDALONE_HEAD + body + "\n</body>\n</html>\n", encoding="utf-8")
    print(f"wrote {OUTPUT} ({OUTPUT.stat().st_size / 1e6:.1f} MB)")
    if args.fragment:
        args.fragment.write_text(body, encoding="utf-8")
        print(f"wrote {args.fragment}")


if __name__ == "__main__":
    main()
