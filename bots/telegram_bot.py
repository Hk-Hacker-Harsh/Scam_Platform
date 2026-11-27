"""Satark Telegram bot (long polling; needs only `requests`).

Citizens send or forward a message, a link, a screenshot / QR photo, an .apk or an .eml. The bot sends it to the
Satark API and replies with the risk level, the detection count, the reasons and what to do (English + Hindi).
Buttons under each result: "Report to police" (adds it to the officer review queue) and "PDF report".

Setup (the Flask app must be running):
  1. Create a bot with @BotFather and copy its token.
  2. Save the token in instance/telegram_token.txt (one line), or set TELEGRAM_BOT_TOKEN.
     The token is only read from there; it is never printed or logged.
  3. python bots/telegram_bot.py
Optional settings:
  PS01_API_URL     Satark server (default http://127.0.0.1:5000)
  PS01_API_KEY     API key (default: instance/api_key.txt)
  PS01_PUBLIC_URL  public https address of the web app; when set, replies include a link to the full result
  PS01_BOT_RATE    analyses per chat per minute (default 6)
"""
import html
import os
import sys
import time
from collections import defaultdict, deque

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_URL = os.environ.get("PS01_API_URL", "http://127.0.0.1:5000").rstrip("/")
PUBLIC_URL = os.environ.get("PS01_PUBLIC_URL", "").rstrip("/")
RATE = int(os.environ.get("PS01_BOT_RATE", "6"))
MAX_FILE = 20 * 1024 * 1024   # Telegram bots can download files up to 20 MB
EMOJI = {"High": "🔴", "Confirmed fraud": "⛔", "Medium": "🟠", "Low": "🟢", "Verified official": "🔵", "Not enough data": "⚪"}
COMMANDS = [{"command": "start", "description": "How to use the scam checker"},
            {"command": "help", "description": "How to use the scam checker"},
            {"command": "lookup", "description": "Has a phone, UPI ID or website been reported?"}]

HELP = ("<b>Satark – check before you trust</b>\n"
        "Send or forward me any of these:\n"
        "• a suspicious SMS / WhatsApp message\n• a link or website\n• a screenshot or a photo of a QR code\n• an .apk file or an .eml e-mail\n\n"
        "I reply with the risk level, how many checks flagged it, the reasons and what to do. "
        "Use the buttons under a result to report it to the police team or get a PDF report.\n"
        "/lookup &lt;phone | UPI ID | website&gt; – has it been reported?\n\n"
        "मुझे कोई भी संदिग्ध मैसेज, लिंक, स्क्रीनशॉट, QR कोड या APK भेजें। मैं बताऊंगा कि यह धोखा है या नहीं।\n"
        "पैसे कट गए हों तो तुरंत <b>1930</b> पर कॉल करें या cybercrime.gov.in पर शिकायत करें।")


