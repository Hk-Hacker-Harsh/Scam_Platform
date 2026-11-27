"""JSON endpoints for the Vue frontend (frontend/). Same rules as the server-rendered pages:
session cookie for police login, CSRF token in the `X-CSRF-Token` header on every POST/DELETE,
every police action written to the audit log."""
import secrets
import threading
import time
from collections import defaultdict, deque
from functools import wraps

from flask import Blueprint, abort, jsonify, request, session, url_for
from werkzeug.security import check_password_hash

from core.advice import advice
from core.analysis import KINDS, analyze, catalogue
from core.image_input import IMAGE_EXT, ocr_available

GROUP_ORDER = ["Intelligence", "URL", "Domain", "Website", "Message", "Email", "Phone", "Payment", "APK"]


def case_view(c, police=False):
    """Everything the result / case page needs. `content` (the stored input) is only sent to police."""
    findings = [dict(id=f["check_id"], group=f["grp"], tier=f["tier"], weight=f["weight"], status=f["status"], detail=f["detail"],
                     desc=f["descr"]) for f in c["findings"]]
    ran = [f for f in findings if f["status"] in ("fired", "clear")]
    flagged = [f for f in findings if f["status"] == "fired" and f["weight"] > 0]
    groups = {}
    for f in findings:
        g = groups.setdefault(f["group"], dict(group=f["group"], ran=0, flagged=0, hard=0))
        if f["status"] in ("fired", "clear"):
            g["ran"] += 1
        if f["status"] == "fired" and f["weight"] > 0:
            g["flagged"] += 1
            g["hard"] += f["tier"] == "H"
    meta = c["meta"] or {}
    out = dict(
        id=c["id"], kind=c["kind"], created=c["created"], title=c["title"], level=c["level"], score=c["score"], hard=c["hard"],
        ran=c["ran"], basis=c["basis"], why=c["why"], status=c["status"], flagged=bool(c["flagged"]), source=c["source"],
        parent_id=c["parent_id"], origin=c["origin"],
        meter=dict(flagged=len(flagged), hard=sum(f["tier"] == "H" for f in flagged), ran=len(ran), total=len(findings),
                   groups=sorted(groups.values(), key=lambda g: GROUP_ORDER.index(g["group"]) if g["group"] in GROUP_ORDER else 99)),
        findings=findings,
        ids=[i for i in c["ids"] if i["type"] != "template"],
        children=c["children"], reports=len(c["reports"]),
        times_checked=1 + (c.get("hits") or 0), last_seen=c.get("last_seen") or c["created"],
        meta={k: meta.get(k) for k in ("apk", "image", "redirects", "fetched", "fetch_note", "address_only", "follow_errors", "downloaded_from")
              if meta.get(k)},
        advice=advice(c["level"]),
        pdf=url_for("pdf", cid=c["id"]),
    )
    if police:
        out["content"] = c["content"]
        out["report_list"] = c["reports"]
    return out


