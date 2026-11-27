// Prototype transport: answers the app's API calls from sample data recorded from the real Satark engine
// (fixtures.json, made by tools/make_prototype.py). Used only by `npm run build:proto`; nothing is sent anywhere.
import fx from "./fixtures.json";

export const isProto = true;

const ids = fx.meta.ids;
const mem = { user: null };
try { mem.user = sessionStorage.getItem("satark-proto-user"); } catch { /* private mode */ }
// screenshot helpers (prototype only): ?as=officer opens the officer pages without the sign-in form
if (new URLSearchParams(location.search).get("as") === "officer") mem.user = "officer.demo";

const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const ok = (data) => ({ status: 200, data });
const err = (status, error) => ({ status, data: { error } });

// Which sample case a submission maps to (the prototype has no engine; the full app analyses anything).
function pickCase(kind, text) {
  const t = (text || "").toLowerCase();
  if (kind === "image") return ids.qr;
  if (kind === "apk") return ids.apk;
  if (kind === "email") return ids.email;
  if (kind === "url") {
    if (/[^\x00-\x7f]/.test(text)) return ids.url_homograph;
    if (/^(https?:\/\/)?(www\.)?(onlinesbi\.sbi|sbi\.co\.in)\/?$/.test(t.trim())) return ids.url_official;
    return ids.url_trick;
  }
  if (/[ऀ-ॿ]/.test(text)) return ids.hindi;
  if (/arrest|cbi|customs|parcel|narcotic/.test(t)) return ids.arrest;
  if (/job|task|youtube|earn|telegram/.test(t)) return ids.job;
  if (/lottery|kbc|won|prize|lucky/.test(t)) return ids.lottery;
  if (/electric|bijli|bill|disconnect/.test(t)) return ids.bill;
  if (/refund|sbi\.kyc@ybl/.test(t)) return ids.confirmed;
  if (/otp|kyc|block|account|bank|link|http|upi/.test(t)) return ids.sbi_kyc;
  return ids.benign;
}

const SMALL = /^\s*(hi+|hello+|hey+|namaste|thanks?|thank you|ok+|okay|bye|नमस्ते|धन्यवाद)[\s!.,?]*$/i;

function assistant(body) {
  const mode = body.mode === "police" ? "police" : "citizen";
  const q = String(body.message || "").trim().toLowerCase();
  const hit = fx.assistant[`${mode}|${mode === "police" ? "" : (body.case_id || "")}|${q}`]
    || (mode === "citizen" && fx.assistant[`citizen||${q}`]);
  if (hit) return hit;
  if (mode === "citizen" && SMALL.test(q)) return fx.assistant["citizen||hello"];
  return { answer: mode === "police"
      ? "This prototype answers the suggested questions from sample data. In the full app the case assistant answers from the live case database."
      : "This prototype answers the suggested questions from sample data. In the full Satark app the assistant checks any message, link, number or UPI ID and answers any cyber-safety question.",
    source: "rules", note: "Prototype: sample answers only.", facts: [], action: "help" };
}

