"""Screenshots of the browser extension's UI, rendered from the extension's own HTML, CSS and scripts.

Headless Chrome cannot open an extension popup, so this builds small pages that load extension/style.css and
extension/common.js with a stand-in for the `chrome.*` API, and feeds them a sample result from the prototype data
(frontend/src/proto/fixtures.json). Output: manual/screenshots/18-ext-popup.png, 19-ext-snip.png, 20-ext-result-tab.png
Usage: python tools/ext_screenshots.py    (after tools/make_prototype.py)
"""
import html
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from screenshots import ROOT, browser, run  # noqa: E402

EXT = os.path.join(ROOT, "extension")
OUT = os.path.join(ROOT, "manual", "screenshots")


def api_json(case):
    """The /api/v1 reply shape the extension receives, built from a prototype case."""
    fired = [f for f in case["findings"] if f["status"] == "fired" and f["weight"] > 0]
    fired.sort(key=lambda f: (f["tier"] != "H", -f["weight"]))
    return {"case_id": case["id"], "level": case["level"], "score": case["score"], "why": case["why"],
            "meter": {"flagged": case["meter"]["flagged"], "ran": case["meter"]["ran"]}, "times_checked": 1,
            "reasons": [{"check": f["id"], "strength": "Hard" if f["tier"] == "H" else "Soft", "detail": f["detail"]} for f in fired],
            "advice": case["advice"], "result_url": "#"}


STUB = """<script>
// stand-in for the chrome.* extension API (screenshots only)
window.chrome = { storage: { local: { get: async d => d }, session: { get: async () => ({}), set: async () => {} },
  onChanged: { addListener() {} } }, runtime: { getManifest: () => ({ version: "1.2.2" }) } };
</script>"""


def page(body, width, extra=""):
    css = open(os.path.join(EXT, "style.css"), encoding="utf-8").read()
    js = open(os.path.join(EXT, "common.js"), encoding="utf-8").read()
    return (f"<!doctype html><meta charset=utf-8><style>{css}\nhtml{{background:#d9d6cf}}body{{width:{width}px;margin:24px auto;"
            f"box-shadow:0 8px 30px rgba(0,0,0,.18);border-radius:6px}}{extra}</style>{STUB}<script>{js}</script>{body}")


def main():
    fx = json.load(open(os.path.join(ROOT, "frontend", "src", "proto", "fixtures.json"), encoding="utf-8"))
    cid = fx["meta"]["ids"]["url_trick"]
    j = api_json(fx["cases"][str(cid)])
    answer = fx["assistant"].get(f"citizen|{cid}|is it safe to click the link?", {}).get("answer", "")
    exe, tmp = browser(), tempfile.mkdtemp(prefix="satark-ext-")
    os.makedirs(OUT, exist_ok=True)

    # 1. popup: page address, buttons, result with the ring, and one assistant exchange
    popup = page(f"""<div class="top"><span class="mark">S</span><h1>Satark</h1></div>
<div class="host">http://sbi.co.in@sbi-kyc-update.xyz/login</div>
<button>Check this page</button><button class="sec">✚ Snip part of the screen</button>
<div id="out"></div>
<script>
renderResult(document.getElementById("out"), {json.dumps(j)});
const box = el("div", {{class: "assist"}}); box.appendChild(el("h3", {{}}, "Ask about this result"));
const log = el("div", {{class: "alog"}}); log.appendChild(el("div", {{class: "q"}}, "Is it safe to click the link?"));
const a = el("div", {{class: "a"}}, {json.dumps(answer)}); a.appendChild(el("div", {{class: "ameta"}}, "Checked answer · Listen"));
log.appendChild(a); box.appendChild(log); document.getElementById("out").appendChild(box);
</script>""", 400)
    # 2. snip: a sample messages page with the overlay and a box being drawn (the overlay markup of extension/snip.js)
    msg = html.escape(fx["cases"][str(fx["meta"]["ids"]["sbi_kyc"])]["title"].replace("…", ""))
    snip = f"""<!doctype html><meta charset=utf-8><style>
body{{margin:0;font:15px Segoe UI,system-ui;background:#eef0f3}}.bar{{background:#2f3a4a;color:#fff;padding:14px 22px;font-weight:600}}
.wrap{{display:flex;height:calc(100vh - 48px)}}.side{{width:300px;background:#fff;border-right:1px solid #ddd;padding:12px}}
.side div{{padding:12px;border-bottom:1px solid #eee;color:#555}}.chat{{flex:1;padding:30px}}
.b{{background:#fff;border-radius:10px;padding:14px 16px;max-width:520px;margin:0 0 14px;box-shadow:0 1px 2px rgba(0,0,0,.1);line-height:1.45}}
.ov{{position:fixed;inset:0;cursor:crosshair}}
.box{{position:fixed;left:342px;top:66px;width:578px;height:118px;border:2px solid #c9a24a;background:rgba(255,255,255,.08);
box-shadow:0 0 0 9999px rgba(28,27,25,.35)}}
.tip{{position:fixed;top:14px;left:50%;transform:translateX(-50%);background:#1c1b19;color:#f6f4ef;font:500 13px Segoe UI;padding:8px 14px;border-radius:4px}}
.tip b{{color:#c9a24a}}.size{{position:fixed;left:342px;top:192px;font:12px Consolas;background:#c9a24a;color:#1c1b19;padding:1px 5px}}
.cur{{position:fixed;left:880px;top:260px;font:28px monospace;color:#fff}}</style>
<div class="bar">Messages (sample page)</div><div class="wrap"><div class="side"><div><b>VK-SBIALR</b><br>SBI ALERT: Dear customer…</div>
<div>Mom<br>Call me when free</div><div>Office<br>Meeting at 4 pm</div></div>
<div class="chat"><div class="b">{msg} … Pay Rs 10 verification fee to sbi.kyc@ybl. Call +923001234567</div>
<div class="b" style="background:#e7f3ff;margin-left:auto">Is this real??</div></div></div>
<div class="ov"><div class="box"></div><div class="size">578 × 118</div><div class="cur" style="left:908px;top:168px">+</div>
<div class="tip"><b>Satark</b> · drag a box around the message or QR code · <b>Esc</b> to cancel</div></div>"""
    # 3. result tab after a snip
    tab = page(f"""<div class="top"><span class="mark">S</span><h1>Satark result</h1></div>
<div class="host">Selected part of https://messages.example/</div><div id="out"></div>
<script>renderResult(document.getElementById("out"), {json.dumps(api_json(fx['cases'][str(fx['meta']['ids']['qr'])]))});</script>""",
               720, "body{padding:20px 26px}")

    for name, body, size in (("18-ext-popup", popup, "520,1300"), ("19-ext-snip", snip, "1280,720"), ("20-ext-result-tab", tab, "900,1100")):
        p = os.path.join(tmp, name + ".html")
        open(p, "w", encoding="utf-8").write(body)
        out = os.path.join(OUT, name + ".png")
        run(exe, [f"--window-size={size}", "--virtual-time-budget=2000", f"--screenshot={out}", "file:///" + p.replace("\\", "/")])
        print("  ", os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
