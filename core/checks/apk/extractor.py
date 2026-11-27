"""Static APK parsing. The APK is never executed.

What is read:
  * manifest (androguard): package, label, versions, uses-permissions, signing certificate, and the
    permissions that guard components (accessibility service, notification listener, device admin),
    launcher icon, cleartext-traffic flag
  * every classes*.dex: the real DEX string table (not raw bytes, which produced junk identifiers)
  * assets, res/raw, resources.arsc and Flutter libapp.so: links, UPI / Telegram strings. Hybrid apps
    (React Native, Flutter, Cordova / WebView wrappers) keep their servers there, not in the DEX
  * native library names (packers), hidden DEX/JAR payloads in assets
Then clean_ids() drops SDK noise, Java package names, version numbers and placeholder values so only
real identifiers reach the linking graph.
"""
import hashlib
import ipaddress
import os
import re
import struct
import zipfile

from ...data import UPI_HANDLES

INTEREST = re.compile(r"(?i)https?://|www\.|@[a-z]{2,}\b|\b[6-9]\d{9}\b|api\.telegram|\b\d{1,3}(\.\d{1,3}){3}\b|upi://|bot\d+:")
URL_BYTES = re.compile(rb"(?:https?|upi|wss?)://[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]{3,300}")
URL_U16 = re.compile(rb"(?:h\x00t\x00t\x00p\x00(?:s\x00)?|u\x00p\x00i\x00):\x00/\x00/\x00(?:[\x21-\x7e]\x00){3,300}")
TG_BYTES = re.compile(rb"\b\d{8,10}:[A-Za-z0-9_\-]{35}\b")
STR_RE = re.compile(rb"[\x20-\x7e]{6,300}")

# class / method names worth knowing about (found in the DEX string table)
API_REFS = {
    "dex_loader": ("Ldalvik/system/DexClassLoader;", "Ldalvik/system/InMemoryDexClassLoader;", "Ldalvik/system/BaseDexClassLoader;"),
    "sms_send": ("sendTextMessage", "sendMultipartTextMessage"),
    "sms_read": ("createFromPdu", "getMessageBody", "content://sms"),
    "hide_icon": ("setComponentEnabledSetting",),
    "accessibility": ("Landroid/accessibilityservice/AccessibilityService;",),
    "notif_listener": ("Landroid/service/notification/NotificationListenerService;",),
    "device_admin": ("Landroid/app/admin/DevicePolicyManager;",),
    "webview_js": ("addJavascriptInterface",),
    "exec": ("Ljava/lang/Runtime;",),
}
PACKER_LIBS = re.compile(r"(?i)lib(jiagu|secexe|secmain|DexHelper|protectClass|shell(x|a)?|tup|nqshield|baiduprotect|apssec|SecShell|mobisec|"
                         r"tosprotection|x3g|ddog|chaosvmp|legudsp|egis|edog|bangcle|jgdtc|kwscmm|sgmain)[\w\-]*\.so$")
ASSET_SCAN = re.compile(r"(?i)^(assets/.+\.(js|json|html?|txt|xml|bundle|properties|cfg|conf|ini|dat)|assets/index\.android\.bundle|"
                        r"res/raw/.+|resources\.arsc|lib/[^/]+/libapp\.so|assets/flutter_assets/.+\.(json|js|txt))$")
MAX_SCAN_FILE, MAX_SCAN_TOTAL = 12 * 1024 * 1024, 60 * 1024 * 1024

# hosts that appear in nearly every app (SDKs, schemas). They are not evidence and must not link unrelated cases.
NOISE_HOST = re.compile(r"(?i)(^|\.)(schemas\.android\.com|android\.com|w3\.org|apache\.org|google(apis|usercontent|adservices|syndication|tagmanager|"
                        r"-analytics)?\.com|gstatic\.com|googleapis\.com|doubleclick\.net|app-measurement\.com|firebase(io|app)?\.com|"
                        r"crashlytics\.com|facebook\.(com|net)|fbcdn\.net|github\.com|githubusercontent\.com|xmlpull\.org|mozilla\.org|"
                        r"jquery\.com|example\.(com|org|net)|adobe\.com|ns\.adobe\.com|apple\.com|microsoft\.com|w3schools\.com|"
                        r"json-schema\.org|xml\.org|openxmlformats\.org|purl\.org|unicode\.org|ietf\.org|java\.com|oracle\.com|"
                        r"kotlinlang\.org|jetbrains\.com|reactnative\.dev|flutter\.dev|cordova\.apache\.org|onesignal\.com|"
                        r"branch\.io|appsflyer\.com|adjust\.com|sentry\.io|mixpanel\.com|amplitude\.com|youtube\.com|twitter\.com|"
                        r"instagram\.com|play\.google\.com|localhost)$")
JAVA_PREFIX = re.compile(r"(?i)^(com|org|net|io|android|androidx|java|javax|kotlin|kotlinx|dalvik|okhttp3|retrofit2|dagger|"
                         r"rx|reactivex|in|co|me|de|fr|uk|us|cn|edu)\.")
