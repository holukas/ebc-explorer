# ebc-explorer

Exploring energy balance closure (EBC) of eddy-covariance sites from the ICOS and NEON networks.

## Data location

Data is NOT in this repo. It lives in a separate synced folder:

    F:\Sync\luhk_work\dev-data\ebc-explorer-data

- Set in `.env` (git-ignored) as `EBC_DATA_DIR`; template in `.env.example`.
- In code, never hard-code paths. Use `ebc_explorer/paths.py`:
  `from ebc_explorer.paths import EBC_RESULTS, INTERIM, REFS`
- Layout and conventions are in `<data dir>/README.md`. Summary:
  - `raw/` — as downloaded, **read-only, never modify**
  - `interim/` — regenerable caches (e.g. Parquet), safe to delete
  - `processed/` — result tables written by this code
  - `figures/` — plots written by this code
  - `refs/` — reference PDFs, named `FirstAuthor_Year_ShortTitle.pdf`

## Main dataset: `raw/EBC_data_ICOS_NEON_2026/`

Nicolini & Papale (2026), Zenodo https://doi.org/10.5281/zenodo.19608436, CC BY 4.0.
84 sites (38 ICOS, 46 NEON). Full description: `raw/EBC_data_ICOS_NEON_2026/EBC_data_README.md`.

| paths.py name | File | Notes |
|---|---|---|
| `EBC_RESULTS` | `processed/EBC_results.csv` | EBC metrics, non-gap-filled, ~73k rows × 22 cols |
| `EBC_RESULTS_GAPFILLED` | `processed/EBC_results_gapfilled.csv` | gap-filled, ~84k rows × 28 cols, adds `EBC_ratio` etc. |
| `SBIO_SPHO_NRCORR` | `intermediate/Sbio_Spho_NRcorr.csv` | **848 MB**, 7.9M half-hourly rows; read in chunks or cache as Parquet in `interim/` |
| `STATIONS_ANCILLARY` | `ancillary/EBC_stations_MD_ANCILLARY.txt` | tab-separated, site metadata |
| `ICOS_RADIOMETER_SETUP` | `ancillary/ICOS_stations_radiometer_setup.txt` | tab-separated, Italian column names |
| `ICOS_RAD_VS_FFP_FOV` | `ancillary/ICOS_stations_RADvsFFP_fov.csv` | month-level, `P` = month |

Results tables: one row per site × `t_scale` × `fattore`/`livello` × `AE_var`/`TE_var` combination.

Gotchas:
- Italian labels. `t_scale`: `semioraria` half-hourly, `giornaliera` daily, `settimanale` weekly,
  `mensile` monthly, `stagionale` seasonal, `annuale` annual. `fattore` = factor, `livello` = level.
  Radiometer file: `h_radiometro` radiometer height, `w_traliccio` tower width, `d_braccio` boom length.
- Missing values are the string `NA`; in `fattore`/`livello` NA means "no stratification".

## CH-Dav FLUXNET data: `raw/ICOS_CH-Dav_FLUXNET_1997-2024_v1.3_r1/`

ICOS FLUXNET (ONEFlux) product, 1997-2024. Half-hourly file ~770 MB; load with
`ebc_explorer.fluxnet.load_ch_dav_hh()` (cached as Parquet in `interim/`).
- Missing = -9999, local standard time, `*_QC == 0` = measured (not gap-filled).
- No storage terms (SH, SLE), no snow depth. Sbio/Spho for CH-Dav exist only for
  2019-2024 in the Nicolini file: `ebc_explorer.nicolini.load_sbio_spho("CH-Dav")`.
- Nicolini et al. (2026) used CH-Dav 2019-2024 only.
- Instrument periods (sonic + gas analyser) from BIFVARINFO: `ebc_explorer.ch_dav.INSTRUMENT_PERIODS`.
  The metadata labels the LI-7500 as GA_CP; it is open path.

## Code layout

- `ebc_explorer/`: reusable code (`paths`, `fluxnet`, `nicolini`, `ebc` closure stats, `ch_dav` site info)
- `analyses/ch_dav_NN_*.py`: numbered analysis scripts; each writes to
  `processed/CH-Dav/NN_*.csv` and `figures/CH-Dav/NN_*.png`. Run with `uv run python analyses/<script>.py`.

## Environment

- Windows. Python 3.12 managed with **uv** (`.python-version`, `pyproject.toml`, `uv.lock`); venv in `.venv/` (git-ignored).
- Run code with `uv run python ...`; add packages with `uv add <pkg>` (never pip, never the system Python 3.9).
- `ebc_explorer` is installed editable in the venv, so `import ebc_explorer` works from anywhere (scripts, notebooks).
