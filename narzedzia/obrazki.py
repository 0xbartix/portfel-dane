"""Ikony i logo monet dla arkuszy (funkcja IMAGE) – uruchamiane ręcznie, wynik commitowany w public/.

    python3 narzedzia/obrazki.py

Ikony: Lucide (licencja ISC) przemalowane na kolory palety arkusza, PNG 64 px → obrazki/ikony/.
Logo monet: cryptocurrency-icons (licencja CC0 1.0), PNG 64 px → obrazki/monety/; moneta spoza zestawu dostaje
kółko z literami. Wymaga ImageMagick (`magick`) i sieci. build_api.py kopiuje obrazki/ do public/ (Pages).
"""

import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from zrodla import krypto  # noqa: E402

LUCIDE = "https://unpkg.com/lucide-static@0.460.0"
MONETY_CC0 = "https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1"
# nazwa pliku: (ikona Lucide, kolor) – kolory akcentów klas z palety arkusza
IKONY = {
    "start": ("house", "A39AD6"), "pulpit": ("layout-dashboard", "A39AD6"), "transakcje": ("list", "8EA9C8"),
    "szukaj": ("search", "8EA9C8"), "akcje": ("trending-up", "8EA9C8"), "krypto": ("bitcoin", "7FB58A"),
    "obligacje": ("landmark", "E8A27F"), "kruszce": ("gem", "E2B93B"), "wplaty": ("piggy-bank", "A39AD6"),
    "dywidendy": ("hand-coins", "7FB58A"), "podatki": ("receipt", "E8A27F"), "obserwowane": ("eye", "8EA9C8"),
    "analiza": ("microscope", "A39AD6"), "ceny": ("tag", "B8B8C8"), "instrukcja": ("book-open", "A39AD6"),
    "ustawienia": ("settings", "B8B8C8"), "konto": ("wallet", "A39AD6"), "cel": ("target", "E8A27F"),
    "kalendarz": ("calendar", "E8A27F"), "gotowka": ("banknote", "B8B8C8"),
}
KOLORY_MONET = {"TON": "0098EA", "SUI": "4DA2FF", "POL": "8247E5"}   # kółko z literami: kolor marki monety


def pobierz(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as odp:
        return odp.read()


def ikony(katalog: Path) -> None:
    katalog.mkdir(parents=True, exist_ok=True)
    (katalog / "LICENSE-lucide.txt").write_bytes(pobierz(f"{LUCIDE}/LICENSE"))
    for nazwa, (ikona, kolor) in IKONY.items():
        svg = pobierz(f"{LUCIDE}/icons/{ikona}.svg").decode().replace('stroke="currentColor"', f'stroke="#{kolor}"')
        tmp = katalog / f"{nazwa}.svg"
        tmp.write_text(svg)
        subprocess.run(["magick", "-background", "none", "-density", "384", str(tmp), "-resize", "64x64",
                        str(katalog / f"{nazwa}.png")], check=True)
        tmp.unlink()


def czcionka() -> str:
    """Pogrubiona czcionka bezszeryfowa z systemu (fontconfig)."""
    return subprocess.run(["fc-match", "sans:bold", "-f", "%{file}"], capture_output=True, text=True).stdout


def monety(katalog: Path) -> list[str]:
    katalog.mkdir(parents=True, exist_ok=True)
    (katalog / "LICENSE-cryptocurrency-icons.txt").write_bytes(pobierz(f"{MONETY_CC0}/LICENSE.md"))
    wygenerowane = []
    for sym in krypto.COINS:
        cel = katalog / f"{sym.lower()}.png"
        try:
            surowe = pobierz(f"{MONETY_CC0}/128/color/{sym.lower()}.png")
            tmp = katalog / "tmp.png"
            tmp.write_bytes(surowe)
            subprocess.run(["magick", str(tmp), "-resize", "64x64", str(cel)], check=True)
            tmp.unlink()
        except Exception:
            kolor = KOLORY_MONET.get(sym, "B8B8C8")
            subprocess.run(["magick", "-size", "64x64", "xc:none", "-fill", f"#{kolor}", "-draw", "circle 32,32 32,1",
                            "-fill", "white", "-font", czcionka(), "-pointsize", "20", "-gravity", "center",
                            "-annotate", "+0+0", sym[:3], str(cel)], check=True)
            wygenerowane.append(sym)
    return wygenerowane


if __name__ == "__main__":
    ikony(ROOT / "obrazki" / "ikony")
    print("bez logo w zestawie CC0 (kółko z literami):", monety(ROOT / "obrazki" / "monety"))
