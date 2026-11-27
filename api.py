"""JSON API used by the browser extension, the Telegram bot and any other client.

Auth: every call except /api/v1/health needs the header `X-API-Key: <key>`.
The key comes from the env var PS01_API_KEY, or is generated on first run into instance/api_key.txt.
CSRF does not apply here (no cookies are used); CORS is opened only for browser-extension origins.
"""
import hmac
import os
import re
import secrets
import threading
import time
from collections import defaultdict, deque

from flask import jsonify, request, url_for

from core.advice import advice
from core.analysis import KINDS, analyze
from core.engine import REGISTRY
from core.extract import norm_phone, parse_url
from core.image_input import IMAGE_EXT, ocr_available

CLIENTS = {"extension", "telegram", "whatsapp", "api"}
RATE_PER_MIN = int(os.environ.get("PS01_API_RATE", "30"))
EXT_ORIGIN = re.compile(r"^(chrome-extension|moz-extension|edge-extension)://[a-z0-9\-]+$", re.I)


def load_api_key(inst_dir):
    key = os.environ.get("PS01_API_KEY", "").strip()
    if key:
        return key
    path = os.path.join(inst_dir, "api_key.txt")
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(secrets.token_urlsafe(24))
        print("\n  First run: API key for the extension / bots saved in instance/api_key.txt\n")
    with open(path) as f:
        return f.read().strip()


def case_json(c):
    fired = [f for f in c["findings"] if f["status"] == "fired" and f["weight"] > 0]
    return {
        "case_id": c["id"], "kind": c["kind"], "created_utc": c["created"],
        "times_checked": 1 + (c.get("hits") or 0), "last_seen_utc": c.get("last_seen") or c["created"],
        "level": c["level"], "score": c["score"], "hard_signals": c["hard"], "checks_ran": c["ran"], "why": c["why"],
        "reasons": [{"check": f["check_id"], "strength": "Hard" if f["tier"] == "H" else "Soft", "description": f["descr"],
                     "detail": f["detail"]} for f in fired],
        "identifiers": [{"type": i["type"], "value": i["value"]} for i in c["ids"] if i["type"] != "template"],
        "meter": {"flagged": len(fired), "ran": sum(f["status"] in ("fired", "clear") for f in c["findings"]), "total": len(c["findings"])},
        "linked_cases": [{"case_id": k["id"], "level": k["level"], "origin": k["origin"]} for k in c["children"]],
        "advice": advice(c["level"]),
        "result_url": url_for("spa", cid=c["id"], _external=True),       # the website's result page
        "report_pdf": url_for("pdf", cid=c["id"], _external=True),
        "helpline": "1930 · cybercrime.gov.in",
    }