class Bot:
    def __init__(self, token, api_key):
        self._base = f"https://api.telegram.org/bot{token}"
        self._file_base = f"https://api.telegram.org/file/bot{token}"
        self.api_key = api_key
        self.s = requests.Session()
        self.hits = defaultdict(deque)
        self.mine = defaultdict(set)      # chat id -> case ids this chat created (buttons only act on these)
        self.reported = set()

    # ---------- Telegram ----------
    def tg(self, method, files=None, **params):
        try:
            if files:
                r = self.s.post(f"{self._base}/{method}", data=params, files=files, timeout=60)
            else:
                r = self.s.post(f"{self._base}/{method}", json=params, timeout=40)
            return r.json()
        except requests.RequestException as e:
            print(f"telegram {method} failed: {type(e).__name__}", file=sys.stderr)  # never the URL: it holds the token
            return {"ok": False}

    def send(self, chat_id, text, reply_to=None, buttons=None):
        p = dict(chat_id=chat_id, text=text[:4000], parse_mode="HTML", disable_web_page_preview=True)
        if reply_to:
            p["reply_parameters"] = {"message_id": reply_to, "allow_sending_without_reply": True}
        if buttons:
            p["reply_markup"] = {"inline_keyboard": buttons}
        return self.tg("sendMessage", **p)

    def download(self, file_id, size):
        if size and size > MAX_FILE:
            raise ValueError("The file is larger than 20 MB, which Telegram bots cannot download.")
        info = self.tg("getFile", file_id=file_id)
        if not info.get("ok"):
            raise ValueError("Could not get the file from Telegram.")
        r = self.s.get(f"{self._file_base}/{info['result']['file_path']}", timeout=60)
        r.raise_for_status()
        return r.content

    # ---------- Satark API ----------
    def api(self, method, path, raw=False, **kw):
        h = {"X-API-Key": self.api_key, "X-Client": "telegram"}
        r = self.s.request(method, API_URL + path, headers=h, timeout=180, **kw)
        if raw:
            r.raise_for_status()
            return r.content
        try:
            j = r.json()
        except ValueError:
            j = {"error": f"server error {r.status_code}"}
        if r.status_code >= 400:
            raise ValueError(j.get("error") or f"server error {r.status_code}")
        return j

    def limited(self, chat):
        now, q = time.time(), self.hits[chat]
        while q and q[0] < now - 60:
            q.popleft()
        if len(q) >= RATE:
            return True
        q.append(now)
        return False

    # ---------- handlers ----------
    def handle(self, m):
        chat, mid = m["chat"]["id"], m.get("message_id")
        text = (m.get("text") or m.get("caption") or "").strip()
        cmd = text.split()[0].split("@")[0].lower() if text.startswith("/") else ""
        if cmd in ("/start", "/help"):
            return self.send(chat, HELP)
        if cmd == "/lookup":
            return self.send(chat, self.lookup(text.split(None, 1)[1].strip() if " " in text else ""), mid)
        if cmd:
            return self.send(chat, "Unknown command. Send a message, link, screenshot or .apk to check it. /help", mid)
        if not (text or m.get("photo") or m.get("document")):
            return self.send(chat, "Send me a message, link, screenshot or .apk to check. /help", mid)
        if self.limited(chat):
            return self.send(chat, "You have sent many checks in the last minute. Please wait a little and try again.", mid)
        self.tg("sendChatAction", chat_id=chat, action="typing")
        try:
            if m.get("photo"):
                ph = m["photo"][-1]  # largest size
                data = self.download(ph["file_id"], ph.get("file_size"))
                res = self.api("POST", "/api/v1/analyze", data={"kind": "image", "text": text}, files={"file": ("photo.jpg", data)})
            elif m.get("document"):
                d = m["document"]
                name = (d.get("file_name") or "file").lower()
                kind = "apk" if name.endswith(".apk") else "image" if name.endswith((".png", ".jpg", ".jpeg", ".webp")) else \
                    "email" if name.endswith(".eml") else None
                if not kind:
                    return self.send(chat, "Send an .apk, an .eml or an image (PNG / JPG).", mid)
                if kind == "apk":
                    self.send(chat, "Analysing the app. It is never installed or run. This can take up to a minute…", mid)
                data = self.download(d["file_id"], d.get("file_size"))
                res = self.api("POST", "/api/v1/analyze", data={"kind": kind, "text": text if kind == "image" else ""}, files={"file": (name, data)})
            else:
                res = self.api("POST", "/api/v1/analyze", json={"kind": "auto", "text": text})
        except ValueError as e:
            return self.send(chat, "Could not check this: " + html.escape(str(e)), mid)
        except requests.RequestException:
            return self.send(chat, "The Satark server is not reachable right now. Please try again later.", mid)
        self.mine[chat].add(res["case_id"])
        self.send(chat, format_result(res), mid, buttons=result_buttons(res))

    def handle_callback(self, q):
        chat = q["message"]["chat"]["id"] if q.get("message") else None
        action, _, cid = (q.get("data") or "").partition(":")
        if not chat or not cid.isdigit() or int(cid) not in self.mine[chat]:
            return self.tg("answerCallbackQuery", callback_query_id=q["id"], text="This button has expired. Send the item again.")
        cid = int(cid)
        try:
            if action == "rep":
                if (chat, cid) in self.reported:
                    return self.tg("answerCallbackQuery", callback_query_id=q["id"], text="Already reported. Thank you.")
                self.api("POST", f"/api/v1/case/{cid}/report", json={"note": "Reported from Telegram"})
                self.reported.add((chat, cid))
                self.tg("answerCallbackQuery", callback_query_id=q["id"], text="Sent to the police review queue.")
                self.send(chat, f"✅ Case #{cid} was added to the police review queue. A report raises its priority; it does not block "
                                f"anything by itself.\nपुलिस समीक्षा के लिए भेज दिया गया।\n\nIf you lost money, also call <b>1930</b>.")
            elif action == "pdf":
                self.tg("answerCallbackQuery", callback_query_id=q["id"], text="Preparing the PDF…")
                pdf = self.api("GET", f"/result/{cid}/report.pdf", raw=True)
                self.tg("sendDocument", chat_id=chat, caption=f"Satark report, case #{cid}",
                        files={"document": (f"satark-case-{cid}.pdf", pdf, "application/pdf")})
            else:
                self.tg("answerCallbackQuery", callback_query_id=q["id"])
        except (ValueError, requests.RequestException) as e:
            self.tg("answerCallbackQuery", callback_query_id=q["id"], text="Failed: " + str(e)[:150])

    def lookup(self, q):
        if not q:
            return "Usage: /lookup 9876543210  or  /lookup refund@ybl  or  /lookup example.xyz"
        t = "upi" if "@" in q and "." not in q.split("@")[1] else "email" if "@" in q else \
            "phone" if q.replace("+", "").replace(" ", "").replace("-", "").isdigit() else "domain"
        try:
            j = self.api("GET", "/api/v1/lookup", params={"type": t, "value": q})
        except (ValueError, requests.RequestException) as e:
            return "Lookup failed: " + html.escape(str(e))
        v = html.escape(j["value"])
        if j["police_label"] == "confirmed_fraud":
            return f"⛔ <b>{v}</b> is marked <b>confirmed fraud</b> by the police team. Do not pay or share anything. Call 1930 if you lost money."
        if j["police_label"] == "verified_official":
            return f"🔵 <b>{v}</b> is marked <b>verified official</b> by the police team."
        if not j["cases_seen"]:
            return f"⚪ <b>{v}</b> has not been seen in our cases yet. That is not proof it is safe."
        return (f"🟠 <b>{v}</b> appears in {j['cases_seen']} checked case(s), {j['high_risk_cases']} of them high risk, "
                f"{j['citizen_reports']} reported by citizens. Last seen {html.escape(j['last_seen_utc'] or '-')} UTC.")

    def run(self):
        me = self.tg("getMe")
        if not me.get("ok"):
            sys.exit("Telegram rejected the token (getMe failed). Check instance/telegram_token.txt or TELEGRAM_BOT_TOKEN.")
        try:
            self.api("GET", "/api/v1/case/0")
        except ValueError as e:
            if "X-API-Key" in str(e):
                sys.exit("The Satark server rejected the API key. Check PS01_API_KEY / instance/api_key.txt.")
        except requests.RequestException:
            sys.exit(f"The Satark server is not reachable at {API_URL}. Start it first: python app.py")
        self.tg("setMyCommands", commands=COMMANDS)
        print(f"Bot @{me['result'].get('username')} running. Satark API: {API_URL}. Ctrl+C to stop.")
        offset = 0
        while True:
            upd = self.tg("getUpdates", offset=offset, timeout=30, allowed_updates=["message", "callback_query"])
            if not upd.get("ok"):
                time.sleep(3)
                continue
            for u in upd["result"]:
                offset = u["update_id"] + 1
                try:
                    if u.get("message"):
                        self.handle(u["message"])
                    elif u.get("callback_query"):
                        self.handle_callback(u["callback_query"])
                except Exception as e:  # one bad update must not stop the bot
                    print(f"handler error: {type(e).__name__}: {e}", file=sys.stderr)


