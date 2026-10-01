"""Buduje statyczne API danych dla arkusza „Portfel inwestora” (katalog public/v1/).

Uruchamiane z harmonogramu (GitHub Actions, co godzinę) albo ręcznie:  python3 build_api.py [--offline]
--offline: bez pobierania – tylko z pamięci podręcznej w dane/ (testy, praca bez sieci).

Każdy plik to jeden wiersz tekstu o stałej szerokości pól (opis formatu: zrodla/format.py, README.md).
Gdy któreś źródło nie odpowiada, zostaje poprzednia wersja jego pliku – arkusze dostają ostatnie dobre dane.
"""

import json
import sys
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from zrodla import format as fmt
from zrodla import gus, metale, nbp, obligacje

ROOT = Path(__file__).parent
DANE, OUT = ROOT / "dane", ROOT / "public" / "v1"
CPI_START = (2014, 1)      # 10- i 12-letnie obligacje potrzebują inflacji sprzed ponad 10 lat
YEARS_BACK = 5             # kursy dzienne i historia kruszców
OFFLINE = "--offline" in sys.argv


def write(name, text):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(text, encoding="ascii")
    print(f"  {name}: {len(text)} zn.")
    if len(text) > 32000:  # Excel WEBSERVICE zwraca najwyżej 32 767 znaków
        raise ValueError(f"{name} za długi dla Excela ({len(text)} zn.)")


def load(name, default):
    p = DANE / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def save(name, data):
    (DANE / name).write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def month_keys(start, end):
    return [f"{y:04d}-{m:02d}" for y, m in obligacje.months(start, end)]


def build_cpi(today):
    data = load("gus_cache.json", None)
    if not OFFLINE:
        data = gus.fetch()
        save("gus_cache.json", data)
    keys = month_keys(CPI_START, (today.year, today.month))
    last = max(k for k in keys if k in data["yoy"])
    keys = keys[:keys.index(last) + 1]
    write("cpi.txt", fmt.monthly("S", CPI_START, [data["yoy"].get(k) for k in keys], 4, 10))
    write("cpi_mm.txt", fmt.monthly("S", CPI_START, [data["mom"].get(k) for k in keys], 4, 10))


def build_ref(today):
    if OFFLINE:
        changes = [(date.fromisoformat(d), r) for d, r in load("ref_cache.json", [])]
    else:
        changes = nbp.ref_changes()
        save("ref_cache.json", [(d.isoformat(), r) for d, r in changes])
    nxt = (today.year + (today.month == 12), today.month % 12 + 1)
    vals = [nbp.ref_for_bond_month(changes, date(y, m, 1)) for y, m in obligacje.months(CPI_START, nxt)]
    write("stopa_ref.txt", fmt.monthly("S", CPI_START, vals, 4, 100))
    since, rate = changes[-1]
    write("stopa_ref_teraz.txt", "R" + fmt.num(rate, 4, 100) + f"{since:%Y%m%d}")


def build_fx(today):
    cache = load("kursy_cache.json", {})
    start = date(today.year - YEARS_BACK, 1, 1) - timedelta(days=20)
    hist = {}
    for code in nbp.CURRENCIES:
        known = {date.fromisoformat(d): v for d, v in cache.get(code, {}).items()}
        if not OFFLINE:
            frm = max(known) - timedelta(days=10) if known else start
            known.update(nbp.fx_history(code, frm, today))
            cache[code] = {d.isoformat(): v for d, v in sorted(known.items()) if d >= start}
        hist[code] = known
    if not OFFLINE:
        save("kursy_cache.json", cache)
    last = max(max(h) for h in hist.values())
    write("kursy.txt", "K" + f"{last:%Y%m%d}" + "".join(fmt.num(hist[c].get(last), 6, 10000) for c in nbp.CURRENCIES))
    day0 = date(today.year - YEARS_BACK, 1, 1)
    days = [day0 + timedelta(d) for d in range((today - day0).days + 1)]
    for code in nbp.CURRENCIES:
        write(f"kurs_{code.lower()}.txt", fmt.daily("D", day0, [nbp.rate_for_tax_day(hist[code], d) for d in days], 6, 10000))
    return hist


