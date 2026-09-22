"""Extract soil and radiation sensor data for CH-Dav from the ICOS ETC L2 archive.

The archive's METEOSENS file (~560 MB) has one column per sensor. This script
reads only the soil heat flux plates (G_*), soil temperature (TS_*), soil
water content (SWC_*) and radiation (NETRAD_*, SW_*, LW_*, PPFD_*) columns
directly from the zip and stores them as Parquet in interim/. It also copies
the sensor metadata (VARINFO_METEOSENS) to raw/ICOSETC_CH-Dav_ARCHIVE_L2_2025/.
The original archive is only read.

    uv run python scripts/extract_ch_dav_meteosens.py [ARCHIVE_ZIP]
"""

import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

from ebc_explorer.paths import CH_DAV_ICOS_L2, CH_DAV_METEOSENS_PARQUET

ARCHIVE = Path(r"F:/Sync/luhk_work/sites/DAV/Data/Datasets/2025_ICOSETC_CH-Dav_ARCHIVE_L2.zip")
BASE = "2025_ICOSETC_CH-Dav_ARCHIVE_L2/"
KEEP = re.compile(r"^(TIMESTAMP_START|TIMESTAMP_END|(G|TS|SWC|NETRAD|SW_IN|SW_OUT|LW_IN|LW_OUT|PPFD_IN)_\d+_\d+_\d+(_SE|_N)?)$")


def main():
    archive = Path(sys.argv[1]) if len(sys.argv) > 1 else ARCHIVE
    with zipfile.ZipFile(archive) as z:
        (CH_DAV_ICOS_L2 / "ICOSETC_CH-Dav_VARINFO_METEOSENS_L2.csv").write_bytes(
            z.read(BASE + "ICOSETC_CH-Dav_VARINFO_METEOSENS_L2.csv"))
        with z.open(BASE + "ICOSETC_CH-Dav_METEOSENS_L2.csv") as f:
            header = f.readline().decode().strip().split(",")
        cols = [c for c in header if KEEP.match(c)]
        with z.open(BASE + "ICOSETC_CH-Dav_METEOSENS_L2.csv") as f:
            df = pd.read_csv(f, usecols=cols, na_values=[-9999], low_memory=False)
    for c in ("TIMESTAMP_START", "TIMESTAMP_END"):
        df[c] = pd.to_datetime(df[c].astype("int64").astype(str), format="%Y%m%d%H%M")
    df = df.set_index("TIMESTAMP_START")
    CH_DAV_METEOSENS_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(CH_DAV_METEOSENS_PARQUET)
    print(f"{len(cols)} columns, {len(df)} rows, {df.index.min()} to {df.index.max()} -> {CH_DAV_METEOSENS_PARQUET}")


if __name__ == "__main__":
    main()
