"""Satark assistant: a small, grounded agent for citizens (web + extension) and officers (dashboard).

How it stays safe with a small local model (default: Ollama `qwen3:1.7b`):
  1. Python decides what the question is about and runs the real tools (case data, analysis, identifier lookup,
     statistics, heat-list, campaigns). The model never chooses tools and never decides a verdict.
  2. Python writes a complete, correct answer from that data ("rules answer"). This is always available.
  3. The model may only rephrase that answer in plain language. Its reply is checked: it must not advise sharing an
     OTP / PIN, must not call a risky item safe (or a low-risk one a confirmed scam), must not invent numbers, links
     or phone numbers, and must not just echo the prompt. If any check fails, or Ollama is slow or off, the rules
     answer is returned instead. Every reply says which one it is.
  4. Raw scam text and page content are never sent to the model; only the checker's own findings are.

Settings (environment): PS01_LLM=0 turns the model off; PS01_LLM_MODEL (default qwen3:1.7b, ~5 s per answer; qwen3.5:4b is better but ~35 s; tinyllama replies rarely pass);
PS01_OLLAMA_URL (default http://127.0.0.1:11434); PS01_LLM_TIMEOUT seconds (default 45).
"""
import json
import os
import re
import threading
import urllib.error
import urllib.request

from .assistant_kb import FAQ, GREETING_EN, GREETING_HI
from .extract import extract_all, norm_phone, parse_url

MODEL = os.environ.get("PS01_LLM_MODEL", "qwen3:1.7b")
OLLAMA = os.environ.get("PS01_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
TIMEOUT = float(os.environ.get("PS01_LLM_TIMEOUT", "45"))
# Officer answers are exact database figures. Small models attach numbers to the wrong item, so the model is only
# used for officers when this is switched on. Measured 20 Nov: qwen3:1.7b wrote 'Today there are 5 cases. Of these, 28 are high
# risk' (real numbers, wrong relation) - the checks cannot catch that, so keep this off for small models.
LLM_POLICE = os.environ.get("PS01_LLM_POLICE", "0") == "1"
# Keep the model in memory between questions (Ollama unloads after 5 idle minutes; reloading qwen3.5:4b takes ~40 s).
KEEP_ALIVE = os.environ.get("PS01_LLM_KEEP_ALIVE", "30m")
_sem = threading.BoundedSemaphore(int(os.environ.get("PS01_LLM_CONCURRENCY", "1")))

LEVEL_HI = {"High": "उच्च जोखिम", "Confirmed fraud": "पुष्ट धोखा", "Medium": "मध्यम जोखिम", "Low": "कम जोखिम",
            "Verified official": "सत्यापित आधिकारिक", "Not enough data": "पर्याप्त जानकारी नहीं"}
DANGER = ("High", "Confirmed fraud", "Medium")
KIND_WORD = {"message": "message", "url": "link", "image": "screenshot", "apk": "app", "email": "e-mail"}


# ---------------------------------------------------------------- model
def llm_enabled():
    return os.environ.get("PS01_LLM", "1") != "0"


def status():
    if not llm_enabled():
        return {"available": False, "model": MODEL, "reason": "switched off (PS01_LLM=0)"}
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=2) as r:
            models = json.load(r).get("models", [])
        names = {m["name"] for m in models} | {m["name"].split(":")[0] for m in models}
        ok = MODEL in names or MODEL.split(":")[0] in names
        return {"available": ok, "model": MODEL, "reason": "" if ok else f"model {MODEL} is not pulled in Ollama"}
    except (urllib.error.URLError, OSError, ValueError):
        return {"available": False, "model": MODEL, "reason": "Ollama is not running"}


