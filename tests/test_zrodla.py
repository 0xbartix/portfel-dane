"""Testy parserów i reguł API (bez sieci – na zapisanych dokumentach źródłowych)."""

import json
from datetime import date, timedelta

import pytest

from pomoc_api import FIX, ROOT
from zrodla import format as fmt
from zrodla import gus, kalendarz, nbp, obligacje


# --- kalendarz -----------------------------------------------------------------------------
@pytest.mark.parametrize("year,expected", [(2024, date(2024, 3, 31)), (2025, date(2025, 4, 20)),
                                           (2026, date(2026, 4, 5)), (2027, date(2027, 3, 28))])
def test_wielkanoc(year, expected):
    assert kalendarz.easter(year) == expected


def test_swieta_i_dni_robocze():
    assert not kalendarz.is_business_day(date(2026, 11, 11))      # Święto Niepodległości (środa)
    assert not kalendarz.is_business_day(date(2026, 6, 4))        # Boże Ciało 2026
    assert not kalendarz.is_business_day(date(2025, 12, 24))      # Wigilia wolna od 2025
    assert kalendarz.is_business_day(date(2024, 12, 24))          # ...a w 2024 jeszcze nie
    assert not kalendarz.is_business_day(date(2026, 10, 3))       # sobota
    assert kalendarz.is_business_day(date(2026, 10, 1))


def test_dzien_roboczy_wstecz():
    # 10. dzień roboczy przed 1.10.2026 (czwartek): 17.09.2026
    assert kalendarz.business_days_before(date(2026, 10, 1), 10) == date(2026, 9, 17)
    # przez święta: 10 dni roboczych przed 1.01.2026 omija 24–26.12 i 1.01
    assert kalendarz.business_days_before(date(2026, 1, 1), 10) == date(2025, 12, 15)


# --- NBP -----------------------------------------------------------------------------------
def test_kurs_dzien_przed_transakcja():
    hist = {date(2026, 9, 25): 4.30, date(2026, 9, 28): 4.31, date(2026, 9, 29): 4.32}
    assert nbp.rate_for_tax_day(hist, date(2026, 9, 29)) == 4.31   # dzień poprzedni roboczy
    assert nbp.rate_for_tax_day(hist, date(2026, 9, 28)) == 4.30   # poniedziałek -> piątkowy
    assert nbp.rate_for_tax_day(hist, date(2026, 9, 27)) == 4.30   # niedziela -> piątkowy
    assert nbp.rate_for_tax_day({}, date(2026, 9, 27)) is None


def test_stopa_dla_ror_dor():
    changes = [(date(2025, 12, 4), 4.00), (date(2026, 3, 5), 3.75)]
    assert nbp.ref_for_bond_month(changes, date(2026, 3, 1)) == 4.00   # 10 dni rob. przed = 13.02
    assert nbp.ref_for_bond_month(changes, date(2026, 4, 1)) == 3.75   # 10 dni rob. przed = 17.03
    assert nbp.ref_for_bond_month(changes, date(2025, 12, 1)) is None


# --- GUS -----------------------------------------------------------------------------------
def test_gus_csv():
    yoy, mom = gus.parse_csv((FIX / "gus_fragment.csv").read_text(encoding="utf-8"))
    assert yoy["2026-08"] == 103.4 and yoy["2026-01"] == 102.1
    assert mom["2026-08"] == pytest.approx(100.3)
    assert "2026-09" not in yoy                   # pusty odczyt nie trafia do danych


# --- obligacje -----------------------------------------------------------------------------
@pytest.mark.parametrize("kind,y,m,code", [("EDO", 2023, 10, "EDO1033"), ("OTS", 2026, 10, "OTS0127"),
                                           ("COI", 2026, 9, "COI0930"), ("ROR", 2026, 12, "ROR1227"),
                                           ("ROD", 2026, 10, "ROD1038"), ("DOR", 2026, 11, "DOR1128")])
def test_kod_serii(kind, y, m, code):
    assert obligacje.series_code(kind, y, m) == code


@pytest.mark.parametrize("fixture,expected", [
    ("10-letnie-edo-2026-10", (5.35, 2.00, 3.00)),
    ("10-letnie-edo-2016-08", (2.50, 1.50, 2.00)),   # starszy wzór: inna marża w 1. okresie
    ("10-letnie-edo-2024-01-literowka", (6.90, 1.50, 2.00)),   # w liście MF: „stopa procentowa wynos 6,90%”
    ("4-letnie-coi-2026-10", (4.75, 1.50, 2.00)),
    ("3-letnie-tos-2026-10", (4.40, 0.00, 1.00)),
    ("3-miesieczne-ots-2026-10", (2.00, 0.00, None)),
    ("roczne-ror-2026-10", (4.00, 0.00, 0.50)),
    ("2-letnie-dor-2026-10", (4.15, 0.15, 0.70)),
    ("6-letnie-ros-2026-10", (5.00, 2.00, 2.00)),
    ("12-letnie-rod-2026-10", (5.60, 2.50, 3.00)),
])
def test_list_emisyjny(fixture, expected):
    assert obligacje.parse_letter((FIX / "listy" / f"{fixture}.txt").read_text(encoding="utf-8")) == expected


