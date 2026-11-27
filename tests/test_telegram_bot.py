"""Telegram bot against the real Flask app. Only Telegram itself is replaced by a recorder (no network, no token)."""
import io
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bots"))
from app import create_app
import telegram_bot as tb

KEY = "bot-test-key"


class FakeResp:
    def __init__(self, r):
        self.status_code, self.content = r.status_code, r.data

    def json(self):
        import json
        return json.loads(self.content)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise tb.requests.HTTPError(str(self.status_code))


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("PS01_POLICE_PASSWORD", "pw")
    monkeypatch.setenv("PS01_API_KEY", KEY)
    app = create_app(db_path=str(tmp_path / "t.db"), network=False)
    client = app.test_client()
    bot = tb.Bot("000:not-a-real-token", KEY)
    sent, calls = [], []

    def fake_request(method, url, headers=None, timeout=None, json=None, data=None, files=None, params=None):
        path = url.replace(tb.API_URL, "")
        kw = dict(headers=headers, query_string=params)
        if json is not None:
            kw["json"] = json
        if data is not None or files:
            form = dict(data or {})
            for k, (name, blob) in (files or {}).items():
                form[k] = (io.BytesIO(blob), name)
            kw["data"], kw["content_type"] = form, "multipart/form-data"
        return FakeResp(client.open(path, method=method, **kw))

    def fake_tg(method, files=None, **p):
        calls.append((method, p, files))
        if method == "getFile":
            return {"ok": True, "result": {"file_path": "x"}}
        return {"ok": True, "result": {}}

    monkeypatch.setattr(bot.s, "request", fake_request)
    monkeypatch.setattr(bot, "tg", fake_tg)
    monkeypatch.setattr(bot, "send", lambda chat, text, reply_to=None, buttons=None: sent.append((text, buttons)))
    return app, bot, sent, calls


def msg(text=None, **kw):
    m = {"chat": {"id": 42}, "message_id": 1}
    if text is not None:
        m["text"] = text
    m.update(kw)
    return m


def test_help_and_unknown_command(env):
    _, bot, sent, _ = env
    bot.handle(msg("/start"))
    assert "1930" in sent[-1][0] and "/lookup" in sent[-1][0]
    bot.handle(msg("/help@SatarkBot"))
    assert "1930" in sent[-1][0]
    bot.handle(msg("/foo"))
    assert "Unknown command" in sent[-1][0]


def test_scam_text_gets_verdict_meter_and_buttons(env):
    app, bot, sent, _ = env
    bot.handle(msg("Your SBI account is blocked. Share OTP now at http://sbi-kyc-update.xyz <b>x</b>"))
    text, buttons = sent[-1]
    assert "High risk" in text and "checks flagged" in text and "1930" in text
    assert "<b>x</b>" not in text                      # scam text is escaped, never Telegram HTML
    data = [b["callback_data"] for row in buttons for b in row if "callback_data" in b]
    assert data[0].startswith("rep:") and data[1].startswith("pdf:")
    cid = int(data[0].split(":")[1])
    assert app.db.get_case(cid)["source"] == "telegram"


def test_report_button_adds_to_review_queue_once(env):
    app, bot, sent, calls = env
    bot.handle(msg("Share your OTP to unblock your account"))
    cid = int(sent[-1][1][0][0]["callback_data"].split(":")[1])
    q = {"id": "q1", "data": f"rep:{cid}", "message": {"chat": {"id": 42}}}
    bot.handle_callback(q)
    c = app.db.get_case(cid)
    assert c["flagged"] and c["reports"][0]["note"].startswith("[telegram]")
    bot.handle_callback(q)
    assert len(app.db.get_case(cid)["reports"]) == 1
    assert any(m == "answerCallbackQuery" and "Already reported" in p.get("text", "") for m, p, _ in calls)


def test_buttons_only_work_for_own_cases(env):
    app, bot, sent, calls = env
    bot.handle(msg("Share your OTP now"))
    cid = int(sent[-1][1][0][0]["callback_data"].split(":")[1])
    bot.handle_callback({"id": "q2", "data": f"rep:{cid}", "message": {"chat": {"id": 999}}})   # another chat
    assert not app.db.get_case(cid)["flagged"]
    assert "expired" in calls[-1][1]["text"]


def test_pdf_button_sends_document(env):
    _, bot, sent, calls = env
    bot.handle(msg("Install AnyDesk and share the OTP"))
    cid = int(sent[-1][1][0][1]["callback_data"].split(":")[1])
    bot.handle_callback({"id": "q3", "data": f"pdf:{cid}", "message": {"chat": {"id": 42}}})
    doc = [c for c in calls if c[0] == "sendDocument"][-1]
    name, blob, mime = doc[2]["document"]
    assert blob.startswith(b"%PDF") and mime == "application/pdf" and str(cid) in name


def test_photo_with_qr(env, monkeypatch):
    qrcode = pytest.importorskip("qrcode")
    b = io.BytesIO()
    qrcode.make("upi://pay?pa=sbi.refund@ybl&am=999").save(b, format="PNG")
    _, bot, sent, _ = env
    monkeypatch.setattr(bot, "download", lambda fid, size: b.getvalue())
    bot.handle(msg(caption="Scan to receive your refund", photo=[{"file_id": "small"}, {"file_id": "big", "file_size": 1000}]))
    assert "High risk" in sent[-1][0] and "sbi.refund@ybl" in sent[-1][0]


def test_rejects_unsupported_document(env):
    _, bot, sent, _ = env
    bot.handle(msg(document={"file_id": "f", "file_name": "notes.docx"}))
    assert ".apk" in sent[-1][0]


def test_rate_limit_per_chat(env, monkeypatch):
    _, bot, sent, _ = env
    monkeypatch.setattr(tb, "RATE", 2)
    for _ in range(3):
        bot.handle(msg("hello there friend"))
    assert "wait" in sent[-1][0]


def test_lookup(env):
    app, bot, sent, _ = env
    bot.handle(msg("Pay the fee to loan.desk@ybl"))
    assert "1 checked case" in bot.lookup("loan.desk@ybl")
    app.db.set_label("upi", "loan.desk@ybl", "confirmed_fraud", "", "police")
    assert "confirmed fraud" in bot.lookup("loan.desk@ybl")
    assert "not been seen" in bot.lookup("never-seen-site.xyz")
    assert "Usage" in bot.lookup("")


def test_links_only_with_public_https_url(monkeypatch):
    j = {"case_id": 7, "level": "Low", "why": "w", "reasons": [], "identifiers": [], "advice": {"en": ["a"], "hi": ["b"]}, "meter": {"flagged": 0, "ran": 9}}
    monkeypatch.setattr(tb, "PUBLIC_URL", "")
    assert "href" not in tb.format_result(j) and len(tb.result_buttons(j)) == 1
    monkeypatch.setattr(tb, "PUBLIC_URL", "https://satark.example.dev")
    assert "https://satark.example.dev/r/7" in tb.format_result(j)
    assert tb.result_buttons(j)[1][0]["url"] == "https://satark.example.dev/r/7"
