"""Static lexicons and registries. Edit here to tune detection; no logic lives in this file."""
import csv
import json
import os

_D = os.path.join(os.path.dirname(__file__), "data")

# brand -> official registered domains, official helpline numbers (digits only), official Android packages
BRANDS = {
    "sbi": {"domains": ["sbi.co.in", "onlinesbi.sbi", "sbicard.com", "sbilife.co.in", "yonosbi.com"],
            "phones": ["18001234", "18002100", "1800112211", "18004253800", "1800110018"],
            "packages": ["com.sbi.lotusintouch", "com.sbi.SBIFreedomPlus", "com.sbi.upi"]},
    "hdfc": {"domains": ["hdfcbank.com", "hdfc.com", "hdfcfund.com", "hdfclife.com", "hdfcergo.com"],
             "phones": ["18002586161", "18001600", "1800202020"], "packages": ["com.snapwork.hdfc", "com.hdfcbank.payzapp"]},
    "icici": {"domains": ["icicibank.com", "icicidirect.com", "iciciprulife.com", "icicilombard.com"],
              "phones": ["18001080", "18002024"], "packages": ["com.csam.icici.bank.imobile", "com.icicibank.pockets"]},
    "axis": {"domains": ["axisbank.com", "axis.bank.in"], "phones": ["18605005555", "18004195959"], "packages": ["com.axis.mobile"]},
    "pnb": {"domains": ["pnbindia.in", "netpnb.com"], "phones": ["18001802222", "18001032222"], "packages": ["com.pnb.one"]},
    "kotak": {"domains": ["kotak.com", "kotakbank.com"], "phones": ["18602662666"], "packages": ["com.msf.kbank.mobile"]},
    "paytm": {"domains": ["paytm.com", "paytmbank.com", "paytmpayments.com"], "phones": ["01204456456"], "packages": ["net.one97.paytm"]},
    "phonepe": {"domains": ["phonepe.com"], "phones": ["08068727374"], "packages": ["com.phonepe.app"]},
    "gpay": {"domains": ["pay.google.com", "gpay.app.goo.gl"], "phones": [], "packages": ["com.google.android.apps.nbu.paisa.user"]},
    "npci": {"domains": ["npci.org.in", "bhimupi.org.in"], "phones": ["18001201740"], "packages": ["in.org.npci.upiapp"]},
    "irctc": {"domains": ["irctc.co.in", "irctc.com"], "phones": ["14646", "08044647999"], "packages": ["cris.org.in.prs.ima"]},
    "income tax": {"domains": ["incometax.gov.in", "incometaxindiaefiling.gov.in"], "phones": ["18001030025"], "packages": []},
    "epfo": {"domains": ["epfindia.gov.in", "unifiedportal-mem.epfindia.gov.in"], "phones": ["14470"], "packages": ["in.gov.umang.negd.g2c"]},
    "aadhaar": {"domains": ["uidai.gov.in", "myaadhaar.uidai.gov.in"], "phones": ["1947"], "packages": ["in.gov.uidai.mAadhaarPlus"]},
    "india post": {"domains": ["indiapost.gov.in", "ippbonline.com"], "phones": ["18002666868"], "packages": []},
    "amazon": {"domains": ["amazon.in", "amazon.com"], "phones": ["18008495500"], "packages": ["in.amazon.mShop.android.shopping"]},
    "flipkart": {"domains": ["flipkart.com"], "phones": ["18002029898"], "packages": ["com.flipkart.android"]},
    "jio": {"domains": ["jio.com", "ril.com"], "phones": ["199", "1800889999"], "packages": ["com.jio.myjio"]},
    "airtel": {"domains": ["airtel.in", "airtel.com"], "phones": ["121", "198"], "packages": ["com.myairtelapp"]},
    "bajaj finserv": {"domains": ["bajajfinserv.in", "bajajfinance.in"], "phones": ["18001021010"], "packages": ["org.altruist.BajajExperia"]},
    "cbi": {"domains": ["cbi.gov.in"], "phones": [], "packages": []},
}
GOV_TLD_SUFFIXES = (".gov.in", ".nic.in")