def register_api(app, db, inst_dir):
    app.config["API_KEY"] = load_api_key(inst_dir)
    hits = defaultdict(deque)
    lock = threading.Lock()

    def err(msg, code=400):
        return jsonify({"error": msg}), code

    def authed():
        given = request.headers.get("X-API-Key", "")
        if not given and request.headers.get("Authorization", "").startswith("Bearer "):
            given = request.headers["Authorization"][7:]
        return bool(given) and hmac.compare_digest(given.encode(), app.config["API_KEY"].encode())

    def rate_ok():
        k = request.remote_addr or "?"
        now = time.time()
        with lock:
            q = hits[k]
            while q and q[0] < now - 60:
                q.popleft()
            if len(q) >= RATE_PER_MIN:
                return False
            q.append(now)
        return True

    def guard():
        if not authed():
            return err("missing or wrong X-API-Key", 401)
        if not rate_ok():
            return err(f"rate limit: {RATE_PER_MIN} requests per minute", 429)
        return None

    @app.after_request
    def _cors(resp):
        if request.path.startswith("/api/"):
            o = request.headers.get("Origin", "")
            if EXT_ORIGIN.match(o):
                resp.headers["Access-Control-Allow-Origin"] = o
                resp.headers["Vary"] = "Origin"
                resp.headers["Access-Control-Allow-Headers"] = "X-API-Key, Content-Type, X-Client"
                resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
                resp.headers["Access-Control-Max-Age"] = "600"
            resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.get("/api/v1/health")
    def api_health():
        return jsonify({"ok": True, "network": app.config["NETWORK"], "ocr": ocr_available(), "checks": len(REGISTRY),
                        "kinds": list(KINDS) + ["auto"]})

    @app.post("/api/v1/analyze")
    def api_analyze():
        bad = guard()
        if bad:
            return bad
        data = request.get_json(silent=True) or request.form
        kind = (data.get("kind") or "auto").strip().lower()
        text = str(data.get("text") or "")[:20000]
        client = (request.headers.get("X-Client") or data.get("client") or "api").lower()
        source = client if client in CLIENTS else "api"
        f = request.files.get("file")
        fb = f.read() if f and f.filename else None
        fname = f.filename if f else ""
        if kind == "auto":
            if fb is not None:
                low = fname.lower()
                kind = "apk" if low.endswith(".apk") else "email" if low.endswith(".eml") else "image" if low.endswith(IMAGE_EXT) else ""
                if not kind:
                    return err("unsupported file type (use .apk, .eml, .png or .jpg)")
            else:
                one = text.strip()
                kind = "url" if one and " " not in one and "\n" not in one and parse_url(one) and "." in (parse_url(one) or {}).get("host", "") else "message"
        if kind not in KINDS:
            return err("kind must be one of: auto, " + ", ".join(KINDS))
        online = str(data.get("online", "1")) in ("1", "true", "True")
        net = bool(app.config["NETWORK"] and online)
        deep = bool(net and str(data.get("deep", "0")) in ("1", "true", "True"))
        try:
            info = {}
            cid = analyze(db, kind, text=text, file_bytes=fb, filename=fname, network=net, source=source,
                          apk_url=str(data.get("apk_url") or ""), deep=deep, fresh=str(data.get("fresh", "0")) in ("1", "true", "True"), info=info)
        except ValueError as e:
            return err(str(e))
        except Exception as e:
            app.logger.exception("api analysis failed")
            return err(f"analysis failed ({type(e).__name__})", 500)
        return jsonify(case_json(db.get_case(cid)) | {"cached": info.get("cached", False)})

    @app.get("/api/v1/case/<int:cid>")
    def api_case(cid):
        bad = guard()
        if bad:
            return bad
        c = db.get_case(cid)
        if not c:
            return err("not found", 404)
        return jsonify(case_json(c))

    @app.post("/api/v1/assistant")
    def api_assistant():
        """Citizen assistant for the extension and bots. Sends only questions and case ids; never page content."""
        from core.assistant_service import AssistantError, run
        bad = guard()
        if bad:
            return bad
        data = request.get_json(silent=True) or {}
        ai = str(data.get("ai", "0")) in ("1", "true", "True")
        client = (request.headers.get("X-Client") or "api").lower()
        try:
            out = run(db, data, mode="citizen", ai=ai, network=False, source=client if client in CLIENTS else "api")
        except AssistantError as e:
            return err(str(e), e.code)
        except Exception as e:
            app.logger.exception("assistant failed")
            return err(f"assistant failed ({type(e).__name__})", 500)
        return jsonify(out)

    @app.get("/api/v1/assistant/status")
    def api_assistant_status():
        from core import assistant as A
        return jsonify(A.status())

    @app.post("/api/v1/case/<int:cid>/report")
    def api_report(cid):
        """A citizen reports a case to the police review queue (from the bot or extension)."""
        bad = guard()
        if bad:
            return bad
        if not db.get_case(cid):
            return err("not found", 404)
        data = request.get_json(silent=True) or {}
        client = (request.headers.get("X-Client") or "api").lower()
        db.add_report(cid, f"[{client if client in CLIENTS else 'api'}] " + str(data.get("note", ""))[:900], str(data.get("contact", ""))[:120])
        return jsonify({"ok": True, "case_id": cid})

    @app.get("/api/v1/lookup")
    def api_lookup():
        """Has this phone / UPI / domain / e-mail been seen or confirmed? Used by the bot's /lookup command."""
        bad = guard()
        if bad:
            return bad
        t, v = request.args.get("type", "").strip().lower(), request.args.get("value", "").strip()
        if t not in db.LINK_TYPES or not v:
            return err("type must be one of " + ", ".join(db.LINK_TYPES) + " and value is required")
        if t == "phone":
            v = norm_phone(v)
        elif t == "domain":
            p = parse_url(v)
            v = p["reg"] if p else v.lower()
        else:
            v = v.lower()
        with db.conn() as c:
            row = c.execute("""SELECT COUNT(DISTINCT cs.id) n, SUM(cs.level IN ('High','Confirmed fraud')) high,
                               SUM(cs.flagged) reported, MAX(cs.created) last_seen
                               FROM identifiers i JOIN cases cs ON cs.id=i.case_id WHERE i.type=? AND i.value=?""", (t, v)).fetchone()
        labels = db.labels_for([(t, v)])
        lab = labels[0]["label"] if labels else None
        return jsonify({"type": t, "value": v, "police_label": lab, "cases_seen": row["n"] or 0, "high_risk_cases": row["high"] or 0,
                        "citizen_reports": row["reported"] or 0, "last_seen_utc": row["last_seen"]})

