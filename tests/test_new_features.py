"""API, screenshot / QR input, Hindi lexicon, citizen advice and the Telegram bot formatter."""
import io
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app
from core.analysis import analyze
from core.image_input import parse_upi_qr

KEY = "test-api-key"
H = {"X-API-Key": KEY}


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("PS01_POLICE_PASSWORD", "pw-123")
    monkeypatch.setenv("PS01_API_KEY", KEY)
    a = create_app(db_path=str(tmp_path / "t.db"), network=False)
    a.config["TESTING"] = True
    a.config["TESTING_NO_CSRF"] = True
    return a


@pytest.fixture()
def client(app):
    return app.test_client()


def qr_png(payload):
    qrcode = pytest.importorskip("qrcode")
    b = io.BytesIO()
    qrcode.make(payload).save(b, format="PNG")
    return b.getvalue()


def fired(app, cid):
    return {f["check_id"] for f in app.db.get_case(cid)["findings"] if f["status"] == "fired"}


# ---------- API ----------
def test_api_health_is_public(client):
    j = client.get("/api/v1/health").get_json()
    assert j["ok"] and j["checks"] >= 99 and "image" in j["kinds"]


def test_api_requires_key(client):
    assert client.post("/api/v1/analyze", json={"text": "hello"}).status_code == 401
    assert client.post("/api/v1/analyze", json={"text": "hello"}, headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.get("/api/v1/case/1").status_code == 401


def test_api_analyze_auto_message_and_url(client):
    j = client.post("/api/v1/analyze", json={"text": "Share your OTP now or your SBI account is blocked http://sbi-kyc-update.xyz"}, headers=H).get_json()
    assert j["kind"] == "message" and j["level"] == "High"
    assert any(r["check"] == "otp_pin_request" and r["strength"] == "Hard" for r in j["reasons"])
    assert j["advice"]["en"] and j["advice"]["hi"] and "1930" in j["helpline"]
    assert j["result_url"].endswith(f"/r/{j['case_id']}")
    u = client.post("/api/v1/analyze", json={"text": "https://sbi.co.in"}, headers=H).get_json()
    assert u["kind"] == "url" and u["level"] == "Verified official"
    c = client.get(f"/api/v1/case/{j['case_id']}", headers=H).get_json()
    assert c["level"] == "High"


def test_api_errors_are_json(client):
    r = client.post("/api/v1/analyze", json={"kind": "nope", "text": "x"}, headers=H)
    assert r.status_code == 400 and "kind" in r.get_json()["error"]
    r = client.post("/api/v1/analyze", json={"kind": "message", "text": ""}, headers=H)
    assert r.status_code == 400 and r.get_json()["error"]


def test_api_source_recorded(client, app):
    j = client.post("/api/v1/analyze", json={"text": "hello there friend"}, headers=dict(H, **{"X-Client": "telegram"})).get_json()
    assert app.db.get_case(j["case_id"])["source"] == "telegram"


def test_api_cors_only_for_extensions(client):
    r = client.options("/api/v1/analyze", headers={"Origin": "chrome-extension://abcdefgh", "Access-Control-Request-Method": "POST"})
    assert r.headers.get("Access-Control-Allow-Origin") == "chrome-extension://abcdefgh"
    r = client.options("/api/v1/analyze", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "Access-Control-Allow-Origin" not in r.headers


def test_api_no_csrf_needed_but_web_still_protected(tmp_path, monkeypatch):
    monkeypatch.setenv("PS01_POLICE_PASSWORD", "pw-123")
    monkeypatch.setenv("PS01_API_KEY", KEY)
    a = create_app(db_path=str(tmp_path / "c.db"), network=False)  # CSRF on
    c = a.test_client()
    assert c.post("/api/v1/analyze", json={"text": "hello friend"}, headers=H).status_code == 200
    assert c.post("/api/ui/analyze", data={"kind": "message", "text": "hello friend"}).status_code == 400   # website API needs CSRF


def test_api_rate_limit(client, monkeypatch):
    import api
    monkeypatch.setattr(api, "RATE_PER_MIN", 30)
    codes = [client.get("/api/v1/case/999999", headers=H).status_code for _ in range(32)]
    assert 429 in codes


def test_api_lookup(client, app):
    client.post("/api/v1/analyze", json={"text": "Pay processing fee to loan.desk@ybl to release your loan. Call 9876543210"}, headers=H)
    j = client.get("/api/v1/lookup", query_string={"type": "phone", "value": "98765 43210"}, headers=H).get_json()
    assert j["value"] == "+919876543210" and j["cases_seen"] == 1
    app.db.set_label("upi", "loan.desk@ybl", "confirmed_fraud", "test", "police")
    j = client.get("/api/v1/lookup", query_string={"type": "upi", "value": "LOAN.DESK@ybl"}, headers=H).get_json()
    assert j["police_label"] == "confirmed_fraud"
    assert client.get("/api/v1/lookup", query_string={"type": "bad", "value": "x"}, headers=H).status_code == 400


# ---------- screenshot / QR ----------
def test_parse_upi_qr():
    u = parse_upi_qr("upi://pay?pa=abc@ybl&pn=Shop&am=10")
    assert u == {"action": "pay", "pa": "abc@ybl", "pn": "Shop", "am": "10", "tn": "", "mode": ""}
    assert parse_upi_qr("https://x.test") is None


def test_qr_refund_trick_high(app):
    png = qr_png("upi://pay?pa=sbi.refund@ybl&pn=SBI%20Refund&am=4999")
    cid = analyze(app.db, "image", text="Scan this QR to receive your refund", file_bytes=png, filename="s.png")
    c = app.db.get_case(cid)
    assert c["kind"] == "image" and c["level"] == "High"
    assert {"qr_decode", "qr_receive_money_trick", "upi_brand_in_id"} <= fired(app, cid)
    assert ("upi", "sbi.refund@ybl") in {(i["type"], i["value"]) for i in c["ids"]}


def test_qr_link_goes_through_url_checks(app):
    cid = analyze(app.db, "image", file_bytes=qr_png("http://sbi.co.in@evil-login.xyz/kyc"), filename="q.png")
    assert {"qr_decode", "userinfo_at_trick"} <= fired(app, cid)


def test_image_without_qr_or_ocr_is_rejected(app, monkeypatch):
    import core.image_input as ii
    monkeypatch.setattr(ii, "ocr_available", lambda: False)
    cv2 = pytest.importorskip("cv2")
    import numpy as np
    ok, buf = cv2.imencode(".png", np.full((60, 60, 3), 255, np.uint8))
    with pytest.raises(ValueError, match="No text or QR"):
        analyze(app.db, "image", file_bytes=buf.tobytes(), filename="blank.png")
    with pytest.raises(ValueError, match="not a readable image"):
        analyze(app.db, "image", file_bytes=b"not an image", filename="x.png")


def test_web_screenshot_upload(client):
    r = client.post("/api/ui/analyze", data={"kind": "image", "file": (io.BytesIO(qr_png("upi://collect?pa=x1@ybl")), "q.png")},
                    content_type="multipart/form-data")
    cid = r.get_json()["id"]
    c = client.get(f"/api/ui/case/{cid}").get_json()
    assert c["kind"] == "image" and c["meta"]["image"]["qr"] == ["upi://collect?pa=x1@ybl"]
    assert any(f["id"] == "qr_decode" and f["status"] == "fired" for f in c["findings"])
    r = client.post("/api/ui/analyze", data={"kind": "image", "file": (io.BytesIO(b"x"), "notes.txt")}, content_type="multipart/form-data")
    assert r.status_code == 400 and "screenshot" in r.get_json()["error"]


def test_api_image_upload(client):
    r = client.post("/api/v1/analyze", data={"file": (io.BytesIO(qr_png("upi://collect?pa=x1@ybl")), "shot.png")},
                    headers=H, content_type="multipart/form-data")
    j = r.get_json()
    assert r.status_code == 200 and j["kind"] == "image" and any(x["check"] == "qr_decode" for x in j["reasons"])


# ---------- Hindi / Hinglish ----------
@pytest.mark.parametrize("text,check", [
    ("आपका बैंक खाता 24 घंटे में बंद हो जाएगा। तुरंत KYC अपडेट करें", "kyc_update_pretext"),
    ("कृपया अपना ओटीपी बताएं ताकि रिफंड मिल सके", "otp_pin_request"),
    ("आपके नाम से पार्सल में ड्रग्स मिले हैं, सीबीआई आपको गिरफ्तार करेगी", "digital_arrest_threat"),
    ("घर बैठे रोज कमाएं ₹3000, पार्ट टाइम नौकरी", "task_job_scam"),
    ("गारंटी के साथ 30% मुनाफा, पैसा डबल", "investment_tip_scam"),
    ("Bhai otp bhej do jaldi", "otp_pin_request"),
])
def test_hindi_patterns(app, text, check):
    assert check in fired(app, analyze(app.db, "message", text=text))


def test_hindi_otp_sms_is_high(app):
    cid = analyze(app.db, "message", text="SBI: आपका खाता बंद हो जाएगा। OTP बताएं और http://sbi-kyc-update.xyz पर KYC अपडेट करें")
    assert app.db.get_case(cid)["level"] == "High"


def test_plain_hindi_greeting_stays_low(app):
    assert app.db.get_case(analyze(app.db, "message", text="नमस्ते, कल शाम को मिलते हैं। खाना साथ में खाएंगे।"))["level"] == "Low"