# Words that make a domain look like a brand lookalike when combined with a brand
LURE_WORDS = ["kyc", "update", "verify", "secure", "login", "refund", "reward", "claim", "support", "care",
              "helpdesk", "customer", "apply", "loan", "offer", "bonus", "cashback", "pay", "online", "net", "bank"]
RISKY_PATH_WORDS = ["kyc", "verify", "update", "login", "secure", "claim", "refund", "reward", "otp", "unblock", "reactivate"]

SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "cutt.ly", "rb.gy", "ow.ly", "shorturl.at", "tiny.cc",
              "t.ly", "s.id", "rebrand.ly", "bl.ink", "v.gd", "lnkd.in", "buff.ly", "wa.me/c", "qrco.de", "shorturl.asia"}
FREE_HOSTS = ["github.io", "pages.dev", "vercel.app", "netlify.app", "blogspot.com", "weebly.com", "wixsite.com",
              "firebaseapp.com", "web.app", "forms.gle", "telegra.ph", "sites.google.com", "herokuapp.com", "glitch.me",
              "000webhostapp.com", "infinityfreeapp.com", "rf.gd", "epizy.com", "onrender.com", "replit.app", "repl.co",
              "workers.dev", "carrd.co", "webflow.io", "framer.app", "godaddysites.com", "my.canva.site"]
DYNDNS_TUNNEL = ["ngrok.io", "ngrok-free.app", "ngrok.app", "trycloudflare.com", "duckdns.org", "no-ip.org", "no-ip.com",
                 "ddns.net", "serveo.net", "loca.lt", "localtunnel.me", "hopto.org", "zapto.org", "dynu.net"]
RISKY_TLDS = {"xyz", "top", "icu", "click", "loan", "cfd", "sbs", "monster", "buzz", "rest", "cyou", "gq", "tk", "ml", "ga", "cf",
              "work", "men", "date", "bid", "win", "zip", "mov", "support", "vip", "fit", "live", "shop", "site", "online",
              "life", "today", "link", "world", "store"}
PUBLIC_SUFFIX_2LD = {"co.in", "org.in", "net.in", "gov.in", "nic.in", "ac.in", "res.in", "firm.in", "gen.in", "ind.in",
                      "co.uk", "com.au", "co.za", "com.br", "co.id", "com.ng", "bank.in", "edu.in"}

FREEMAIL = {"gmail.com", "yahoo.com", "yahoo.in", "outlook.com", "hotmail.com", "rediffmail.com", "proton.me", "protonmail.com",
            "aol.com", "icloud.com", "mail.com", "ymail.com", "zoho.com", "gmx.com"}

# NPCI-registered UPI handles (subset of the widely used PSP suffixes; extendable)
UPI_HANDLES = {"upi", "okaxis", "oksbi", "okhdfcbank", "okicici", "ybl", "ibl", "axl", "paytm", "pthdfc", "ptaxis", "ptyes", "ptsbi",
               "sbi", "hdfcbank", "icici", "axisbank", "pnb", "kotak", "barodampay", "boi", "cnrb", "canarabank", "unionbank",
               "uboi", "idfcfirst", "idfcbank", "federal", "fbl", "yesbank", "yesbankltd", "indus", "indusind", "rbl", "aubank",
               "apl", "freecharge", "airtel", "jio", "postbank", "ikwik", "abfspay", "waaxis", "wahdfcbank", "waicici", "wasbi",
               "okbizaxis", "naviaxis", "slice", "jupiteraxis", "fam", "superyes", "tapicici", "dbs", "citi", "hsbc", "sc",
               "kmbl", "kmb", "psb", "centralbank", "iob", "mahb", "cub", "dlb", "ezetap", "rajgovhdfcbank", "equitas",
               "ubi", "sib", "tmb", "karb", "kvb", "jsb", "csbpay", "dcb", "hdfcbankjd", "payzapp", "myicici", "bandhan",
               "ibkpay", "jkb", "lvb", "mbl", "okbizicici", "okbizhdfc", "pingpay", "shriramhdfcbank", "timecosmos"}