def build_metals(today, fx):
    usd = fx["USD"]
    last_usd = usd[max(usd)]
    if not OFFLINE:
        spot = metale.spot_usd()
        save("metale_spot.json", spot)
    spot = load("metale_spot.json", {})
    stamp = max(v["czas"] for v in spot.values())[:16].replace("-", "").replace("T", "").replace(":", "")
    write("metale.txt", "M" + stamp + "".join(fmt.num(spot[s]["usd"] * last_usd, 9, 100) for s in metale.SYMBOLS))
    write("krypto.txt", "C" + stamp + "".join(fmt.num(spot[s]["usd"] * last_usd, 11, 100) for s in metale.CRYPTO))

    hist = load("metale_hist.json", {})
    stale = hist.get("_pobrano", "") < (datetime.now(timezone.utc) - timedelta(hours=20)).isoformat()
    start = (today.year - YEARS_BACK, 1)
    if stale and not OFFLINE:
        hist = metale.monthly_usd(f"{start[0]:04d}-01")
        hist["_pobrano"] = datetime.now(timezone.utc).isoformat()
        save("metale_hist.json", hist)
    keys = month_keys(start, (today.year, today.month))
    avg = {}
    for k in keys:  # średni kurs USD/PLN w miesiącu
        vals = [v for d, v in usd.items() if d.strftime("%Y-%m") == k]
        avg[k] = sum(vals) / len(vals) if vals else None
    last = max((k for k in keys if all(k in hist.get(s, {}) for s in ("XAU", "XAG", "XPT"))), default=keys[0])
    keys = keys[:keys.index(last) + 1]
    cells = []
    for k in keys:
        for s in metale.SYMBOLS:
            v = hist.get(s, {}).get(k)
            cells.append(v * avg[k] if v is not None and avg[k] else None)
    write("metale_hist.txt", fmt.monthly("S", start, cells, 9, 100))


def build_bonds(today):
    cache = obligacje.update_cache(DANE / "obligacje_cache.json", today) if not OFFLINE else load("obligacje_cache.json", {})
    rows = []
    for code in sorted(k for k in cache if not k.startswith("_")):
        c = cache[code]
        rows.append(code + fmt.num(c["r1"], 4, 100) + fmt.num(c["marza"], 4, 100) + fmt.num(c["oplata"], 4, 100))
    write("obligacje.txt", fmt.records("B", rows))
    offer = obligacje.current_offer(cache, today)
    body = ""
    for kind in obligacje.ORDER:
        c = offer.get(kind)
        body += (fmt.num(c["r1"], 4, 100) + fmt.num(c["marza"], 4, 100) + fmt.num(c["oplata"], 4, 100)) if c else "-" * 12
    write("oferta.txt", f"O{today:%Y%m}" + body)


def expand_broker_rules(data):
    """Reguły z dane/brokerzy.json -> rekordy o stałej długości (55 znaków + średnik)."""
    rows = []
    for r in data["reguly"]:
        for konto in r["konta"]:
            for rynek in r["rynki"]:
                for instr in r["instrumenty"]:
                    rows.append(r["broker"] + konto + rynek + instr + r["od"].replace("-", "") + r["do"].replace("-", "")
                                + fmt.num(r["proc"], 5, 100) + fmt.num(r["min_zl"], 6, 100)
                                + fmt.num(r["przewalutowanie_proc"], 4, 100)
                                + fmt.num(r.get("prog_eur_mies", 0), 7, 1)
                                + fmt.num(r.get("proc_ponad_prog", 0), 5, 100)
                                + fmt.num(r.get("min_ponad_prog_eur", 0), 6, 100))
    return rows


def build_static():
    write("brokerzy.txt", fmt.records("F", expand_broker_rules(load("brokerzy.json", None))))
    lim = load("limity.json", None)["limity"]
    write("limity.txt", fmt.records("L", [y + fmt.num(v["ike"], 8, 100) + fmt.num(v["ikze"], 8, 100)
                                          + fmt.num(v["ikze_jdg"], 8, 100) for y, v in sorted(lim.items())]))


