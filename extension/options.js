// Settings page: server address and API key (kept in chrome.storage.local), with a connection test.
(async () => {
  const s = await getSettings();
  document.getElementById("server").value = s.server;
  document.getElementById("key").value = s.apiKey;
})();

document.getElementById("save").onclick = async () => {
  const server = document.getElementById("server").value.trim().replace(/\/+$/, "") || DEFAULTS.server;
  const apiKey = document.getElementById("key").value.trim();
  const st = document.getElementById("status");
  await chrome.storage.local.set({ server, apiKey });
  try {
    const h = await (await fetch(server + "/api/v1/health")).json();
    st.textContent = "Saved. Server is up: " + h.checks + " checks, online lookups " + (h.network ? "on" : "off") + ", OCR " + (h.ocr ? "on" : "off") + ".";
  } catch (e) {
    st.textContent = "Saved, but the server did not answer: " + e.message;
  }
};