# keyword lexicons (lowercase; Hindi/Hinglish included)
KW = {
    "otp_pin": [r"\b(share|send|tell|give|forward|enter|bata(?:o|iye)?|batayein)\b.{0,40}\b(otp|pin|cvv|password|passcode|mpin|upi pin)\b",
                r"\b(otp|cvv|mpin|upi pin)\b.{0,30}\b(share|send|tell|forward|bata)",
                r"enter (your )?(upi )?pin to (receive|get|accept)"],
    "remote_app": [r"anydesk", r"teamviewer", r"quick ?support", r"rustdesk", r"airdroid", r"alpemix", r"ultraviewer", r"screen ?share",
                   r"aap ?support", r"remote access"],
    "ussd": [r"\*\*21\*", r"\*401\*", r"\*21\*", r"\*67\*", r"\*72\*", r"##002#", r"\*#21#", r"\*\*61\*", r"\*\*62\*", r"\*\*67\*"],
    "digital_arrest": [r"digital arrest", r"\b(cbi|ed|ncb|narcotics|customs|cyber ?crime|trai|supreme court)\b.{0,80}\b(arrest|warrant|case|fir|illegal|parcel|drugs)\b",
                       r"\b(parcel|courier|fedex|dhl)\b.{0,60}\b(drugs|illegal|passport|seized|customs)\b",
                       r"(video call|skype|whatsapp call).{0,60}(verify|statement|investigation|police)",
                       r"money laundering", r"aadhaar.{0,40}(misuse|illegal|blocked).{0,40}(arrest|case)"],
    "task_job": [r"(like|subscribe|rate|review) .{0,30}(youtube|video|product|hotel|google map)", r"per task", r"work from home",
                 r"part[- ]?time job", r"daily (income|earning|salary)", r"earn (rs\.?|₹|inr)? ?\d[\d,]*.{0,20}(daily|per day|a day)",
                 r"telegram (group|channel|id)", r"prepaid task", r"commission.{0,30}(task|order)", r"hiring.{0,30}(online|home)"],
    "investment": [r"guaranteed (return|profit)", r"(double|triple) (your )?(money|investment)", r"\bvip (group|channel|tips)\b",
                   r"(stock|share|ipo|crypto|forex).{0,40}(tips?|signal|allot|guaranteed|profit)", r"insider (tip|info)", r"\d{2,3}% (return|profit|monthly|weekly)",
                   r"trading (group|course|academy)", r"sebi (registered|approved).{0,30}(advis|tips)", r"mutual fund.{0,30}guarantee"],
    "urgency": [r"within (24|12|2|1) ?(hours?|hrs?|mins?|minutes?)", r"(account|card|sim|number|service|upi).{0,30}(blocked|suspended|expire|deactivat|freeze|frozen|disconnect)",
                r"(last|final) (warning|notice|chance|reminder)", r"immediately", r"turant", r"band ho jaye", r"urgent", r"act now", r"today only", r"abhi"],
    "kyc": [r"\bkyc\b.{0,40}(update|expire|pending|verify|incomplete|karein)", r"(pan|aadhaar) (card )?(update|link|verify).{0,30}(account|bank)",
            r"update (your )?(pan|aadhaar|kyc|details)"],
    "prize": [r"\b(lottery|lucky draw|you (have )?won|winner|jackpot|kbc|congratulations)\b", r"claim (your )?(prize|reward|gift|cashback)",
              r"\b(reward points?).{0,30}(expire|redeem)"],
    "loan": [r"(instant|pre-?approved|easy|quick) (personal )?loan", r"no (cibil|credit score|documents?|income proof)", r"loan (approved|sanctioned).{0,30}(processing|insurance|gst) fee",
             r"(processing|insurance|gst|registration|release) fee.{0,40}(before|to) (loan|disburs|release)", r"pay .{0,20}fee.{0,30}(loan|release)",
             r"loan in \d+ ?(min|minutes|hrs|hours)", r"(₹|rs\.?|inr)\s?\d[\d,]*.{0,20}loan.{0,20}(approved|ready|waiting)"],
    "bill_sim": [r"electricity.{0,40}(disconnect|cut|bill|pending)", r"(sim|mobile number).{0,30}(block|deactivat|disconnect|kyc)", r"fastag.{0,30}(block|suspend|kyc)",
                 r"(challan|e-?challan).{0,30}(pending|pay|fine)", r"(gas|lpg).{0,20}(subsidy|kyc|block)"],
    "app_install": [r"(download|install).{0,40}(apk|app)\b", r"\.apk\b", r"(update|install).{0,30}(app).{0,30}(link|below)"],
    "chat_move": [r"wa\.me/", r"t\.me/", r"chat\.whatsapp\.com", r"join (our )?(whatsapp|telegram)", r"telegram\.me/"],
    "refund_collect": [r"(refund|cashback).{0,40}(scan|qr|collect|pin|approve)", r"approve (the )?(collect|request).{0,30}(receive|refund)"],
}

