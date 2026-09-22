"""Build the CH-Dav energy balance closure overview page.

Collects network results (Nicolini et al. 2026 dataset) and the CH-Dav
analyses (analyses/ch_dav_01..07, outputs in processed/CH-Dav/) into one JSON
payload and injects it into reports/templates/ch_dav_overview.html.

Run the analyses first, then:
    uv run python reports/build_ch_dav_overview.py [--fragment PATH]
Output: reports/ch_dav_overview.html, a standalone, self-contained page (web
fonts from Google Fonts, no other external resources). --fragment also writes
the page body without the html/head wrapper (for hosts that add their own).

The page must not contain personal data: no person names from the fieldbook,
no IP addresses. Fieldbook events are summarised by hand below.
"""

import json
import re
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from ebc_explorer.ch_dav import INSTRUMENT_PERIODS
from ebc_explorer.paths import (CH_DAV_PROCESSED, EBC_RESULTS, EBC_RESULTS_GAPFILLED,
                                STATIONS_ANCILLARY)

HERE = Path(__file__).parent
TEMPLATE = HERE / "templates" / "ch_dav_overview.html"
OUTPUT = HERE / "ch_dav_overview.html"

# Dataset codes -> formulations of Nicolini et al. (2026), Table 2 (mapping
# verified by reproducing the published network means).
AE_CODES = {
    "AE1": "NR",
    "AE2": "NR_G2",
    "AE3": "NR_G1",
    "AE4": "NR_G1_SH_SLE",
    "AE5": "NR_G1_SH_SLE_Spho",
    "AE6": "NR_G1_SH_SLE_Spho_Sbio",
}
TE_FULLQC, TE_USTAR, TE_UNCORR = "H_LE", "Hust_LEust", "Hun_LEun"
TIME_SCALES = {"semioraria": "30 min", "giornaliera": "day", "settimanale": "week",
               "mensile": "month", "stagionale": "season", "annuale": "year"}
STRAT_ORDER = {
    "atm_strat": ["very_stable", "stable", "neutral_stable", "neutral_unstable", "unstable", "very_unstable"],
    "twilight": ["night", "astronomical_twilight", "nautical_twilight", "civil_twilight", "day"],
}

# Curated, anonymised site history (fieldbook, ICOS labelling report, site page).
EVENTS = [
    ("1997-08-12", "processing", "Error in the flux calculation corrected: 10 s pre-averaging had removed air motions slower than 10 s."),
    ("2002-01-09", "set-up", "EC boom found loose and rotated to the south, for an unknown time; turned back to the west. Air supply for the radiometer domes broken."),
    ("2005-08-09", "instrument", "Open-path LI-7500 replaces the closed-path LI-6262; new data acquisition."),
    ("2006-06-12", "radiation", "CNR1 radiometer installed. Later found: wrong sign of SW_OUT, and SW_OUT and LW_OUT channels swapped; corrected in processing."),
    ("2006-10-31", "site", "Trees harvested on 25 × 70 m (1750 m²) in the northeast part of the flux footprint."),
    ("2006-12-20", "instrument", "Sonic Gill R2 replaced by Gill R3-50."),
    ("2008-11-19", "soil", "Soil heat flux plate found wrongly connected."),
    ("2012-09-25", "instrument", "Enclosed-path LI-7200 installed."),
    ("2013-11-08", "site", "Trees thinned in the flux footprint."),
    ("2014-07-16", "instrument", "ICOS system installed (Gill HS-50 and LI-7200), on the same boom as the old system until 2016-11."),
    ("2014-10-16", "soil", "Five soil heat flux plates at 5 to 6 cm depth replace the single plate."),
    ("2016-06-15", "instrument", "Heated intake tube fitted to the LI-7200."),
    ("2017-04-12", "radiation", "CNR4 radiometer installed on a boom pointing south."),
    ("2019-11-18", "network", "ICOS labelling. Wrong wind direction setting of the sonic found and corrected."),
    ("2020-09-22", "instrument", "Replacement HS-100 used while the HS-50 was calibrated (until 2021-02)."),
    ("2021-11-08", "instrument", "LI-7200RS replaces the LI-7200."),
    ("2022-02-09", "instrument", "Sonic transducer found out of place, since an unknown date; HS-50 sent for repair."),
    ("2023-05-02", "instrument", "Replacement HS-50 installed; its tilt readings fluctuate by about 2°."),
]


