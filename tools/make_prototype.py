"""Build the offline, single-file Satark prototype (for the R4C action-plan submission).

What it does:
  1. Runs synthetic scam samples through the REAL engine on a throw-away database (nothing touches instance/ps01.db),
     adds a few officer labels and citizen reports, and records the real JSON answers of every page as sample data
     (frontend/src/proto/fixtures.json).
  2. Builds the Vue app in "proto" mode (`npm run build:proto`): the same screens, but the API calls are answered from
     that sample data, routing uses #/ links, and a banner offers a wireframe view.
  3. Packs the build into ONE html file (fonts, styles, scripts and the graph library inlined), so it opens offline
     by double-click: <output> (default: dist-proto/Satark_Prototype.html).

Usage (from the project folder):
    python tools/make_prototype.py                      # fixtures + build + single file
    python tools/make_prototype.py --out "C:/Users/me/Desktop/Satark_Prototype.html"
    python tools/make_prototype.py --fixtures-only
All sample data is synthetic. The local AI model is switched off here, so assistant replies are the checked answers.
"""
import argparse
import base64
import io
import json
import mimetypes
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONT = os.path.join(ROOT, "frontend")
FIXTURES = os.path.join(FRONT, "src", "proto", "fixtures.json")

# ---------------------------------------------------------------- synthetic samples (no real person's data)
MESSAGES = {
    "sbi_kyc": "SBI ALERT: Dear customer, your YONO account will be blocked today. Update KYC at http://sbi-kyc-update.xyz/login "
               "and share the OTP with our executive. Pay Rs 10 verification fee to sbi.kyc@ybl. Call +923001234567",
    "job": "Part time job! Like YouTube videos and earn Rs 3000 daily from home. Join our Telegram group t.me/earn-daily-task "
           "and pay Rs 500 registration to taskpay.help@ybl",
    "arrest": "This is CBI Mumbai. A parcel in your name with drugs and fake passports was seized by customs. You are under "
              "digital arrest. Stay on the WhatsApp video call and do not tell anyone. Call 9876501234",
    "bill": "Dear consumer, your electricity connection will be disconnected tonight at 9.30 pm as last month bill was not "
            "updated. Pay now at http://bijli-bill-pay.xyz",
    "lottery": "Congratulations! You won Rs 25 lakh in the KBC lucky draw. Pay processing fee to claim. WhatsApp +923001234567",
    "hindi": "प्रिय ग्राहक, आपका बैंक खाता 24 घंटे में बंद हो जाएगा। तुरंत KYC अपडेट करें और OTP बताएं: http://sbi-kyc-update.xyz",
    "benign": "Hi, the team meeting has moved to 4 pm tomorrow. See you in the conference room.",
    "confirmed": "Refund approved. Send Rs 1 to sbi.kyc@ybl to receive your Rs 4,999 refund today.",
}
URLS = {
    "url_trick": "http://sbi.co.in@sbi-kyc-update.xyz/login",
    "url_official": "https://www.onlinesbi.sbi",
    "url_homograph": "https://sbі-netbanking.com/verify",          # Cyrillic і
}
EMAIL = """From: "SBI Alerts" <alerts@sbi-secure-mail.xyz>
Reply-To: helpdesk.sbi@gmail.com
To: customer@example.com
Subject: Urgent: complete your KYC to avoid account suspension
Authentication-Results: mx.example.com; spf=fail smtp.mailfrom=sbi-secure-mail.xyz; dkim=none; dmarc=fail
Content-Type: text/plain; charset=utf-8

Dear customer, your account will be suspended within 24 hours. Verify your PAN and Aadhaar at
http://sbi-secure-mail.xyz/kyc and keep your OTP ready. SBI Team
"""

CITIZEN_QS = ["Why is this risky?", "Is it safe to click the link?", "What should I do now?", "How do I report it?",
              "hello", "thanks", "यह खतरनाक क्यों है?", "अब मुझे क्या करना चाहिए?", "शिकायत कैसे करें?"]
GENERAL_QS = ["How do I report a fraud?", "What is digital arrest?", "Is it safe to share an OTP?", "I lost money, what now?",
              "hello", "thanks", "who are you", "शिकायत कैसे करें?", "डिजिटल अरेस्ट क्या है?", "पैसे कट गए, क्या करूं?",
              "someone asked me to install anydesk"]


