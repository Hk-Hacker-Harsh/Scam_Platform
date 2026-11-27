"""Orchestration: turn a submitted message / e-mail / URL / APK into a saved case."""
import email
import email.policy
import hashlib
import json
import os
import re
import tempfile
from email.message import EmailMessage

from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from . import checks as _checks
from .checks.apk import extractor as apk_extractor

_checks.load_all()  # registers every check under core/checks/
from .engine import HIGH_AT, MEDIUM_AT, REGISTRY, build_ctx, run_checks, verdict
from .extract import extract_all, parse_url
from .checks.url.common import is_official

KINDS = ("message", "email", "url", "apk", "image")
MAX_TEXT = 20000

# ---- result cache ----
# The same input (same text / link / file, same online + deep settings) within CACHE_TTL reuses the earlier case and
# counts a repeat instead of re-running every check and creating a duplicate case. A cached result is NOT reused when
# a police label on one of its identifiers changed since, or when the rules changed (ENGINE_VERSION).
CACHE_TTL = float(os.environ.get("PS01_CACHE_TTL_HOURS", "12")) * 3600
RULES_REVISION = "2026-11-20b"   # bump when check logic changes without a weight change, to invalidate cached results
ENGINE_VERSION = hashlib.sha256(json.dumps([RULES_REVISION, HIGH_AT, MEDIUM_AT] + sorted(
    [c["id"], c["tier"], c["weight"], c["net"]] for c in REGISTRY.values())).encode()).hexdigest()[:16]


def cache_key(kind, text, file_bytes, page_html, apk_url, network, deep):
    h = hashlib.sha256()
    for part in (kind, re.sub(r"\s+", " ", text or "").strip(), (apk_url or "").strip(),
                 hashlib.sha256(file_bytes).hexdigest() if file_bytes else "",
                 hashlib.sha256(page_html.encode("utf-8", "ignore")).hexdigest() if page_html else "",
                 "net" if network else "off", "deep" if deep else "flat"):
        h.update(part.encode("utf-8", "ignore") + b"\x00")
    return h.hexdigest()


def _label_set(labels):
    return {(l["type"], l["value"], l["label"]) for l in labels}


def cached_result(db, ckey):
    """Case id that can be reused for this cache key, or None."""
    if CACHE_TTL <= 0:
        return None
    cid = db.cached_case(ckey, CACHE_TTL)
    if not cid:
        return None
    c = db.get_case(cid)
    if not c or (c["meta"] or {}).get("engine") != ENGINE_VERSION:
        return None
    now_labels = db.labels_for([(i["type"], i["value"]) for i in c["ids"]])
    if _label_set(now_labels) != _label_set(c["meta"].get("labels") or []):
        return None          # an officer confirmed / cleared something since: the old verdict may be wrong
    return cid


def pairs_from(ctx, extra=()):
    ids, p = ctx.ids, []
    p += [("domain", d) for d in ids.get("domains", [])]
    for k, t in (("phones", "phone"), ("upis", "upi"), ("emails", "email"), ("crypto", "crypto"), ("ips", "ip"),
                 ("tgbots", "tgbot"), ("ifsc", "ifsc"), ("gstin", "gstin")):
        p += [(t, v) for v in ids.get(k, [])]
    p += list(extra)
    return sorted(set(p))


def _parse_email(raw: bytes | str):
    if isinstance(raw, str):
        raw = raw.encode("utf-8", "ignore")
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    body, html = "", ""
    for part in msg.walk():
        ct = part.get_content_type()
        if part.is_multipart():
            continue
        try:
            if ct == "text/plain" and not part.get_filename():
                body += part.get_content() + "\n"
            elif ct == "text/html" and not part.get_filename():
                html += part.get_content() + "\n"
        except Exception:
            continue
    if not body and html:
        body = BeautifulSoup(html, "lxml").get_text(" ", strip=True)
    subj = str(msg.get("Subject", ""))
    return msg, (f"Subject: {subj}\n\n{body}")[:MAX_TEXT], html[:MAX_TEXT * 5]


NOISE_HOST = re.compile(r"(?i)(schemas\.android|w3\.org|apache\.org|google|gstatic|googleapis|facebook|firebase|crashlytics|github\.com|android\.com|xmlpull|mozilla|jquery|example\.(com|org)|telegram\.org)")
MAX_DEPTH, MAX_CHILDREN = 3, 12


