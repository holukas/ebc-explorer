"""CH-Dav site specifics.

Setup facts (ICOS labelling report 2019-11-18; fieldbook; swissfluxnet site page):
- 46.81533 N, 9.85591 E, ~1639 m a.s.l.; subalpine Norway spruce, mean tree
  height 17.5 m (max 41 m), LAI ~4; "the slopes at the site are steep";
  a road crosses the target area; forest edges with grassland in parts of it
- EC system at 35 m, EC boom points west (fieldbook 2002-01-09);
  Gill HS config "Axis", SA_OFFSET_N = 270 deg. ETC found wrong wind
  directions from a bad sonic configuration after the first ICOS submission
  (fixed before labelling 2019), so WD in earlier HS years may be wrong
- radiometer boom extends south from the east edge of the triangular tower
  platform (3 m side); CNR4 at 35 m since 2017 (CNR1 before)
- disturbances in footprint: 1750 m2 harvest (25 x 70 m) in the NE part,
  Oct 2006; thinning 2013-11
"""

import pandas as pd

# Instrument periods of the EC system, from the BIFVARINFO_HH metadata of the
# ICOS FLUXNET product (VAR_INFO_MODEL of H_F_MDS and LE_F_MDS).
# Note: the metadata labels the LI-7500 as GA_CP, but it is an open-path analyser.
INSTRUMENT_PERIODS = pd.DataFrame(
    [
        ("1997-01-01", "2005-08-09 12:00", "R2 + LI-6262 (CP)", "closed"),
        ("2005-08-09 12:00", "2006-12-20 12:00", "R2 + LI-7500 (OP)", "open"),
        ("2006-12-20 12:00", "2012-09-25 12:00", "R3-50 + LI-7500 (OP)", "open"),
        ("2012-09-25 12:00", "2014-07-16 12:00", "R3-50 + LI-7200 (EP)", "enclosed"),
        ("2014-07-16 12:00", "2021-11-08 00:00", "HS + LI-7200 (EP)", "enclosed"),
        ("2021-11-08 00:00", "2025-01-01 00:00", "HS + LI-7200RS (EP)", "enclosed"),
    ],
    columns=["start", "end", "label", "ga_type"],
).astype({"start": "datetime64[ns]", "end": "datetime64[ns]"})


def instrument_period(index):
    """Label of the instrument period for each timestamp in `index`."""
    labels = pd.Series(pd.NA, index=index, dtype="string")
    for p in INSTRUMENT_PERIODS.itertuples():
        labels[(index >= p.start) & (index < p.end)] = p.label
    return pd.Categorical(labels, categories=INSTRUMENT_PERIODS["label"], ordered=True)
