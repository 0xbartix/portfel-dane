# API danych „Portfel inwestora”

Statyczne pliki tekstowe, które arkusz pobiera przy każdym otwarciu (Arkusze Google: `IMPORTDATA`,
Excel 365 na Windows: `WEBSERVICE`). Budowane co godzinę przez `build_api.py` i publikowane jako
zwykła strona (GitHub Pages, Cloudflare Pages albo dowolny hosting plików).

## Pliki (`public/v1/`)

| Plik | Zawartość | Źródło |
|---|---|---|
| `meta.txt` | `V1` + czas budowy (UTC); po `!` lista źródeł, które się nie odświeżyły | – |
| `kursy.txt` | `K` + data tabeli + EUR, USD, GBP, CHF (×10 000) | NBP, tabela A |
| `kurs_eur.txt` … `kurs_chf.txt` | `D` + pierwszy dzień + kurs na każdy dzień kalendarzowy od 1.01 sprzed 5 lat: **kurs z ostatniego dnia roboczego przed tym dniem** (do PIT) | NBP |
| `cpi.txt`, `cpi_mm.txt` | `S` + RRRRMM + inflacja r/r i m/m (×10) od 01.2014 | GUS |
| `stopa_ref.txt` | `S` + RRRRMM + stopa referencyjna obowiązująca 10 dni roboczych przed 1. dniem miesiąca (ROR/DOR) | NBP |
| `stopa_ref_teraz.txt` | `R` + stopa (×100) + data obowiązywania | NBP |
| `obligacje.txt` | `B` + rekordy `;KOD(7)` + oproc. 1. okresu, marża (×100), opłata za wykup (×100) dla każdej serii od 2014 r. | listy emisyjne MF (PDF) |
| `oferta.txt` | `O` + RRRRMM + bieżąca oferta 8 rodzajów (po 12 cyfr) | listy emisyjne MF |
| `brokerzy.txt` | `F` + reguły prowizji (broker, konto, rynek, instrument, od, do, %, minimum, przewalutowanie, próg obrotu) | `dane/brokerzy.json` (z tabel opłat) |
| `limity.txt` | `L` + limity wpłat IKE / IKZE / IKZE JDG na każdy rok | `dane/limity.json` |
| `metale.txt`, `krypto.txt` | cena spot zł/oz (XAU, XAG, XPT, XPD) i zł (BTC, ETH) | gold-api.com × kurs NBP |
| `metale_hist.txt` | średnie miesięczne zł/oz od 5 lat | Bank Światowy (Pink Sheet, CC BY 4.0), MFW przez DBnomics |

Format: jedna linia, pola o stałej szerokości, same cyfry (brak danych = `-`), na początku litera –
dzięki temu ani Google, ani Excel nie zamieni treści na liczbę i nie pomyli separatora dziesiętnego.
Najdłuższy plik ma ok. 13 tys. znaków (limit `WEBSERVICE` w Excelu: 32 767).

## Utrzymanie ręczne

- `dane/brokerzy.json` – po każdej zmianie tabeli opłat XTB / mBanku / Bossy dopisz nową regułę
  z datą `od`, a starej ustaw `do`. Test `test_brokerzy_kazda_kombinacja_dokladnie_jedna_regula`
  pilnuje, żeby okresy się nie nakładały. Pozycje z `do_sprawdzenia` wymagają potwierdzenia.
- `dane/limity.json` – w styczniu dopisz limity na nowy rok.

## Uruchomienie

```bash
python3 build_api.py            # pobiera i buduje public/v1
python3 build_api.py --offline  # tylko z pamięci podręcznej (dane/)
python3 -m pytest -q tests      # testy parserów na zapisanych dokumentach
```

Wymaga `pdftotext` (poppler-utils) i `openpyxl`. Pierwsze pobranie wszystkich serii obligacji trwa
ok. 20 minut (~650 listów emisyjnych), kolejne – sekundy.

## Hosting (GitHub Pages)

Repozytorium: https://github.com/0xbartix/portfel-dane – workflow `.github/workflows/dane-api.yml`
co godzinę buduje dane i publikuje je pod adresem **https://0xbartix.github.io/portfel-dane/v1**.
Ręczne uruchomienie: Actions → `dane-api` → Run workflow (albo `gh workflow run dane-api`).
Własna domena: Settings → Pages → Custom domain (stary adres github.io przekierowuje na nowy).

## Licencje źródeł

NBP i GUS – dane publiczne, ponowne wykorzystanie z podaniem źródła. Listy emisyjne MF – dokumenty
urzędowe (art. 4 prawa autorskiego). Bank Światowy – CC BY 4.0. MFW (DBnomics) – z podaniem źródła.
gold-api.com – darmowe API dopuszczające użycie komercyjne. Notowań akcji i ETF API **nie** udostępnia
(licencje giełd) – arkusz bierze je z GOOGLEFINANCE / STOCKHISTORY po stronie użytkownika.
