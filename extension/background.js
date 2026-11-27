// Right-click menu: check a link before opening it, or check selected text. Nothing runs unless the user clicks.
importScripts("common.js");

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({ id: "check-link", title: "Satark: check this link before opening", contexts: ["link"] });
  chrome.contextMenus.create({ id: "check-text", title: "Satark: check selected text", contexts: ["selection"] });
  chrome.runtime.openOptionsPage();
});

chrome.runtime.onMessage.addListener((msg, sender) => {
  if (msg && msg.type === "snip" && sender.tab) snipAndAnalyze(sender.tab, msg);
  if (msg && msg.type === "snip-cancel" && sender.tab) {
    chrome.action.setBadgeText({ text: "", tabId: sender.tab.id });
    chrome.storage.session.remove("snipShot");          // do not keep the screenshot
  }
});

async function snipAndAnalyze(tab, msg) {
  await chrome.action.setBadgeText({ text: "…", tabId: tab.id });
  await chrome.action.setBadgeBackgroundColor({ color: "#45423c", tabId: tab.id });
  await chrome.storage.session.set({ last: { pending: true, input: "Selected part of " + pageUrlForCheck(tab.url || "") } });
  const resultTab = await chrome.tabs.create({ url: chrome.runtime.getURL("result.html"), index: tab.index + 1 });
  let stored;
  try {
    const { snipShot } = await chrome.storage.session.get("snipShot");
    await chrome.storage.session.remove("snipShot");      // used once, then forgotten
    if (!snipShot || snipShot.tabId !== tab.id || Date.now() - snipShot.at > 10 * 60 * 1000)
      throw new Error("The screenshot for this snip was not found. Click the Satark icon and choose Snip again.");
    const blob = await crop(snipShot.dataUrl, msg.rect, msg.view);
    const fd = new FormData();
    fd.append("kind", "image");
    fd.append("file", blob, "snip.png");
    const j = await analyze(fd, true);
    stored = { ok: true, result: j, input: "Selected part of " + pageUrlForCheck(tab.url || "") };
    await setBadge(tab.id, j.level);
  } catch (e) {
    stored = { ok: false, error: String(e.message || e), input: "Selected part of the page" };
    await chrome.action.setBadgeText({ text: "", tabId: tab.id });
  }
  await chrome.storage.session.set({ last: stored });
  chrome.tabs.update(resultTab.id, { active: true });
}

async function crop(dataUrl, r, view) {
  // the screenshot is in device pixels; the box is in CSS pixels of the viewport
  const bmp = await createImageBitmap(await (await fetch(dataUrl)).blob());
  const sx = bmp.width / view.w, sy = bmp.height / view.h;
  const x = Math.max(0, Math.round(r.x * sx)), y = Math.max(0, Math.round(r.y * sy));
  const w = Math.min(bmp.width - x, Math.round(r.w * sx)), h = Math.min(bmp.height - y, Math.round(r.h * sy));
  // small snips are scaled up so text and QR codes are easier to read
  const k = Math.min(3, Math.max(1, 900 / Math.max(w, h)));
  const c = new OffscreenCanvas(Math.round(w * k), Math.round(h * k));
  const g = c.getContext("2d");
  g.imageSmoothingQuality = "high";
  g.drawImage(bmp, x, y, w, h, 0, 0, c.width, c.height);
  return c.convertToBlob({ type: "image/png" });
}

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  let body;
  // The full link is sent here because the open-redirect and XSS checks need its query string.
  if (info.menuItemId === "check-link") body = { kind: "url", text: info.linkUrl };
  else if (info.menuItemId === "check-text") body = { kind: "auto", text: (info.selectionText || "").slice(0, 20000) };
  else return;
  let stored;
  try {
    const j = await analyze(body, false);
    stored = { ok: true, result: j, input: body.text.slice(0, 300) };
    await setBadge(tab && tab.id, j.level);
  } catch (e) {
    stored = { ok: false, error: String(e.message || e), input: body.text.slice(0, 300) };
  }
  await chrome.storage.session.set({ last: stored });
  chrome.tabs.create({ url: chrome.runtime.getURL("result.html") });
});
