// Snip tool: injected into the current tab only when the user clicks "Snip part of the screen" in the popup.
// Shows a + crosshair over the page; the user drags a box; Esc or a right-click cancels.
// Only the box's position is sent to the extension; the extension then captures and crops the visible tab itself.
(() => {
  if (window.__satarkSnip) return;            // already open in this tab
  window.__satarkSnip = true;

  const root = document.createElement("div");
  root.setAttribute("data-satark-snip", "");
  const sh = root.attachShadow({ mode: "closed" }); // page styles cannot reach the overlay
  sh.innerHTML = `
    <style>
      .ov { position: fixed; inset: 0; z-index: 2147483647; cursor: crosshair; background: rgba(28,27,25,.35); user-select: none; }
      .box { position: fixed; border: 2px solid #c9a24a; background: rgba(255,255,255,.08); box-shadow: 0 0 0 9999px rgba(28,27,25,.35); display: none; }
      .ov.dragging { background: transparent; }
      .tip { position: fixed; top: 14px; left: 50%; transform: translateX(-50%); background: #1c1b19; color: #f6f4ef;
             font: 500 13px/1.4 "Segoe UI", system-ui, sans-serif; padding: 8px 14px; border-radius: 4px; pointer-events: none;
             box-shadow: 0 2px 10px rgba(0,0,0,.25); }
      .tip b { color: #c9a24a; }
      .size { position: fixed; font: 12px Consolas, monospace; color: #1c1b19; background: #c9a24a; padding: 1px 5px; border-radius: 2px; display: none; pointer-events: none; }
    </style>
    <div class="ov"><div class="box"></div><div class="size"></div>
      <div class="tip"><b>Satark</b> · drag a box around the message or QR code · <b>Esc</b> to cancel</div></div>`;
  const ov = sh.querySelector(".ov"), box = sh.querySelector(".box"), size = sh.querySelector(".size");
  document.documentElement.appendChild(root);
  // the screenshot was taken when Snip was clicked: stop the page scrolling under the box until the snip is done
  const stopScroll = (e) => { e.preventDefault(); };
  const scrollKeys = (e) => { if (["ArrowUp", "ArrowDown", "PageUp", "PageDown", "Home", "End", " "].includes(e.key)) e.preventDefault(); };
  window.addEventListener("wheel", stopScroll, { passive: false, capture: true });
  window.addEventListener("touchmove", stopScroll, { passive: false, capture: true });
  window.addEventListener("keydown", scrollKeys, true);

  let x0 = 0, y0 = 0, drag = false;
  const rect = (e) => ({ x: Math.min(x0, e.clientX), y: Math.min(y0, e.clientY), w: Math.abs(e.clientX - x0), h: Math.abs(e.clientY - y0) });

  function close() {
    window.removeEventListener("keydown", onKey, true);
    window.removeEventListener("wheel", stopScroll, { capture: true });
    window.removeEventListener("touchmove", stopScroll, { capture: true });
    window.removeEventListener("keydown", scrollKeys, true);
    root.remove();
    window.__satarkSnip = false;
  }
  function onKey(e) {
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); close(); chrome.runtime.sendMessage({ type: "snip-cancel" }); }
  }

  ov.addEventListener("mousedown", (e) => {
    if (e.button !== 0) return;
    e.preventDefault();
    drag = true; x0 = e.clientX; y0 = e.clientY;
    ov.classList.add("dragging");
    Object.assign(box.style, { display: "block", left: x0 + "px", top: y0 + "px", width: "0px", height: "0px" });
  });
  ov.addEventListener("mousemove", (e) => {
    if (!drag) return;
    const r = rect(e);
    Object.assign(box.style, { left: r.x + "px", top: r.y + "px", width: r.w + "px", height: r.h + "px" });
    Object.assign(size.style, { display: "block", left: r.x + "px", top: Math.max(0, r.y - 20) + "px" });
    size.textContent = `${Math.round(r.w)} × ${Math.round(r.h)}`;
  });
  ov.addEventListener("mouseup", (e) => {
    if (!drag) return;
    drag = false;
    const r = rect(e);
    close();
    if (r.w < 12 || r.h < 12) { chrome.runtime.sendMessage({ type: "snip-cancel" }); return; }
    chrome.runtime.sendMessage({ type: "snip", rect: r, dpr: window.devicePixelRatio || 1,
                                 view: { w: window.innerWidth, h: window.innerHeight } });
  });
  ov.addEventListener("contextmenu", (e) => { e.preventDefault(); close(); chrome.runtime.sendMessage({ type: "snip-cancel" }); });
  window.addEventListener("keydown", onKey, true);
})();
