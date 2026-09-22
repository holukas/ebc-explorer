"""Site fieldbook exports (GIN), e.g. info/fieldbook_gin/CH-DAV-...-export_YYYYMMDD.csv."""

import html
import re

import pandas as pd

from ebc_explorer.paths import DATA_DIR

FIELDBOOK_DIR = DATA_DIR / "info" / "fieldbook_gin"


def load_fieldbook(pattern="CH-DAV-*.csv"):
    """Newest fieldbook export matching `pattern`, with parsed dates and plain text."""
    path = sorted(FIELDBOOK_DIR.glob(pattern))[-1]
    fb = pd.read_csv(path, encoding="utf-8-sig", na_values=["na"])
    fb["Date"] = pd.to_datetime(fb["Date"], format="%d.%m.%Y")
    fb["Text"] = fb["Text"].fillna("").map(lambda s: html.unescape(re.sub(r"<[^>]+>", " ", s)))
    fb["Text"] = fb["Text"].str.replace(r"\s+", " ", regex=True).str.strip()
    return fb.sort_values("Date").reset_index(drop=True)