function filterCases(qs) {
  const p = new URLSearchParams(qs);
  const q = (p.get("q") || "").toLowerCase();
  return fx.allcases.filter((r) => (!q || (r.title + " " + r.id).toLowerCase().includes(q.replace(/^#/, "")) ||
      Object.values(fx.pcases[r.id]?.ids || []).some((i) => i.value.includes(q)))
    && (!p.get("level") || r.level === p.get("level")) && (!p.get("kind") || r.kind === p.get("kind"))
    && (!p.get("status") || r.status === p.get("status")) && (p.get("flagged") !== "1" || r.flagged));
}

export async function transport(method, url, opt = {}) {
  const [path, qs = ""] = url.split("?");
  let body = {};
  if (opt.body instanceof FormData) body = Object.fromEntries([...opt.body.entries()].filter(([, v]) => typeof v === "string"));
  else if (opt.body) body = JSON.parse(opt.body);
  const kindOf = opt.body instanceof FormData ? opt.body.get("kind") : body.kind;
  let m;

  // ---- session and public pages
  if (path === "/api/ui/session") return ok({ user: mem.user, role: mem.user ? "admin" : null, csrf: "proto", network: false, ocr: true,
    kinds: ["message", "email", "url", "apk", "image"] });
  if (path === "/api/ui/login") {
    await wait(400);
    mem.user = String(body.username || "").trim() || "officer";
    try { sessionStorage.setItem("satark-proto-user", mem.user); } catch { /* not kept */ }
    return ok({ user: mem.user, role: "admin", csrf: "proto" });
  }
  if (path === "/api/ui/logout") { mem.user = null; try { sessionStorage.removeItem("satark-proto-user"); } catch { /* */ } return ok({ ok: true, csrf: "proto" }); }
  if (path === "/api/ui/checks") return ok(fx.checks);
  if (path === "/api/ui/assistant/status") return ok(fx.status);
  if (path === "/api/ui/assistant") {
    if (body.mode === "police" && !mem.user) return err(401, "login required");
    await wait(700 + Math.random() * 700);          // the real model takes a few seconds; show the typing dots
    return ok(assistant(body));
  }
  if (path === "/api/ui/analyze") {
    await wait(900);
    const text = body.text || body.apk_url || "";
    if (!text.trim() && !["image", "apk", "email"].includes(kindOf)) return err(400, "Paste the message text");
    return ok({ id: pickCase(kindOf, text), cached: false });
  }
  if ((m = path.match(/^\/api\/ui\/case\/(\d+)$/))) return fx.cases[m[1]] ? ok(fx.cases[m[1]]) : err(404, "not found");
  if ((m = path.match(/^\/api\/ui\/case\/(\d+)\/report$/))) { fx.cases[m[1]].reports++; return ok({ ok: true }); }
  if ((m = path.match(/^\/api\/ui\/case\/(\d+)\/recheck$/))) { await wait(700); return ok({ id: +m[1] }); }

  // ---- officer pages
  if (path.startsWith("/api/ui/police/")) {
    if (!mem.user) return err(401, "login required");
    const p = path.slice("/api/ui/police/".length);
    if (p === "overview") return ok(fx.overview);
    if (p === "cases") return ok({ rows: filterCases(qs) });
    if (p === "campaigns") return ok(fx.campaigns);
    if (p === "heatlist") return ok(fx.heatlist);
    if (p === "audit") return ok(fx.audit);
    if (p === "registry" && method === "GET") return ok(fx.registry);
    if (p === "registry") {
      fx.registry.labels.unshift({ ...body, by_user: mem.user, ts: new Date().toISOString().slice(0, 19).replace("T", " ") });
      return ok({ ok: true });
    }
    if (p === "registry/delete") { fx.registry.labels = fx.registry.labels.filter((l) => !(l.type === body.type && l.value === body.value)); return ok({ ok: true }); }
    if (p === "graph") {
      const c = new URLSearchParams(qs).get("case");
      return ok(c && fx.graphs[c] ? fx.graphs[c] : new URLSearchParams(qs).get("all") ? fx.graph_all : fx.graph);
    }
    if ((m = p.match(/^case\/(\d+)$/))) return fx.pcases[m[1]] ? ok(fx.pcases[m[1]]) : err(404, "not found");
    if ((m = p.match(/^case\/(\d+)\/status$/))) { fx.pcases[m[1]].status = body.status; return ok({ ok: true }); }
    if ((m = p.match(/^case\/(\d+)\/rescan$/))) return ok({ id: +m[1] });
    if ((m = p.match(/^case\/(\d+)\/label$/))) {
      const c = fx.pcases[m[1]];
      c.labels = c.labels.filter((l) => !(l.type === body.type && l.value === body.value));
      if (body.label !== "clear") c.labels.push({ type: body.type, value: body.value, label: body.label, by_user: mem.user, ts: new Date().toISOString().slice(0, 10) });
      return ok({ ok: true });
    }
  }
  return err(404, "Not available in the prototype");
}
