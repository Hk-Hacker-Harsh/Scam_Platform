"""SSRF-safe page / file downloader used by the website checks and the analysis pipeline."""
import ipaddress
import re
import socket

import requests
from urllib.parse import urljoin, urlsplit


ALLOWED_PORTS = {80, 443, 8080, 8443}


class FetchError(Exception):
    pass


def _public_ip(host: str):
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise FetchError(f"cannot resolve {host}") from e
    for i in infos:
        ip = ipaddress.ip_address(i[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise FetchError(f"{host} resolves to a non-public address; refusing to fetch")
    return True


def fetch_bytes(url: str, max_bytes=1_500_000, max_redirects=4, timeout=10, require_complete=False):
    """Fetch without letting the user aim our server at internal addresses. Every redirect hop is re-validated.
    Returns (final_url, raw_bytes, redirect_chain, encoding). require_complete=True raises if the file exceeds max_bytes."""
    import requests
    chain = []
    cur = url if re.match(r"(?i)^https?://", url) else "http://" + url
    for _ in range(max_redirects + 1):
        sp = urlsplit(cur)
        if sp.scheme not in ("http", "https") or not sp.hostname:
            raise FetchError("only http/https URLs can be fetched")
        if sp.port and sp.port not in ALLOWED_PORTS:
            raise FetchError("port not allowed")
        _public_ip(sp.hostname)
        r = requests.get(cur, timeout=timeout, allow_redirects=False, stream=True,
                         headers={"User-Agent": "Mozilla/5.0 (compatible; SatarkScanner/0.1)"})
        chain.append(cur)
        if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("Location"):
            cur = urljoin(cur, r.headers["Location"])
            r.close()
            continue
        if r.status_code >= 400:
            r.close()
            raise FetchError(f"server answered HTTP {r.status_code}")
        data = b""
        for chunk in r.iter_content(65536):
            data += chunk
            if len(data) > max_bytes:
                if require_complete:
                    r.close()
                    raise FetchError(f"file larger than {max_bytes // (1024*1024)} MB")
                data = data[:max_bytes]
                break
        r.close()
        return cur, data, chain, r.encoding or "utf-8"
    raise FetchError("too many redirects")


def safe_fetch(url: str, max_bytes=1_500_000, max_redirects=4, timeout=8):
    """Returns (final_url, html_text, redirect_chain). Pages are cached for a few hours (core/netcache.py)."""
    from ... import netcache

    def look():
        final, data, chain, enc = fetch_bytes(url, max_bytes, max_redirects, timeout)
        return [final, data.decode(enc, errors="replace"), chain]
    try:
        final, html, chain = netcache.cached(f"page:{url.strip()}", netcache.TTL["page"], look)
    except netcache.Offline as e:
        raise FetchError(str(e))
    return final, html, chain