BARE_TLDS = {"com", "net", "org", "in", "co.in", "info", "biz", "io", "app", "xyz", "top", "online", "site", "store", "shop", "live",
             "club", "vip", "tech", "me", "cc", "tk", "ml", "ga", "cf", "gq", "pw", "icu", "cfd", "sbs", "buzz", "click", "link", "loan",
             "money", "finance", "cash", "work", "fun", "space", "website", "pro", "asia", "us", "uk", "ru", "cn", "hk", "sg", "ae", "net.in",
             "org.in", "firm.in", "gen.in", "ind.in", "bank.in", "gov.in", "nic.in", "ac.in", "monster", "rest", "cyou", "today", "world"}
PLACEHOLDER_PHONE = re.compile(r"^\+91(\d)\1{9}$|^\+91(1234567890|9876543210|0123456789|9898989898)$")


def analyze_apk(path: str) -> dict:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    info = {"sha256": h.hexdigest(), "size": os.path.getsize(path), "package": "", "label": "", "version": "", "perms": [],
            "component_perms": [], "target_sdk": None, "min_sdk": None, "cert": {}, "signed_v": [], "services": [], "receivers": [],
            "launcher": None, "cleartext": None, "strings": [], "api_refs": [], "packers": [], "hidden_payloads": [],
            "framework": "", "dex_count": 0, "scanned_files": 0, "limited": False, "error": ""}
    if not zipfile.is_zipfile(path):
        raise ValueError("Not a valid APK (not a zip archive)")
    try:
        from loguru import logger
        logger.remove()  # androguard is extremely chatty at DEBUG
    except Exception:
        pass
    try:
        from androguard.core.apk import APK
        a = APK(path)
        info["package"] = a.get_package() or ""
        info["label"] = a.get_app_name() or ""
        info["version"] = str(a.get_androidversion_name() or "")
        info["perms"] = sorted({p.split(".")[-1] for p in a.get_permissions()})
        info["target_sdk"] = _int(a.get_target_sdk_version())
        info["min_sdk"] = _int(a.get_min_sdk_version())
        info["services"] = [s for s in a.get_services()][:50]
        info["receivers"] = [s for s in a.get_receivers()][:50]
        info["signed_v"] = [v for v, ok in (("v1", a.is_signed_v1()), ("v2", a.is_signed_v2()), ("v3", a.is_signed_v3())) if ok]
        try:
            certs = a.get_certificates()
            if certs:
                c = certs[0]
                info["cert"] = {"subject": c.subject.human_friendly, "issuer": c.issuer.human_friendly, "self_signed": c.issuer == c.subject}
        except Exception:
            pass
        try:
            info.update(manifest_facts(a.get_android_manifest_xml()))
        except Exception:
            pass
    except Exception as e:
        info["limited"] = True
        info["error"] = f"{type(e).__name__}: {e}"[:200]

    strings, seen = [], set()

    def add(s):
        if s and s not in seen and len(strings) < 6000:
            seen.add(s)
            strings.append(s)

    refs = set()
    total = 0
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        info["framework"] = detect_framework(names)
        info["packers"] = sorted({os.path.basename(n) for n in names if PACKER_LIBS.search(n)})[:10]
        for n in names:
            if re.fullmatch(r"classes\d*\.dex", n):
                info["dex_count"] += 1
                blob = z.read(n)
                dex_strings = dex_string_table(blob)
                if dex_strings is None:      # not a well-formed DEX: fall back to printable runs
                    dex_strings = [m.group(0).decode("ascii", "ignore") for m in STR_RE.finditer(blob)]
                for s in dex_strings:
                    for key, needles in API_REFS.items():
                        if key not in refs and any(x in s for x in needles):
                            refs.add(key)
                    if INTEREST.search(s):
                        add(s[:400])
            elif n.lower().startswith("assets/") and re.search(r"(?i)\.(dex|jar|apk|odex)$", n) or \
                    n.lower().startswith("assets/") and _peek(z, n) in (b"dex\n", b"PK\x03\x04"):
                info["hidden_payloads"].append(n[:120])
            if ASSET_SCAN.match(n) and total < MAX_SCAN_TOTAL:
                zi = z.getinfo(n)
                if zi.file_size > MAX_SCAN_FILE:
                    continue
                data = z.read(n)
                total += len(data)
                info["scanned_files"] += 1
                for m in URL_BYTES.finditer(data):
                    add(m.group(0).decode("ascii", "ignore").rstrip("\\'\",;)"))
                for m in URL_U16.finditer(data):
                    add(m.group(0).decode("utf-16-le", "ignore"))
                for m in TG_BYTES.finditer(data):
                    add(m.group(0).decode())
    info["hidden_payloads"] = info["hidden_payloads"][:10]
    info["api_refs"] = sorted(refs)
    info["strings"] = strings
    return info