OPIS = {
    "meta": "czas aktualizacji API (UTC) i ewentualne błędy źródeł",
    "kursy": "kursy średnie NBP (EUR, USD, GBP, CHF) – ostatnia tabela",
    "kurs_eur": "EUR – kurs z dnia roboczego przed każdym dniem (do PIT), 5 lat",
    "kurs_usd": "USD – jw.", "kurs_gbp": "GBP – jw.", "kurs_chf": "CHF – jw.",
    "cpi": "inflacja GUS r/r, miesięcznie od 2014", "cpi_mm": "inflacja GUS m/m",
    "stopa_ref": "stopa referencyjna NBP dla okresów ROR/DOR", "stopa_ref_teraz": "stopa referencyjna NBP teraz",
    "obligacje": "serie obligacji skarbowych: oprocentowanie 1. okresu, marża, opłata za wykup",
    "oferta": "bieżąca oferta obligacji skarbowych",
    "brokerzy": "prowizje XTB, mBank, BOŚ (Bossa), PKO z datami obowiązywania",
    "limity": "limity wpłat IKE / IKZE", "metale": "kruszce – cena spot zł/oz",
    "krypto": "BTC, ETH – cena zł", "metale_hist": "kruszce – średnie miesięczne zł/oz",
}


def write_index():
    """Strona startowa (bez niej adres katalogu w przeglądarce daje 404 na GitHub Pages)."""
    stamp = (OUT / "meta.txt").read_text() if (OUT / "meta.txt").exists() else ""
    when = f"{stamp[2:6]}-{stamp[6:8]}-{stamp[8:10]} {stamp[10:12]}:{stamp[12:14]} UTC" if len(stamp) >= 14 else "?"
    errors = stamp.split("!", 1)[1] if "!" in stamp else ""
    rows = "".join(f'<tr><td><a href="{n}.txt">{n}.txt</a></td><td>{OPIS.get(n, "")}</td>'
                   f'<td class="r">{(OUT / f"{n}.txt").stat().st_size:,}</td></tr>'.replace(",", " ")
                   for n in OPIS if (OUT / f"{n}.txt").exists())
    status = (f'<p class="err">Nie odświeżyły się: {errors}</p>' if errors else '<p class="ok">✓ wszystkie źródła aktualne</p>')
    html = f"""<!doctype html><html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Portfel – dane</title>
<style>body{{font:15px/1.5 system-ui,sans-serif;max-width:860px;margin:2rem auto;padding:0 16px;color:#3f3f46;background:#fff}}
h1{{font-weight:500}}table{{border-collapse:collapse;width:100%}}td,th{{padding:6px 8px;border-bottom:1px solid #eee;text-align:left}}
.r{{text-align:right;white-space:nowrap}}.ok{{color:#2f855a}}.err{{color:#c53030}}small{{color:#8a8a99}}</style></head><body>
<h1>Dane dla arkusza „Portfel inwestora”</h1>
<p>Ostatnia aktualizacja: <b>{when}</b> (odświeżane co godzinę).</p>{status}
<table><tr><th>Plik</th><th>Zawartość</th><th class="r">Znaków</th></tr>{rows}</table>
<p><small>Źródła: NBP, GUS, Ministerstwo Finansów (listy emisyjne), Bank Światowy (CC BY 4.0), MFW, gold-api.com.
Format plików i kod: <a href="https://github.com/0xbartix/portfel-dane">github.com/0xbartix/portfel-dane</a>.</small></p>
</body></html>"""
    (OUT / "index.html").write_text(html, encoding="utf-8")
    (OUT.parent / "index.html").write_text('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" '
                                           'content="0; url=v1/"><a href="v1/">Dane – v1</a>', encoding="utf-8")


def main(today=None):
    today = today or date.today()
    steps = [("inflacja", lambda: build_cpi(today)), ("stopy NBP", lambda: build_ref(today)),
             ("kursy", lambda: build_fx(today)), ("obligacje", lambda: build_bonds(today)), ("stałe", build_static)]
    failed, fx = [], None
    for name, fn in steps:
        print(name)
        try:
            res = fn()
            if name == "kursy":
                fx = res
        except Exception:
            traceback.print_exc()
            failed.append(name)
    print("kruszce")
    try:
        build_metals(today, fx or {"USD": {date.fromisoformat(d): v for d, v in load("kursy_cache.json", {})["USD"].items()}})
    except Exception:
        traceback.print_exc()
        failed.append("kruszce")
    write("meta.txt", "V1" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M") + ("" if not failed else "!" + ",".join(failed)))
    write_index()
    if failed:
        print("BŁĘDY:", failed)
    return failed


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
