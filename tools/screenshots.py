"""Take PNG screenshots of the Satark prototype (and the extension UI) with headless Chrome or Edge.

Needs the prototype first: python tools/make_prototype.py
Usage:  python tools/screenshots.py [--out manual/screenshots] [--only result-high]
Every screen uses the prototype's synthetic sample data, so no real case data ends up in a screenshot.
Also writes Satark_Wireframes.pdf (the main screens in wireframe view) next to the screenshots.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTO = os.path.join(ROOT, "frontend", "dist-proto", "Satark_Prototype.html")
BROWSERS = [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", "google-chrome", "chromium", "msedge"]

# name -> (route, query, viewport w, h, wait ms)
SHOTS = {
    "01-home":              ("/", "", 1600, 1000, 2500),
    "02-result-high":       ("/r/1", "", 1600, 1000, 2500),
    "03-result-detection":  ("/r/1", "scroll=900", 1600, 1000, 3000),
    "04-result-apk":        ("/r/12", "tab=details", 1600, 1000, 3000),
    "05-result-official":   ("/r/9", "", 1600, 1000, 2500),
    "06-assistant":         ("/r/1", "ask=Why is this risky?", 1600, 1000, 6000),
    "07-assistant-hindi":   ("/", "ask=डिजिटल अरेस्ट क्या है?", 1600, 1000, 6000),
    "08-officer-overview":  ("/officer", "as=officer", 1600, 1000, 3000),
    "09-officer-cases":     ("/officer/cases", "as=officer", 1600, 1000, 3000),
    "10-officer-case":      ("/officer/case/1", "as=officer", 1600, 1000, 3000),
    "11-officer-graph":     ("/officer/graph", "as=officer", 1600, 1000, 5000),
    "12-officer-campaigns": ("/officer/campaigns", "as=officer", 1600, 1000, 3000),
    "13-officer-heatlist":  ("/officer/heatlist", "as=officer", 1600, 1000, 3000),
    "14-officer-assistant": ("/officer", "as=officer&ask=Top reported identifiers", 1600, 1000, 6000),
    "15-dark-result":       ("/r/1", "theme=dark", 1600, 1000, 2500),
    "16-catalogue":         ("/catalogue", "", 1600, 1000, 2500),
    "17-phone-result":      ("/r/1", "", 420, 900, 2500),
}
WIRES = ["01-home", "02-result-high", "06-assistant", "08-officer-overview", "10-officer-case", "11-officer-graph"]


def browser():
    for b in BROWSERS:
        p = b if os.path.isabs(b) else shutil.which(b)
        if p and os.path.isfile(p):
            return p
    sys.exit("Chrome or Edge not found")


def run(exe, args, timeout=90):
    prof = tempfile.mkdtemp(prefix="satark-shot-")       # clean profile: no history, cookies or extensions
    try:
        subprocess.run([exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", "--no-default-browser-check",
                        "--blink-settings=preferredColorScheme=1",          # light, whatever the computer's theme
                        f"--user-data-dir={prof}", "--force-device-scale-factor=1", *args],
                       check=True, capture_output=True, timeout=timeout)
    finally:
        time.sleep(0.3)
        shutil.rmtree(prof, ignore_errors=True)


def url_for(route, query, extra=""):
    q = "&".join(p for p in (query, extra) if p)
    q = "&".join(f"{k}={quote(v)}" for k, _, v in (s.partition("=") for s in q.split("&")) if k) if q else ""
    return "file:///" + PROTO.replace("\\", "/") + (f"?{q}" if q else "") + "#" + route


def shot(exe, name, out, wire=False):
    route, query, w, h, ms = SHOTS[name]
    path = os.path.join(out, f"{name}{'-wire' if wire else ''}.png")
    run(exe, [f"--window-size={w},{h}", f"--virtual-time-budget={ms}", f"--screenshot={path}",
              url_for(route, query, "wire=1" if wire else "")])
    print("  ", os.path.relpath(path, ROOT))
    return path


def wire_pdf(exe, pngs, out_pdf):
    """Print the wireframe screenshots into one PDF, one screen per landscape page."""
    page = os.path.join(tempfile.mkdtemp(prefix="satark-wire-"), "wire.html")
    titles = {"01-home": "Citizen checker", "02-result-high": "Result: detection meter and advice", "06-assistant": "Assistant on a result",
              "08-officer-overview": "Officer overview", "10-officer-case": "Officer case view", "11-officer-graph": "Link graph"}
    body = "".join(f'<section><h1>Satark · {titles.get(os.path.basename(p)[:-9], "")}</h1>'
                   f'<img src="file:///{p.replace(os.sep, "/")}"></section>' for p in pngs)
    open(page, "w", encoding="utf-8").write(
        "<!doctype html><meta charset=utf-8><style>@page{size:A4 landscape;margin:10mm}body{margin:0;font:14px Segoe UI,Arial}"
        "section{page-break-after:always;text-align:center}h1{font-size:16px;font-weight:600;margin:0 0 6px;text-align:left}"
        "img{max-width:100%;max-height:175mm;border:1px solid #999}</style>" + body)
    run(exe, ["--no-pdf-header-footer", f"--print-to-pdf={out_pdf}", "file:///" + page.replace("\\", "/")])
    print("  ", out_pdf)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(ROOT, "manual", "screenshots"))
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    if not os.path.isfile(PROTO):
        sys.exit("Build the prototype first: python tools/make_prototype.py")
    os.makedirs(a.out, exist_ok=True)
    exe = browser()
    names = [n for n in SHOTS if not a.only or n == a.only]
    for n in names:
        shot(exe, n, a.out)
    if not a.only:
        wires = [shot(exe, n, a.out, wire=True) for n in WIRES]
        wire_pdf(exe, wires, os.path.join(a.out, "Satark_Wireframes.pdf"))
