"""Core tests: detection on sample messages / links / e-mails / APKs, police override and linking, SSRF safety,
the website API end to end, deep scan (against a local test server) and the one-file-per-check rule."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import io
import pytest
from app import create_app
from core.analysis import analyze, catalogue
from core.engine import REGISTRY

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
PW = "test-pass-123"


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("PS01_POLICE_PASSWORD", PW)
    a = create_app(db_path=str(tmp_path / "t.db"), network=False)
    a.config["TESTING"] = True
    a.config["TESTING_NO_CSRF"] = True
    return a


@pytest.fixture()
def client(app):
    return app.test_client()


def level(app, kind, text="", **kw):
    return app.db.get_case(analyze(app.db, kind, text=text, **kw))


def fired(c):
    return {f["check_id"] for f in c["findings"] if f["status"] == "fired"}


def test_registry_size():
    assert len(REGISTRY) >= 90
    assert sum(r["implemented"] for r in catalogue()) >= 60


def test_scam_sms_high(app):
    c = level(app, "message", "Your SBI account will be blocked within 24 hours. Update KYC http://sbi-kyc-update.xyz/login and share OTP. Call +923001234567")
    assert c["level"] == "High" and {"otp_pin_request", "combosquat", "foreign_number_claiming_local"} <= fired(c)
    assert ("phone", "+923001234567") in {(i["type"], i["value"]) for i in c["ids"]}


def test_benign_message_low(app):
    assert level(app, "message", "Hi, your lunch is at 1pm tomorrow")["level"] == "Low"


def test_soft_signals_cap_at_medium(app):
    c = level(app, "message", "Your electricity bill is pending, power will be disconnected tonight. Install app http://bit.ly/abc123")
    assert c["level"] == "Medium" and c["hard"] == 0


def test_ussd_and_remote_app(app):
    assert {"ussd_forwarding_code", "remote_access_app"} <= fired(level(app, "message", "Dial **21*9876543210# and install AnyDesk now"))


def test_homograph_url(app):
    c = level(app, "url", "https://раyраl-secure.com")
    assert "mixed_script_label" in fired(c) and c["level"] == "High"


def test_userinfo_and_open_redirect(app):
    assert {"userinfo_at_trick", "open_redirect_param"} <= fired(level(app, "url", "http://sbi.co.in@evil-site.top/login?redirect=http://x.com"))


def test_xss_in_url(app):
    assert "xss_payload_in_url" in fired(level(app, "url", "http://x.example/a?q=<script>alert(1)</script>"))


def test_official_domain_verified_but_lookalike_not(app):
    assert level(app, "url", "https://www.onlinesbi.sbi")["level"] == "Verified official"
    assert level(app, "url", "https://sbi.co.in.evil.top/login")["level"] != "Verified official"


def test_website_html_checks(app):
    html = '<title>HDFC Bank Login</title><form action="https://api.telegram.org/bot1/sendMessage"><input name="otp"><input type="password" name="pw"></form><img src="https://www.hdfcbank.com/logo.png">'
    c = level(app, "url", "http://hdfc-secure.example.top/", page_html=html)
    assert {"sensitive_fields_form", "form_posts_elsewhere", "brand_assets_hotlink"} <= fired(c)


def test_email_headers(app):
    raw = "From: SBI Support <sbi.support@gmail.com>\nReply-To: x@evil.top\nSubject: KYC\nAuthentication-Results: mx; spf=fail; dkim=none; dmarc=fail\nContent-Type: text/html\n\n<a href='http://evil.top/x'>www.sbi.co.in</a>"
    c = level(app, "email", raw)
    assert {"email_spf_dkim_dmarc_fail", "email_display_name_spoof", "email_anchor_text_mismatch", "email_reply_to_mismatch"} <= fired(c) and c["level"] == "High"


def test_email_address_only(app):
    c = level(app, "email", "help@sbi-support.co")
    assert c["level"] in ("Medium", "Low") and "email_spf_dkim_dmarc_fail" not in fired(c) and c["meta"]["address_only"]


def test_apk_fake(app):
    c = level(app, "apk", file_bytes=open(os.path.join(FIX, "fake_sbi.apk"), "rb").read(), filename="fake_sbi.apk")
    assert c["level"] == "High" and {"apk_repackaged_clone", "apk_permission_combo", "apk_telegram_exfil"} <= fired(c)
    types = {i["type"] for i in c["ids"]}
    assert {"apk_sha256", "apk_package", "ip"} <= types


def test_apk_rejects_non_apk(app):
    with pytest.raises(ValueError):
        analyze(app.db, "apk", file_bytes=b"not a zip", filename="x.apk")


def test_police_override_and_linking(app):
    a = level(app, "message", "Pay refund to fraudster@okaxis now, share OTP. http://evil-kyc.top")
    assert a["level"] == "High"
    app.db.set_label("upi", "fraudster@okaxis", "confirmed_fraud", "FIR 1", "police")
    b = level(app, "message", "Please send money to fraudster@okaxis thanks")
    assert b["level"] == "Confirmed fraud"
    assert "police_confirmed_identifier" in fired(b)
    app.db.set_label("upi", "fraudster@okaxis", "verified_official", "", "police")
    assert level(app, "message", "send to fraudster@okaxis")["level"] != "Confirmed fraud"
    assert app.db.campaigns() and app.db.heatlist()


def test_ssrf_blocked():
    from core.checks.web.fetcher import safe_fetch, FetchError
    for u in ("http://127.0.0.1/", "http://localhost:8080/", "http://169.254.169.254/latest/meta-data", "http://10.0.0.1/", "http://[::1]/", "file:///etc/passwd"):
        with pytest.raises(FetchError):
            safe_fetch(u)


# ---------------- web layer ----------------

def _csrf(c):
    return c.get("/api/ui/session").get_json()["csrf"]


def test_website_routes(client):
    # without a build the server explains how to build the website; the API works either way
    for p in ("/", "/catalogue", "/how-it-works", "/officer", "/officer/case/3", "/r/5"):
        assert client.get(p).status_code == 200
    assert client.get("/api/ui/checks").get_json()["implemented"] >= 100


def test_police_requires_login(client):
    for p in ("overview", "cases", "campaigns", "heatlist", "registry", "audit", "graph"):
        assert client.get(f"/api/ui/police/{p}").status_code == 401
    assert client.get("/police/export.csv").status_code == 401


def test_full_flow(client, app):
    """Citizen checks an SMS, reports it; officer signs in, confirms the domain; the next check is Confirmed fraud."""
    r = client.post("/api/ui/analyze", data={"kind": "message", "text": "KYC update http://sbi-kyc-update.xyz share OTP"})
    cid = r.get_json()["id"]
    c = client.get(f"/api/ui/case/{cid}").get_json()
    assert c["level"] == "High" and "1930" in " ".join(c["advice"]["en"])
    assert client.get(f"/result/{cid}/report.pdf").data[:4] == b"%PDF"
    assert client.post(f"/api/ui/case/{cid}/report", json={"note": "got this sms"}).status_code == 200
    assert client.post("/api/ui/login", json={"username": "police", "password": "bad"}).status_code == 401
    assert client.post("/api/ui/login", json={"username": "police", "password": PW}).status_code == 200
    ov = client.get("/api/ui/police/overview").get_json()
    assert ov["queue"] and ov["queue"][0]["id"] == cid               # citizen-reported, waiting for review
    assert client.get("/api/ui/police/cases?q=sbi-kyc").get_json()["rows"][0]["id"] == cid
    assert client.get(f"/api/ui/police/case/{cid}").status_code == 200
    r = client.post(f"/api/ui/police/case/{cid}/label", json={"label": "confirmed_fraud", "type": "domain", "value": "sbi-kyc-update.xyz", "note": "FIR 9"})
    assert r.status_code == 200
    r2 = client.post("/api/ui/analyze", data={"kind": "url", "text": "http://sbi-kyc-update.xyz/x"}).get_json()
    assert client.get(f"/api/ui/case/{r2['id']}").get_json()["level"] == "Confirmed fraud"
    assert any(a["action"] == "confirmed_fraud" for a in client.get("/api/ui/police/audit").get_json()["rows"])
    assert client.get("/police/export.csv").data.startswith(b"case_id")
    # label on an identifier that is not part of the case is rejected
    bad = client.post(f"/api/ui/police/case/{cid}/label", json={"label": "confirmed_fraud", "type": "domain", "value": "unrelated.com"})
    assert bad.status_code == 400


def test_web_all_input_types(client):
    ok = lambda r: r.status_code == 200 and r.get_json()["id"] > 0
    assert ok(client.post("/api/ui/analyze", data={"kind": "message", "text": "Send OTP now"}))
    assert ok(client.post("/api/ui/analyze", data={"kind": "url", "text": "hdfc-kyc.cfd"}))
    assert ok(client.post("/api/ui/analyze", data={"kind": "email", "text": "a@b-bank.top"}))
    eml = b"From: A <a@evil.top>\nSubject: hi\n\nhello http://evil.top"
    assert ok(client.post("/api/ui/analyze", data={"kind": "email", "file": (io.BytesIO(eml), "m.eml")}, content_type="multipart/form-data"))
    apk = open(os.path.join(FIX, "benign.apk"), "rb").read()
    assert ok(client.post("/api/ui/analyze", data={"kind": "apk", "file": (io.BytesIO(apk), "b.apk")}, content_type="multipart/form-data"))
    bad = client.post("/api/ui/analyze", data={"kind": "apk", "file": (io.BytesIO(b"x"), "b.exe")}, content_type="multipart/form-data")
    assert bad.status_code == 400 and ".apk" in bad.get_json()["error"]


def test_csrf_enforced(app):
    app.config["TESTING_NO_CSRF"] = False
    c = app.test_client()
    assert c.post("/api/ui/analyze", data={"kind": "message", "text": "x"}).status_code == 400
    assert c.post("/api/ui/analyze", data={"kind": "message", "text": "hello friend"}, headers={"X-CSRF-Token": _csrf(c)}).status_code == 200


# ---------------- cascade (follow APK links) ----------------

@pytest.fixture()
def local_site(monkeypatch):
    import http.server, threading, core.checks.web.fetcher as cw
    apk = open(os.path.join(FIX, "fake_sbi.apk"), "rb").read()
    page = b'<html><title>Get SBI YONO</title><a href="/files/sbi_kyc.apk">Download app</a></html>'

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/notapk.apk":
                body, ct = b"<html>nope</html>", "text/html"
            elif self.path.endswith(".apk"):
                body, ct = apk, "application/vnd.android.package-archive"
            else:
                body, ct = page, "text/html"
            self.send_response(200); self.send_header("Content-Type", ct); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        def log_message(self, *a): pass
    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setattr(cw, "_public_ip", lambda host: True)   # test-only: allow loopback
    monkeypatch.setattr(cw, "ALLOWED_PORTS", {srv.server_port})
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_apk_from_link(app, local_site):
    c = level(app, "apk", apk_url=local_site + "/files/sbi_kyc.apk", network=True)
    assert c["level"] == "High" and c["meta"]["downloaded_from"].endswith("sbi_kyc.apk")


def test_apk_link_rejects_html(app, local_site):
    with pytest.raises(ValueError):
        analyze(app.db, "apk", apk_url=local_site + "/notapk.apk", network=True)


def test_apk_link_needs_network(app):
    with pytest.raises(ValueError):
        analyze(app.db, "apk", apk_url="http://x.example/a.apk", network=False)


def test_deep_scan_follows_apk_on_page_and_inside_apk(app, local_site):
    cid = analyze(app.db, "url", text=local_site + "/", network=True, deep=True)
    root = app.db.get_case(cid)
    kids = root["children"]
    assert any(k["kind"] == "apk" and k["level"] == "High" for k in kids)
    assert "followed_content_malicious" in fired(root) and root["level"] in ("High", "Medium")
    apk_case = next(k for k in kids if k["kind"] == "apk")
    grand = app.db.get_case(apk_case["id"])["children"]
    assert grand, "domains/e-mails inside the APK should become child cases"
    g = app.db.graph()
    assert any(e["data"]["rel"] == "followed" for e in g["edges"])
    assert app.db.graph(focus=cid)["nodes"]


def test_deep_off_does_not_follow(app, local_site):
    cid = analyze(app.db, "url", text=local_site + "/", network=True, deep=False)
    assert app.db.get_case(cid)["children"] == []


def test_graph_and_pages(client, app):
    analyze(app.db, "message", text="send to fraudster@okaxis OTP http://evil-kyc.top")
    analyze(app.db, "message", text="pay fraudster@okaxis now share OTP")
    client.post("/api/ui/login", json={"username": "police", "password": PW})
    g = client.get("/api/ui/police/graph").get_json()
    assert any(n["data"]["kind"] == "identifier" for n in g["nodes"]) and len(g["edges"]) >= 2
    assert client.get("/api/ui/police/graph?case=1&all=1").get_json()["nodes"]
    assert client.get("/api/ui/police/case/1").status_code == 200
    assert client.get("/static/cytoscape.min.js").status_code == 200      # graph library, served for offline use


def test_one_file_per_check_and_new_check_stub(tmp_path):
    import glob, subprocess, sys
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core", "checks")
    for cid, c in REGISTRY.items():
        folder = {"URL": "url", "Domain": "domain", "Message": "message", "Phone": "phone", "Payment": "payment", "Email": "email",
                  "Website": "web", "APK": "apk", "Intelligence": "intelligence"}[c["group"]]
        assert os.path.exists(os.path.join(base, folder, cid + ".py")), f"{cid} has no file in {folder}/"
    stray = [f for f in glob.glob(base + "/*/*.py") if os.path.basename(f) not in ("__init__.py", "common.py", "fetcher.py", "extractor.py") and os.path.basename(f)[:-3] not in REGISTRY]
    assert not stray, stray
