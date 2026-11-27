"""JSON endpoints used by the Vue frontend: session, CSRF, login, public result, police actions, SPA serving."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app

PW = "pw-123-test"


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("PS01_POLICE_PASSWORD", PW)
    monkeypatch.setenv("PS01_API_KEY", "k")
    a = create_app(db_path=str(tmp_path / "t.db"), network=False)   # CSRF on
    a.config["TESTING"] = True
    return a


@pytest.fixture()
def client(app):
    return app.test_client()


def csrf(c):
    return c.get("/api/ui/session").get_json()["csrf"]


def login(c):
    r = c.post("/api/ui/login", json={"username": "police", "password": PW}, headers={"X-CSRF-Token": csrf(c)})
    assert r.status_code == 200
    return r.get_json()["csrf"]


def test_session_and_csrf_required(client):
    s = client.get("/api/ui/session").get_json()
    assert s["user"] is None and s["csrf"] and "image" in s["kinds"]
    assert client.post("/api/ui/analyze", data={"kind": "message", "text": "hello"}).status_code == 400
    assert "Session expired" in client.post("/api/ui/analyze", data={"kind": "message", "text": "hello"}).get_json()["error"]


def test_public_analyze_and_result(client):
    t = csrf(client)
    r = client.post("/api/ui/analyze", data={"kind": "message", "text": "Share your OTP now, SBI account blocked http://sbi-kyc-update.xyz"},
                    headers={"X-CSRF-Token": t})
    cid = r.get_json()["id"]
    c = client.get(f"/api/ui/case/{cid}").get_json()
    assert c["level"] == "High" and c["meter"]["flagged"] >= 3 and c["meter"]["ran"] > c["meter"]["flagged"]
    assert any(g["group"] == "Message" and g["flagged"] for g in c["meter"]["groups"])
    assert "content" not in c                              # stored input is police-only
    assert c["advice"]["hi"] and c["pdf"].endswith(f"/result/{cid}/report.pdf")
    assert client.post(f"/api/ui/case/{cid}/report", json={"note": "got it on WhatsApp"}, headers={"X-CSRF-Token": t}).status_code == 200
    assert client.get(f"/api/ui/case/{cid}").get_json()["reports"] == 1
    assert client.get("/api/ui/case/99999").status_code == 404


def test_analyze_errors(client):
    t = csrf(client)
    h = {"X-CSRF-Token": t}
    assert client.post("/api/ui/analyze", data={"kind": "bogus"}, headers=h).status_code == 400
    r = client.post("/api/ui/analyze", data={"kind": "message", "text": ""}, headers=h)
    assert r.status_code == 400 and r.get_json()["error"]
    assert "screenshot" in client.post("/api/ui/analyze", data={"kind": "image"}, headers=h).get_json()["error"]


def test_police_requires_login(client):
    for u in ("overview", "cases", "case/1", "campaigns", "graph", "heatlist", "registry", "audit"):
        assert client.get(f"/api/ui/police/{u}").status_code == 401, u


def test_login_wrong_password_and_rate_limit(client):
    t = csrf(client)
    codes = [client.post("/api/ui/login", json={"username": "police", "password": "nope"}, headers={"X-CSRF-Token": t}).status_code for _ in range(11)]
    assert codes[0] == 401 and codes[-1] == 429


def test_police_flow(client):
    t = login(client)
    h = {"X-CSRF-Token": t}
    cid = client.post("/api/ui/analyze", data={"kind": "message", "text": "Pay fee to loan.desk@ybl to release loan. Call 9876543211", "from_police": "1"},
                      headers=h).get_json()["id"]
    ov = client.get("/api/ui/police/overview").get_json()
    assert ov["stats"]["total"] == 1 and ov["recent"][0]["id"] == cid
    assert client.get("/api/ui/police/cases?q=loan.desk").get_json()["rows"][0]["id"] == cid
    c = client.get(f"/api/ui/police/case/{cid}").get_json()
    assert c["content"].startswith("Pay fee") and c["source"] == "police" and "upi" in c["link_types"]
    # label the UPI ID: next case containing it is Confirmed fraud
    assert client.post(f"/api/ui/police/case/{cid}/label", json={"type": "upi", "value": "loan.desk@ybl", "label": "confirmed_fraud", "note": "FIR 12"},
                       headers=h).status_code == 200
    assert client.post(f"/api/ui/police/case/{cid}/label", json={"type": "upi", "value": "not-in-case@ybl", "label": "confirmed_fraud"},
                       headers=h).status_code == 400
    cid2 = client.post("/api/ui/analyze", data={"kind": "message", "text": "Send money to loan.desk@ybl"}, headers=h).get_json()["id"]
    assert client.get(f"/api/ui/case/{cid2}").get_json()["level"] == "Confirmed fraud"
    assert client.post(f"/api/ui/police/case/{cid}/status", json={"status": "reviewed"}, headers=h).status_code == 200
    assert client.post(f"/api/ui/police/case/{cid}/status", json={"status": "weird"}, headers=h).status_code == 400
    new = client.post(f"/api/ui/police/case/{cid}/rescan", headers=h).get_json()["id"]
    assert new > cid2
    assert client.get("/api/ui/police/campaigns").get_json()["campaigns"]
    g = client.get(f"/api/ui/police/graph?case={cid}").get_json()
    assert any(n["data"]["id"] == f"c{cid}" for n in g["nodes"])
    assert client.get("/api/ui/police/heatlist").get_json()["rows"]
    assert client.post("/api/ui/police/registry", json={"type": "phone", "value": "+919000000009", "label": "confirmed_fraud"}, headers=h).status_code == 200
    assert any(l["value"] == "+919000000009" for l in client.get("/api/ui/police/registry").get_json()["labels"])
    assert client.post("/api/ui/police/registry/delete", json={"type": "phone", "value": "+919000000009"}, headers=h).status_code == 200
    actions = [r["action"] for r in client.get("/api/ui/police/audit").get_json()["rows"]]
    assert {"login", "confirmed_fraud", "status", "rescan", "label_removed"} <= set(actions)
    t2 = client.post("/api/ui/logout", headers=h).get_json()["csrf"]
    assert t2 != t and client.get("/api/ui/police/overview").status_code == 401


def test_website_served_when_built(tmp_path, monkeypatch):
    import app as appmod
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<div id=app>SPA</div>")
    (dist / "assets" / "x.js").write_text("console.log(1)")
    monkeypatch.setenv("PS01_POLICE_PASSWORD", PW)
    a = appmod.create_app(db_path=str(tmp_path / "s.db"), network=False)
    c = a.test_client()
    monkeypatch.setattr(appmod, "DIST", str(tmp_path / "missing"))
    assert b"has not been built" in c.get("/").data              # before the build: instructions, not an error
    monkeypatch.setattr(appmod, "DIST", str(dist))
    for u in ("/", "/r/5", "/officer", "/officer/case/3", "/catalogue"):
        assert b"SPA" in c.get(u).data, u
    assert c.get("/assets/x.js").status_code == 200
