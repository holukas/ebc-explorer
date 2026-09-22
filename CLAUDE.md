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

## Literature: `refs/EBC/`

Zotero export (`EBC.rdf`, `files/<id>/<Author - Year - Title>.pdf`, ~110 PDFs: the
references of Nicolini 2026 plus recent EBC papers). Find with
`ebc_explorer.refs.find_refs("Mauder", 2024)`; extract text with `pdf_text()` (pypdf,
run via `uv run --with pypdf`). File names may contain Unicode hyphens: use glob, not typed paths.

Main paper: Nicolini et al. 2026, GCB 32:e70892 (`files/21788/`). Key facts:
- AE1..AE6 = NETRAD, -G, -SG, -SH-SLE, -Spho, -Sbio; TE uncorrected / fullQC / u*-filtered; RMA slopes reported
- Sbio uses layer-weighted *air* temperature as biomass temperature (likely underestimates storage)
- imbalance grows with biomass: ~25 W m-2 + 0.18 * biomass (kg m-2); CH-Dav is far above this
- NETRAD corrections (slope, shadow, tower, FoV) change EBC by only a few % across sites
- Table 1: CH-Dav slope 16.2 deg WNW (steepest ICOS site), EC 35 m, canopy 19.2 m, biomass 62.5 kg m-2
- CH-Dav is not discussed individually

## ICOS L2 fluxes with footprint: `raw/ICOSETC_CH-Dav_ARCHIVE_L2_2025/`

`ICOSETC_CH-Dav_FLUXES_L2.csv` (2019-2024), extracted from the station's archive
`F:\Sync\luhk_work\sites\DAV\Data\Datasets\2025_ICOSETC_CH-Dav_ARCHIVE_L2.zip` (never modify
the original). Load with `ebc_explorer.fluxnet.load_ch_dav_fluxes_l2()`. Contains per half-hour
FETCH_OFFSET/MAX/50/70/80/90, FOOTPRINT_80_SURF, FOOTPRINT_TA_CONTR, FOOTPRINT_FLAG (0 = valid),
V_SIGMA, MO_LENGTH, ZL, WD. The FLUXNET product has no footprint variables.
Sensor-level soil and radiation data (5 heat flux plates G_<plot>_1_1 at 5-6 cm, TS/SWC profiles
per plot, SW_IN from 2 pyranometers) from the archive's METEOSENS file are extracted with
`scripts/extract_ch_dav_meteosens.py` to `interim/.../METEOSENS_soil_radiation.parquet`
(`paths.CH_DAV_METEOSENS_PARQUET`), 2020-2024. Analysis 13 (error budget): plot-to-plot range of
G + soil storage ~20 W m-2 at summer midday (~7 % of the gap); all AE-term errors together ≤ ~50 %.
Analysis 12: daytime 90 % fetch ~190-210 m; lake contributes ~3 % for N wind and has no effect on
closure within the N sector; at equal u*, closure is poorest near neutral (FETCH ranks with z/L).

## How H and LE are computed (CH-Dav)

ICOS ETC processing (Sabbatini et al. 2018, EddyPro on 20 Hz raw data): 30 min block average, no
detrending; time lag by covariance maximisation (RH-dependent for H2O); H with Schotanus/van Dijk
humidity correction of sonic temperature; LE from LI-7200 dry mole fraction (no WPL needed); spectral
corrections: block-average low-frequency transfer function, analytic high-frequency for H (Moncrieff
1997), in-situ RH-dependent for H2O (Ibrom 2007, Fratini 2012); QC by Foken & Wichura steady-state/ITC,
Mauder & Foken flags and Vitale 2020 cleaning. No angle-of-attack correction; no wind sector excluded
(ECSYS_WIND_EXCL empty).
- **Rotation: CH-Dav uses double rotation, NOT planar fit (yet)**, although sector-wise planar fit is
  the ICOS default. On the 16 deg slope this is a candidate cause of the N/S closure contrast
  (half-hourly pitch angle, cross-contamination at low wind, high-pass filtering with 30 min averaging,
  Finnigan et al. 2003). Cannot be tested with FLUXNET/L2 data; needs raw 20 Hz data.
