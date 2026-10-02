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
| `metale.txt`, `krypto.txt` | cena spot zł/oz (XAU, XAG, XPT, XPD) i zł (BTC, ETH – starszy format); `metale.txt` ma na końcu 4 pola z ceną sprzed 24 h (starsze arkusze ich nie czytają) | gold-api.com × kurs NBP |
| `kryptowaluty_24h.txt` | jak `kryptowaluty.txt`, cena zł sprzed 24 h (zmiana dzienna) | odczyty godzinowe z `dane/godzinowe.json` (ostatnie 30 h) |
| `kryptowaluty.txt` | `W` + RRRRMMDDGGMM + rekordy `;` + symbol (6 znaków, dopełniony spacjami) + cena zł ×10⁸ (16 cyfr); arkusze czytają do 30 monet | BTC, ETH: gold-api.com; pozostałe: Bitstamp (tylko z licencją – niżej) × kurs NBP |
| `metale_hist.txt` | średnie miesięczne zł/oz od 5 lat | Bank Światowy (Pink Sheet, CC BY 4.0), MFW przez DBnomics |

Format: jedna linia, pola o stałej szerokości, same cyfry (brak danych = `-`), na początku litera –
dzięki temu ani Google, ani Excel nie zamieni treści na liczbę i nie pomyli separatora dziesiętnego.
Najdłuższy plik ma ok. 13 tys. znaków (limit `WEBSERVICE` w Excelu: 32 767).

## Obrazki (`obrazki/` → `public/ikony/`, `public/monety/`)

Ikony zakładek (Lucide, licencja ISC) w kolorach palety arkusza i logo monet (cryptocurrency-icons, licencja
CC0 1.0; moneta spoza zestawu – kółko z literami), PNG 64 px dla funkcji `IMAGE` w arkuszach. Pliki licencji
leżą obok obrazków. `build_api.py` kopiuje je do `public/` przy każdej budowie. Odświeżenie (ręcznie, wymaga
ImageMagick): `python3 narzedzia/obrazki.py`.

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

**Kryptowaluty.** Darmowe plany CoinGecko, CoinPaprika, Binance, Coinbase i CoinLore zabraniają redystrybucji albo
użytku komercyjnego (sprawdzone 1.10.2026). Bitstamp pozwala na redystrybucję danych do celów komercyjnych po
podpisaniu „Data License Agreement” (partners@bitstamp.net); zapasowo Kraken (marketdata@kraken.com, też za zgodą).
Do czasu podpisania umowy `kryptowaluty.txt` zawiera tylko BTC i ETH z gold-api.com. Po podpisaniu: w repozytorium
Settings → Secrets and variables → Actions → Variables dodaj `KRYPTO_BITSTAMP` = `1` – kolejny przebieg dopisze
pozostałe monety (lista w `zrodla/krypto.py`). Arkusze nie wymagają zmian.
