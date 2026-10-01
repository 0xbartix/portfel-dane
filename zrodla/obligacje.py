"""Parametry detalicznych obligacji skarbowych z listów emisyjnych MF.

Dla każdej serii (np. EDO1033): oprocentowanie w 1. okresie, marża i opłata za przedterminowy wykup.
Źródło prawdy to PDF listu emisyjnego podlinkowany na stronie serii w obligacjeskarbowe.pl – strony
serii mają nieaktualny, szablonowy tekst o opłatach (np. EDO1036: strona 2,00 zł, list 3,00 zł).
Parametry raz wyemitowanej serii się nie zmieniają, więc trzymamy je w pamięci podręcznej
(dane/obligacje_cache.json) i pobieramy tylko nowe serie.
"""

import json
import re
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from .http import get

BASE = "https://www.obligacjeskarbowe.pl"
# rodzaj: (adres strony, miesięcy do wykupu, od kiedy pobieramy)
TYPES = {
    "EDO": ("obligacje-10-letnie-edo", 120, (2014, 1)),
    "COI": ("obligacje-4-letnie-coi", 48, (2020, 1)),
    "ROS": ("obligacje-6-letnie-ros", 72, (2019, 1)),
    "ROD": ("obligacje-12-letnie-rod", 144, (2019, 1)),
    "TOS": ("obligacje-3-letnie-tos", 36, (2021, 1)),
    "OTS": ("obligacje-3-miesieczne-ots", 3, (2021, 1)),
    "ROR": ("obligacje-roczne-ror", 12, (2021, 1)),
    "DOR": ("obligacje-2-letnie-dor", 24, (2021, 1)),
}
ORDER = list(TYPES)
NO_EARLY = 99.99  # OTS: brak przedterminowego wykupu


def series_code(kind, year, month):
    """Seria sprzedawana w danym miesiącu: rodzaj + miesiąc i rok wykupu, np. EDO + 10/2033 -> EDO1033."""
    k = year * 12 + month - 1 + TYPES[kind][1]
    return f"{kind}{k % 12 + 1:02d}{(k // 12) % 100:02d}"


def _num(s):
    return float(s.replace(",", "."))


def parse_letter(text):
    """Z tekstu listu emisyjnego: (oproc. 1. okresu %, marża %, opłata zł). Brak = None."""
    t = re.sub(r"\s+", " ", text)
    r1 = (re.search(r"pierwszym (?:rocznym |miesięcznym )?okresie odsetkowym stopa procentowa wynos\w* ([\d,]+)\s*%", t)
          or re.search(r"Oprocentowanie obligacji (?:jest stałe i )?wynos\w* ([\d,]+)\s*%", t))
    # starsze listy: „w pierwszym okresie o marżę 2,50%, zaś w następnych o stałą marżę 1,50%”
    margin = (re.search(r"stał\w* marż\w* w wysokości ([\d,]+)\s*%", t)
              or re.search(r"marż\w*(?: odsetkow\w*)? w wysokości ([\d,]+)\s*%", t))
    fee = re.search(r"nie wyższ\w* niż ([\d,]+) zł", t)
    return (_num(r1.group(1)) if r1 else None,
            _num(margin.group(1)) if margin else 0.0,
            _num(fee.group(1)) if fee else None)


def pdf_text(data):
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(data)
        f.flush()
        return subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, text=True,
                              check=True).stdout


def fetch_series(kind, code):
    page = get(f"{BASE}/oferta-obligacji/{TYPES[kind][0]}/{code.lower()}/").decode("utf-8", "ignore")
    pdfs = re.findall(r'href="(/media_files/[^"]+\.pdf)"', page)
    if not pdfs:
        return None
    r1, margin, fee = parse_letter(pdf_text(get(BASE + pdfs[0])))
    if r1 is None:
        return None
    if kind == "OTS":
        fee = NO_EARLY
    return {"r1": r1, "marza": margin, "oplata": fee, "list": BASE + pdfs[0]}


def months(start, end):
    y, m = start
    while (y, m) <= end:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def update_cache(cache_path, today=None, log=print):
    today = today or date.today()
    path = Path(cache_path)
    cache = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    misses = cache.setdefault("_brak", [])
    for kind, (_slug, _m, start) in TYPES.items():
        for y, m in months(start, (today.year, today.month)):
            code = series_code(kind, y, m)
            if code in cache or code in misses:
                continue
            try:
                row = fetch_series(kind, code)
            except Exception as e:  # 404 = seria nie istniała (np. TOS przed 08.2022)
                row = None
                log(f"  {code}: {e}")
            if row is None:
                if (y, m) < (today.year, today.month):  # bieżący miesiąc ponawiamy przy kolejnym przebiegu
                    misses.append(code)
                continue
            row["sprzedaz"] = f"{y:04d}-{m:02d}"
            cache[code] = row
            log(f"  {code}: {row['r1']}% / marża {row['marza']}% / opłata {row['oplata']} zł")
            path.write_text(json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    return cache


def current_offer(cache, today=None):
    """Bieżąca oferta = serie sprzedawane w tym miesiącu (MF publikuje je przed 1. dniem miesiąca)."""
    today = today or date.today()
    out = {}
    for kind in ORDER:
        code = series_code(kind, today.year, today.month)
        if code in cache:
            out[kind] = cache[code] | {"seria": code}
    return out


if __name__ == "__main__":
    import sys
    update_cache(sys.argv[1] if len(sys.argv) > 1 else "dane/obligacje_cache.json")
