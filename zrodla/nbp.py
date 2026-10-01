"""NBP: kursy średnie (tabela A) i stopa referencyjna."""

import json
import re
from datetime import date, timedelta

from .http import get
from .kalendarz import business_days_before

CURRENCIES = ("EUR", "USD", "GBP", "CHF")
RATES_URL = "https://api.nbp.pl/api/exchangerates/rates/a/{}/{}/{}/?format=json"
REF_ARCHIVE = "https://static.nbp.pl/dane/stopy/stopy_procentowe_archiwum.xml"


def fx_history(code, start, end):
    """Kursy średnie NBP: {data publikacji: kurs} (zapytania po max 93 dni, limit API)."""
    out, d = {}, start
    while d <= end:
        e = min(d + timedelta(days=92), end)
        try:
            data = json.loads(get(RATES_URL.format(code.lower(), d.isoformat(), e.isoformat())))
            for r in data["rates"]:
                out[date.fromisoformat(r["effectiveDate"])] = r["mid"]
        except Exception as ex:  # 404 = brak notowań w przedziale (np. same święta)
            if "404" not in str(ex):
                raise
        d = e + timedelta(days=1)
    return out


def rate_for_tax_day(history, day):
    """Kurs do PIT: średni kurs NBP z ostatniego dnia roboczego poprzedzającego dzień transakcji."""
    d = day - timedelta(days=1)
    for _ in range(15):
        if d in history:
            return history[d]
        d -= timedelta(days=1)
    return None


def ref_changes():
    xml = get(REF_ARCHIVE).decode("utf-8-sig")
    out = []
    for since, block in re.findall(r'obowiazuje_od="([\d-]+)">(.*?)</pozycje>', xml, flags=re.S):
        m = re.search(r'id="ref"\s+oprocentowanie="([\d,]+)"', block)
        if m:
            out.append((date.fromisoformat(since), float(m.group(1).replace(",", "."))))
    return sorted(out)


def ref_on(changes, day):
    rate = None
    for since, r in changes:
        if since <= day:
            rate = r
    return rate


def ref_for_bond_month(changes, first_of_month):
    """ROR/DOR: stopa referencyjna obowiązująca w 10. dniu roboczym przed 1. dniem miesiąca,
    w którym zaczyna się okres odsetkowy (listy emisyjne ROR/DOR, ust. 16)."""
    return ref_on(changes, business_days_before(first_of_month, 10))
