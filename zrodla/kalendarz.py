"""Polskie dni robocze (weekendy + święta ustawowe), potrzebne do reguł NBP i obligacji."""

from datetime import date, timedelta
from functools import lru_cache


def easter(year):
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


@lru_cache(maxsize=None)
def holidays(year):
    e = easter(year)
    days = {date(year, 1, 1), date(year, 1, 6), e, e + timedelta(1), date(year, 5, 1), date(year, 5, 3),
            e + timedelta(49), e + timedelta(60), date(year, 8, 15), date(year, 11, 1), date(year, 11, 11),
            date(year, 12, 25), date(year, 12, 26)}
    if year >= 2025:  # Wigilia dniem wolnym od 2025 r.
        days.add(date(year, 12, 24))
    return days


def is_business_day(d):
    return d.weekday() < 5 and d not in holidays(d.year)


def business_days_before(d, n):
    """n-ty dzień roboczy przed dniem d (d się nie liczy)."""
    while n:
        d -= timedelta(1)
        if is_business_day(d):
            n -= 1
    return d