# Hindi (Devanagari) and extra Hinglish patterns. No word-boundary anchors here: Devanagari vowel signs do not count as word characters.
KW_HI = {
    "otp_pin": [r"(ओटीपी|OTP|पिन|PIN|पासवर्ड|सीवीवी).{0,30}(बताएं|बताइए|बताओ|भेजें|भेजो|शेयर|दें|दीजिए)",
                r"(बताएं|भेजें|शेयर करें).{0,20}(ओटीपी|OTP|पिन)", r"(?i)otp\s*(bhej|de do|dedo|share kar)"],
    "remote_app": [r"(एनीडेस्क|टीमव्यूअर|स्क्रीन शेयर)", r"(?i)(anydesk|app) (download|install) kar"],
    "digital_arrest": [r"डिजिटल अरेस्ट", r"(गिरफ्तार|गिरफ़्तार|वारंट|एफआईआर).{0,60}(सीबीआई|पुलिस|कस्टम|पार्सल|ड्रग्स)",
                       r"(सीबीआई|पुलिस|कस्टम|नारकोटिक्स).{0,60}(गिरफ्तार|गिरफ़्तार|वारंट|केस)", r"मनी लॉन्ड्रिंग",
                       r"(?i)(arrest|giraftar) (ho jaoge|hoga|kar liya jayega)"],
    "task_job": [r"(घर बैठे|पार्ट टाइम|वर्क फ्रॉम होम).{0,40}(कमाएं|कमाई|नौकरी|इनकम)", r"(रोज|रोज़ाना|प्रतिदिन).{0,20}(कमाई|कमाएं|₹)",
                 r"(?i)ghar baithe.{0,30}(kamaye|kamao|earning|income)", r"(?i)(like|review) kar(o|ke).{0,30}(paise|kamao)"],
    "investment": [r"(गारंटी|पक्का).{0,30}(रिटर्न|मुनाफा|मुनाफ़ा|लाभ)", r"(पैसा|पैसे|रकम).{0,20}(डबल|दोगुना|तिगुना)",
                   r"(?i)(paisa|paise) (double|dugna)", r"(?i)guaranteed? (munafa|profit) milega"],
    "urgency": [r"(तुरंत|अभी|फौरन|24 घंटे).{0,40}(बंद|ब्लॉक|निलंबित|कट)", r"(खाता|अकाउंट|सिम|बिजली|कनेक्शन).{0,30}(बंद|ब्लॉक|कट) (हो जाएगा|हो जायेगा|कर दिया जाएगा)",
                r"(?i)(account|sim|bijli).{0,20}(band|block) ho (jayega|jaega)", r"अंतिम (चेतावनी|मौका)"],
    "kyc": [r"(केवाईसी|KYC).{0,40}(अपडेट|अपडेट करें|पूरा करें|लंबित|समाप्त)", r"(पैन|आधार).{0,30}(अपडेट|लिंक).{0,30}(खाता|अकाउंट|बैंक)",
            r"(?i)kyc (update|pura) kar(o|ein|e)"],
    "prize": [r"(लॉटरी|इनाम|बधाई हो|आप जीत गए|आपने जीता|विजेता|कौन बनेगा करोड़पति)", r"(?i)(lottery|inaam) (lagi|jeeta|jeete)"],
    "loan": [r"(तुरंत|इंस्टेंट|बिना).{0,20}(लोन|ऋण)", r"(लोन|ऋण).{0,40}(प्रोसेसिंग|फीस|शुल्क)", r"बिना (सिबिल|दस्तावेज|कागज)",
             r"(?i)(loan|lone) (pass|approve) (ho gaya|hua).{0,40}(fees?|charge)"],
    "bill_sim": [r"बिजली.{0,40}(कट|बिल|बकाया|कनेक्शन)", r"(सिम|मोबाइल नंबर).{0,30}(बंद|ब्लॉक)", r"(चालान|ई-चालान).{0,30}(बकाया|भुगतान|जुर्माना)"],
    "app_install": [r"(ऐप|एप|APK).{0,30}(डाउनलोड|इंस्टॉल)", r"(डाउनलोड|इंस्टॉल) (करें|करो).{0,20}(ऐप|एप|APK)"],
    "refund_collect": [r"(रिफंड|कैशबैक|पैसे).{0,40}(स्कैन|क्यूआर|QR|पिन डालें)", r"(?i)(refund|paise) (lene|pane) ke liye.{0,30}(scan|pin|qr)"],
}
for _k, _v in KW_HI.items():
    KW.setdefault(_k, []).extend(_v)

