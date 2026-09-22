"""Nicolini & Papale (2026) EBC dataset (Zenodo 10.5281/zenodo.19608436)."""

import pandas as pd

from ebc_explorer.paths import INTERIM, SBIO_SPHO_NRCORR

SBIO_CACHE_DIR = INTERIM / "EBC_data_ICOS_NEON_2026" / "Sbio_Spho_NRcorr"


def load_sbio_spho(site, rebuild=False):
    """Half-hourly Sbio, Spho and net radiation corrections for one site.

    The source CSV is ~850 MB for all sites, so it is read in chunks once per
    site and cached as Parquet in interim/. Indexed by TIMESTAMP_START.
    """
    cache = SBIO_CACHE_DIR / f"{site}.parquet"
    if cache.is_file() and not rebuild:
        return pd.read_parquet(cache)
    parts = [chunk[chunk["site"] == site]
             for chunk in pd.read_csv(SBIO_SPHO_NRCORR, chunksize=1_000_000)]
    df = pd.concat(parts).drop(columns="site")
    df["TIMESTAMP_START"] = pd.to_datetime(df["TIMESTAMP_START"].astype("int64").astype(str),
                                           format="%Y%m%d%H%M")
    df = df.set_index("TIMESTAMP_START").sort_index()
    cache.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache)
    return df
