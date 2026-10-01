"""Pobieranie z ponawianiem i grzecznym odstępem między zapytaniami."""

import time
import urllib.request

UA = "Mozilla/5.0 (portfel-dane; +https://github.com/0xbartix/portfel-dane)"
_last = [0.0]


def get(url, timeout=60, tries=3, delay=0.3):
    for attempt in range(tries):
        wait = _last[0] + delay - time.time()
        if wait > 0:
            time.sleep(wait)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                _last[0] = time.time()
                return r.read()
        except urllib.error.HTTPError as e:
            _last[0] = time.time()
            if e.code == 404:
                raise
            if attempt == tries - 1:
                raise
        except Exception:
            _last[0] = time.time()
            if attempt == tries - 1:
                raise
        time.sleep(2 * (attempt + 1))