def make_fixtures():
    os.environ.update({"PS01_LLM": "0", "PS01_SPA": "0", "PS01_NETWORK": "0", "PS01_API_KEY": "proto-key",
                       "PS01_CACHE_TTL_HOURS": "0"})
    pw = secrets.token_urlsafe(12)                    # one-off officer password for the throw-away database
    os.environ["PS01_POLICE_PASSWORD"] = pw
    sys.path.insert(0, ROOT)
    from app import create_app

    tmp = tempfile.mkdtemp(prefix="satark-proto-")
    app = create_app(db_path=os.path.join(tmp, "proto.db"), network=False)
    app.config["TESTING"] = True
    app.config["TESTING_NO_CSRF"] = True
    c = app.test_client()
    ids = {}

    def analyze(key, kind, text="", file=None):
        data = {"kind": kind, "text": text}
        if file:
            data["file"] = file
        r = c.post("/api/ui/analyze", data=data, content_type="multipart/form-data")
        assert r.status_code == 200, (key, r.get_json())
        ids[key] = r.get_json()["id"]

    for k in ("sbi_kyc", "job", "arrest", "bill", "lottery", "hindi", "benign"):
        analyze(k, "message", MESSAGES[k])
    for k, u in URLS.items():
        analyze(k, "url", u)
    import qrcode
    b = io.BytesIO()
    qrcode.make("upi://pay?pa=sbi.refund@ybl&pn=SBI%20Refund&am=4999").save(b, format="PNG")
    analyze("qr", "image", "Scan this QR code to receive your SBI refund of Rs 4999", (io.BytesIO(b.getvalue()), "screenshot.png"))
    with open(os.path.join(ROOT, "tests", "fixtures", "fake_sbi.apk"), "rb") as f:
        analyze("apk", "apk", "", (io.BytesIO(f.read()), "SBI_KYC_Update.apk"))
    analyze("email", "email", EMAIL)

    # citizen reports, then an officer signs in, labels, reviews
    for k, note in (("sbi_kyc", "Received on WhatsApp from an unknown number"), ("job", "Lost Rs 1,500 after 'registration'"),
                    ("lottery", "Got this SMS twice today")):
        c.post(f"/api/ui/case/{ids[k]}/report", json={"note": note, "contact": ""})
    r = c.post("/api/ui/login", json={"username": "police", "password": pw})
    assert r.status_code == 200
    c.post(f"/api/ui/police/case/{ids['sbi_kyc']}/label", json={"type": "upi", "value": "sbi.kyc@ybl", "label": "confirmed_fraud", "note": "FIR 214/2026, Jaipur"})
    c.post(f"/api/ui/police/case/{ids['arrest']}/status", json={"status": "reviewed"})
    c.post("/api/ui/police/registry", json={"type": "domain", "value": "onlinesbi.sbi", "label": "verified_official", "note": "Official SBI net banking"})
    analyze("confirmed", "message", MESSAGES["confirmed"])           # now "Confirmed fraud" through the police label

    j = lambda u: c.get(u).get_json()
    fx = {"meta": {"note": "Synthetic sample data recorded from the real Satark engine by tools/make_prototype.py", "ids": ids},
          "session_citizen": None, "checks": j("/api/ui/checks"),
          "cases": {}, "pcases": {}, "graphs": {}, "assistant": {}}
    for cid in sorted(set(ids.values())):
        fx["cases"][str(cid)] = j(f"/api/ui/case/{cid}")
        fx["pcases"][str(cid)] = j(f"/api/ui/police/case/{cid}")
        fx["graphs"][str(cid)] = j(f"/api/ui/police/graph?case={cid}")
    fx.update(overview=j("/api/ui/police/overview"), allcases=j("/api/ui/police/cases")["rows"],
              campaigns=j("/api/ui/police/campaigns"), graph=j("/api/ui/police/graph"), graph_all=j("/api/ui/police/graph?all=1"),
              heatlist=j("/api/ui/police/heatlist"), registry=j("/api/ui/police/registry"), audit=j("/api/ui/police/audit"),
              status={"available": True, "model": "qwen3:1.7b", "police_ai": False, "reason": ""})
    for row in fx["allcases"]:
        row.pop("content", None)        # list rows do not need the stored input

    n_ask = [0]

    def ask(mode, msg, case_id=None, lang="en"):
        body = {"message": msg, "mode": mode, "lang": lang}
        if case_id:
            body["case_id"] = case_id
        n_ask[0] += 1      # one client address per recorded question, so the per-minute rate limit does not trip
        r = c.post("/api/ui/assistant", json=body, environ_base={"REMOTE_ADDR": f"10.9.{n_ask[0] // 200}.{n_ask[0] % 200 + 1}"})
        out = r.get_json()
        assert r.status_code == 200 and "error" not in out, (msg, out)
        return out
    A = fx["assistant"]
    for cid in sorted(set(ids.values())):
        for q in CITIZEN_QS:
            A[f"citizen|{cid}|{q.lower()}"] = ask("citizen", q, cid, "hi" if re.search("[\u0900-\u097F]", q) else "en")
    for q in GENERAL_QS:
        A[f"citizen||{q.lower()}"] = ask("citizen", q, None, "hi" if re.search("[\u0900-\u097F]", q) else "en")
    for q in ["Summary of today", "Top reported identifiers", "Campaigns", "Latest high-risk cases", "Open citizen reports"]:
        A[f"police||{q.lower()}"] = ask("police", q)
    for cid in sorted(set(ids.values())):
        for q in (f"Summarise case {cid}", f"Cases linked to {cid}"):
            A[f"police||{q.lower()}"] = ask("police", q)

    os.makedirs(os.path.dirname(FIXTURES), exist_ok=True)
    with open(FIXTURES, "w", encoding="utf-8") as f:
        json.dump(fx, f, ensure_ascii=False, separators=(",", ":"))
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"fixtures: {len(fx['cases'])} cases, {len(A)} assistant answers -> {os.path.relpath(FIXTURES, ROOT)} "
          f"({os.path.getsize(FIXTURES) // 1024} KB)")


