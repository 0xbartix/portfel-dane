"""Kruszce i BTC/ETH: cena spot (gold-api.com, użycie komercyjne dozwolone) i historia miesięczna
(Bank Światowy – Pink Sheet, CC BY 4.0: złoto, srebro, platyna; MFW przez DBnomics: pallad)."""

import io
import json
from collections import defaultdict

import openpyxl

from .http import get

SYMBOLS = ("XAU", "XAG", "XPT", "XPD")
CRYPTO = ("BTC", "ETH")
WB_URL = ("https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/"
          "related/CMO-Historical-Data-Monthly.xlsx")
IMF_PD = "https://api.db.nomics.world/v22/series/IMF/PCPS/M.W00.PPALLA.USD?observations=1"


def spot_usd():
    out = {}
    for s in SYMBOLS + CRYPTO:
        d = json.loads(get(f"https://api.gold-api.com/price/{s}"))
        out[s] = {"usd": d["price"], "czas": d["updatedAt"]}
    return out


def monthly_usd(start_key):
    """{symbol: {"RRRR-MM": średnia miesięczna USD/oz}}"""
    out = defaultdict(dict)
    wb = openpyxl.load_workbook(io.BytesIO(get(WB_URL)), read_only=True, data_only=True)
    rows = list(wb["Monthly Prices"].iter_rows(values_only=True))
    hdr = rows[4]
    cols = {"XAU": hdr.index("Gold"), "XAG": hdr.index("Silver"), "XPT": hdr.index("Platinum")}
    for row in rows[6:]:
        if not row[0] or "M" not in str(row[0]):
            continue
        y, m = str(row[0]).split("M")
        key = f"{y}-{m}"
        if key >= start_key:
            for s, c in cols.items():
                if isinstance(row[c], (int, float)):
                    out[s][key] = float(row[c])
    imf = json.loads(get(IMF_PD))["series"]["docs"][0]
    for p, v in zip(imf["period"], imf["value"]):
        if p >= start_key and isinstance(v, (int, float)):
            out["XPD"][p] = float(v)
    return out
