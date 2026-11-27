"""Assistant: output checker, citizen tools (case, lookup, analysis, guide), police tools, endpoints. The model is stubbed."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app
from core import assistant as A
from core.analysis import analyze

PW = "pw-assist"


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("PS01_POLICE_PASSWORD", PW)
    monkeypatch.setenv("PS01_API_KEY", "k")
    a = create_app(db_path=str(tmp_path / "t.db"), network=False)
    a.config["TESTING"] = True
    return a


@pytest.fixture()
def scam(app):
    return app.db.get_case(analyze(app.db, "message", text="Your SBI account is blocked. Share the OTP now at http://sbi-kyc-update.xyz or call +923001234567"))


def fake_model(monkeypatch, reply):
    monkeypatch.setattr(A, "llm_enabled", lambda: True)
    monkeypatch.setattr(A, "llm", lambda system, user, max_tokens=180: reply)


# ---------- output checker ----------
FACTS = ["The message (case 7) was rated High. 5 of 40 checks flagged it.", "Strong sign: asks for an OTP (share the OTP)"]


@pytest.mark.parametrize("text,reason", [
    ("Please share the OTP with the caller so the bank can verify you.", "unsafe advice"),
    ("You can install AnyDesk so they can help you fix this.", "unsafe advice"),
    ("This message is safe to open and you can relax about it.", "contradicts"),
    ("It was rated High because 9 checks flagged it out of 40.", "invented number 9"),
    ("Visit sbi-help-desk.com to fix your account quickly today.", "invented link"),
    ("Sure! Here's an updated version of the answer for you.", "talked about the task"),
    ("- It is high risk\n- Do not click", "list"),
    ("Do not click it. Do not click it.", "repeated"),
])
def test_guard_rejects(text, reason):
    assert reason in (A.guard(text, FACTS, level="High") or "")


@pytest.mark.parametrize("text", [
    "The message asks you to share your OTP, which a real bank never does. Do not reply or click the link.",
    "Never share an OTP with anyone. This message was rated High, so do not open the link and call 1930 if you paid.",
])
def test_guard_accepts_good_answers(text):
    assert A.guard(text, FACTS, level="High") is None


def test_guard_low_risk_must_not_call_it_a_scam():
    assert "contradicts" in A.guard("This link is a scam and you should report it now.", FACTS, level="Low")


def test_clean_strips_role_labels():
    assert A.clean("It is risky, do not click it.\nUser: thanks\nAssistant: ok") == "It is risky, do not click it."


# ---------- citizen: case questions ----------
def test_case_answers_by_intent(scam):
    assert A.answer_case(scam, "Why is this risky?", use_llm=False)["answer"].startswith("It is rated High because")
    safe = A.answer_case(scam, "Is it safe to click the link?", use_llm=False)
    assert safe["answer"].startswith("No.") and safe["intent"] == "safety"
    assert "1930" in A.answer_case(scam, "I already paid, what now?", use_llm=False)["answer"]
    assert "Report to police" in A.answer_case(scam, "how do I report it", use_llm=False)["answer"]
    r = A.answer_case(scam, "Why?", use_llm=False)
    assert r["polish"] == {"case_id": scam["id"], "message": "Why?"} and r["source"] == "rules"


def test_case_answer_in_hindi_never_uses_the_model(scam, monkeypatch):
    fake_model(monkeypatch, "This should not be used at all, it is English.")
    r = A.answer_case(scam, "यह खतरनाक क्यों है?", lang="hi")
    assert "उच्च जोखिम" in r["answer"] and r["source"] == "rules" and r["polish"] is None


def test_good_model_reply_is_used(scam, monkeypatch):
    fake_model(monkeypatch, "No, do not open it. The message asks for your OTP and the link only pretends to be SBI.")
    r = A.answer_case(scam, "Is it safe to click?")
    assert r["source"] == "ai" and r["answer"].startswith("No, do not open it")


def test_bad_model_reply_falls_back(scam, monkeypatch):
    fake_model(monkeypatch, "Yes, it is safe. Just share the OTP with them and the issue will be solved.")
    r = A.answer_case(scam, "Is it safe to click?")
    assert r["source"] == "rules" and r["answer"].startswith("No.") and "rejected" in r["note"]


def test_model_down_falls_back(scam, monkeypatch):
    monkeypatch.setattr(A, "llm_enabled", lambda: True)
    monkeypatch.setattr(A, "OLLAMA", "http://127.0.0.1:9")   # nothing listens there
    r = A.answer_case(scam, "why")
    assert r["source"] == "rules" and "unavailable" in r["note"]


# ---------- citizen: general chat (agent tools) ----------
def test_general_lookup_tool(app, scam):
    r = A.answer_general(app.db, "+923001234567", use_llm=False)
    assert r["action"] == "lookup" and r["lookup"]["cases"] == 1 and scam["id"] in r["case_ids"]
    app.db.set_label("phone", "+923001234567", "confirmed_fraud", "", "police")
    assert "confirmed fraud" in A.answer_general(app.db, "+923001234567", use_llm=False)["answer"]


def test_general_analysis_tool_creates_a_case(app):
    calls = []
    run = lambda kind, text: calls.append(kind) or analyze(app.db, kind, text=text)
    r = A.answer_general(app.db, "Pay Rs 500 registration to taskpay.help@ybl and like YouTube videos to earn daily", run_analysis=run, use_llm=False)
    assert r["action"] == "analyzed" and calls == ["message"] and app.db.get_case(r["case_id"])
    assert r["polish"]["case_id"] == r["case_id"]       # the AI follow-up asks about the case, it does not re-analyse


def test_general_guide_and_help(app):
    assert A.answer_general(app.db, "someone asked me to install anydesk", use_llm=False)["topic"] == "remote"
    assert A.answer_general(app.db, "what is digital arrest", lang="hi", use_llm=False)["answer"].startswith("'डिजिटल अरेस्ट'")
    assert A.answer_general(app.db, "hello", use_llm=False)["action"] == "smalltalk"
    assert A.answer_general(app.db, "zxqv plorb wint", use_llm=False)["action"] == "help"


# ---------- police tools ----------
def test_police_tools(app, scam):
    cid = scam["id"]
    analyze(app.db, "url", text="http://sbi-kyc-update.xyz/login")
    db = app.db
    assert A.answer_police(db, "summary of today")["tool"] == "stats"
    c = A.answer_police(db, f"case {cid}")
    assert c["tool"] == "case" and f"case {cid}" in c["answer"] and c["source"] == "rules"
    l = A.answer_police(db, f"cases linked to {cid}")
    assert l["tool"] == "linked" and "sbi-kyc-update.xyz" in l["answer"]
    assert A.answer_police(db, f"links for #{cid}")["tool"] == "linked"
    assert A.answer_police(db, "+923001234567")["tool"] == "identifier"
    assert A.answer_police(db, "top reported identifiers")["items"]
    assert A.answer_police(db, "campaigns")["tool"] == "campaigns"
    assert A.answer_police(db, "open citizen reports")["tool"] == "queue"
    assert A.answer_police(db, "case 99999")["answer"] == "There is no case #99999."
    assert A.answer_police(db, "who won the match")["tool"] == "help"


def test_police_never_uses_small_model_by_default(app, scam, monkeypatch):
    fake_model(monkeypatch, "There are 999 cases today and all are solved.")
    r = A.answer_police(app.db, "summary of today")
    assert r["source"] == "rules" and "999" not in r["answer"] and r["polish"] is None


# ---------- endpoints ----------
def _csrf(c):
    return c.get("/api/ui/session").get_json()["csrf"]


def test_ui_endpoint_citizen_and_police(app, scam):
    c = app.test_client()
    h = {"X-CSRF-Token": _csrf(c)}
    r = c.post("/api/ui/assistant", json={"message": "Why is this risky?", "case_id": scam["id"]}, headers=h).get_json()
    assert r["source"] == "rules" and r["case_id"] == scam["id"]
    assert c.post("/api/ui/assistant", json={"message": "x", "case_id": 99999}, headers=h).status_code == 404
    assert c.post("/api/ui/assistant", json={"message": ""}, headers=h).status_code == 400
    assert c.post("/api/ui/assistant", json={"message": "summary", "mode": "police"}, headers=h).status_code == 401
    assert c.post("/api/ui/assistant", json={"message": "hi"}).status_code == 400            # CSRF still enforced
    t = c.post("/api/ui/login", json={"username": "police", "password": PW}, headers=h).get_json()["csrf"]
    r = c.post("/api/ui/assistant", json={"message": "summary of today", "mode": "police"}, headers={"X-CSRF-Token": t}).get_json()
    assert r["tool"] == "stats"
    assert any(a["action"] == "assistant" for a in app.db.audit())
    assert "available" in c.get("/api/ui/assistant/status").get_json()


def test_api_endpoint_for_extension(app, scam):
    c = app.test_client()
    assert c.post("/api/v1/assistant", json={"message": "why"}).status_code == 401
    r = c.post("/api/v1/assistant", json={"message": "What should I do now?", "case_id": scam["id"]}, headers={"X-API-Key": "k"}).get_json()
    assert "1930" in r["answer"]
    r = c.post("/api/v1/assistant", json={"message": "how do I report a fraud"}, headers={"X-API-Key": "k"}).get_json()
    assert r["topic"] == "report"
    assert c.get("/api/v1/assistant/status").status_code == 200


def test_model_may_not_answer_yes_to_a_trust_question(scam, monkeypatch):
    fake_model(monkeypatch, "Yes, but do not click the link, pay, or share any OTP. The message is high-risk.")
    r = A.answer_case(scam, "Can I trust this message?")
    assert r["source"] == "rules" and r["answer"].startswith("No.") and "answered yes" in r["note"]


# ---------- small talk, open questions, single-call flow ----------
from core.assistant_service import run as svc_run


@pytest.mark.parametrize("msg", ["hello", "Hi!", "namaste", "thanks", "thank you", "ok", "who are you", "नमस्ते"])
def test_small_talk_never_returns_case_data(app, scam, msg):
    for data in ({"message": msg}, {"message": msg, "case_id": scam["id"]}):
        r = svc_run(app.db, data)
        assert r["action"] == "smalltalk" and "checks flagged" not in r["answer"]


def test_general_question_on_result_page_uses_guide_not_case(app, scam):
    r = svc_run(app.db, {"message": "what is digital arrest", "case_id": scam["id"]})
    assert r["action"] == "faq" and r["topic"] == "digital_arrest"
    assert svc_run(app.db, {"message": "why is this risky?", "case_id": scam["id"]})["intent"] == "why"
    assert svc_run(app.db, {"message": "tell me more please", "case_id": scam["id"]})["case_id"] == scam["id"]


def test_open_question_answered_by_model_and_checked(app, monkeypatch):
    fake_model(monkeypatch, "Phishing is when fraudsters pretend to be a bank or company to trick you into giving passwords or OTPs. Never share them.")
    r = svc_run(app.db, {"message": "what is phishing", "ai": 1}, ai=True)
    assert r["action"] == "open" and r["source"] == "ai" and r["answer"].startswith("Phishing")
    fake_model(monkeypatch, "Call 98765 43210 or visit sbi-help.in to get your money back quickly.")
    r = svc_run(app.db, {"message": "what is phishing"}, ai=True)
    assert r["action"] == "help" and r["source"] == "rules"     # invented number / link -> rejected


def test_single_call_analyses_once_and_uses_model(app, monkeypatch):
    fake_model(monkeypatch, "Do not reply. The message asks for your OTP and uses a fake bank link, so it is a scam attempt.")
    before = app.db.stats()["total"]
    r = svc_run(app.db, {"message": "Your SBI account is blocked, share OTP at http://sbi-kyc-update.xyz now"}, ai=True)
    assert r["action"] == "analyzed" and r["source"] == "ai" and app.db.stats()["total"] == before + 1
