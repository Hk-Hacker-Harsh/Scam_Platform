"""Cache for online lookups (RDAP domain age, DNS, page fetches), stored in instance/netcache.db.

Why: the same domains come up again and again, lookups are slow, and the venue may have weak or no internet.
Modes (env PS01_NETWORK): "1" = look up online and cache the answer; "cache" = use only cached answers, never go online
(run the sample data once with internet beforehand); "0" = online checks are skipped entirely (handled by the engine).
Only real answers are cached. Errors and timeouts are not, so a flaky connection is retried next time.
"""
import json
import os
import sqlite3
import threading
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.environ.get("PS01_NETCACHE", os.path.join(_ROOT, "instance", "netcache.db"))
_lock = threading.Lock()

# how long answers stay valid (seconds)
TTL = {"rdap": 7 * 86400, "rdap_none": 6 * 3600, "dns": 6 * 3600, "page": 6 * 3600}


class Offline(Exception):
    """Cache-only mode and the answer is not cached."""


def cache_only():
    return os.environ.get("PS01_NETWORK", "1") == "cache"


def _conn():
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    c = sqlite3.connect(PATH, timeout=10)
    c.execute("CREATE TABLE IF NOT EXISTS netcache(key TEXT PRIMARY KEY, value TEXT, ts REAL)")
    return c


def get(key, ttl):
    with _lock:
        c = _conn()
        try:
            r = c.execute("SELECT value, ts FROM netcache WHERE key=?", (key,)).fetchone()
        finally:
            c.close()
    if r and (cache_only() or time.time() - r[1] <= ttl):   # offline: an old answer beats no answer
        return True, json.loads(r[0])
    return False, None


def put(key, value):
    with _lock:
        c = _conn()
        try:
            c.execute("INSERT OR REPLACE INTO netcache(key,value,ts) VALUES(?,?,?)", (key, json.dumps(value), time.time()))
            c.commit()
        finally:
            c.close()


def cached(key, ttl, fn):
    """Return the cached value for key, or call fn(), cache and return its result. fn may raise (nothing is cached)."""
    hit, val = get(key, ttl)
    if hit:
        return val
    if cache_only():
        raise Offline(f"offline mode: no cached answer for {key.split(':', 1)[0]}")
    val = fn()
    put(key, val)
    return val


def stats():
    try:
        with _lock:
            c = _conn()
            try:
                rows = c.execute("SELECT substr(key,1,instr(key,':')-1) k, COUNT(*) FROM netcache GROUP BY k").fetchall()
            finally:
                c.close()
        return {k: n for k, n in rows}
    except sqlite3.Error:
        return {}


# ---------- the cached lookups ----------
def dns_status(domain, rtype):
    """'ok' | 'nxdomain' | 'noanswer'. Raises on timeouts / other errors (not cached)."""
    def look():
        import dns.resolver
        try:
            dns.resolver.resolve(domain, rtype, lifetime=4)
            return "ok"
        except dns.resolver.NXDOMAIN:
            return "nxdomain"
        except dns.resolver.NoAnswer:
            return "noanswer"
    return cached(f"dns:{rtype}:{domain.lower()}", TTL["dns"], look)


def dns_txt(domain):
    """TXT records joined into one string ('' when none). Raises on errors."""
    def look():
        import dns.resolver
        try:
            return " ".join(r.to_text() for r in dns.resolver.resolve(domain, "TXT", lifetime=4))
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            return ""
    return cached(f"dns:TXT:{domain.lower()}", TTL["dns"], look)
