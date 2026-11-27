"""Identifier extraction and URL helpers. Pure string work, no network."""
import re
import unicodedata
from urllib.parse import urlsplit, unquote

from .data import PUBLIC_SUFFIX_2LD, UPI_HANDLES

URL_RE = re.compile(r"(?i)\b((?:https?://|www\.)[^\s<>\"'\)\]]+|(?:[a-z0-9¡-￿-]+\.)+(?:[a-z]{2,}|xn--[a-z0-9-]+)(?:/[^\s<>\"'\)\]]*)?)")
EMAIL_RE = re.compile(r"(?i)\b[a-z0-9._%+\-]+@(?:[a-z0-9\-]+\.)+[a-z]{2,}\b")
UPI_RE = re.compile(r"(?i)(?<![\w.\-])([a-z0-9._\-]{2,64})@([a-z][a-z0-9]{1,30})\b(?!\.[a-z])")
PHONE_RE = re.compile(r"(?<![\d])(?:\+|00)?(?:91[\s\-]?)?[6-9]\d{4}[\s\-]?\d{5}(?!\d)|(?<!\d)(?:\+|00)[1-9]\d{0,2}[\s\-]?\d{6,12}(?!\d)|(?<!\d)1800[\s\-]?\d{3,4}[\s\-]?\d{3,4}(?!\d)")
IFSC_RE = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")
BTC_RE = re.compile(r"\b(?:bc1[a-z0-9]{25,60}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b")
ETH_RE = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
TRX_RE = re.compile(r"\bT[1-9A-HJ-NP-Za-km-z]{33}\b")
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
GSTIN_RE = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b")
PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
CIN_RE = re.compile(r"\b[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b")
CARD_RE = re.compile(r"\b(?:\d[ \-]?){13,19}\b")
TG_BOT_RE = re.compile(r"\b\d{8,10}:[A-Za-z0-9_\-]{35}\b")
ZW_RE = re.compile("[​‌‍⁠﻿‪-‮⁦-⁩]")


def registered_domain(host: str) -> str:
    host = (host or "").lower().strip(".")
    if re.fullmatch(r"[\d.]+", host):
        return host
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    if ".".join(parts[-2:]) in PUBLIC_SUFFIX_2LD:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def parse_url(raw: str):
    raw = raw.strip().rstrip(".,;:!?)")
    u = raw if re.match(r"(?i)^[a-z][a-z0-9+.\-]*://", raw) else "http://" + raw
    try:
        sp = urlsplit(u)
        host = (sp.hostname or "").lower()
    except ValueError:
        return None
    if not host:
        return None
    userinfo = sp.netloc.rsplit("@", 1)[0] if "@" in sp.netloc else ""
    try:
        port = sp.port
    except ValueError:
        port = None
    return {"raw": raw, "scheme": sp.scheme.lower(), "host": host, "reg": registered_domain(host), "path": sp.path or "",
            "query": sp.query or "", "userinfo": userinfo, "port": port, "had_scheme": u is raw}


def luhn_ok(num: str) -> bool:
    d = [int(c) for c in re.sub(r"\D", "", num)]
    if not 13 <= len(d) <= 19:
        return False
    s = 0
    for i, x in enumerate(reversed(d)):
        if i % 2:
            x = x * 2
            if x > 9:
                x -= 9
        s += x
    return s % 10 == 0


def norm_phone(p: str) -> str:
    digits = re.sub(r"[^\d+]", "", p)
    if digits.startswith("00"):
        digits = "+" + digits[2:]
    if digits.startswith("+"):
        return digits
    if digits.startswith("91") and len(digits) == 12:
        return "+" + digits
    if len(digits) == 10:
        return "+91" + digits
    return digits


def gstin_ok(g: str) -> bool:
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if not re.fullmatch(r"\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]", g):
        return False
    total = 0
    for i, c in enumerate(g[:14]):
        v = chars.index(c) * (1 if i % 2 == 0 else 2)
        total += v // 36 + v % 36
    return chars[(36 - total % 36) % 36] == g[14]


