"""Satark – Scam Intelligence Platform (PS01). The Flask server: start it with `python app.py`.

What this file does:
  * creates the app, the database and the first officer login (`police`, password in instance/initial_police_password.txt)
  * serves the Vue website from frontend/dist (build it with `npm run build` in frontend/)
  * registers the two JSON APIs:  ui_api.py  -> /api/ui/*  (the website, session login + CSRF)
                                  api.py     -> /api/v1/*  (extension and Telegram bot, API key)
  * keeps two download routes the website links to: the case PDF and the officer CSV export
  * adds security headers to every response
Settings (environment variables) are listed in manual/03_configuration.txt.
"""
import csv
import io
import os
import secrets

from flask import Flask, Response, abort, jsonify, send_file, send_from_directory, session
from werkzeug.security import generate_password_hash

from api import register_api
from core.db import DB
from core.report import case_pdf
from ui_api import register_ui

BASE = os.path.dirname(os.path.abspath(__file__))
INST = os.path.join(BASE, "instance")                  # database, keys, tokens: never share this folder
DIST = os.path.join(BASE, "frontend", "dist")          # built Vue website
os.makedirs(INST, exist_ok=True)

NOT_BUILT = """<!doctype html><meta charset=utf-8><title>Satark</title>
<body style="font:16px system-ui;max-width:640px;margin:60px auto;padding:0 16px">
<h1>Satark server is running</h1><p>The website has not been built yet. In a terminal:</p>
<pre style="background:#eee;padding:12px">cd frontend
npm install
npm run build</pre><p>then reload this page. The APIs at /api/ui and /api/v1 already work.</p></body>"""


def create_app(db_path=None, network=None):
    """Build the Flask app. db_path / network are for tests; normally they come from PS01_DB / PS01_NETWORK."""
    app = Flask(__name__, instance_path=INST)

    # session cookie key, created once and kept in instance/secret.key
    keyf = os.path.join(INST, "secret.key")
    if not os.path.exists(keyf):
        with open(keyf, "w") as f:
            f.write(secrets.token_hex(32))
    app.secret_key = open(keyf).read().strip()
    app.config.update(MAX_CONTENT_LENGTH=160 * 1024 * 1024,          # largest upload (APK limit is 150 MB)
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                      # PS01_NETWORK: 1 = online lookups, cache = only cached lookups (offline venue), 0 = none
                      NETWORK=(os.environ.get("PS01_NETWORK", "1") in ("1", "cache")) if network is None else network)
    db = DB(db_path or os.environ.get("PS01_DB") or os.path.join(INST, "ps01.db"))
    app.db = db

    # first start: create the officer account `police`
    if db.user_count() == 0:
        pw = os.environ.get("PS01_POLICE_PASSWORD") or secrets.token_urlsafe(9)
        db.add_user("police", generate_password_hash(pw), "admin")
        if not os.environ.get("PS01_POLICE_PASSWORD"):
            with open(os.path.join(INST, "initial_police_password.txt"), "w") as f:
                f.write(f"username: police\npassword: {pw}\n(add more users with `python manage.py adduser <name> officer`)\n")
            print("\n  First run: police login created. Credentials saved in instance/initial_police_password.txt\n")

    @app.after_request
    def _headers(resp):
        # no MIME sniffing, no framing, no referrer leaks, and only our own scripts may run
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; script-src 'self'"
        return resp

    # ---------- the website (Vue, frontend/dist) ----------
    # Every page route returns the same index.html; the Vue router shows the right screen.
    @app.get("/")
    @app.get("/r/<int:cid>")
    @app.get("/catalogue")
    @app.get("/how-it-works")
    @app.get("/officer")
    @app.get("/officer/<path:sub>")
    def spa(cid=None, sub=None):
        if not os.path.exists(os.path.join(DIST, "index.html")):
            return NOT_BUILT
        return send_from_directory(DIST, "index.html", max_age=0)

    @app.get("/assets/<path:name>")
    def spa_assets(name):
        # file names contain a content hash, so they can be cached for a year
        return send_from_directory(os.path.join(DIST, "assets"), name, max_age=31536000)

    # ---------- downloads ----------
    @app.get("/result/<int:cid>/report.pdf")
    def pdf(cid):
        """Case report (findings, identifiers, evidence hash). Public, like the result page itself."""
        c = db.get_case(cid)
        if not c:
            abort(404)
        return send_file(io.BytesIO(case_pdf(c)), mimetype="application/pdf", download_name=f"satark-case-{cid}.pdf")

    @app.get("/police/export.csv")
    def p_export():
        """All cases as CSV for officers (session login). Cells are escaped so Excel never runs them as formulas."""
        if not session.get("user"):
            return jsonify(error="login required"), 401
        rows = db.search_cases(limit=5000)
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["case_id", "created_utc", "type", "risk", "score", "status", "citizen_reported", "times_checked", "title"])
        for r in rows:
            w.writerow([r["id"], r["created"], r["kind"], r["level"], r["score"], r["status"], r["flagged"], 1 + (r.get("hits") or 0),
                        _csv_safe(r["title"])])
        db.log(session["user"], "export_csv", "", f"{len(rows)} rows")
        return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=satark-cases.csv"})

    register_api(app, db, INST)       # /api/v1/*  extension + bot
    register_ui(app, db)              # /api/ui/*  website
    return app


def _csv_safe(s):
    """Stop spreadsheet formula injection: a title starting with = + - @ is written as text."""
    s = str(s or "")
    return "'" + s if s[:1] in "=+-@\t\r" else s


app = create_app()

if __name__ == "__main__":
    # HOST=0.0.0.0 to reach it from other devices on the network; behind a proper WSGI server for anything beyond a demo
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 5000)), debug=False)
