# ebc-explorer

Exploring the energy balance closure (EBC) of eddy covariance flux sites in the ICOS and
NEON networks, with a detailed case study of the ICOS forest station **CH-Dav** (Davos
Seehornwald, Switzerland).

At most flux sites the measured turbulent heat fluxes (sensible heat H and latent heat LE)
add up to 70 to 90 % of the available energy (net radiation minus heat stored in soil, air
and biomass). At CH-Dav they add up to only about half. This repository contains the code to
compare CH-Dav with the network and to test possible causes.

## Findings for CH-Dav so far

- Closure is the 3rd lowest of 80 ICOS and NEON sites in the dataset of Nicolini et al.
  (2026): RMA slope 0.62 against a network median of 0.86, with all storage terms included.
- The closure slope has been 0.38 to 0.58 in every year since 1998, with every sonic
  anemometer and gas analyser used at the site.
- The missing energy is about half of the available energy at every hour of the day.
  Biomass heat storage and photosynthesis explain only a small part (slope 0.50 to 0.54),
  and the radiation measurements are consistent.
- Closure depends on wind direction: at the same friction velocity, northerly wind closes at
  about 0.5, southerly and westerly wind at 0.75 to 1.0. Northerly wind is the most frequent
  daytime wind and blows along the valley.
- The tower stands at the foot of a 16° forested slope, about 80 m above the valley floor,
  and 222 m from the Davoser See. According to the ICOS footprint model, the lake contributes
  only about 3 % of the measured flux; it likely acts indirectly, through cool air and the
  along-valley flow. At the same friction velocity, closure is poorest near neutral stability.

The interactive report `reports/ch_dav_overview.html` explains these results and lists
further tests and possible corrections; `reports/ch_dav_3d.html` shows the landscape,
lake, wind sectors and flux footprint in 3D.

## Repository layout

```
ebc_explorer/          reusable code
  paths.py             data locations (reads EBC_DATA_DIR)
  fluxnet.py           readers for ICOS FLUXNET and ICOS L2 flux files (Parquet cache)
  ebc.py               energy balance terms and closure statistics
  nicolini.py          Nicolini et al. (2026) dataset (biomass storage, radiation corrections)
  ch_dav.py            CH-Dav site facts and instrument periods
  swisstopo.py         swisstopo open data (STAC tiles, vector features)
  terrain.py           raster helpers (mosaic, hillshade, sampling)
  fieldbook.py         site fieldbook exports
  refs.py              lookup of reference PDFs
analyses/              numbered analysis scripts ch_dav_01 ... ch_dav_12
scripts/               data download (swisstopo terrain, surface, aerial photo)
reports/               report generators, HTML templates and generated pages
```

Each analysis writes tables to `processed/CH-Dav/` and figures to `figures/CH-Dav/` in the
data folder.

| Script | Content |
|---|---|
| `ch_dav_01_yearly_closure` | closure per year 1997 to 2024, half-hourly and daily |
| `ch_dav_02_term_timeseries` | yearly means of each energy balance term, radiation checks |
| `ch_dav_03_instrument_periods` | closure per sonic and gas analyser period, humidity effects |
| `ch_dav_04_diurnal_storage` | daily cycle of the imbalance, biomass storage and photosynthesis |
| `ch_dav_05_radiation_checks` | incoming radiation against PAR, ERA5 and potential radiation |
| `ch_dav_06_wind_sectors` | closure by wind direction and friction velocity |
| `ch_dav_07_sector_diagnostics` | sector diagnostics (stability, u*/wind speed, data share) |
| `ch_dav_08_terrain` | terrain slope, profiles and canopy height per wind sector |
| `ch_dav_09_lake` | Davoser See dimensions and lake share per wind sector |
| `ch_dav_10_report_maps` | base map images for the overview report |
| `ch_dav_11_3d_assets` | terrain mesh and textures for the 3D page |
| `ch_dav_12_footprint` | ICOS footprint distances, lake share in the footprint, closure |

## Setup

Requires [uv](https://docs.astral.sh/uv/) (Python 3.12 is pinned in `.python-version`).

```bash
uv sync
```

The data are not part of the repository. Copy `.env.example` to `.env` and set the path to
the data folder:

```
EBC_DATA_DIR=/path/to/ebc-explorer-data
```

The data folder uses `raw/` (data as received, read-only), `interim/` (caches that can be
rebuilt), `processed/` (tables), `figures/` and `refs/` (literature).

## Data

| Data | Source | Licence |
|---|---|---|
| EBC results for 84 ICOS and NEON sites | Nicolini, G., Papale, D. (2026), EBC_data, Zenodo, doi:10.5281/zenodo.19608436 | CC BY 4.0 |
| CH-Dav FLUXNET product 1997 to 2024 (v1.3_r1) | ICOS Carbon Portal | CC BY 4.0 |
| CH-Dav ETC L2 fluxes 2019 to 2024, incl. footprint | ICOS Carbon Portal (ETC L2 archive) | CC BY 4.0 |
| Terrain, surface model, aerial photo, lake outline | swisstopo: swissALTI3D, swissSURFACE3D, SWISSIMAGE, swissTLM3D | swisstopo open data, credit "© swisstopo" |

The swisstopo tiles around the tower are downloaded with:

```bash
uv run python scripts/download_ch_dav_terrain.py
```

## Running the analyses and reports

```bash
uv run python analyses/ch_dav_01_yearly_closure.py   # and so on, 01 to 12
uv run python reports/build_ch_dav_overview.py
uv run python reports/build_ch_dav_3d.py
```

The reports embed all data and images and can be opened directly in a browser; the 3D page
loads three.js from a CDN. To preview them with a local web server:

```bash
uv run python -m http.server 8765 --directory reports
```

## Reference

Nicolini, G., Durden, D., Di Fiore, L., et al. (2026). Bridging the energy balance gap in
eddy-covariance measurements: insights from standardized network data. Global Change
Biology, 32(5), e70892. https://doi.org/10.1111/gcb.70892

## Licence

Code: GNU General Public License v3.0 (see `LICENSE`). Data remain under the licences of
their providers listed above.
