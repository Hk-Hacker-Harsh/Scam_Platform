// Result tab opened after a right-click check or a snip: shows a waiting state, then the result and the assistant.
function show(last) {
  const out = document.getElementById("out");
  out.textContent = "";
  if (!last) { out.textContent = "No result yet."; return; }
  document.getElementById("input").textContent = last.input || "";
  if (last.pending) {
    const p = el("div", { class: "a typing pending" });
    for (let n = 0; n < 3; n++) p.appendChild(el("span"));
    out.appendChild(p);
    out.appendChild(el("p", { class: "hint" }, "Reading the text and any QR code in the selected area…"));
    return;
  }
  if (last.ok) { renderResult(out, last.result); mountAssistant(out, last.result.case_id); }
  else out.appendChild(el("p", { class: "err" }, last.error));
}

(async () => {
  const { last } = await chrome.storage.session.get("last");
  show(last);
  chrome.storage.onChanged.addListener((ch, area) => { if (area === "session" && ch.last) show(ch.last.newValue); });
})();
