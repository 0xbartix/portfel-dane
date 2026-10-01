"""Inflacja GUS: „Miesięczne wskaźniki cen towarów i usług konsumpcyjnych od 1982 r.” (CSV)."""

import csv
import io
import re

from .http import get

PAGE = ("https://stat.gov.pl/obszary-tematyczne/ceny-handel/wskazniki-cen/"
        "wskazniki-cen-towarow-i-uslug-konsumpcyjnych-pot-inflacja-/"
        "miesieczne-wskazniki-cen-towarow-i-uslug-konsumpcyjnych-od-1982-roku/")


def parse_csv(raw):
    """-> (r/r, m/m): słowniki "RRRR-MM" -> indeks (poprzedni okres = 100)."""
    yoy, mom = {}, {}
    for row in csv.reader(io.StringIO(raw), delimiter=";"):
        if len(row) < 6 or not row[3].strip().isdigit() or not row[5].strip():
            continue
        key = f"{int(row[3]):04d}-{int(row[4]):02d}"
        val = float(row[5].replace(",", "."))
        if row[2].startswith("Analogiczny miesiąc"):
            yoy[key] = val
        elif row[2].startswith("Poprzedni miesiąc"):
            mom[key] = val
    return yoy, mom


def fetch():
    page = get(PAGE).decode("utf-8", "ignore")
    path = re.search(r'href="(/download/[^"]+\.csv)"', page).group(1)
    url = "https://stat.gov.pl" + path
    yoy, mom = parse_csv(get(url).decode("cp1250"))
    return {"yoy": yoy, "mom": mom, "url": url}