SENSITIVE_FIELD_WORDS = ["password", "passwd", "otp", "cvv", "cvc", "pin", "aadhaar", "aadhar", "pan", "card", "debit", "atm",
                         "mpin", "upi", "account number", "ifsc", "net banking", "netbanking", "expiry"]

DANGEROUS_PERMS = {
    "READ_SMS", "RECEIVE_SMS", "SEND_SMS", "READ_CONTACTS", "READ_CALL_LOG", "WRITE_CALL_LOG", "CALL_PHONE", "RECORD_AUDIO",
    "CAMERA", "READ_PHONE_STATE", "READ_PHONE_NUMBERS", "ACCESS_FINE_LOCATION", "READ_EXTERNAL_STORAGE", "SYSTEM_ALERT_WINDOW",
    "REQUEST_INSTALL_PACKAGES", "BIND_ACCESSIBILITY_SERVICE", "BIND_DEVICE_ADMIN", "MANAGE_EXTERNAL_STORAGE", "QUERY_ALL_PACKAGES",
    "RECEIVE_BOOT_COMPLETED", "READ_PHONE_NUMBERS", "WRITE_SETTINGS", "PROCESS_OUTGOING_CALLS", "READ_MEDIA_IMAGES",
}

# ISO calling codes that commonly appear in scam traffic but are never used by Indian bank/government brands
FOREIGN_CC = ["+1", "+44", "+92", "+880", "+971", "+66", "+84", "+855", "+95", "+62", "+60", "+63", "+234", "+27", "+7", "+86", "+977", "+94"]


def load_json(name):
    with open(os.path.join(_D, name), encoding="utf-8") as f:
        return json.load(f)


_rbi_cache = {}


def rbi_bank_domains():
    if "banks" not in _rbi_cache:
        d = load_json("rbi_bank_domains.json")
        s = set(d.get("rbi_listed", []))
        s |= set((d.get("manual") or {}).get("domains", []) if isinstance((d.get("manual") or {}).get("domains"), list) else [])
        _rbi_cache["banks"] = {x.lower() for x in s}
    return _rbi_cache["banks"]


def rbi_entities():
    if "ent" not in _rbi_cache:
        names = []
        try:
            with open(os.path.join(_D, "rbi_entities.csv"), encoding="utf-8") as f:
                r = csv.reader(f)
                next(r, None)
                names = [row[0].strip() for row in r if row]
        except OSError:
            pass
        _rbi_cache["ent"] = names
    return _rbi_cache["ent"]


def official_domains():
    out = set(rbi_bank_domains())
    for b in BRANDS.values():
        out.update(b["domains"])
    return out