def public_link(j):
    return f"{PUBLIC_URL}/r/{j['case_id']}" if PUBLIC_URL else ""


def result_buttons(j):
    rows = [[{"text": "🚩 Report to police", "callback_data": f"rep:{j['case_id']}"},
             {"text": "📄 PDF report", "callback_data": f"pdf:{j['case_id']}"}]]
    link = public_link(j)
    if link.startswith("https://"):      # Telegram only accepts public http(s) links on buttons
        rows.append([{"text": "Open full result", "url": link}])
    return rows


def format_result(j):
    e = html.escape
    lvl = j["level"]
    m = j.get("meter") or {}
    head = f"{EMOJI.get(lvl, '⚪')} <b>{e(lvl)}{' risk' if lvl in ('High', 'Medium', 'Low') else ''}</b>"
    sub = f"{m.get('flagged', len(j.get('reasons', [])))} of {m.get('ran', j.get('checks_ran', 0))} checks flagged · case #{j['case_id']}"
    lines = [head, sub, e(j["why"])]
    if j.get("times_checked", 1) > 1:
        lines.append(f"<i>Seen before: this exact item has been checked {j['times_checked']} times.</i>")
    if j.get("reasons"):
        lines.append("\n<b>Why</b>")
        for r in j["reasons"][:6]:
            tag = "strong" if r["strength"] == "Hard" else "weak"
            lines.append(f"• {e(r['check'].replace('_', ' '))} ({tag}): {e(r['detail'][:160])}")
        if len(j["reasons"]) > 6:
            lines.append(f"…and {len(j['reasons']) - 6} more")
    ids = [i for i in j.get("identifiers", []) if i["type"] in ("phone", "upi", "domain", "email", "crypto")]
    if ids:
        lines.append("\n<b>Found</b>: " + ", ".join(f"{e(i['type'])} <code>{e(i['value'])}</code>" for i in ids[:8]))
    lines.append("\n<b>What to do</b>")
    lines += [f"• {e(t)}" for t in j["advice"]["en"]]
    lines.append("")
    lines += [f"• {e(t)}" for t in j["advice"]["hi"]]
    link = public_link(j)
    if link:
        lines.append(f'\n<a href="{e(link)}">Full result</a>')
    return "\n".join(lines)


def _read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return ""


if __name__ == "__main__":
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() or _read(os.path.join(ROOT, "instance", "telegram_token.txt"))
    key = os.environ.get("PS01_API_KEY", "").strip() or _read(os.path.join(ROOT, "instance", "api_key.txt"))
    if not tok:
        sys.exit("No bot token. Save it in instance/telegram_token.txt (one line) or set TELEGRAM_BOT_TOKEN.")
    if not key:
        sys.exit("No API key. Start the server once (it creates instance/api_key.txt) or set PS01_API_KEY.")
    Bot(tok, key).run()