# ---------------------------------------------------------------- build + pack into one html file
def build():
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    subprocess.run([npm, "run", "build:proto"], cwd=FRONT, check=True, shell=os.name == "nt")


def pack(out):
    dist = os.path.join(FRONT, "dist-proto")
    html = open(os.path.join(dist, "index.html"), encoding="utf-8").read()

    def data_uri(path):
        mime = mimetypes.guess_type(path)[0] or ("font/woff2" if path.endswith(".woff2") else "application/octet-stream")
        return f"data:{mime};base64," + base64.b64encode(open(path, "rb").read()).decode()

    def local(ref, base_dir):
        # "./assets/x", "/assets/x" or "x" (relative to the file that mentions it)
        ref = ref.strip("'\"")
        return os.path.normpath(os.path.join(dist, ref.lstrip("/")) if ref.startswith("/") else os.path.join(base_dir, ref))

    def inline_css(m):
        path = local(m.group(1), dist)
        css = open(path, encoding="utf-8").read()
        # keep only the woff2 fonts (smaller); drop the woff fallbacks, then inline the rest
        css = re.sub(r",\s*url\([^)]+\.woff\)\s*format\([\"']woff[\"']\)", "", css)
        css = re.sub(r"url\(([^)]+\.woff2)\)", lambda u: f"url({data_uri(local(u.group(1), os.path.dirname(path)))})", css)
        return f"<style>{css}</style>"

    def inline_js(m):
        js = open(local(m.group(1), dist), encoding="utf-8").read()
        js = js.replace("</script", "<\\/script")
        return f'<script type="module">{js}</script>'

    html = re.sub(r'<link rel="stylesheet"[^>]*href="([^"]+)"[^>]*>', inline_css, html)
    html = re.sub(r'<script type="module"[^>]*src="([^"]+)"[^>]*></script>', inline_js, html)
    left = re.findall(r'(?:src|href)="(\./assets/[^"]+)"', html)
    assert not left, f"not inlined: {left}"
    cy = open(os.path.join(ROOT, "static", "cytoscape.min.js"), encoding="utf-8").read()
    html = html.replace("</head>", f"<script>{cy}</script>\n</head>", 1)     # graph library, offline
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"prototype: {out} ({os.path.getsize(out) // 1024} KB, works offline)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(FRONT, "dist-proto", "Satark_Prototype.html"))
    ap.add_argument("--fixtures-only", action="store_true")
    a = ap.parse_args()
    make_fixtures()
    if not a.fixtures_only:
        build()
        pack(a.out)