def llm(system, user, max_tokens=180):
    """One chat call to Ollama. Returns text, or None if off, busy, slow or failing."""
    if not llm_enabled() or not _sem.acquire(timeout=3):
        return None
    try:
        body = {"model": MODEL, "stream": False, "keep_alive": KEEP_ALIVE, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "options": {"temperature": 0.3, "num_predict": max_tokens, "num_ctx": 2048, "repeat_penalty": 1.15}}
        if MODEL.startswith("qwen3"):
            body["think"] = False  # thinking models otherwise spend the whole budget before answering
        req = urllib.request.Request(OLLAMA + "/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return (json.load(r).get("message") or {}).get("content", "").strip() or None
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return None
    finally:
        _sem.release()


SYSTEM = ("You are the Satark assistant of Rajasthan Police. Rewrite the ANSWER for the user in 2 or 3 short, plain sentences. "
          "Use only the information in the ANSWER and FACTS. Do not add new facts, numbers, links or phone numbers. "
          "Never tell anyone to share an OTP, PIN or password. Do not write 'User:' or 'Assistant:'.")
SYSTEM_POLICE = ("You are an analyst assistant for Rajasthan Police officers. Summarise the DATA in 2 or 3 short sentences for an officer. "
                 "Use only the DATA. Do not invent numbers, case numbers or names. Do not write 'User:' or 'Assistant:'.")

NEG = re.compile(r"(?i)\b(never|not|don'?t|do not|no one|nobody|avoid|refuse|stop|without)\b")
UNSAFE_SHARE = re.compile(r"(?i)\b(share|give|tell|send|enter|provide|type)\b[^.?!]{0,40}\b(otp|pin|password|cvv|passcode)\b")
UNSAFE_REMOTE = re.compile(r"(?i)\b(install|download|use)\b[^.?!]{0,25}\b(anydesk|teamviewer|quick ?support|screen ?shar)")
CALLS_SAFE = re.compile(r"(?i)\b(is|are|looks?|seems?|appears?)\s+(completely\s+|totally\s+|perfectly\s+)?(safe|legit|legitimate|genuine|trustworthy|real)\b|\bnot a scam\b|\bno risk\b")
CALLS_SCAM = re.compile(r"(?i)\b(is|are)\s+(definitely\s+|certainly\s+)?(a\s+)?(scam|fraud|fake|confirmed fraud)\b")
ROLE = re.compile(r"(?im)^\s*(user question|user|assistant|human|ai|question|background|answer|facts|data)\s*:")
# describing what the scam does ("the message asks you to share your OTP") is not advice to do it
DESCRIBES = re.compile(r"(?i)\b(ask|asks|asking|asked|want|wants|request|requests|requesting|trick|tricks|tricking|pressur\w*|lure\w*|"
                       r"tries to get you to|trying to get you to)\b[^.?!]{0,20}\b(share|give|tell|send|enter|provide|type)")
# model talking about the task instead of answering it
META = re.compile(r"(?i)\b(here'?s|here is|updated version|rewrit\w*|summari[sz]e|the user|user question|the facts|the answer|"
                  r"as an ai|language model|i am an ai|in bold)\b|^\s*sure\b")
ALLOWED_NUMS = {"1930"}


def _sentences(t):
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", t) if s.strip()]


def clean(text):
    if not text:
        return ""
    m = ROLE.search(text)
    if m and m.start() > 20:
        text = text[:m.start()]
    elif m:
        text = ROLE.sub("", text)
    text = re.sub(r"[*#`]+", "", text).strip()
    if len(text) > 650:
        cut = text[:650]
        text = cut[:max(cut.rfind(". "), cut.rfind("? ")) + 1] or cut
    return text.strip()


def guard(answer, facts, level=None, strict_numbers=True):
    """Return None if the model's answer is acceptable, else the reason it was rejected."""
    if not answer or len(answer) < 25:
        return "empty"
    if META.search(answer):
        return "talked about the task instead of answering"
    if any(re.match(r"\s*([-•*]|\d+[.)])\s", l) for l in answer.splitlines()):
        return "returned a list instead of an answer"
    sents = [re.sub(r"\W+", " ", s).strip().lower() for s in _sentences(answer)]
    if len(sents) != len(set(sents)):
        return "repeated itself"
    for s in _sentences(answer):
        if (UNSAFE_SHARE.search(s) or UNSAFE_REMOTE.search(s)) and not NEG.search(s) and not DESCRIBES.search(s):
            return "unsafe advice"
        if level in DANGER and CALLS_SAFE.search(s) and not NEG.search(s):
            return "contradicts the verdict"
        if level in ("Low", "Verified official") and CALLS_SCAM.search(s) and not NEG.search(s):
            return "contradicts the verdict"
    ftxt = " ".join(facts)
    if strict_numbers:
        fnums = set(re.findall(r"\d+", ftxt)) | ALLOWED_NUMS
        for n in re.findall(r"\d+", answer):
            if n not in fnums:
                return f"invented number {n}"
    for host in re.findall(r"(?i)\b(?:[a-z0-9-]+\.)+[a-z]{2,}\b", answer):
        if host.lower() not in ftxt.lower() and host.lower() not in ("cybercrime.gov.in",):
            return f"invented link {host}"
    flines = [l.strip().lower() for l in facts if len(l.strip()) > 30]
    if flines and sum(l in answer.lower() for l in flines) >= max(2, len(flines) // 2):
        return "echoed the prompt"
    return None


def polish(rules_answer, facts, question, level=None, police=False):
    """Let the model rephrase a rules answer. Returns (text, source, note)."""
    prompt = (f"FACTS:\n" + "\n".join(f"- {f}" for f in facts) + f"\n\nANSWER:\n{rules_answer}\n\nUSER QUESTION: {question}")
    raw = llm(SYSTEM_POLICE if police else SYSTEM, prompt)
    if raw is None:
        return rules_answer, "rules", "AI model unavailable; answer written from the case data."
    text = clean(raw)
    why = guard(text, facts + [rules_answer], level)
    # small models open with "Yes, but…" / "Yes, it is not safe…" to trust and safety questions; never allow a "Yes"
    # the checked answer does not give (the checked answers never start with Yes)
    if not why and re.match(r"(?i)\s*(yes|yeah|sure|of course|absolutely)\b", text) and not re.match(r"(?i)\s*yes\b", rules_answer):
        why = "answered yes where the checked answer does not"
    if why:
        return rules_answer, "rules", f"AI reply rejected ({why}); answer written from the case data."
    return text, "ai", f"Written by the local AI model ({MODEL}) from the case data and checked."


def _reply(answer, source, note, facts, **kw):
    out = {"answer": answer, "source": source, "note": note, "facts": facts, "model": MODEL}
    out.update(kw)
    return out


# ---------------------------------------------------------------- citizen: one case
def case_facts(c, n=5):
    fired = [f for f in c["findings"] if f["status"] == "fired" and f["weight"] > 0]
    fired.sort(key=lambda f: (f["tier"] != "H", -f["weight"]))
    ran = sum(f["status"] in ("fired", "clear") for f in c["findings"])
    head = f"The {KIND_WORD.get(c['kind'], 'input')} (case {c['id']}) was rated {c['level']}. {len(fired)} of {ran} checks flagged it."
    reasons = [f"{'Strong' if f['tier'] == 'H' else 'Weak'} sign: {f['descr'].rstrip('.')} ({f['detail'][:90]})" for f in fired[:n]]
    return head, reasons, fired, ran


def case_intent(q):
    q = q.lower()
    if re.search(r"\b(report|complain|complaint|fir|police)\b|शिकायत|रिपोर्ट", q):
        return "report"
    if re.search(r"\b(paid|lost|pay|money|what (should|do|can) i|next|now|help|do now)\b|क्या करूं|पैसे", q):
        return "advice"
    if re.search(r"\b(safe|click|open|trust|real|genuine|legit|fake|scam|fraud)\b|सुरक्षित|असली", q):
        return "safety"
    if re.search(r"\b(why|explain|reason|reasons|risky|risk|danger\w*|wrong|suspicious|summary|summari[sz]e|details?|"
                 r"how do you know|what (is|was) (found|flagged)|this (message|link|result|case|sms|app|mail|e-mail|number)|"
                 r"result|verdict|score|checks?)\b|क्यों|खतरनाक|कारण", q):
        return "why"
    return None


def answer_case(c, question, lang="en", use_llm=True):
    from .advice import advice
    head, reasons, fired, ran = case_facts(c)
    adv = advice(c["level"])
    lvl = c["level"]
    intent = case_intent(question)
    hi = lang == "hi"
    if intent == "advice":
        ans = " ".join(adv["hi"] if hi else adv["en"])
    elif intent == "report":
        f = next(x for x in FAQ if x["id"] == "report")
        ans = f["hi" if hi else "en"] + (" इस परिणाम पर 'पुलिस को रिपोर्ट करें' से भी भेज सकते हैं।" if hi else
                                          " You can also use 'Report to police' on this result to add it to the review queue.")
    elif intent == "safety":
        if lvl in DANGER:
            ans = (f"नहीं। इसे {LEVEL_HI.get(lvl, lvl)} आंका गया है। लिंक न खोलें, जवाब न दें, पैसे न भेजें और OTP न बताएं।" if hi else
                   f"No. It is rated {lvl}. Do not open the link, reply, pay or share any OTP." + (f" Main reason: {fired[0]['descr'].rstrip('.')}." if fired else ""))
        elif lvl == "Verified official":
            ans = ("यह आधिकारिक सूची में है। फिर भी पता जांचें और OTP कभी न बताएं।" if hi else
                   "It is on the official registry. Still check the address bar before typing a password, and never share an OTP.")
        else:
            ans = ("कोई बड़ा खतरा नहीं मिला, पर यह सुरक्षा की गारंटी नहीं है। OTP कभी न बताएं।" if hi else
                   "No strong warning signs were found, but that is not a guarantee. Never share an OTP, and verify unexpected requests through official channels.")
    else:  # why
        if fired:
            top = "; ".join(f["descr"].rstrip(".") for f in fired[:3])
            ans = (f"इसे {LEVEL_HI.get(lvl, lvl)} आंका गया है: {ran} में से {len(fired)} जांचों में खतरा मिला। मुख्य कारण: {top}." if hi else
                   f"It is rated {lvl} because {len(fired)} of {ran} checks flagged it. The main reasons: {top}.")
        else:
            ans = (f"{ran} जांचों में कोई चेतावनी नहीं मिली। यह सुरक्षा की गारंटी नहीं है।" if hi else
                   f"None of the {ran} checks that could run found a warning sign. That is not a guarantee of safety.")
        if c["basis"] == "police":
            ans = (c["why"] + ". " + ans) if not hi else ("पुलिस ने इसे पुष्ट धोखा चिह्नित किया है। " + ans)
    facts = [head] + reasons + ["Advice: " + " ".join(adv["en"])]
    if hi or not use_llm:
        # polish: what the client sends back to ask for the AI-written version (none for Hindi: the model cannot write it)
        return _reply(ans, "rules", "Answer written from the case data.", facts, case_id=c["id"], level=lvl, intent=intent,
                      polish=None if hi else {"case_id": c["id"], "message": question})
    text, src, note = polish(ans, facts, question, level=lvl)
    return _reply(text, src, note, facts, case_id=c["id"], level=lvl, intent=intent)


# ---------------------------------------------------------------- citizen: general chat (agent)
def identifier_lookup(db, t, v):
    with db.conn() as c:
        r = c.execute("""SELECT COUNT(DISTINCT cs.id) n, SUM(cs.level IN ('High','Confirmed fraud')) high, SUM(cs.flagged) rep,
                         MAX(cs.created) last, GROUP_CONCAT(DISTINCT cs.id) ids
                         FROM identifiers i JOIN cases cs ON cs.id=i.case_id WHERE i.type=? AND i.value=?""", (t, v)).fetchone()
    lab = db.labels_for([(t, v)])
    ids = sorted(int(x) for x in (r["ids"] or "").split(",") if x)[-8:]
    return dict(type=t, value=v, cases=r["n"] or 0, high=r["high"] or 0, reported=r["rep"] or 0, last=r["last"],
                label=lab[0]["label"] if lab else None, case_ids=ids)


def _single_identifier(msg, ids):
    m = msg.strip()
    if " " in m or len(m) > 120:
        return None
    if ids["upis"] and m.lower() == ids["upis"][0]:
        return ("upi", ids["upis"][0])
    if ids["phones"] and re.fullmatch(r"[+\d\s\-()]{7,20}", m):
        return ("phone", ids["phones"][0])
    if ids["emails"] and m.lower() == ids["emails"][0]:
        return ("email", ids["emails"][0])
    return None


def _kw_in(k, t):
    if k.isascii():
        return re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", t) is not None
    return k in t


def _faq(msg):
    t = msg.lower()
    best, score = None, 0
    for f in FAQ:
        s = sum(len(k) for k in f["kw"] if _kw_in(k, t))   # longer, more specific keywords win ties
        if s > score:
            best, score = f, s
    return best


SCAMMY = re.compile(r"(?i)\b(otp|kyc|blocked|refund|prize|lottery|loan|apk|urgent|arrest|parcel|click|link|account|verify|pay|won|task|earn)\b")


SMALLTALK = [
    ("greet", re.compile(r"(?i)^\s*(hi+|hello+|hey+|hii+|helo|namaste|namaskar|good\s+(morning|afternoon|evening|night)|"
                         r"नमस्ते|नमस्कार|हेलो|हाय)[\s!.,]*$")),
    ("thanks", re.compile(r"(?i)^\s*(thanks?|thank\s*(you|u)|thx|ty|ok+|okay|great|nice|cool|got it|"
                          r"धन्यवाद|शुक्रिया|ठीक है)[\s!.,]*$")),
    ("bye", re.compile(r"(?i)^\s*(bye|goodbye|see you|tata|अलविदा)[\s!.,]*$")),
    ("who", re.compile(r"(?i)^\s*(who are you|what are you|what can you do|help|how (does|do) (this|you) work|"
                       r"what is satark|तुम कौन हो|आप कौन हैं|मदद)[\s?!.]*$")),
]
SMALLTALK_REPLY = {
    "greet": ("Hello! I am Satark's assistant. Paste a suspicious message, link, phone number or UPI ID and I will check it, "
              "or ask me about any scam.", "नमस्ते! मैं सतर्क सहायक हूं। कोई संदिग्ध मैसेज, लिंक, नंबर या UPI ID भेजें, या किसी धोखे के बारे में पूछें।"),
    "thanks": ("You're welcome. Stay alert: never share an OTP or PIN, and call 1930 if you lose money.",
               "आपका स्वागत है। सतर्क रहें: OTP या PIN कभी न बताएं, और पैसे कटें तो 1930 पर कॉल करें।"),
    "bye": ("Goodbye, and stay safe online.", "अलविदा, ऑनलाइन सुरक्षित रहें।"),
    "who": ("I am Satark's assistant for Rajasthan Police. I check messages, links, numbers and UPI IDs, explain results and "
            "tell you what to do. The risk level always comes from the rule checks, not from me.",
            "मैं राजस्थान पुलिस का सतर्क सहायक हूं। मैं मैसेज, लिंक, नंबर और UPI ID जांचता हूं और बताता हूं कि क्या करना है।"),
}


def smalltalk(msg, lang="en", case_id=None):
    for kind, rx in SMALLTALK:
        if rx.match(msg):
            en, hi = SMALLTALK_REPLY[kind]
            if kind == "greet" and case_id:
                en = f"Hello! Ask me why this result (case {case_id}) is risky, whether the link is safe, or what to do now."
                hi = "नमस्ते! पूछें कि यह परिणाम खतरनाक क्यों है, लिंक सुरक्षित है या नहीं, या अब क्या करें।"
            return _reply(hi if lang == "hi" else en, "rules", "", [], action="smalltalk")
    return None


SYSTEM_OPEN = ("You are Satark, the cyber-safety assistant of Rajasthan Police. Answer the question in 2 or 3 short, plain sentences "
               "about online fraud and cyber safety in India. If the question is not about scams, fraud, cyber safety or reporting a "
               "crime, reply only: 'I can only help with scams, fraud and cyber safety.' Never tell anyone to share an OTP, PIN or "
               "password. Do not give phone numbers or website links, except the helpline 1930 and cybercrime.gov.in. "
               "Do not write 'User:' or 'Assistant:'.")


def answer_open(msg):
    """A cyber-safety question the guide does not cover: the model answers, checked like every other reply."""
    raw = llm(SYSTEM_OPEN, msg, max_tokens=160)
    text = clean(raw) if raw else ""
    why = guard(text, ["Helpline 1930. Report at cybercrime.gov.in."], level=None) if text else "unavailable"
    if not why and re.match(r"(?i)\s*(yes|yeah|sure|of course)\b", text):
        why = "answered yes"
    if why:
        return None
    return _reply(text, "ai", f"Written by the local AI model ({MODEL}) and checked; not based on a case.", [], action="open")


def answer_general(db, msg, lang="en", run_analysis=None, use_llm=True):
    """run_analysis(kind, text) -> case id; provided by the web layer so this module does no I/O of its own."""
    hi = lang == "hi"
    st = smalltalk(msg, lang)
    if st:
        return st
    ids = extract_all(msg)
    single = _single_identifier(msg, ids)
    if single:   # tool: lookup
        t, v = single
        r = identifier_lookup(db, t, norm_phone(v) if t == "phone" else v.lower())
        if r["label"] == "confirmed_fraud":
            ans = f"{v} को पुलिस ने पुष्ट धोखा चिह्नित किया है। पैसे न भेजें, कुछ न बताएं।" if hi else \
                f"{v} is marked confirmed fraud by the police team. Do not pay or share anything. If you lost money, call 1930."
        elif r["label"] == "verified_official":
            ans = f"{v} पुलिस द्वारा सत्यापित आधिकारिक है।" if hi else f"{v} is marked verified official by the police team."
        elif r["cases"]:
            ans = (f"{v} हमारे {r['cases']} केस में मिला है, जिनमें {r['high']} उच्च जोखिम वाले हैं।" if hi else
                   f"{v} appears in {r['cases']} checked case(s), {r['high']} of them high risk and {r['reported']} reported by citizens. Treat it with caution.")
        else:
            ans = f"{v} अभी तक हमारे केस में नहीं मिला। यह सुरक्षित होने का प्रमाण नहीं है।" if hi else \
                f"{v} has not been seen in our cases yet. That is not proof that it is safe."
        return _reply(ans, "rules", "Looked up in the case database.", [ans], action="lookup", lookup=r, case_ids=r["case_ids"])
    if run_analysis and (ids["urls"] or ids["phones"] or ids["upis"] or (len(msg) > 40 and SCAMMY.search(msg))):   # tool: analyse
        one = msg.strip()
        kind = "url" if ids["urls"] and " " not in one and "\n" not in one else "message"
        cid = run_analysis(kind, msg)
        c = db.get_case(cid)
        out = answer_case(c, "Why is this risky?", lang, use_llm=use_llm)
        out.update(action="analyzed", case_id=cid)
        return out
    f = _faq(msg)
    if f:   # tool: knowledge base
        ans = f["hi" if hi else "en"]
        if hi:
            return _reply(ans, "rules", "From the Satark safety guide.", [f["en"]], action="faq", topic=f["id"])
        if not use_llm:
            return _reply(ans, "rules", "From the Satark safety guide.", [f["en"]], action="faq", topic=f["id"], polish={"message": msg})
        text, src, note = polish(ans, [f["en"]], msg)
        return _reply(text, src, note.replace("case data", "safety guide"), [f["en"]], action="faq", topic=f["id"])
    if use_llm and not hi and len(msg) >= 8:
        open_ans = answer_open(msg)
        if open_ans:
            return open_ans
    return _reply(GREETING_HI if hi else GREETING_EN, "rules", "", [], action="help")


# ---------------------------------------------------------------- police: officer analyst
POLICE_HELP = ("I can answer from the case database: 'summary of today', 'top reported identifiers', 'campaigns', "
               "'open citizen reports', 'latest high-risk cases', 'case 13', 'cases linked to 13', or paste a phone number, UPI ID or domain.")


def _case_line(r):
    return f"#{r['id']} {r['level']} {KIND_WORD.get(r['kind'], r['kind'])}: {r['title'][:70]}"


def answer_police(db, msg, use_llm=None):
    t = msg.lower().strip()
    num = (re.search(r"#\s*(\d{1,7})\b", t) or re.search(r"\bcases?\b\D{0,25}?\b(\d{1,7})\b", t) or re.fullmatch(r"(\d{1,7})", t)
           or (re.search(r"link|connect|relat|network", t) and re.search(r"(?<![\d+])\b(\d{1,7})\b(?!\d)", t)))
    ids = extract_all(msg)
    facts, ans, case_ids, items, tool = [], "", [], [], ""

    if num and re.search(r"link|connect|relat|same|share|campaign|network", t):
        tool = "linked"
        cid = int(num.group(1))
        c = db.get_case(cid)
        if not c:
            return _reply(f"There is no case #{cid}.", "rules", "", [], tool=tool)
        sh = db.shared_cases([(i["type"], i["value"]) for i in c["ids"]], exclude=cid)
        if not sh:
            ans = f"Case #{cid} shares no identifier with any other case."
        else:
            high = [s for s in sh if s["level"] in ("High", "Confirmed fraud")]
            ans = f"Case #{cid} is linked to {len(sh)} case(s), {len(high)} of them high risk or confirmed. " + \
                  "Strongest links: " + "; ".join(f"#{s['case_id']} via {s['via'][0][0]} {s['via'][0][1]}" for s in sh[:4]) + "."
        facts = [ans]
        case_ids = [cid] + [s["case_id"] for s in sh[:10]]
        items = [{"label": f"#{s['case_id']} {s['level']} via " + ", ".join(f"{a} {b}" for a, b in s["via"][:2]), "case_id": s["case_id"]} for s in sh[:10]]
    elif num:
        tool = "case"
        cid = int(num.group(1))
        c = db.get_case(cid)
        if not c:
            return _reply(f"There is no case #{cid}.", "rules", "", [], tool=tool)
        head, reasons, fired, ran = case_facts(c, n=4)
        linked = db.shared_cases([(i["type"], i["value"]) for i in c["ids"]], exclude=cid)
        idl = [f"{i['type']} {i['value']}" for i in c["ids"] if i["type"] in ("phone", "upi", "domain", "email", "crypto", "apk_package")][:6]
        ans = (f"{head} Status: {c['status']}. Citizen reports: {len(c['reports'])}. Linked cases: {len(linked)}. "
               + (f"Key identifiers: {', '.join(idl)}. " if idl else "") + (f"Top signal: {fired[0]['descr'].rstrip('.')}." if fired else ""))
        facts = [head] + reasons + [f"Status {c['status']}", f"{len(c['reports'])} citizen reports", f"{len(linked)} linked cases"] + idl
        case_ids = [cid] + [s["case_id"] for s in linked[:6]]
        items = [{"label": r, "case_id": None} for r in reasons]
    elif ids["phones"] or ids["upis"] or ids["emails"] or ids["domains"]:
        tool = "identifier"
        t_, v = (("phone", ids["phones"][0]) if ids["phones"] else ("upi", ids["upis"][0]) if ids["upis"] else
                 ("email", ids["emails"][0]) if ids["emails"] else ("domain", ids["domains"][0]))
        r = identifier_lookup(db, t_, v)
        lab = {"confirmed_fraud": "confirmed fraud", "verified_official": "verified official"}.get(r["label"], "no police label")
        ans = (f"{t_} {v}: seen in {r['cases']} case(s), {r['high']} high risk, {r['reported']} citizen-reported, {lab}."
               + (f" Last seen {r['last']} UTC. Cases: " + ", ".join(f"#{x}" for x in r["case_ids"]) + "." if r["cases"] else ""))
        facts, case_ids = [ans], r["case_ids"]
    elif re.search(r"heat|top|trend|most|frequent|repeat", t):
        tool = "heatlist"
        rows = db.heatlist(8)
        if not rows:
            ans = "No identifiers recorded yet."
        else:
            ans = "Most-seen identifiers: " + "; ".join(f"{r['type']} {r['value']} in {r['n']} case(s), {r['high']} high" for r in rows[:5]) + "."
        facts = [ans]
        items = [{"label": f"{r['type']} {r['value']}: {r['n']} cases, {r['high']} high, {r['flagged'] or 0} reported", "case_id": None} for r in rows]
    elif re.search(r"campaign|cluster|group|gang|operation", t):
        tool = "campaigns"
        camps = db.campaigns()[:5]
        if not camps:
            ans = "No campaigns yet: no two cases share an identifier."
        else:
            ans = f"{len(db.campaigns())} campaign(s) found. Largest: " + "; ".join(
                f"{g['size']} cases ({sum(l in ('High', 'Confirmed fraud') for l in g['levels'])} high) sharing " +
                ", ".join(f"{s['type']} {s['value']}" for s in g["shared"][:2]) for g in camps[:3]) + "."
        facts = [ans]
        for g in camps:
            case_ids += g["cases"][:6]
            items.append({"label": f"{g['size']} cases: " + ", ".join(f"#{x}" for x in g["cases"][:8]), "case_id": g["cases"][0]})
    elif re.search(r"queue|reported|pending|review|citizen|complain", t):
        tool = "queue"
        rows = db.search_cases(flagged=True, status="open", limit=10)
        ans = f"{len(rows)} citizen-reported case(s) are open." + (" Oldest first to review: " + "; ".join(_case_line(r) for r in rows[-3:]) + "." if rows else "")
        facts, case_ids = [ans], [r["id"] for r in rows]
        items = [{"label": _case_line(r), "case_id": r["id"]} for r in rows]
    elif re.search(r"high|latest|recent|new|danger|serious", t):
        tool = "recent_high"
        rows = [r for r in db.search_cases(limit=60) if r["level"] in ("High", "Confirmed fraud")][:8]
        ans = f"Latest high-risk cases: " + "; ".join(_case_line(r) for r in rows[:4]) + "." if rows else "No high-risk cases yet."
        facts, case_ids = [ans], [r["id"] for r in rows]
        items = [{"label": _case_line(r), "case_id": r["id"]} for r in rows]
    elif re.search(r"stat|today|how many|overview|summary|total|count|status", t):
        tool = "stats"
        s = db.stats()
        lv = ", ".join(f"{k} {v}" for k, v in s["by_level"].items())
        ans = (f"{s['total']} cases in total, {s['today']} today. {s['high']} are high risk or confirmed. "
               f"{s['flagged']} citizen reports are open. {s['labels']} identifiers are confirmed fraud. By level: {lv}.")
        facts = [ans]
    else:
        return _reply(POLICE_HELP, "rules", "", [], tool="help")

    if not LLM_POLICE or use_llm is False:
        return _reply(ans, "rules", "Exact figures from the case database.", facts, tool=tool, case_ids=case_ids, items=items,
                      polish={"message": msg} if LLM_POLICE else None)
    text, src, note = polish(ans, facts, msg, police=True)
    return _reply(text, src, note.replace("case data", "case database"), facts, tool=tool, case_ids=case_ids, items=items)
