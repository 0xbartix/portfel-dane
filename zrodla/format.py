"""Format tekstowy API v1 – czytany w arkuszu przez MID (stała szerokość pól).

Zasady (wspólne dla wszystkich plików):
  * plik zaczyna się wielką literą (Arkusze Google nie zamienią go wtedy na liczbę),
  * same cyfry, bez separatora dziesiętnego (wartość × skala), dopełnione zerami do szerokości pola,
  * brak danych = same minusy ("----"), MID+VALUE w arkuszu daje wtedy błąd -> IFERROR -> "".
"""


def num(v, width, scale):
    if v is None:
        return "-" * width
    n = round(v * scale)
    if n < 0 or len(str(n)) > width:
        raise ValueError(f"{v} nie mieści się w {width} cyfrach (skala {scale})")
    return str(n).zfill(width)


def monthly(tag, start, values, width, scale):
    """tag + RRRRMM pierwszego miesiąca + wartość na każdy kolejny miesiąc."""
    return f"{tag}{start[0]:04d}{start[1]:02d}" + "".join(num(v, width, scale) for v in values)


def daily(tag, start, values, width, scale):
    """tag + RRRRMMDD pierwszego dnia + wartość na każdy kolejny dzień kalendarzowy."""
    return f"{tag}{start:%Y%m%d}" + "".join(num(v, width, scale) for v in values)


def records(tag, rows):
    """tag + rekordy poprzedzone średnikiem (każdy rekord ma stałą długość)."""
    return tag + "".join(";" + r for r in rows)