def analyze(db, kind, text="", file_bytes=None, filename="", network=False, page_html="", source="public",
            apk_url="", deep=False, parent_id=None, origin="", _depth=0, _state=None, fresh=False, info=None):
    """Returns case id. Raises ValueError for unusable input.
    fresh=True skips the result cache. info (a dict) receives {"cached": bool}.
    deep=True (needs network): follow .apk links found on pages / in messages, and scan the domains and
    e-mail addresses found inside APKs, each as a linked child case (max depth 3, max 12 children)."""
    _state = _state if _state is not None else {"count": 0, "seen": set()}
    if kind not in KINDS:
        raise ValueError("Unknown input type")
    text = (text or "").strip()
    info = info if info is not None else {}
    ckey = cache_key(kind, text, file_bytes, page_html, apk_url, network, deep)
    # officers' own submissions, re-scans and deep-scan children always run fresh
    if not fresh and parent_id is None and source != "police":
        hit = cached_result(db, ckey)
        if hit:
            db.touch_case(hit)
            info["cached"] = True
            return hit
    info["cached"] = False
    extra_pairs, meta, notes = [], {"network": network, "engine": ENGINE_VERSION}, []
    html, final_url, headers, apk, email_html = "", "", None, None, ""
    tmp = None
    title = text[:100] + ("…" if len(text) > 100 else "")
    qr_payloads = []

    if kind == "image":
        if not file_bytes:
            raise ValueError("Choose a screenshot or photo (PNG / JPG)")
        from .image_input import read_image
        img = read_image(file_bytes)
        qr_payloads = img["qr"]
        meta["image"] = {"qr": img["qr"], "ocr_used": img["ocr"] is not None, "ocr_available": img["ocr_available"],
                         "filename": (filename or "")[:120]}
        text = "\n".join(x for x in (text, img["text"]) if x and x.strip()).strip()
        if len(text) < 3:
            raise ValueError("No text or QR code could be read from this image." + (
                "" if img["ocr_available"] else " Text reading (OCR) is not installed on this server, so only QR codes"
                " are read. Paste the message text in the Message tab instead."))
        title = ("Screenshot: " + text.replace("\n", " "))[:100]

    if kind in ("message", "image"):
        if len(text) < 3:
            raise ValueError("Paste the message text")
        text = text[:MAX_TEXT]
        ctx = build_ctx("message", text, db=db, network=network)
        ctx.qr = qr_payloads
        ctx.sha = hashlib.sha256(re.sub(r"\W+", "", text.lower()).encode()).hexdigest()
        extra_pairs.append(("template", ctx.sha[:16]))

    elif kind == "email":
        if file_bytes:
            headers, body, email_html = _parse_email(file_bytes)
            text = body
            title = f"{headers.get('From', 'e-mail')} — {headers.get('Subject', '')}"[:120]
            meta["source_file"] = filename
        elif re.match(r"(?im)^(from|received|return-path|delivered-to|subject|authentication-results|x-[\w-]+):", text):
            headers, body, email_html = _parse_email(text)
            text = body
            title = f"{headers.get('From', 'e-mail')} — {headers.get('Subject', '')}"[:120]
        elif re.fullmatch(r"[^\s@]+@[^\s@]+\.[a-z]{2,}", text, re.I):
            m = EmailMessage()
            m["From"] = text
            headers, notes = m, ["addr_only"]
            title = f"Sender address {text}"
            meta["address_only"] = True
        else:
            raise ValueError("Upload a .eml file, paste the full original email with headers, or enter just the sender address")
        ctx = build_ctx("email", text, headers=headers, network=network, db=db)
        ctx.email_html = email_html
        ctx.notes = notes
        if email_html:
            ex = extract_all(email_html)
            seen = {u["raw"] for u in ctx.ids["urls"]}
            ctx.ids["urls"] += [u for u in ex["urls"] if u["raw"] not in seen]
            ctx.ids["domains"] = sorted({u["reg"] for u in ctx.ids["urls"]})
        frm = str(headers.get("From", ""))
        fa = re.search(r"[\w.+\-]+@[\w.\-]+", frm)
        if fa:
            addr = fa.group(0).lower()
            if addr not in ctx.ids["emails"]:
                ctx.ids["emails"].append(addr)
            fd = addr.split("@")[1]
            p = parse_url(fd)
            if p and not any(u["host"] == p["host"] for u in ctx.ids["urls"]):
                ctx.ids["urls"].append(p)
            if p and p["reg"] not in ctx.ids["domains"]:
                ctx.ids["domains"].append(p["reg"])
        ctx.sha = hashlib.sha256(re.sub(r"\W+", "", text.lower()).encode()).hexdigest()

    elif kind == "url":
        if not text or len(text) > 2000:
            raise ValueError("Enter a URL or domain")
        p = parse_url(text.split()[0])
        if not p or "." not in p["host"] and not re.fullmatch(r"[\d.]+", p["host"]):
            raise ValueError("That does not look like a URL or domain")
        text = text.split()[0]
        title = text[:100]
        html = (page_html or "")[:2_000_000]
        notes_fetch = ""
        if not html and network:
            from .checks.web.fetcher import safe_fetch, FetchError
            try:
                final_url, html, chain = safe_fetch(text)
                meta["fetched"] = final_url
                meta["redirects"] = chain[1:]
            except FetchError as e:
                notes_fetch = str(e)
            except Exception as e:
                notes_fetch = f"fetch failed: {type(e).__name__}"
            if notes_fetch:
                meta["fetch_note"] = notes_fetch
        ctx = build_ctx("url", text, html=html, network=network, db=db, final_url=final_url or "")
        if final_url:
            fp = parse_url(final_url)
            if fp and fp["reg"] != p["reg"] and fp["reg"] not in ctx.ids["domains"]:
                ctx.ids["domains"].append(fp["reg"])
                ctx.ids["urls"].append(fp)
        ctx.sha = hashlib.sha256(p["host"].encode()).hexdigest()

    else:  # apk
        if not file_bytes and apk_url:
            if not network:
                raise ValueError("Downloading an APK from a link needs online lookups, which are switched off")
            from .checks.web.fetcher import fetch_bytes, FetchError
            try:
                final, file_bytes, chain, _ = fetch_bytes(apk_url.strip(), max_bytes=150 * 1024 * 1024, timeout=25, require_complete=True)
            except FetchError as e:
                raise ValueError(f"Could not download the APK: {e}")
            except Exception as e:
                raise ValueError(f"Could not download the APK ({type(e).__name__})")
            if not file_bytes.startswith(b"PK"):
                raise ValueError("That link did not return an APK (not a zip/APK file). Many scam sites hide the file behind a button or a redirect.")
            filename = filename or os.path.basename(urlsplit(final).path) or "downloaded.apk"
            meta["apk_url"], meta["downloaded_from"] = apk_url.strip(), final
            extra_pairs.append(("domain", parse_url(final)["reg"]))
        if not file_bytes:
            raise ValueError("Choose an .apk file or paste a link to one")
        if len(file_bytes) > 150 * 1024 * 1024:
            raise ValueError("APK too large (limit 150 MB)")
        fd, tmp = tempfile.mkstemp(suffix=".apk")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(file_bytes)
            apk = apk_extractor.analyze_apk(tmp)
        finally:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)  # the uploaded file is never executed and not kept
        title = f"{apk['label'] or filename} ({apk['package'] or 'unknown package'})"[:120]
        text = f"APK {filename or apk['package']} sha256={apk['sha256']}"
        ctx = build_ctx("apk", text, apk=apk, db=db, network=network)
        ctx.ids = apk_extractor.clean_ids(ctx.ids)   # drop SDK hosts, Java names, version numbers, placeholders
        extra_pairs += [("apk_sha256", apk["sha256"])] + ([("apk_package", apk["package"])] if apk["package"] else [])
        meta["apk"] = {k: apk[k] for k in ("sha256", "size", "package", "label", "version", "target_sdk", "min_sdk", "cert", "signed_v", "limited",
                                           "error", "component_perms", "launcher", "cleartext", "api_refs", "packers", "hidden_payloads",
                                           "framework", "dex_count", "scanned_files")}
        meta["apk"]["perms"] = apk["perms"]
        ctx.sha = apk["sha256"]
        ctx.text = ""   # text-lexicon checks should not run on dex strings
        ctx.ids = ctx.ids

    ctx.pairs = pairs_from(ctx, extra_pairs)
    ctx.case_kind = kind
    if kind == "url":
        ctx.subject = {("domain", d) for d in ctx.ids.get("domains", [])[:2]}
    elif kind == "apk":
        ctx.subject = {pr for pr in ctx.pairs if pr[0] in ("apk_sha256", "apk_package")}
    else:
        ctx.subject = set()
    ctx.ckey = ckey
    results = run_checks(ctx)

    official = None
    if kind == "url" and ctx.ids["urls"] and all(is_official(u["host"]) for u in ctx.ids["urls"]):
        official = "Domain is on the official registry: " + ", ".join(sorted({u['reg'] for u in ctx.ids['urls']}))
    labels = db.labels_for(ctx.pairs)
    lab = next((l for l in labels if l["label"] == "confirmed_fraud"), None) or next((l for l in labels if l["label"] == "verified_official"), None)
    v = verdict(results, label=lab, official=official)
    if lab and lab["label"] == "confirmed_fraud":
        v["why"] = f"{lab['type']} {lab['value']} was marked confirmed fraud by the police team"
    meta["labels"] = [{k: l[k] for k in ("type", "value", "label", "note", "ts")} for l in labels]
    if kind == "apk":
        content = text
    else:
        content = (text if kind != "email" else text)
    cid = db.save_case(kind, title, content, v, results, ctx.pairs, source=source, meta=meta, parent_id=parent_id, origin=origin, ckey=ckey)
    if deep and network and _depth < MAX_DEPTH:
        _cascade(db, cid, kind, ctx, html, final_url or text, v, source, _depth, _state)
    return cid


