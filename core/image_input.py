"""Screenshot / photo input: decode QR codes (OpenCV, offline) and read text (Tesseract OCR, optional).

Nothing here touches the network. The image is decoded in memory and never saved.
OCR is optional: if `pytesseract` and the Tesseract program are not installed, only QR decoding runs
and the result says so, instead of failing.
"""
import os
import shutil
from urllib.parse import parse_qs, urlsplit

MAX_IMAGE_BYTES = 12 * 1024 * 1024
MAX_SIDE = 2400          # larger images are scaled down before decoding
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


# Where to find the Tesseract program: PS01_TESSERACT, then PATH, then the usual Windows install folders.
_TESS_CANDIDATES = [r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe")]


def tesseract_path():
    p = os.environ.get("PS01_TESSERACT", "").strip()
    if p and os.path.isfile(p):
        return p
    p = shutil.which("tesseract")
    if p:
        return p
    p = _tesseract_from_registry()
    if p:
        return p
    return next((c for c in _TESS_CANDIDATES if os.path.isfile(c)), None)


def _tesseract_from_registry():
    """The UB-Mannheim Windows installer records its folder (any drive) under HKLM/HKCU\\SOFTWARE\\Tesseract-OCR\\Path."""
    try:
        import winreg
    except ImportError:            # not Windows
        return None
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(hive, r"SOFTWARE\Tesseract-OCR") as k:
                folder = winreg.QueryValueEx(k, "Path")[0]
        except OSError:
            continue
        exe = os.path.join(folder, "tesseract.exe")
        if os.path.isfile(exe):
            return exe
    return None


def ocr_available():
    try:
        import pytesseract
    except ImportError:
        return False
    path = tesseract_path()
    if not path:
        return False
    pytesseract.pytesseract.tesseract_cmd = path
    return True


def ocr_languages():
    """Installed OCR languages that we use (eng, hin), or [] when OCR is not available."""
    if not ocr_available():
        return []
    import pytesseract
    try:
        langs = pytesseract.get_languages(config="")
    except Exception:
        return []
    return [l for l in ("eng", "hin") if l in langs]


def _load(data: bytes):
    import cv2
    import numpy as np
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Image is empty or larger than 12 MB")
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("That file is not a readable image (use PNG or JPG)")
    h, w = img.shape[:2]
    if max(h, w) > MAX_SIDE:
        f = MAX_SIDE / max(h, w)
        img = cv2.resize(img, (int(w * f), int(h * f)), interpolation=cv2.INTER_AREA)
    return img


def decode_qr(img):
    """Return the distinct QR payloads found in the image (tries the image, then grayscale and 2x upscale)."""
    import cv2
    det = cv2.QRCodeDetector()
    found = []
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    variants = [img, gray, cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)]
    for v in variants:
        try:
            ok, texts, _pts, _ = det.detectAndDecodeMulti(v)
        except cv2.error:
            ok, texts = False, ()
        if ok:
            for t in texts:
                if t and t not in found:
                    found.append(t)
        if not found:
            try:
                t, _pts, _ = det.detectAndDecode(v)
            except cv2.error:
                t = ""
            if t and t not in found:
                found.append(t)
        if found:
            break
    return found


def ocr_text(img):
    if not ocr_available():
        return None
    import cv2
    import pytesseract
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    if max(h, w) < 1200:                       # small snips: enlarge so the letters are big enough to read
        f = min(3.0, 1200 / max(h, w))
        gray = cv2.resize(gray, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
    if gray.mean() < 110:                      # dark-mode screenshots: Tesseract reads dark text on light best
        gray = 255 - gray
    lang = "+".join(ocr_languages()) or "eng"
    try:
        return pytesseract.image_to_string(gray, lang=lang, config="--psm 6", timeout=25).strip()
    except RuntimeError:                       # timeout on a huge image
        return ""


def parse_upi_qr(payload: str):
    """upi://pay?pa=...&pn=...&am=... -> dict, else None."""
    if not payload.lower().startswith("upi://"):
        return None
    sp = urlsplit(payload)
    q = {k.lower(): v[0] for k, v in parse_qs(sp.query).items()}
    return {"action": sp.netloc.lower() or sp.path.strip("/").lower(), "pa": q.get("pa", ""), "pn": q.get("pn", ""),
            "am": q.get("am", ""), "tn": q.get("tn", ""), "mode": q.get("mode", "")}


def read_image(data: bytes):
    """Return dict(qr=[payloads], ocr=str|None, ocr_available=bool, text=combined text to analyse)."""
    img = _load(data)
    qr = decode_qr(img)
    ocr = ocr_text(img)
    parts = []
    if ocr:
        parts.append(ocr)
    for p in qr:
        u = parse_upi_qr(p)
        if u:
            parts.append(f"QR code: UPI {u['action']} to {u['pa']}" + (f" ({u['pn']})" if u["pn"] else "")
                         + (f" amount {u['am']}" if u["am"] else "") + (f" note: {u['tn']}" if u["tn"] else ""))
        else:
            parts.append(f"QR code: {p}")
    return {"qr": qr, "ocr": ocr, "ocr_available": ocr is not None or ocr_available(), "text": "\n".join(parts)}
