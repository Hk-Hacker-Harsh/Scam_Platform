// Normal transport: real HTTP calls to the Flask server (same origin, session cookie).
// The prototype build swaps this file for src/proto/transport.js (see vite.config.js).
export const isProto = false;

export async function transport(method, url, opt) {
  const r = await fetch(url, { method, credentials: "same-origin", ...opt });
  let data = {};
  try { data = await r.json(); } catch { /* empty or non-JSON body */ }
  return { status: r.status, data };
}
