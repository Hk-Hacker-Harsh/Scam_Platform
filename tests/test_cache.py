"""Result cache (same input reuses the case unless labels / rules changed) and the online-lookup cache."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app
import core.analysis as an
from core import netcache

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
SMS = "Pay Rs 500 fee to loan.desk@ybl to release your loan today. Share OTP to confirm."


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("PS01_POLICE_PASSWORD", "pw")
    monkeypatch.setenv("PS01_API_KEY", "k")
    a = create_app(db_path=str(tmp_path / "t.db"), network=False)
    a.config["TESTING"] = True
    a.config["TESTING_NO_CSRF"] = True
    return a


def run(app, text=SMS, **kw):
    info = {}
    cid = an.analyze(app.db, kw.pop("kind", "message"), text=text, info=info, **kw)
    return cid, info["cached"]


# ---------- result cache ----------
def test_same_input_reuses_case_and_counts_repeats(app):
    a, c1 = run(app)
    b, c2 = run(app, "  Pay Rs 500 fee to loan.desk@ybl   to release your loan today.\nShare OTP to confirm. ")  # whitespace only
    assert a == b and (c1, c2) == (False, True)
    case = app.db.get_case(a)
    assert case["hits"] == 1 and case["last_seen"] >= case["created"]
    assert app.db.stats()["total"] == 1


def test_different_input_or_settings_is_not_cached(app):
    a, _ = run(app)
    assert run(app, SMS + " now")[0] != a
    assert run(app, network=True)[0] != a            # online result is a different check
    assert run(app, fresh=True)[0] != a              # "check again"
    assert run(app, source="police")[0] != a         # officers always get a fresh analysis


def test_police_label_change_invalidates_cache(app):
    a, _ = run(app)
    assert app.db.get_case(a)["level"] != "Confirmed fraud"
    app.db.set_label("upi", "loan.desk@ybl", "confirmed_fraud", "FIR 1", "police")
    b, cached = run(app)
    assert b != a and not cached and app.db.get_case(b)["level"] == "Confirmed fraud"
    assert run(app)[0] == b                           # cached again until the next label change
    app.db.del_label("upi", "loan.desk@ybl")
    c, cached = run(app)
    assert c != b and not cached and app.db.get_case(c)["level"] != "Confirmed fraud"


def test_rule_change_and_expiry_invalidate_cache(app, monkeypatch):
    a, _ = run(app)
    monkeypatch.setattr(an, "ENGINE_VERSION", "different-rules")
    b, cached = run(app)
    assert b != a and not cached
    monkeypatch.setattr(an, "CACHE_TTL", 0)
    assert run(app)[0] != b


def test_apk_cache_skips_parsing(app, monkeypatch):
    blob = open(os.path.join(FIX, "fake_sbi.apk"), "rb").read()
    calls = []
    real = an.apk_extractor.analyze_apk
    monkeypatch.setattr(an.apk_extractor, "analyze_apk", lambda p: calls.append(p) or real(p))
    a, _ = run(app, "", kind="apk", file_bytes=blob, filename="a.apk")
    b, cached = run(app, "", kind="apk", file_bytes=blob, filename="renamed.apk")
    assert a == b and cached and len(calls) == 1


def test_repeat_submission_check_now_fires(app):
    for _ in range(3):
        run(app)                                       # 1 case + 2 cache hits
    cid, _ = run(app, fresh=True)
    fired = {f["check_id"]: f["detail"] for f in app.db.get_case(cid)["findings"] if f["status"] == "fired"}
    assert "citizen_repeat_submissions" in fired and "3 time" in fired["citizen_repeat_submissions"]


def test_heatlist_counts_repeats(app):
    for _ in range(3):
        run(app)
    row = next(r for r in app.db.heatlist(20) if r["value"] == "loan.desk@ybl")
    assert row["n"] == 1 and row["seen"] == 3


# ---------- endpoints ----------
def test_ui_cached_flag_and_recheck(app):
    c = app.test_client()
    r1 = c.post("/api/ui/analyze", data={"kind": "message", "text": SMS}).get_json()
    r2 = c.post("/api/ui/analyze", data={"kind": "message", "text": SMS}).get_json()
    assert r1["id"] == r2["id"] and not r1["cached"] and r2["cached"]
    assert c.get(f"/api/ui/case/{r1['id']}").get_json()["times_checked"] == 2
    r3 = c.post("/api/ui/analyze", data={"kind": "message", "text": SMS, "fresh": "1"}).get_json()
    assert r3["id"] != r1["id"]
    new = c.post(f"/api/ui/case/{r1['id']}/recheck").get_json()["id"]
    assert new not in (r1["id"], r3["id"])
    apk = an.analyze(app.db, "apk", file_bytes=open(os.path.join(FIX, "benign.apk"), "rb").read(), filename="b.apk")
    assert "Upload the app again" in c.post(f"/api/ui/case/{apk}/recheck").get_json()["error"]


def test_api_v1_cached_flag(app):
    c = app.test_client()
    h = {"X-API-Key": "k"}
    a = c.post("/api/v1/analyze", json={"text": SMS}, headers=h).get_json()
    b = c.post("/api/v1/analyze", json={"text": SMS}, headers=h).get_json()
    assert a["case_id"] == b["case_id"] and b["cached"] and b["times_checked"] == 2
    assert c.post("/api/v1/analyze", json={"text": SMS, "fresh": 1}, headers=h).get_json()["case_id"] != a["case_id"]


# ---------- online-lookup cache ----------
@pytest.fixture()
def nc(tmp_path, monkeypatch):
    monkeypatch.setattr(netcache, "PATH", str(tmp_path / "net.db"))
    monkeypatch.setenv("PS01_NETWORK", "1")
    return netcache


def test_dns_answers_are_cached(nc, monkeypatch):
    import dns.resolver
    calls = []

    def fake(dom, rtype, lifetime=4):
        calls.append(dom)
        raise dns.resolver.NXDOMAIN()
    monkeypatch.setattr(dns.resolver, "resolve", fake)
    assert nc.dns_status("gone.example", "A") == "nxdomain"
    assert nc.dns_status("GONE.example", "A") == "nxdomain"
    assert len(calls) == 1


def test_errors_are_not_cached(nc, monkeypatch):
    import dns.resolver
    calls = []

    def fake(dom, rtype, lifetime=4):
        calls.append(dom)
        raise dns.resolver.LifetimeTimeout()
    monkeypatch.setattr(dns.resolver, "resolve", fake)
    for _ in range(2):
        with pytest.raises(Exception):
            nc.dns_status("slow.example", "A")
    assert len(calls) == 2


def test_cache_only_mode(nc, monkeypatch):
    nc.put("dns:A:known.example", "ok")
    monkeypatch.setenv("PS01_NETWORK", "cache")
    assert nc.dns_status("known.example", "A") == "ok"
    with pytest.raises(nc.Offline):
        nc.dns_status("unknown.example", "A")


def test_page_fetch_and_rdap_cached(nc, monkeypatch):
    from core.checks.web import fetcher
    from core.checks.url import common
    calls = []
    monkeypatch.setattr(fetcher, "fetch_bytes", lambda url, *a, **k: calls.append(url) or ("https://x.test/", b"<p>hi</p>", ["https://x.test/"], "utf-8"))
    assert fetcher.safe_fetch("https://x.test/")[1] == "<p>hi</p>"
    assert fetcher.safe_fetch("https://x.test/")[1] == "<p>hi</p>" and len(calls) == 1
    monkeypatch.setenv("PS01_NETWORK", "cache")
    with pytest.raises(fetcher.FetchError):
        fetcher.safe_fetch("https://never-fetched.test/")

    monkeypatch.setenv("PS01_NETWORK", "1")

    class R:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"events": [{"eventAction": "registration", "eventDate": "2026-11-01T00:00:00Z"}]}
    rd = []
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: rd.append(a) or R())
    d1, d2 = common._rdap_created("new-scam.xyz"), common._rdap_created("new-scam.xyz")
    assert d1 == d2 and d1.year == 2026 and len(rd) == 1