def _targets(kind, ctx, html, base):
    """What to follow from this case: [(child_kind, value, why)]"""
    out = []
    if kind == "url" and html:
        for m in re.finditer(r'(?is)(?:href|src|data-url|data-href)\s*=\s*["\']([^"\']+?\.apk)(?:\?[^"\']*)?["\']', html):
            out.append(("apk_url", urljoin(base if re.match(r"(?i)https?://", base) else "http://" + base, m.group(1)), "APK link on page"))
        for m in re.finditer(r"(?i)https?://[^\s\"'<>]+\.apk\b[^\s\"'<>]*", html):
            out.append(("apk_url", m.group(0), "APK link on page"))
    if kind in ("message", "email", "image"):
        for u in ctx.ids.get("urls", [])[:6]:
            if not is_official(u["host"]) and not NOISE_HOST.search(u["host"]):
                out.append(("apk_url" if u["path"].lower().endswith(".apk") else "url", u["raw"], "link in " + kind))
    if kind == "apk":
        for u in ctx.ids.get("urls", []):
            if not is_official(u["host"]) and not NOISE_HOST.search(u["host"]):
                out.append(("url", u["raw"], "server found inside APK"))
        for e in ctx.ids.get("emails", []):
            dom = e.split("@")[1]
            if not is_official(dom) and not NOISE_HOST.search(dom):
                out.append(("email", e, "e-mail found inside APK"))
    return out


