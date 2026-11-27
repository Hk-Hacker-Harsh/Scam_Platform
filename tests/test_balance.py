"""Weight balancing, UPI extraction precision and the self-linking feedback loop (portfolio site went Medium -> High)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app
from core.analysis import analyze
from core.engine import verdict
from core.extract import extract_all


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("PS01_POLICE_PASSWORD", "pw-123")
    monkeypatch.setenv("PS01_API_KEY", "k")
    a = create_app(db_path=str(tmp_path / "t.db"), network=False)
    a.config["TESTING"] = True
    return a


def r(cid, tier, w, status="fired"):
    return dict(id=cid, group="X", tier=tier, weight=w, desc="", status=status, detail="d")


CLEAR = [r(f"c{i}", "S", 10, "clear") for i in range(5)]


# ---------- UPI extraction ----------
@pytest.mark.parametrize("text,upis", [
    ("Portfolio by Harsh. Find me harsh@portfolio on GitHub", []),
    ("scheduler@b8488ee2c322 started", []),
    ("Pay the fee to loan.desk@ybl now", ["loan.desk@ybl"]),
    ("Send payment on UPI to refund.help@abcd", ["refund.help@abcd"]),     # unknown handle but clearly UPI: kept
    ("यूपीआई आईडी: sbi.care@xyzbank पर भुगतान करें", ["sbi.care@xyzbank"]),
])
def test_upi_extraction_precision(text, upis):
    assert extract_all(text)["upis"] == upis


# ---------- verdict rule ----------
def test_single_ordinary_hard_signal_caps_at_medium():
    v = verdict([r("userinfo_at_trick", "H", 40), r("x", "S", 10)] + CLEAR)
    assert v["level"] == "Medium" and "nothing else backs it up" in v["why"]


def test_decisive_hard_signal_alone_is_high():
    assert verdict([r("otp_pin_request", "H", 45)] + CLEAR)["level"] == "High"


def test_two_hard_signals_are_high():
    assert verdict([r("a", "H", 35), r("b", "H", 30)] + CLEAR)["level"] == "High"


def test_one_hard_backed_by_soft_is_high():
    assert verdict([r("a", "H", 35), r("s1", "S", 20), r("s2", "S", 20)] + CLEAR)["level"] == "High"


def test_soft_only_still_caps_at_medium():
    assert verdict([r(f"s{i}", "S", 40) for i in range(5)] + CLEAR)["level"] == "Medium"


# ---------- the portfolio case ----------
PORTFOLIO = "<html><title>Harsh Khandal</title><body>Developer portfolio. Contact harsh@portfolio · projects · blog</body></html>"


def test_portfolio_rescans_do_not_escalate(app):
    levels = []
    for _ in range(3):
        c = app.db.get_case(analyze(app.db, "url", text="harshkhandal.dev", page_html=PORTFOLIO))
        levels.append(c["level"])
        fired = {f["check_id"] for f in c["findings"] if f["status"] == "fired"}
        assert not {"upi_handle_valid", "identifier_linking_campaigns", "repeat_cases_linked"} & fired
        assert "upi" not in {i["type"] for i in c["ids"]}
    assert "High" not in levels


def test_cross_kind_link_still_works(app):
    """A scam SMS that was High on its own merits still links a later scan of the site it pointed to."""
    sms = app.db.get_case(analyze(app.db, "message", text="Share your OTP to unblock SBI account: http://sbi-unblock-help.xyz/login"))
    assert sms["level"] == "High"
    site = app.db.get_case(analyze(app.db, "url", text="http://sbi-unblock-help.xyz/login"))
    assert "identifier_linking_campaigns" in {f["check_id"] for f in site["findings"] if f["status"] == "fired"}


def test_linked_high_must_be_earned(app):
    """A High that came only from linking does not spread to further cases."""
    from core.checks.intelligence.common import earned_high
    a = analyze(app.db, "message", text="Share OTP now, SBI KYC blocked. Call 9123456780")
    b = app.db.save_case("message", "t", "only linked", dict(level="High", score=50, hard=1, ran=5, basis="rules", why="x"),
                         [r("identifier_linking_campaigns", "H", 35)], [("phone", "+919000000001")])
    assert earned_high(app.db, [a, b]) == {a}
