"""Locations of the project data.

Data lives outside the repo. The data root is taken from, in this order:

1. the environment variable ``EBC_DATA_DIR``
2. the line ``EBC_DATA_DIR=...`` in ``.env`` at the repo root (git-ignored)

Usage::

    from ebc_explorer.paths import EBC_RESULTS, INTERIM
"""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_VAR = "EBC_DATA_DIR"


def _read_dotenv(path):
    """Return the key/value pairs of a simple KEY=VALUE .env file."""
    values = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _data_root():
    root = os.environ.get(ENV_VAR) or _read_dotenv(REPO_ROOT / ".env").get(ENV_VAR)
    if not root:
        raise RuntimeError(
            f"Data folder not set. Set the environment variable {ENV_VAR} or add "
            f"'{ENV_VAR}=<path>' to {REPO_ROOT / '.env'} (see .env.example)."
        )
    root = Path(root).expanduser()
    if not root.is_dir():
        raise RuntimeError(f"{ENV_VAR} points to a folder that does not exist: {root}")
    return root


DATA_DIR = _data_root()

# Top-level folders, see DATA_DIR / "README.md"
RAW = DATA_DIR / "raw"  # as downloaded, read-only
INTERIM = DATA_DIR / "interim"  # regenerable caches
PROCESSED = DATA_DIR / "processed"  # analysis outputs
FIGURES = DATA_DIR / "figures"
REFS = DATA_DIR / "refs"  # reference PDFs

# Nicolini & Papale (2026), https://doi.org/10.5281/zenodo.19608436
EBC_2026 = RAW / "EBC_data_ICOS_NEON_2026" / "EBC_data"
EBC_RESULTS = EBC_2026 / "processed" / "EBC_results.csv"
EBC_RESULTS_GAPFILLED = EBC_2026 / "processed" / "EBC_results_gapfilled.csv"
SBIO_SPHO_NRCORR = EBC_2026 / "intermediate" / "Sbio_Spho_NRcorr.csv"
STATIONS_ANCILLARY = EBC_2026 / "ancillary" / "EBC_stations_MD_ANCILLARY.txt"
ICOS_RADIOMETER_SETUP = EBC_2026 / "ancillary" / "ICOS_stations_radiometer_setup.txt"
ICOS_RAD_VS_FFP_FOV = EBC_2026 / "ancillary" / "ICOS_stations_RADvsFFP_fov.csv"

# ICOS FLUXNET (ONEFlux) product for CH-Dav, 1997-2024, release v1.3_r1
CH_DAV_FLUXNET = RAW / "ICOS_CH-Dav_FLUXNET_1997-2024_v1.3_r1"
CH_DAV_FLUXMET_HH = CH_DAV_FLUXNET / "ICOS_CH-Dav_FLUXNET_FLUXMET_HH_1997-2024_v1.3_r1.csv"
CH_DAV_FLUXMET_HH_PARQUET = INTERIM / CH_DAV_FLUXNET.name / "FLUXMET_HH.parquet"
CH_DAV_PROCESSED = PROCESSED / "CH-Dav"
CH_DAV_FIGURES = FIGURES / "CH-Dav"