def _cascade(db, cid, kind, ctx, html, base, v, source, depth, state):
    errors, children = [], []
    for ck, val, why in _targets(kind, ctx, html, base):
        key = (ck, val.lower().rstrip("/"))
        host = parse_url(val).get("host") if ck != "email" and parse_url(val) else None
        hk = ("host", host) if host and ck == "url" else None
        if key in state["seen"] or (hk and hk in state["seen"]):
            continue
        if state["count"] >= MAX_CHILDREN:
            errors.append("child limit reached")
            break
        state["seen"].add(key)
        if hk:
            state["seen"].add(hk)
        state["count"] += 1
        try:
            kw = dict(network=True, source=source, deep=True, parent_id=cid, origin=why, _depth=depth + 1, _state=state)
            if ck == "apk_url":
                child = analyze(db, "apk", apk_url=val, **kw)
            else:
                child = analyze(db, ck, text=val, **kw)
            children.append((child, val))
        except ValueError as e:
            errors.append(f"{val[:60]}: {e}")
        except Exception as e:
            errors.append(f"{val[:60]}: {type(e).__name__}")
    if errors or children:
        c = db.get_case(cid)
        m = c["meta"]
        m["follow_errors"] = errors
        db.update_meta(cid, m)
    bad = [(c_, val) for c_, val in children if db.get_case(c_)["level"] in ("High", "Confirmed fraud")]
    if bad and v["basis"] == "rules":
        row = dict(id="followed_content_malicious", group="Intelligence", tier="H", weight=45, status="fired", desc="Something this input leads to (APK, linked site, server or e-mail inside an APK) scored High",
                   detail="; ".join(f"{val[:50]} → case #{c_}" for c_, val in bad[:3]))
        db.add_finding(cid, row)
        res = db.findings_as_results(cid)
        nv = verdict(res)
        db.update_verdict(cid, nv["level"], nv["score"], nv["basis"], nv["why"])


def catalogue():
    """The full 150-check catalogue with implementation status derived from the live registry."""
    import json
    rows = json.load(open(os.path.join(os.path.dirname(__file__), "data", "catalogue.json"), encoding="utf-8"))
    impl = set(REGISTRY)
    out = []
    for g, cid, desc, tier, st, pr, net in rows:
        out.append(dict(group=g, id=cid, desc=desc, tier=tier, net=net, priority=pr, implemented=cid in impl))
    known = {r["id"] for r in out}
    for cid, c in REGISTRY.items():
        if cid not in known:
            out.append(dict(group=c["group"] + " (added)", id=cid, desc=c["desc"], tier=c["tier"], net="Y" if c["net"] else "N", priority=1, implemented=True))
    return out