# --- format --------------------------------------------------------------------------------
def test_format():
    assert fmt.num(3.75, 4, 100) == "0375"
    assert fmt.num(None, 4, 100) == "----"
    assert fmt.monthly("S", (2026, 7), [103.0, None], 4, 10) == "S2026071030----"
    assert fmt.daily("D", date(2026, 9, 30), [4.3672], 6, 10000) == "D20260930043672"
    with pytest.raises(ValueError):
        fmt.num(-1, 4, 10)
    with pytest.raises(ValueError):
        fmt.num(100000, 4, 1)


# --- dane utrzymywane ręcznie: brokerzy i limity -------------------------------------------
BROKERS = json.loads((ROOT / "dane" / "brokerzy.json").read_text(encoding="utf-8"))


def test_brokerzy_kazda_kombinacja_dokladnie_jedna_regula():
    """Dla każdego brokera, konta, rynku, instrumentu i dnia (2015–2030) obowiązuje dokładnie jedna reguła."""
    day = date(2015, 1, 1)
    while day <= date(2030, 12, 31):
        for b in BROKERS["brokerzy"]:
            for konto in "ZIK":
                for rynek in "PZ":
                    for instr in "AE":
                        hits = [r for r in BROKERS["reguly"] if r["broker"] == b and konto in r["konta"]
                                and rynek in r["rynki"] and instr in r["instrumenty"]
                                and r["od"] <= day.isoformat() <= r["do"]]
                        assert len(hits) == 1, (b, konto, rynek, instr, day, hits)
        day += timedelta(days=13)


def test_brokerzy_wartosci_z_tabel_oplat():
    def rule(b, k, r, i, d):
        return next(x for x in BROKERS["reguly"] if x["broker"] == b and k in x["konta"] and r in x["rynki"]
                    and i in x["instrumenty"] and x["od"] <= d <= x["do"])
    assert rule("MBK", "Z", "P", "A", "2026-10-01")["proc"] == 0.39 and rule("MBK", "Z", "P", "A", "2026-10-01")["min_zl"] == 5
    assert rule("MBK", "I", "Z", "E", "2026-10-01")["proc"] == 0.0
    assert rule("BOS", "Z", "P", "A", "2026-10-01")["proc"] == 0.38
    assert rule("BOS", "I", "Z", "E", "2027-03-01")["proc"] == 0.29      # po końcu promocji
    assert rule("XTB", "Z", "Z", "E", "2026-10-01")["przewalutowanie_proc"] == 0.5


def test_limity_rosna_i_ikze_to_40_procent_ike():
    lim = json.loads((ROOT / "dane" / "limity.json").read_text(encoding="utf-8"))["limity"]
    years = sorted(lim)
    assert years[-1] >= "2026"
    for y in years:
        assert lim[y]["ikze"] == pytest.approx(lim[y]["ike"] * 0.4, abs=0.01)       # 1,2 / 3
        assert lim[y]["ikze_jdg"] == pytest.approx(lim[y]["ike"] * 0.6, abs=0.01)   # 1,8 / 3
    assert all(lim[a]["ike"] < lim[b]["ike"] for a, b in zip(years, years[1:]))


# --- kryptowaluty --------------------------------------------------------------------------
def test_kryptowaluty_format():
    from zrodla import krypto
    s = krypto.line("202610011219", {"BTC": 452318.37, "ETH": 15234.5, "SHIB": 0.0000512, "XXX": None})
    assert s.startswith("W202610011219;BTC   ")
    recs = s[13:].split(";")[1:]
    assert [r[:6].strip() for r in recs] == ["BTC", "ETH", "SHIB"]     # kolejność z COINS, bez braków
    assert all(len(r) == 6 + krypto.WIDTH for r in recs)
    assert int(recs[2][6:]) / 1e8 == pytest.approx(0.0000512)
    assert int(recs[0][6:]) / 1e8 == pytest.approx(452318.37)


def test_kryptowaluty_bitstamp_tylko_z_licencja(monkeypatch):
    from zrodla import krypto
    monkeypatch.delenv("KRYPTO_BITSTAMP", raising=False)
    assert not krypto.bitstamp_enabled()
    monkeypatch.setenv("KRYPTO_BITSTAMP", "1")
    assert krypto.bitstamp_enabled()
    assert all(len(c) <= 6 for c in krypto.COINS)
