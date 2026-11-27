// Shared by popup, background and result pages. Talks only to the Satark server the user configured.
const DEFAULTS = { server: "http://127.0.0.1:5000", apiKey: "" };

async function getSettings() {
  const s = await chrome.storage.local.get(DEFAULTS);
  s.server = (s.server || DEFAULTS.server).replace(/\/+$/, "");
  return s;
}

// Privacy: for a page we send only origin + path. Query strings and fragments can hold tokens or personal data.
function pageUrlForCheck(u) {
  try { const x = new URL(u); return x.origin + x.pathname; } catch (e) { return ""; }
}

async function analyze(body, isForm) {
  const s = await getSettings();
  if (!s.apiKey) throw new Error("Set the server address and API key in the extension options first.");
  const r = await fetch(s.server + "/api/v1/analyze", {
    method: "POST",
    headers: Object.assign({ "X-API-Key": s.apiKey, "X-Client": "extension" }, isForm ? {} : { "Content-Type": "application/json" }),
    body: isForm ? body : JSON.stringify(body)
  });
  let j = {};
  try { j = await r.json(); } catch (e) { /* non-JSON */ }
  if (!r.ok) throw new Error(j.error || ("Server error " + r.status));
  return j;
}

const LEVEL_CLASS = { "High": "high", "Confirmed fraud": "conf", "Medium": "med", "Low": "low", "Verified official": "ok" };
const BADGE = { "High": ["HIGH", "#b3261e"], "Confirmed fraud": ["FRAUD", "#7a0c0c"], "Medium": ["MED", "#b26a00"],
                "Low": ["LOW", "#2e6b34"], "Verified official": ["OK", "#1b5e8c"] };

function el(tag, attrs, text) {
  const e = document.createElement(tag);
  for (const k in (attrs || {})) e.setAttribute(k, attrs[k]);
  if (text !== undefined) e.textContent = text;   // textContent only: server text is never parsed as HTML
  return e;
}