- Our analyses use FLUXNET `H_F_MDS`/`LE_F_MDS` with `QC == 0` (measured, cleaned, no closure
  correction); `H_CORR`/`LE_CORR` are not used.
- L2 `FLUXES` diagnostics (daytime 2019-2024): spectral correction factors are small, median
  `H_SCF_STAT` ~1.01 in all sectors, `LE_SCF_STAT` 1.10 in N (p90 1.41) vs 1.06 in S (p90 1.18), so
  high-frequency loss does not explain the gap. QC removes 55-84 % of daytime half-hours per sector
  (N 55 %, S 61 %). Closure with `*_UNCLEANED` fluxes is dominated by outliers and not meaningful.

Possible next steps (not done yet):
- With raw 20 Hz data (one summer, N- and S-dominated periods): reprocess with EddyPro, double
  rotation vs sector-wise planar fit (12-16 sectors) and 30 vs 60/120/240 min averaging; ogives of
  w'T' and w'q' by sector; pitch angle vs wind direction; angle-of-attack correction (Nakai & Shimoyama
  2012) as sensitivity test.
- With existing data (candidate analysis 14): does the residual scale with H/buoyancy flux or Bowen
  ratio (Charuchittipan 2014, Mauder 2020); which conditions QC removes (by sector, u*, z/L);
  flow distortion indicators (sigma_w/u*, sigma_v/u*) by sector vs flat-terrain similarity;
  independent LE check (sap flow, soil water depletion).

## Terrain data: `raw/swisstopo_CH-Dav/`

swisstopo tiles (1 × 1 km, LV95/EPSG:2056, credit "© swisstopo"), fetched with
`uv run python scripts/download_ch_dav_terrain.py` (resumable, `ebc_explorer.swisstopo`):
`alti3d_2m/` terrain 8 × 8 km, `alti3d_0.5m/` terrain and `surface3d_0.5m/` surface 3 × 4 km.
Canopy height = surface − terrain. Tower: LV95 E 2784453, N 1187750, ground 1637.7 m.
The tower stands at the foot of the forested WNW slope, ~80 m above the open valley floor
to the N/NW/W; forest ends ~250–300 m north of the tower.
Davoser See (swissTLM3D outline in `raw/swisstopo_CH-Dav/davoser_see_swisstlm3d.geojson`,
analysis 09): 0.58 km², 1.43 × 0.61 km, long axis 36° (along the valley), surface 1558 m,
nearest shore 222 m NW of the tower, centroid 565 m at 331°. Lake covers 49 % of the
N sector within 500 m and 94 % at 500–1000 m.

## Code layout

- `ebc_explorer/`: reusable code (`paths`, `fluxnet`, `nicolini`, `ebc` closure stats, `ch_dav` site info)
- `analyses/ch_dav_NN_*.py`: numbered analysis scripts; each writes to
  `processed/CH-Dav/NN_*.csv` and `figures/CH-Dav/NN_*.png`. Run with `uv run python analyses/<script>.py`.
- `reports/build_ch_dav_overview.py` + `reports/templates/ch_dav_overview.html` -> `reports/ch_dav_overview.html`
  (interactive overview page; data and map images embedded). Needs analyses 01-10, 12 and 13 (08-10: terrain,
  lake and map images from the swisstopo data). Rebuild after re-running the analyses.
  Preview: `.claude/launch.json` entry "reports" serves `reports/` on http://localhost:8765.
- `reports/build_ch_dav_3d.py` + `reports/templates/ch_dav_3d.html` -> `reports/ch_dav_3d.html`
  (3D landscape, three.js from jsdelivr; needs analyses 07, 09, 11, 12). Published copy:
  https://claude.ai/artifact/FjLpmhyvvmphCKn1ngo5Cp (linked from the overview's published copy).
  Never put personal data in reports: no person names from the fieldbook, no IP addresses.
  Exception: the report author (`AUTHOR` in the build script) is shown in the footer.

## Environment

- Windows. Python 3.12 managed with **uv** (`.python-version`, `pyproject.toml`, `uv.lock`); venv in `.venv/` (git-ignored).
- Run code with `uv run python ...`; add packages with `uv add <pkg>` (never pip, never the system Python 3.9).
- `ebc_explorer` is installed editable in the venv, so `import ebc_explorer` works from anywhere (scripts, notebooks).
