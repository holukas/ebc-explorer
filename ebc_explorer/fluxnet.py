"""Read FLUXNET (ONEFlux) format files.

Format notes (see README.txt of the product):
- missing values are -9999
- timestamps are local standard time (no DST), YYYYMMDDHHMM
- *_QC flags for gap-filled variables: 0 = measured, 1-3 = gap-filled (increasing uncertainty)
"""

import pandas as pd

from ebc_explorer.paths import CH_DAV_FLUXMET_HH, CH_DAV_FLUXMET_HH_PARQUET


def read_fluxnet_csv(path):
    """Read a FLUXNET CSV into a DataFrame indexed by TIMESTAMP_START."""
    df = pd.read_csv(path, na_values=[-9999], low_memory=False)
    for col in ("TIMESTAMP_START", "TIMESTAMP_END"):
        df[col] = pd.to_datetime(df[col].astype("int64").astype(str), format="%Y%m%d%H%M")
    return df.set_index("TIMESTAMP_START")


def load_ch_dav_hh(rebuild=False):
    """Half-hourly CH-Dav FLUXMET data, cached as Parquet in interim/."""
    if rebuild or not CH_DAV_FLUXMET_HH_PARQUET.is_file():
        df = read_fluxnet_csv(CH_DAV_FLUXMET_HH)
        CH_DAV_FLUXMET_HH_PARQUET.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(CH_DAV_FLUXMET_HH_PARQUET)
        return df
    return pd.read_parquet(CH_DAV_FLUXMET_HH_PARQUET)