const ACRONYM = /\b(otp|pin|upi|url|apk|kyc|qr|ip|dns|tld|spf|dkim|dmarc|ussd|rbi|xss|idn|sdk|ifsc|gstin|https|mx|vip)\b/gi;
function human(id) {
  const s = id.replace(/_/g, " ").replace(ACRONYM, (m) => m.toUpperCase());
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function ring(flagged, ran) {
  // the same detection ring as the web app: flagged checks out of the checks that ran
  const NS = "http://www.w3.org/2000/svg", size = 76, sw = 7, r = size / 2 - sw / 2 - 1, circ = 2 * Math.PI * r;
  const wrap = el("div", { class: "ring" });
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("width", size); svg.setAttribute("height", size);
  const mk = (stroke, dash) => {
    const c = document.createElementNS(NS, "circle");
    c.setAttribute("cx", size / 2); c.setAttribute("cy", size / 2); c.setAttribute("r", r); c.setAttribute("fill", "none");
    c.setAttribute("stroke-width", sw); c.setAttribute("stroke", stroke);
    if (dash !== undefined) { c.setAttribute("stroke-dasharray", `${dash} ${circ}`); c.setAttribute("transform", `rotate(-90 ${size / 2} ${size / 2})`); }
    return c;
  };
  svg.appendChild(mk("var(--sunk)"));
  if (flagged) svg.appendChild(mk("var(--v)", Math.max(flagged / Math.max(ran, 1), 0.035) * circ));
  wrap.appendChild(svg);
  const c = el("div", { class: "c" });
  c.appendChild(el("div", { class: "n" }, String(flagged)));
  c.appendChild(el("div", { class: "of" }, "/ " + ran));
  wrap.appendChild(c);
  return wrap;
}

function renderResult(root, j) {
  root.textContent = "";
  const v = el("div", { class: "verdict " + (LEVEL_CLASS[j.level] || "nd") });
  const m = j.meter || { flagged: j.reasons.length, ran: j.checks_ran };
  v.appendChild(ring(m.flagged, m.ran));
  const t = el("div");
  t.appendChild(el("div", { class: "lvl" }, j.level + (["High", "Medium", "Low"].includes(j.level) ? " risk" : "")));
  t.appendChild(el("div", { class: "why" }, j.why));
  t.appendChild(el("div", { class: "meta" }, m.flagged + " of " + m.ran + " checks flagged · case #" + j.case_id +
    (j.times_checked > 1 ? " · checked " + j.times_checked + " times" : "")));
  v.appendChild(t);
  root.appendChild(v);
  if (["High", "Confirmed fraud"].includes(j.level)) {
    const h = el("div", { class: "helpline" });
    h.appendChild(el("b", {}, "1930"));
    h.appendChild(document.createTextNode("  Lost money or shared an OTP? Call now and report at cybercrime.gov.in."));
    root.appendChild(h);
  }
  if (j.reasons && j.reasons.length) {
    root.appendChild(el("h3", {}, "Why"));
    const ul = el("ul", { class: "reasons" });
    j.reasons.slice(0, 8).forEach(r => {
      const li = el("li");
      li.appendChild(el("span", { class: "st " + (r.strength === "Hard" ? "h" : "s") }, r.strength === "Hard" ? "Strong" : "Weak"));
      li.appendChild(el("span", {}, human(r.check)));
      li.appendChild(el("div", { class: "d" }, r.detail));
      ul.appendChild(li);
    });
    root.appendChild(ul);
  }
  if (j.advice) {
    root.appendChild(el("h3", {}, "What to do"));
    const ul = el("ul");
    j.advice.en.forEach(x => ul.appendChild(el("li", {}, x)));
    root.appendChild(ul);
    const hi = el("ul", { lang: "hi", class: "hi" });
    j.advice.hi.forEach(x => hi.appendChild(el("li", {}, x)));
    root.appendChild(hi);
  }
  const p = el("p", { class: "hint" });
  p.appendChild(el("a", { href: j.result_url, target: "_blank", rel: "noopener" }, "Open the full report or report it to police"));
  root.appendChild(p);
}

// ---------- assistant ----------
// Privacy: only the question and the case number are sent. Page content is never sent to the assistant.
async function apiCall(path, body) {
  const s = await getSettings();
  if (!s.apiKey) throw new Error("Set the server address and API key in the extension options first.");
  const r = await fetch(s.server + path, {
    method: body ? "POST" : "GET",
    headers: Object.assign({ "X-API-Key": s.apiKey, "X-Client": "extension" }, body ? { "Content-Type": "application/json" } : {}),
    body: body ? JSON.stringify(body) : undefined
  });
  let j = {};
  try { j = await r.json(); } catch (e) { /* non-JSON */ }
  if (!r.ok) throw new Error(j.error || ("Server error " + r.status));
  return j;
}

let aiStatus = null;
async function assistantStatus() {
  if (aiStatus) return aiStatus;
  try { aiStatus = await apiCall("/api/v1/assistant/status"); } catch (e) { aiStatus = { available: false }; }
  return aiStatus;
}

function mountAssistant(root, caseId) {
  const box = el("div", { class: "assist" });
  box.appendChild(el("h3", {}, caseId ? "Ask about this result" : "Ask the assistant"));
  const log = el("div", { class: "alog" });
  box.appendChild(log);
  const chips = el("div", { class: "chips" });
  (caseId ? ["Why is this risky?", "Is it safe to click?", "What should I do now?"]
          : ["How do I report a fraud?", "What is digital arrest?", "Is it safe to share an OTP?"]).forEach(q => {
    const b = el("button", { class: "chipb", type: "button" }, q);
    b.onclick = () => ask(q);
    chips.appendChild(b);
  });
  box.appendChild(chips);
  const form = el("form", { class: "ain" });
  const input = el("input", { type: "text", placeholder: caseId ? "Your question about this result" : "Ask a question", "aria-label": "Your question" });
  const send = el("button", { type: "submit" }, "Ask");
  form.appendChild(input); form.appendChild(send);
  form.onsubmit = (e) => { e.preventDefault(); ask(input.value); input.value = ""; };
  box.appendChild(form);
  root.appendChild(box);

  async function ask(q) {
    q = (q || "").trim();
    if (!q) return;
    log.appendChild(el("div", { class: "q" }, q));
    const dots = el("div", { class: "a typing" });
    for (let n = 0; n < 3; n++) dots.appendChild(el("span"));
    log.appendChild(dots);
    try {
      const st = await assistantStatus();
      const body = { message: q, ai: st.available ? 1 : 0 };
      if (caseId) body.case_id = caseId;
      const r = await apiCall("/api/v1/assistant", body);
      if (r.action === "analyzed" && r.case_id) caseId = r.case_id;
      const a = el("div", { class: "a" });
      dots.replaceWith(a);
      await typeInto(a, r.answer);
      const meta = el("div", { class: "ameta" }, r.source === "ai" ? "AI · checked against the data" : "Checked answer");
      if ("speechSynthesis" in self) {
        const say = el("button", { type: "button", class: "say" }, "Listen");
        say.onclick = () => readAloud(r.answer, say);
        meta.appendChild(say);
      }
      a.appendChild(meta);
    } catch (e) {
      const a = el("div", { class: "a err" }, String(e.message || e));
      dots.replaceWith(a);
    }
  }
}

function readAloud(text, btn) {
  // the computer's own voices (offline); Hindi needs the Windows Hindi language pack
  speechSynthesis.cancel();
  if (btn.dataset.on === "1") { btn.dataset.on = ""; btn.textContent = "Listen"; return; }
  const hi = /[\u0900-\u097F]/.test(text);
  const u = new SpeechSynthesisUtterance(text);
  u.lang = hi ? "hi-IN" : "en-IN";
  const v = speechSynthesis.getVoices().find(x => x.lang === u.lang) || speechSynthesis.getVoices().find(x => x.lang.startsWith(hi ? "hi" : "en"));
  if (v) u.voice = v;
  u.onend = u.onerror = () => { btn.dataset.on = ""; btn.textContent = "Listen"; };
  btn.dataset.on = "1"; btn.textContent = "Stop";
  speechSynthesis.speak(u);
}

function typeInto(node, text) {
  // types the reply out quickly (max ~1.2 s); instant when the user prefers reduced motion
  if (!text || matchMedia("(prefers-reduced-motion: reduce)").matches) { node.textContent = text || ""; return Promise.resolve(); }
  const step = Math.max(2, Math.ceil(text.length / 70));
  return new Promise((done) => {
    let n = 0;
    const t = setInterval(() => {
      n = Math.min(text.length, n + step);
      node.textContent = text.slice(0, n);
      if (n >= text.length) { clearInterval(t); done(); }
    }, 16);
  });
}

async function setBadge(tabId, level) {
  const b = BADGE[level];
  if (!b) return;
  const opt = tabId ? { tabId } : {};
  await chrome.action.setBadgeText(Object.assign({ text: b[0] }, opt));
  await chrome.action.setBadgeBackgroundColor(Object.assign({ color: b[1] }, opt));
}