def extract_all(text: str) -> dict:
    """Return identifier dict. UPI IDs are distinguished from e-mails by having no dot in the handle."""
    text = text or ""
    clean = ZW_RE.sub("", text)
    urls, seen = [], set()
    for m in URL_RE.finditer(clean):
        s = m.group(1)
        if clean[m.end():m.end() + 1] == "@" or (m.start() > 0 and clean[m.start() - 1] in "@"):
            continue  # part of an e-mail / UPI ID, not a link
        if "@" in s and not s.lower().startswith("http"):
            continue
        # bare "file.txt"-style tokens: need a plausible TLD
        p = parse_url(s)
        if not p or "." not in p["host"] and not re.fullmatch(r"(\d+\.){3}\d+", p["host"]):
            continue
        tld = p["host"].rsplit(".", 1)[-1]
        if not p["had_scheme"] and not s.lower().startswith("www.") and (tld.isdigit() or len(tld) < 2 or tld in {"txt", "pdf", "png", "jpg", "doc", "docx", "py", "js", "html"}):
            continue
        if p["raw"] in seen:
            continue
        seen.add(p["raw"])
        urls.append(p)
    nourl = re.sub(r"(?i)https?://\S+", " ", clean)
    emails = sorted({e.lower() for e in EMAIL_RE.findall(nourl)})
    upis = sorted({f"{m.group(1)}@{m.group(2)}".lower() for m in UPI_RE.finditer(nourl)
                   if f"{m.group(1)}@{m.group(2)}".lower() not in emails and "." not in m.group(2) and _upi_plausible(nourl, m)})
    phones = []
    for m in PHONE_RE.finditer(clean):
        n = norm_phone(m.group(0))
        if len(re.sub(r"\D", "", n)) >= 7 and n not in phones:
            phones.append(n)
    cards = [re.sub(r"\D", "", c) for c in CARD_RE.findall(clean) if luhn_ok(c)]
    return {
        "urls": urls,
        "domains": sorted({u["reg"] for u in urls}),
        "emails": emails,
        "upis": upis,
        "phones": phones,
        "ifsc": sorted(set(IFSC_RE.findall(clean))),
        "crypto": sorted(set(BTC_RE.findall(clean)) | set(ETH_RE.findall(clean)) | set(TRX_RE.findall(clean))),
        "ips": sorted({i for i in IP_RE.findall(clean) if all(0 <= int(x) <= 255 for x in i.split("."))}),
        "gstin": sorted(set(GSTIN_RE.findall(clean))),
        "pan": sorted(set(PAN_RE.findall(clean))),
        "cin": sorted(set(CIN_RE.findall(clean))),
        "cards": cards,
        "tgbots": sorted(set(TG_BOT_RE.findall(clean))),
    }


UPI_CONTEXT = re.compile(r"(?i)(upi|vpa|bhim|g ?pay|phone ?pe|paytm|pa=|pay(ment)? (to|on|at|kare|karein)|send (money|payment)|यूपीआई|भुगतान)")


def _upi_plausible(text, m):
    """name@handle is a UPI ID only if the handle is a real PSP handle, or the text around it talks about UPI / paying.
    Without this, social handles such as harsh@portfolio or code like scheduler@b8488ee2 were stored as UPI IDs."""
    if m.group(2).lower() in UPI_HANDLES:
        return True
    window = text[max(0, m.start() - 60): m.end() + 40]
    return bool(UPI_CONTEXT.search(window.replace(m.group(0), " ")))


def has_non_ascii_letters(s: str) -> bool:
    return any(ord(c) > 127 and unicodedata.category(c).startswith("L") for c in s)


def scripts_in(s: str):
    out = set()
    for c in s:
        if c.isalpha():
            try:
                out.add(unicodedata.name(c).split()[0])
            except ValueError:
                out.add("UNKNOWN")
    return out