def register_ui(app, db):
    bp = Blueprint("ui", __name__, url_prefix="/api/ui")
    hits, lock = defaultdict(deque), threading.Lock()

    def limited(key, per_min):
        now = time.time()
        with lock:
            q = hits[key]
            while q and q[0] < now - 60:
                q.popleft()
            if len(q) >= per_min:
                return True
            q.append(now)
        return False

    @bp.before_request
    def _guard():
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(16)
        if request.method in ("POST", "PUT", "DELETE") and not app.config.get("TESTING_NO_CSRF"):
            if request.headers.get("X-CSRF-Token", "") != session["csrf"]:
                return jsonify(error="Session expired. Reload the page and try again."), 400

    def police(f):
        @wraps(f)
        def w(*a, **k):
            if not session.get("user"):
                return jsonify(error="login required"), 401
            return f(*a, **k)
        return w

    def body():
        return request.get_json(silent=True) or request.form

    # ---------- session ----------
    @bp.get("/session")
    def sess():
        return jsonify(user=session.get("user"), role=session.get("role"), csrf=session["csrf"], network=app.config["NETWORK"],
                       ocr=ocr_available(), kinds=list(KINDS))

    @bp.post("/login")
    def login():
        ip = request.remote_addr or "?"
        if limited("login:" + ip, 10):
            return jsonify(error="Too many attempts. Wait a minute and try again."), 429
        d = body()
        u = db.get_user(str(d.get("username", "")).strip())
        if not u or not check_password_hash(u["pw_hash"], str(d.get("password", ""))):
            db.log(str(d.get("username", "?"))[:40], "login_failed", ip)
            return jsonify(error="Wrong username or password"), 401
        session.clear()
        session["user"], session["role"], session["csrf"] = u["username"], u["role"], secrets.token_hex(16)
        db.log(u["username"], "login")
        return jsonify(user=u["username"], role=u["role"], csrf=session["csrf"])

    @bp.post("/logout")
    def logout():
        db.log(session.get("user", "?"), "logout")
        session.clear()
        session["csrf"] = secrets.token_hex(16)
        return jsonify(ok=True, csrf=session["csrf"])

    # ---------- public ----------
    @bp.post("/analyze")
    def do_analyze():
        if limited("an:" + (request.remote_addr or "?"), 40):
            return jsonify(error="Too many checks in a minute. Please wait a little."), 429
        d = body()
        kind = str(d.get("kind", ""))
        if kind not in KINDS:
            return jsonify(error="Unknown input type"), 400
        f = request.files.get("file")
        fb = f.read() if f and f.filename else None
        fname = f.filename if f else ""
        try:
            if kind == "apk" and not d.get("apk_url") and (not fb or not fname.lower().endswith(".apk")):
                raise ValueError("Choose a file ending in .apk or paste a link to one")
            if kind == "image" and (not fb or not fname.lower().endswith(IMAGE_EXT)):
                raise ValueError("Choose a screenshot or photo (PNG, JPG or WEBP)")
            if kind == "email" and fb is not None and not fname.lower().endswith((".eml", ".txt")):
                raise ValueError("Upload a .eml file (or paste the email text)")
            net = app.config["NETWORK"] and str(d.get("online", "0")) in ("1", "true")
            from_police = bool(session.get("user")) and str(d.get("from_police", "0")) in ("1", "true")
            info = {}
            cid = analyze(db, kind, text=str(d.get("text", "")), file_bytes=fb, filename=fname, network=net,
                          page_html=str(d.get("page_html", "")), apk_url=str(d.get("apk_url", "")).strip(),
                          deep=bool(net and str(d.get("deep", "0")) in ("1", "true")), source="police" if from_police else "public",
                          fresh=str(d.get("fresh", "0")) in ("1", "true"), info=info)
        except ValueError as e:
            return jsonify(error=str(e)), 400
        except Exception as e:
            app.logger.exception("analysis failed")
            return jsonify(error=f"Could not analyse this input ({type(e).__name__}). Try again or use another input type."), 500
        return jsonify(id=cid, cached=info.get("cached", False))

    @bp.post("/case/<int:cid>/recheck")
    def recheck(cid):
        """Run the checks again on the stored input, ignoring the result cache (public; APKs need a new upload)."""
        if limited("an:" + (request.remote_addr or "?"), 40):
            return jsonify(error="Too many checks in a minute. Please wait a little."), 429
        c = db.get_case(cid)
        if not c:
            return jsonify(error="not found"), 404
        if c["kind"] == "apk":
            return jsonify(error="Upload the app again to re-check it (app files are not kept)."), 400
        if c["kind"] == "email" and c["meta"].get("source_file"):
            return jsonify(error="Upload the e-mail file again to re-check it."), 400
        net = bool((c["meta"] or {}).get("network")) and app.config["NETWORK"]
        try:
            new = analyze(db, "message" if c["kind"] == "image" else c["kind"], text=c["content"], network=net, source="public", fresh=True)
        except ValueError as e:
            return jsonify(error=str(e)), 400
        return jsonify(id=new)

    @bp.get("/case/<int:cid>")
    def case(cid):
        c = db.get_case(cid)
        if not c:
            return jsonify(error="not found"), 404
        return jsonify(case_view(c))

    @bp.post("/case/<int:cid>/report")
    def report(cid):
        if not db.get_case(cid):
            return jsonify(error="not found"), 404
        if limited("rep:" + (request.remote_addr or "?"), 10):
            return jsonify(error="Too many reports. Please wait a little."), 429
        d = body()
        db.add_report(cid, str(d.get("note", "")), str(d.get("contact", "")))
        return jsonify(ok=True)

    # ---------- assistant (citizen + police) ----------
    @bp.get("/assistant/status")
    def assistant_status():
        from core import assistant as A
        return jsonify(A.status() | {"police_ai": A.LLM_POLICE})

    @bp.post("/assistant")
    def assistant():
        from core.assistant_service import AssistantError, run
        d = body()
        mode = "police" if str(d.get("mode", "")) == "police" else "citizen"
        if mode == "police" and not session.get("user"):
            return jsonify(error="login required"), 401
        ai = str(d.get("ai", "0")) in ("1", "true", "True")
        ip = request.remote_addr or "?"
        if limited(("ai:" if ai else "as:") + ip, 20 if ai else 30):
            return jsonify(error="Too many questions in a minute. Please wait a little."), 429
        try:
            out = run(db, d, mode=mode, ai=ai, network=bool(app.config["NETWORK"] and str(d.get("online", "0")) == "1"),
                      source="police" if mode == "police" else "public")
        except AssistantError as e:
            return jsonify(error=str(e)), e.code
        except Exception as e:
            app.logger.exception("assistant failed")
            return jsonify(error=f"The assistant failed ({type(e).__name__})."), 500
        if mode == "police":
            db.log(session["user"], "assistant", "", out.get("tool", "")[:40] + ": " + str(d.get("message", ""))[:120])
        return jsonify(out)

    @bp.get("/checks")
    def checks():
        cat = catalogue()
        return jsonify(checks=cat, implemented=sum(r["implemented"] for r in cat), total=len(cat))

    # ---------- police ----------
    @bp.get("/police/overview")
    @police
    def overview():
        return jsonify(stats=db.stats(), recent=db.search_cases(limit=8), queue=db.search_cases(flagged=True, status="open", limit=8),
                       heat=db.heatlist(8))

    @bp.get("/police/cases")
    @police
    def cases():
        a = request.args
        rows = db.search_cases(a.get("q", "").strip(), a.get("level", ""), a.get("kind", ""), a.get("status", ""), a.get("flagged") == "1")
        return jsonify(rows=rows)

    @bp.get("/police/case/<int:cid>")
    @police
    def pcase(cid):
        c = db.get_case(cid)
        if not c:
            return jsonify(error="not found"), 404
        pairs = [(i["type"], i["value"]) for i in c["ids"]]
        v = case_view(c, police=True)
        v["linked"] = db.shared_cases(pairs, exclude=cid)
        v["labels"] = db.labels_for(pairs)
        v["link_types"] = list(db.LINK_TYPES)
        return jsonify(v)

    @bp.post("/police/case/<int:cid>/label")
    @police
    def label(cid):
        c = db.get_case(cid)
        if not c:
            abort(404)
        d = body()
        t, val, lab, note = str(d.get("type", "")), str(d.get("value", "")), str(d.get("label", "")), str(d.get("note", ""))[:200]
        if (t, val) not in {(i["type"], i["value"]) for i in c["ids"]}:
            return jsonify(error="identifier not in this case"), 400
        if lab == "clear":
            db.del_label(t, val)
            db.log(session["user"], "label_removed", f"{t}:{val}", f"case {cid}")
        elif lab in ("confirmed_fraud", "verified_official"):
            db.set_label(t, val, lab, note, session["user"])
            db.log(session["user"], lab, f"{t}:{val}", f"case {cid}: {note}")
        else:
            return jsonify(error="bad label"), 400
        return jsonify(ok=True)

    @bp.post("/police/case/<int:cid>/status")
    @police
    def status(cid):
        st = str(body().get("status", ""))
        if st not in ("open", "reviewed", "closed", "false_positive") or not db.get_case(cid):
            return jsonify(error="bad status"), 400
        db.set_status(cid, st)
        db.log(session["user"], "status", cid, st)
        return jsonify(ok=True)

    @bp.post("/police/case/<int:cid>/rescan")
    @police
    def rescan(cid):
        c = db.get_case(cid)
        if not c or c["kind"] == "apk":
            return jsonify(error="APK cases cannot be re-scanned (the file is not kept)"), 400
        new = analyze(db, "message" if c["kind"] == "image" else c["kind"], text=c["content"], network=app.config["NETWORK"], source="police", fresh=True)
        db.log(session["user"], "rescan", cid, f"-> {new}")
        return jsonify(id=new)

    @bp.get("/police/campaigns")
    @police
    def campaigns():
        return jsonify(campaigns=db.campaigns())

    @bp.get("/police/graph")
    @police
    def graph():
        f = request.args.get("case", "")
        return jsonify(db.graph(focus=int(f) if f.isdigit() else None, show_all=request.args.get("all") == "1"))

    @bp.get("/police/heatlist")
    @police
    def heat():
        return jsonify(rows=db.heatlist(100))

    @bp.get("/police/registry")
    @police
    def registry():
        return jsonify(labels=db.all_labels(), types=list(db.LINK_TYPES))

    @bp.post("/police/registry")
    @police
    def registry_add():
        d = body()
        t, v, lab = str(d.get("type", "")), str(d.get("value", "")).strip().lower(), str(d.get("label", ""))
        if t not in db.LINK_TYPES or not v or lab not in ("confirmed_fraud", "verified_official"):
            return jsonify(error="Choose a type, a value and a label"), 400
        db.set_label(t, v, lab, str(d.get("note", ""))[:200], session["user"])
        db.log(session["user"], lab, f"{t}:{v}", "added from registry page")
        return jsonify(ok=True)

    @bp.post("/police/registry/delete")
    @police
    def registry_del():
        d = body()
        t, v = str(d.get("type", "")), str(d.get("value", ""))
        db.del_label(t, v)
        db.log(session["user"], "label_removed", f"{t}:{v}")
        return jsonify(ok=True)

    @bp.get("/police/audit")
    @police
    def audit():
        return jsonify(rows=db.audit())

    app.register_blueprint(bp)