def manifest_facts(xml) -> dict:
    """Facts from the decoded manifest (an lxml element): component permissions, launcher, cleartext flag."""
    ns = "{http://schemas.android.com/apk/res/android}"
    comp = set()
    for tag in ("service", "receiver", "activity", "provider"):
        for el in xml.iter(tag):
            p = el.get(ns + "permission")
            if p:
                comp.add(p.split(".")[-1])
            for act in el.iter("action"):
                n = act.get(ns + "name") or ""
                if n.endswith(("accessibilityservice.AccessibilityService", "notification.NotificationListenerService")):
                    comp.add({"AccessibilityService": "BIND_ACCESSIBILITY_SERVICE",
                              "NotificationListenerService": "BIND_NOTIFICATION_LISTENER_SERVICE"}[n.rsplit(".", 1)[-1]])
                if n == "android.app.action.DEVICE_ADMIN_ENABLED":
                    comp.add("BIND_DEVICE_ADMIN")
    launcher = False
    for tag in ("activity", "activity-alias"):
        for el in xml.iter(tag):
            for f in el.iter("intent-filter"):
                acts = {a.get(ns + "name") for a in f.iter("action")}
                cats = {c.get(ns + "name") for c in f.iter("category")}
                if "android.intent.action.MAIN" in acts and "android.intent.category.LAUNCHER" in cats:
                    launcher = True
    app = next(iter(xml.iter("application")), None)
    clear = None
    if app is not None:
        v = app.get(ns + "usesCleartextTraffic")
        clear = (v.lower() == "true") if v else None
    return {"component_perms": sorted(comp), "launcher": launcher, "cleartext": clear}


def detect_framework(names):
    s = set(names)
    if any(n.endswith("libflutter.so") for n in names):
        return "Flutter"
    if "assets/index.android.bundle" in s or any(n.endswith("libreactnativejni.so") for n in names):
        return "React Native"
    if any(n.startswith("assets/www/") for n in names) and any("cordova" in n.lower() for n in names):
        return "Cordova / WebView"
    if any(n.startswith(("assets/www/", "assets/public/")) and n.endswith("index.html") for n in names):
        return "WebView wrapper"
    if any("xamarin" in n.lower() or n.endswith("libmonodroid.so") for n in names):
        return "Xamarin"
    if any(n.endswith("libunity.so") for n in names):
        return "Unity"
    return "Native Android (Java/Kotlin)"


def dex_string_table(blob: bytes):
    """Read the DEX string_ids table. Returns a list of str, or None when the file is not a usable DEX."""
    if len(blob) < 0x70 or not blob.startswith(b"dex\n"):
        return None
    try:
        size, off = struct.unpack_from("<II", blob, 0x38)
        if size > 2_000_000 or off + size * 4 > len(blob):
            return None
        out = []
        for i in range(size):
            (p,) = struct.unpack_from("<I", blob, off + i * 4)
            # skip the uleb128 utf16 length
            while p < len(blob) and blob[p] & 0x80:
                p += 1
            p += 1
            end = blob.find(b"\x00", p)
            if end < 0:
                break
            out.append(blob[p:end].decode("utf-8", "replace"))
        return out
    except struct.error:
        return None


def clean_ids(ids: dict) -> dict:
    """Drop identifiers that come from SDKs, Java names, version numbers or placeholders."""
    ids = dict(ids)
    urls = []
    for u in ids.get("urls", []):
        host = u["host"]
        if NOISE_HOST.search(host):
            continue
        if not u.get("had_scheme") and not u["raw"].lower().startswith("www."):
            reg = u["reg"]
            tld = reg.split(".", 1)[1] if "." in reg else ""
            if JAVA_PREFIX.match(u["raw"]) or tld not in BARE_TLDS or len(reg.split(".")[0]) < 3:
                continue
        if u["scheme"] not in ("http", "https", "ws", "wss", ""):
            continue
        if re.fullmatch(r"[\d.]+", host) and not _real_ip(host):
            continue
        urls.append(u)
    ids["urls"] = urls
    ids["domains"] = sorted({u["reg"] for u in urls if not re.fullmatch(r"[\d.]+", u["host"])})
    url_hosts = {u["host"] for u in urls}
    ids["ips"] = sorted(i for i in ids.get("ips", []) if _real_ip(i) and (i in url_hosts or _octets_look_real(i)))
    ids["upis"] = sorted(v for v in ids.get("upis", []) if v.split("@")[1] in UPI_HANDLES and re.search(r"[a-z]{2}", v.split("@")[0]))
    ids["emails"] = sorted(e for e in ids.get("emails", []) if not NOISE_HOST.search(e.split("@")[1]))
    ids["phones"] = [p for p in ids.get("phones", []) if not PLACEHOLDER_PHONE.match(p)]
    return ids


def _real_ip(ip):
    try:
        return ipaddress.ip_address(ip).is_global
    except ValueError:
        return False


def _octets_look_real(ip):
    """Version strings like 8.1.2.1 look like IPs; real server addresses rarely have three octets under 10."""
    return sum(int(x) < 10 for x in ip.split(".")) < 3


def _peek(z, n):
    try:
        with z.open(n) as f:
            return f.read(4)
    except Exception:
        return b""


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