def clean(x):
    """JSON-safe number: NaN/inf -> None, numpy -> python, rounded."""
    if x is None:
        return None
    if isinstance(x, (float, np.floating)):
        return None if not np.isfinite(x) else round(float(x), 4)
    if isinstance(x, (np.integer,)):
        return int(x)
    return x


def records(df):
    return [{k: clean(v) for k, v in row.items()} for row in df.to_dict(orient="records")]


def level_key(label):
    """Sort key for bin labels like '(-60--57]' or '[0.0, 50.0)'."""
    m = re.search(r"-?\d+(\.\d+)?", str(label))
    return float(m.group()) if m else 0.0


def network_payload():
    res = pd.read_csv(EBC_RESULTS)
    gf = pd.read_csv(EBC_RESULTS_GAPFILLED)
    anc = pd.read_csv(STATIONS_ANCILLARY, sep="\t").set_index("station")

    base = res[(res["t_scale"] == "semioraria") & res["fattore"].isna()]
    rma = base.pivot_table(index="site", columns=["AE_var", "TE_var"], values="RMA_slope")
    imb = base.pivot_table(index="site", columns=["AE_var", "TE_var"], values="EBC_imb")
    gfb = gf[gf["fattore"].isna() & (gf["AE_var"] == AE_CODES["AE6"]) & (gf["TE_var"] == TE_USTAR)]
    ratio = gfb.pivot_table(index="site", columns="t_scale", values="EBC_ratio")

    def get(table, site, ae, te):
        try:
            return clean(table.loc[site, (ae, te)])
        except KeyError:
            return None

    sites = []
    info = base.drop_duplicates("site").set_index("site")
    for site in sorted(info.index):
        a = anc.loc[site] if site in anc.index else None
        entry = {
            "site": site,
            "network": info.loc[site, "network"],
            "pft": info.loc[site, "igbp"],
            "rma": {k: get(rma, site, v, TE_FULLQC) for k, v in AE_CODES.items()},
            "imb": get(imb, site, AE_CODES["AE6"], TE_USTAR),
            "ratio": {TIME_SCALES[k]: clean(ratio.loc[site, k]) if site in ratio.index and k in ratio.columns else None
                      for k in TIME_SCALES},
        }
        entry["rma"]["AE6u"] = get(rma, site, AE_CODES["AE6"], TE_USTAR)
        entry["rma"]["AE6un"] = get(rma, site, AE_CODES["AE6"], TE_UNCORR)
        if a is not None:
            entry.update({
                "lat": clean(a["lat"]), "lon": clean(a["lon"]), "elev": clean(a["elevation"]),
                "ec_h": clean(a["EC_height"]), "slope": clean(a["slope"]), "aspect": a["aspect_class"],
                "hc": clean(a["hc_avg"]), "bio": clean(a["bio_avg"]), "lai": clean(a["lai_avg"]),
            })
        sites.append(entry)

    strat = {}
    s = res[res["fattore"].notna() & (res["t_scale"] == "semioraria")
            & (res["AE_var"] == AE_CODES["AE6"]) & (res["TE_var"] == TE_FULLQC)]
    for factor, g in s.groupby("fattore"):
        levels = STRAT_ORDER.get(factor) or sorted(g["livello"].unique(), key=level_key)
        values = {}
        for site, gs in g.groupby("site"):
            by = gs.set_index("livello")
            values[site] = [
                [clean(by.loc[lv, "RMA_slope"]), clean(by.loc[lv, "datacov_a"])] if lv in by.index else None
                for lv in levels
            ]
        strat[factor] = {"levels": [str(lv) for lv in levels], "values": values}
    return {"sites": sites, "strat": strat}


