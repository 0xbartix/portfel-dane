"""Kryptowaluty: lista monet z ceną w zł do pliku kryptowaluty.txt.

Licencje (sprawdzone 1.10.2026):
  * gold-api.com – „Commercial use of the API is always permitted” (gold-api.com/terms §9), ale tylko BTC i ETH;
  * Bitstamp – wszystkie monety z listy w jednym zapytaniu; redystrybucja do celów komercyjnych dozwolona dopiero
    po podpisaniu „Data License Agreement” (partners@bitstamp.net). Dlatego włączane zmienną środowiskową
    KRYPTO_BITSTAMP=1 – dopiero po podpisaniu umowy.
CoinGecko, CoinPaprika, Binance, Coinbase, CoinLore – darmowe plany zabraniają redystrybucji/użytku komercyjnego.
"""

import json
import os

from . import format as fmt
from .http import get

# kolejność = kolejność w pliku (najpopularniejsze najpierw); BTC i ETH zawsze z gold-api.com
COINS = ("BTC", "ETH", "USDT", "XRP", "BNB", "SOL", "USDC", "DOGE", "ADA", "TRX", "LINK", "AVAX", "XLM", "DOT",
         "LTC", "BCH", "SHIB", "TON", "SUI", "POL")
GOLD_API = ("BTC", "ETH")
WIDTH, SCALE = 16, 10 ** 8          # zł × 1e8 – mieści i BTC (setki tysięcy zł), i SHIB (ułamki grosza)


def bitstamp_enabled():
    return os.environ.get("KRYPTO_BITSTAMP") == "1"


def bitstamp_usd(coins=COINS):
    """Cena USD jako środek bid/ask (odporny na rzadko handlowane pary)."""
    data = json.loads(get("https://www.bitstamp.net/api/v2/ticker/"))
    ticks = {d["pair"]: d for d in data}
    out = {}
    for c in coins:
        d = ticks.get(f"{c}/USD")
        if d and d.get("bid") and d.get("ask"):
            out[c] = (float(d["bid"]) + float(d["ask"])) / 2
    return out


def line(stamp, prices_pln):
    """"W" + RRRRMMDDGGMM + rekordy ";" + symbol (6 znaków, dopełniony spacjami) + cena zł × 1e8 (16 cyfr)."""
    rows = [sym.ljust(6) + fmt.num(prices_pln[sym], WIDTH, SCALE) for sym in COINS if prices_pln.get(sym)]
    for sym in prices_pln:
        if len(sym) > 6:
            raise ValueError(f"symbol {sym} dłuższy niż 6 znaków")
    return "W" + stamp + "".join(";" + r for r in rows)
