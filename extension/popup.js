// Toolbar popup: check this page, start the snip tool, check a pasted message, ask the assistant.
// Snip: the visible tab is captured here (while the click counts), then snip.js draws the selection box.
let tab = null;
const out = document.getElementById("out");

function busy(on, label) {
  document.querySelectorAll("button").forEach(b => { b.disabled = on; });
  if (on) { out.textContent = ""; out.appendChild(el("p", { class: "hint" }, label || "Checking…")); }
}

function fail(e) { out.textContent = ""; out.appendChild(el("p", { class: "err" }, String(e.message || e))); }

async function run(body, isForm, label) {
  busy(true, label);
  try {
    const j = await analyze(body, isForm);
    renderResult(out, j);
    mountAssistant(out, j.case_id);
    if (tab) setBadge(tab.id, j.level);
  } catch (e) {
    fail(e);
  } finally {
    document.querySelectorAll("button").forEach(b => { b.disabled = false; });
  }
}

mountAssistant(document.getElementById("askBox"), null);

(async () => {
  [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const u = tab ? pageUrlForCheck(tab.url || "") : "";
  document.getElementById("host").textContent = /^https?:/.test(u) ? u : "This tab is not a web page, so only the message check works here.";
  if (!/^https?:/.test(u)) document.getElementById("checkPage").disabled = true;
  // the snip button stays clickable so it can explain why a page cannot be snipped
})();

document.getElementById("checkPage").onclick = () => run({ kind: "url", text: pageUrlForCheck(tab.url) }, false, "Checking this page…");

document.getElementById("snip").onclick = async () => {
  // The popup closes as soon as the page gets focus, so the overlay is drawn by snip.js inside the tab and the
  // capture + crop + upload happen in the background service worker.
  const why = snipBlocked(tab);
  if (why) { fail(new Error(why)); return; }
  try {
    // Chrome only allows a capture while the click on the Satark icon still counts, so the visible page is captured now
    // (before the popup closes) and kept in the extension's session memory. The box drawn next is cropped from this.
    let shot = await chrome.tabs.captureVisibleTab(tab.windowId, { format: "png" });
    if (shot.length > 8_000_000) shot = await chrome.tabs.captureVisibleTab(tab.windowId, { format: "jpeg", quality: 92 });
    await chrome.storage.session.set({ snipShot: { tabId: tab.id, dataUrl: shot, at: Date.now() } });
    await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["snip.js"] });
    window.close();
  } catch (e) {
    const m = String(e && e.message || e);
    fail(new Error(/permission|cannot access|must request/i.test(m)
      ? "Chrome did not allow Satark to draw on this page. Close this popup, click the Satark icon again on the page, then Snip. (" + m + ")"
      : "Could not start the snip tool: " + m));
  }
};

// Say exactly why a page cannot be snipped instead of one catch-all message.
function snipBlocked(t) {
  const url = (t && t.url) || "";
  if (!chrome.scripting) {
    const v = chrome.runtime.getManifest().version;
    return "The snip tool needs a permission added in Satark 1.2.0 (running " + v + "). Open chrome://extensions and click the " +
           "reload ↻ button on Satark, then try again.";
  }
  if (!t || !t.id) return "No page to snip. Click the Satark icon while the page is open.";
  if (/^(chrome|edge|brave|about|devtools|view-source|chrome-extension):/i.test(url))
    return "Browser pages (" + url.split("/")[0] + "//…) are protected by Chrome and cannot be snipped. Open the website itself.";
  if (/^https:\/\/(chromewebstore\.google\.com|chrome\.google\.com\/webstore|microsoftedge\.microsoft\.com\/addons)/i.test(url))
    return "Extension stores are protected by the browser and cannot be snipped.";
  if (/^file:/i.test(url))
    return "This is a file on your computer. To snip local files: chrome://extensions → Satark → Details → turn on " +
           "\"Allow access to file URLs\", then try again.";
  if (url.endsWith(".pdf") || /^https?:\/\/[^/]+\/.*\.pdf(\?|#|$)/i.test(url))
    return "Chrome's PDF viewer cannot be snipped. Take a screenshot (Win+Shift+S) and upload it on the Satark website instead.";
  return "";
}

document.getElementById("checkMsg").onclick = () => {
  const t = document.getElementById("msg").value.trim();
  if (t) run({ kind: "auto", text: t }, false, "Checking message…");
};
