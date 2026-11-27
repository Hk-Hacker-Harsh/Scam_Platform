// Talks to the Flask server: session state (who is signed in, CSRF token), get/post helpers, shared labels.
// Every screen calls the server only through request() here.
import { reactive } from "vue";
import { transport, isProto } from "@transport";

export { isProto };   // true only in the offline prototype build

// Session state shared by every view: who is logged in, the CSRF token and server capabilities.
export const session = reactive({ ready: false, user: null, role: null, csrf: "", network: false, ocr: false });

export async function loadSession() {
  const s = await request("GET", "/api/ui/session");
  Object.assign(session, s, { ready: true });
  return s;
}

export async function request(method, url, body) {
  const opt = { headers: {} };
  if (method !== "GET") opt.headers["X-CSRF-Token"] = session.csrf;   // the server rejects changes without it
  if (body instanceof FormData) opt.body = body;
  else if (body !== undefined) {
    opt.headers["Content-Type"] = "application/json";
    opt.body = JSON.stringify(body);
  }
  const { status, data } = await transport(method, url, opt);
  if (status < 200 || status >= 300) {
    const e = new Error(data.error || `Request failed (${status})`);
    e.status = status;
    throw e;
  }
  return data;
}

export const get = (url) => request("GET", url);
export const post = (url, body) => request("POST", url, body);

export const LEVEL_CLASS = { "High": "high", "Confirmed fraud": "conf", "Medium": "med", "Low": "low", "Verified official": "ok", "Not enough data": "nd" };
export const KIND_LABEL = { message: "Message", url: "Link", image: "Screenshot", apk: "Android app", email: "E-mail" };

export function humanCheck(id) {
  const s = id.replace(/_/g, " ").replace(/\bapk\b/i, "APK").replace(/\burl\b/i, "URL").replace(/\bupi\b/gi, "UPI")
    .replace(/\botp\b/i, "OTP").replace(/\bxss\b/i, "XSS").replace(/\bidn\b/i, "IDN").replace(/\bqr\b/i, "QR")
    .replace(/\bspf\b/i, "SPF").replace(/\bdkim\b/i, "DKIM").replace(/\bdmarc\b/i, "DMARC").replace(/\bdns\b/i, "DNS").replace(/\bip\b/i, "IP")
    .replace(/\bussd\b/i, "USSD").replace(/\brbi\b/i, "RBI").replace(/\bkyc\b/i, "KYC").replace(/\bsdk\b/i, "SDK")
    .replace(/\btld\b/i, "TLD").replace(/\bpin\b/i, "PIN").replace(/\bmx\b/i, "MX").replace(/\bifsc\b/i, "IFSC").replace(/\bgstin\b/i, "GSTIN")
    .replace(/\bcin\b/i, "CIN").replace(/\bpan\b/i, "PAN").replace(/\bjs\b/i, "JS").replace(/\bjavascript\b/i, "JavaScript").replace(/\bhttps\b/i, "HTTPS")
    .replace(/\bbidi\b/i, "bidi").replace(/\bcert\b/i, "certificate").replace(/\bdyndns\b/i, "dynamic DNS").replace(/\bvip\b/i, "VIP");
  return s.charAt(0).toUpperCase() + s.slice(1);
}