def read_multi(name):
    return pd.read_csv(CH_DAV_PROCESSED / name, header=[0, 1], index_col=0)


def dav_payload():
    p = CH_DAV_PROCESSED
    y = read_multi("01_yearly_closure.csv")
    yearly = pd.DataFrame({
        "year": y.index.astype(int),
        "hh_slope": y[("hh", "ols_slope")], "hh_rma": y[("hh", "rma_slope")], "hh_ebr": y[("hh", "ebr")],
        "hh_n": y[("hh", "n")], "hh_intercept": y[("hh", "ols_intercept")],
        "day_slope": y[("daily", "ols_slope")], "day_n": y[("daily", "n")],
    })
    t = read_multi("02_yearly_term_means.csv")
    terms = pd.DataFrame({"year": t.index.astype(int)})
    for part in ("day", "night"):
        for v in ("NETRAD", "G", "H", "LE"):
            terms[f"{part}_{v}"] = t[(part, v)].to_numpy()

    periods = pd.read_csv(p / "03_period_summary.csv")
    rh = pd.read_csv(p / "03_ebr_by_rh.csv")[["AE_class", "period", "RH_class", "ebr", "n"]]
    diurnal = pd.read_csv(p / "04_diurnal_by_season.csv")
    storage = pd.read_csv(p / "04_storage_summary.csv", index_col=0)
    storage = storage[["noS_ols_slope", "withS_ols_slope", "noS_ebr", "withS_ebr"]].reset_index(names="season")
    radiation = pd.read_csv(p / "05_radiation_checks.csv")
    sectors = pd.read_csv(p / "06_ebr_by_wind_sector.csv")
    ustar = pd.read_csv(p / "06_ebr_by_ustar.csv")
    quad_ustar = pd.read_csv(p / "06_ebr_by_quadrant_and_ustar.csv")
    quad_period = pd.read_csv(p / "06_ebr_by_quadrant_and_period.csv")
    sector_diag = pd.read_csv(p / "07_sector_diagnostics.csv")

    ip = INSTRUMENT_PERIODS.copy()
    ip["start"] = ip["start"].dt.strftime("%Y-%m-%d")
    ip["end"] = ip["end"].dt.strftime("%Y-%m-%d")

    return {
        "yearly": records(yearly), "terms": records(terms),
        "periods": records(periods), "period_dates": records(ip),
        "rh": records(rh), "diurnal": records(diurnal), "storage": records(storage),
        "radiation": records(radiation), "sectors": records(sectors), "ustar": records(ustar),
        "quad_ustar": records(quad_ustar), "quad_period": records(quad_period),
        "sector_diag": records(sector_diag),
        "events": [{"date": d, "kind": k, "text": txt} for d, k, txt in EVENTS],
    }


STANDALONE_HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>:root{color-scheme:light}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>
</head>
<body>
"""


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fragment", type=Path, help="also write the page without html/head wrapper")
    args = parser.parse_args(argv)
    payload = {
        "generated": date.today().isoformat(),
        "network": network_payload(),
        "dav": dav_payload(),
    }
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    for pattern in (r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",):  # no IP addresses in the page
        assert not re.search(pattern, text), f"payload matches forbidden pattern {pattern}"
    body = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", text)
    OUTPUT.write_text(STANDALONE_HEAD + body + "\n</body>\n</html>\n", encoding="utf-8")
    print(f"wrote {OUTPUT} ({OUTPUT.stat().st_size / 1e3:.0f} kB)")
    if args.fragment:
        args.fragment.write_text(body, encoding="utf-8")
        print(f"wrote {args.fragment}")


if __name__ == "__main__":
    main()
