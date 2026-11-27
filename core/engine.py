"""Check registry, context object and the scoring / verdict engine.

Design rules (same as the loan-fraud scanner this grew from):
  * rules decide the verdict, never an LLM
  * HIGH needs a decisive HARD signal, or two hard signals, or one hard signal backed by soft ones;
    a single unbacked hard signal and soft signals alone cap at MEDIUM
  * a police-confirmed label overrides the rules; a registry match gives "Verified official"
  * we never output a bare "Safe" - the lowest outcome is Low risk / Not enough data
"""
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .extract import extract_all

REGISTRY: dict = {}

HARD_W, SOFT_W = 1.0, 0.5
HIGH_AT, MEDIUM_AT = 45.0, 18.0
DECISIVE_W = 45          # a hard signal this strong (OTP request, digital arrest, police label, trojan APK...) can decide High alone
CORROBORATION = 10.0     # otherwise one hard signal needs a meaningful soft signal (weight 20+) or a second hard signal for High


@dataclass
class Ctx:
    kind: str                      # message | email | url | apk  (screenshots are analysed as message)
    text: str = ""                 # message body / email body / url string / apk label+strings
    ids: dict = field(default_factory=dict)
    html: str = ""                 # fetched or pasted page
    final_url: str = ""
    headers: Any = None            # email.message.Message for .eml
    apk: Optional[dict] = None
    network: bool = False          # allow DNS / RDAP lookups
    db: Any = None                 # for intelligence checks
    notes: list = field(default_factory=list)
    brand_ctx: set = field(default_factory=set)
    qr: list = field(default_factory=list)       # decoded QR payloads (screenshot input)

    def have(self, what: str) -> bool:
        return {
            "text": bool(self.text.strip()),
            "urls": bool(self.ids.get("urls")),
            "html": bool(self.html.strip()),
            "headers": self.headers is not None,
            "apk": self.apk is not None,
            "phones": bool(self.ids.get("phones")),
            "upis": bool(self.ids.get("upis")),
            "ifsc": bool(self.ids.get("ifsc")),
            "qr": bool(self.qr),
            "any": True,
            "network": self.network,
        }.get(what, False)


def check(cid, group, tier, weight, desc, needs="any", net=False, hint=""):
    """Register a check. Function returns None (clear) or a detail string / list of strings (fired)."""
    def deco(fn: Callable):
        REGISTRY[cid] = dict(id=cid, group=group, tier=tier, weight=weight, desc=desc, needs=needs, net=net, fn=fn, hint=hint)
        return fn
    return deco


def build_ctx(kind, text="", html="", headers=None, apk=None, network=False, db=None, final_url="") -> Ctx:
    body = text
    if kind == "apk" and apk:
        body = " ".join(filter(None, [apk.get("label", ""), " ".join(apk.get("strings", [])[:4000])]))
    ids = extract_all(body)
    if kind == "url":
        ids = extract_all(text)
        if not ids["urls"]:
            from .extract import parse_url
            p = parse_url(text)
            if p:
                ids["urls"] = [p]
                ids["domains"] = [p["reg"]]
    if html:
        extra = extract_all(html)
        for k in ("emails", "upis", "phones", "ifsc", "gstin", "pan", "cin", "crypto", "tgbots"):
            ids[k] = sorted(set(ids.get(k, [])) | set(extra.get(k, [])))
    if apk:
        for k in ("emails", "upis", "phones", "ips", "tgbots"):
            ids[k] = sorted(set(ids.get(k, [])))
    return Ctx(kind=kind, text=text, ids=ids, html=html, headers=headers, apk=apk, network=network, db=db, final_url=final_url)


def run_checks(ctx: Ctx):
    results = []
    for cid, c in REGISTRY.items():
        if c["net"] and not ctx.network:
            results.append(_row(c, "skipped", "needs internet lookups (disabled)"))
            continue
        if not ctx.have(c["needs"]):
            results.append(_row(c, "na", ""))
            continue
        try:
            out = c["fn"](ctx)
        except Exception as e:  # a broken check must never break a scan
            results.append(_row(c, "error", f"{type(e).__name__}: {e}"[:160]))
            continue
        if out:
            detail = out if isinstance(out, str) else "; ".join(map(str, out))
            results.append(_row(c, "fired", detail[:400]))
        else:
            results.append(_row(c, "clear", ""))
    return results


def _row(c, status, detail):
    return dict(id=c["id"], group=c["group"], tier=c["tier"], weight=c["weight"], desc=c["desc"], status=status, detail=detail)


def score(results):
    fired = [r for r in results if r["status"] == "fired"]
    s = 0.0
    hard = 0
    for r in fired:
        if r["tier"] == "H":
            s += r["weight"] * HARD_W
            hard += 1
        elif r["tier"] == "S":
            s += r["weight"] * SOFT_W
    s = min(100.0, s)
    ran = sum(1 for r in results if r["status"] in ("fired", "clear"))
    return round(s, 1), hard, ran


def verdict(results, label=None, official=None):
    """label: police label dict or None. official: registry match string or None."""
    s, hard, ran = score(results)
    if label and label.get("label") == "confirmed_fraud":
        return dict(level="Confirmed fraud", score=100.0, hard=hard, ran=ran, basis="police", why="Marked as confirmed fraud by the police team")
    if official and hard == 0:
        return dict(level="Verified official", score=0.0, hard=hard, ran=ran, basis="registry", why=official)
    if label and label.get("label") == "verified_official":
        return dict(level="Verified official", score=0.0, hard=hard, ran=ran, basis="police", why="Marked as verified official by the police team")
    if ran < 3:
        return dict(level="Not enough data", score=s, hard=hard, ran=ran, basis="rules", why="Too few checks could run on this input")
    fired = [r for r in results if r["status"] == "fired"]
    decisive = any(r["tier"] == "H" and r["weight"] >= DECISIVE_W for r in fired)
    soft_pts = sum(r["weight"] * SOFT_W for r in fired if r["tier"] == "S")
    backed = decisive or hard >= 2 or (hard == 1 and soft_pts >= CORROBORATION)
    if s >= HIGH_AT and hard >= 1 and backed:
        lvl, why = "High", ("A decisive warning sign" if decisive and hard == 1 else "Several strong warning signs that back each other up")
    elif s >= MEDIUM_AT or hard >= 1:
        if hard == 1 and not backed:
            why = "One strong warning sign, but nothing else backs it up, so capped at Medium"
        elif hard == 0 and s >= HIGH_AT:
            why = "Several warning signs; no hard indicator so capped at Medium"
        else:
            why = "Several warning signs"
        lvl = "Medium"
    else:
        lvl, why = "Low", "No strong warning signs found by the checks that could run (not a guarantee of safety)"
    return dict(level=lvl, score=s, hard=hard, ran=ran, basis="rules", why=why)
