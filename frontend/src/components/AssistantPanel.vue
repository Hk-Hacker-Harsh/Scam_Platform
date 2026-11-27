<!-- The chat assistant (citizen or officer mode): typing dots, typed-out replies, Listen / auto-speak, voice input,
     suggestion chips and the case it is talking about. Server side: core/assistant.py. -->
<template>
  <button v-if="!open" class="launcher" @click="toggle" aria-label="Open the assistant">
    <span class="dot" :class="{ on: st && st.available }"></span>{{ police ? 'Ask the case assistant' : 'Ask Satark' }}
  </button>

  <aside v-else class="drawer panel" role="dialog" aria-label="Assistant">
    <header class="dh">
      <div>
        <div class="t">{{ police ? 'Case assistant' : 'Satark assistant' }}</div>
        <div class="s small muted">
          <template v-if="!st">Checking AI model…</template>
          <template v-else-if="police && !st.police_ai">Exact answers from the case database</template>
          <template v-else-if="st.available">Local AI ({{ st.model }}) · answers checked against the data</template>
          <template v-else>AI off ({{ st.reason }}) · answers from the data</template>
        </div>
      </div>
      <div class="row">
        <button v-if="canSpeak" class="ico" :class="{ on: autoSpeak }" type="button" @click="setAutoSpeak(!autoSpeak)"
                :aria-pressed="autoSpeak" :title="autoSpeak ? 'Replies are read aloud (click to stop)' : 'Read replies aloud'"
                :aria-label="autoSpeak ? 'Stop reading replies aloud' : 'Read replies aloud'">
          <svg viewBox="0 0 24 24" width="17" height="17" aria-hidden="true"><path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>
            <path v-if="autoSpeak" d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
            <path v-else d="M16 9.5l5 5m0-5l-5 5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>
        </button>
        <div v-if="!police" class="lang" role="group" aria-label="Language">
          <button :class="{ on: lang === 'en' }" @click="lang = 'en'">EN</button>
          <button :class="{ on: lang === 'hi' }" @click="lang = 'hi'" lang="hi">हिं</button>
        </div>
        <button class="x" @click="toggle" aria-label="Close the assistant">×</button>
      </div>
    </header>

    <div ref="log" class="log" aria-live="polite">
      <div v-if="!msgs.length" class="intro small">
        <p>{{ police ? 'Ask about cases, links between cases, reported identifiers or today\'s figures. Answers come from the case database and show the case numbers they use.'
          : (lang === 'hi' ? 'कोई संदिग्ध मैसेज, लिंक, नंबर या UPI ID भेजें, या धोखे के बारे में पूछें।' : 'Paste a suspicious message, link, number or UPI ID, or ask about a scam. The verdict always comes from the rule checks, never from the AI.') }}</p>
      </div>
      <div v-for="(m, i) in msgs" :key="i" class="msg" :class="m.role">
        <div class="bubble">
          <p class="txt">{{ m.shown ?? m.text }}<span v-if="m.typing" class="caret" aria-hidden="true"></span></p>
          <template v-if="m.role === 'bot' && !m.typing">
            <ul v-if="m.items && m.items.length" class="items">
              <li v-for="(it, j) in m.items" :key="j">
                <RouterLink v-if="it.case_id" :to="caseLink(it.case_id)">{{ it.label }}</RouterLink><span v-else>{{ it.label }}</span>
              </li>
            </ul>
            <div v-if="m.cases && m.cases.length" class="cases small">
              Cases: <RouterLink v-for="c in m.cases.slice(0, 10)" :key="c" :to="caseLink(c)" class="num">#{{ c }}</RouterLink>
            </div>
            <RouterLink v-if="m.analyzed" :to="caseLink(m.analyzed)" class="btn ghost sm open">Open the full result #{{ m.analyzed }}</RouterLink>
            <div class="meta small" :title="m.note">
              <span v-if="m.note || m.source === 'ai'" class="src" :class="m.source">{{ m.source === 'ai' ? 'AI · checked against the data' : 'Checked answer' }}</span>
              <button v-if="canSpeak" class="say" type="button" @click="speak(m.text, i)" :aria-label="speaking === i ? 'Stop reading' : 'Read this answer aloud'">
                {{ speaking === i ? 'Stop' : 'Listen' }}
              </button>
            </div>
            <details v-if="m.facts && m.facts.length" class="facts small">
              <summary>Based on</summary>
              <ul><li v-for="(f, j) in m.facts" :key="j">{{ f }}</li></ul>
            </details>
          </template>
        </div>
      </div>
      <div v-if="busy" class="msg bot" aria-label="The assistant is typing">
        <div class="bubble typing"><span></span><span></span><span></span></div>
      </div>
    </div>

    <div class="sugg" v-if="!busy">
      <button v-for="s in suggestions" :key="s" class="chip-b" @click="send(s)">{{ s }}</button>
    </div>
    <div v-if="ctxCase" class="ctx small">About case <span class="num">#{{ ctxCase }}</span>
      <button class="link" @click="ctxCase = null" aria-label="Stop asking about this case">clear</button></div>
    <form class="in" @submit.prevent="send(input)">
      <textarea v-model="input" rows="2" :placeholder="police ? 'e.g. cases linked to 13, top reported numbers' : (lang === 'hi' ? 'अपना सवाल लिखें या मैसेज पेस्ट करें' : 'Ask a question or paste a message')"
                @keydown.enter.exact.prevent="send(input)" aria-label="Your question"></textarea>
      <button v-if="canListen" class="ico mic" :class="{ on: listening }" type="button" @click="voice" :disabled="busy"
              :aria-label="listening ? 'Stop listening' : 'Ask by voice'" :title="listening ? 'Listening… click to stop' : 'Ask by voice (uses your browser\'s speech service, needs internet)'">
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><rect x="9" y="3.5" width="6" height="11" rx="3" fill="none" stroke="currentColor" stroke-width="1.7"/>
          <path d="M6 11.5a6 6 0 0 0 12 0M12 17.5v3" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>
      </button>
      <button class="btn" :disabled="busy || !input.trim()">Send</button>
    </form>
    <p v-if="micErr" class="micerr small">{{ micErr }}</p>
  </aside>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { get, post } from "../api.js";
import { canListen, canSpeak, listen, listening, speak, speaking, stopSpeaking } from "../speech.js";

const p = defineProps({ police: Boolean, caseId: [String, Number] });
const open = ref(false), st = ref(null), msgs = ref([]), input = ref(""), busy = ref(false), lang = ref("en"), log = ref(null);
const ctxCase = ref(p.caseId || null);
const micErr = ref("");
// prototype screenshots only: ?ask=question opens the panel and asks it
onMounted(async () => {
  const q = import.meta.env.MODE === "proto" ? new URLSearchParams(location.search).get("ask") : null;
  if (q) setTimeout(async () => { await toggle(); send(q); }, 900);   // after the route (and its case number) has loaded
});
function savedAuto() { try { return localStorage.getItem("satark-autospeak") === "1"; } catch { return false; } }
const autoSpeak = ref(savedAuto());
function setAutoSpeak(v) {
  autoSpeak.value = v;
  if (!v) stopSpeaking();
  try { localStorage.setItem("satark-autospeak", v ? "1" : "0"); } catch { /* not remembered */ }
}
function voice() {
  micErr.value = "";
  listen(lang.value, (t) => { input.value = t; }, (final, err) => {
    if (err) micErr.value = err === "not-allowed" ? "Microphone permission was refused." :
      err === "network" ? "Voice input needs internet (the browser's speech service)." : "Could not hear that. Try again.";
    else if (final) send(final);
  });
}
watch(() => p.caseId, (v) => { ctxCase.value = v || null; });

const suggestions = computed(() => {
  if (p.police) return ctxCase.value ? [`Summarise case ${ctxCase.value}`, `Cases linked to ${ctxCase.value}`, "Open citizen reports"]
    : ["Summary of today", "Top reported identifiers", "Campaigns", "Latest high-risk cases"];
  if (lang.value === "hi") return ctxCase.value ? ["यह खतरनाक क्यों है?", "अब मुझे क्या करना चाहिए?", "शिकायत कैसे करें?"]
    : ["शिकायत कैसे करें?", "डिजिटल अरेस्ट क्या है?", "पैसे कट गए, क्या करूं?"];
  return ctxCase.value ? ["Why is this risky?", "Is it safe to click the link?", "What should I do now?", "How do I report it?"]
    : ["How do I report a fraud?", "What is digital arrest?", "Is it safe to share an OTP?", "I lost money, what now?"];
});

const caseLink = (id) => (p.police ? `/officer/case/${id}` : `/r/${id}`);

async function loadStatus() {
  try { st.value = await get("/api/ui/assistant/status"); } catch { st.value = { available: false, reason: "unreachable" }; }
}

async function toggle() {
  open.value = !open.value;
  if (!open.value) stopSpeaking();
  if (open.value && !st.value) await loadStatus();
}

function scroll() { nextTick(() => { if (log.value) log.value.scrollTop = log.value.scrollHeight; }); }

async function send(text) {
  text = (text || "").trim();
  if (!text || busy.value) return;
  input.value = "";
  msgs.value.push({ role: "user", text });
  scroll();
  busy.value = true;
  if (!st.value) await loadStatus();
  const useAi = !!(st.value && st.value.available && (!p.police || st.value.police_ai));
  const payload = { message: text, lang: lang.value, mode: p.police ? "police" : "citizen", ai: useAi ? 1 : 0 };
  if (!p.police && ctxCase.value) payload.case_id = ctxCase.value;
  let m;
  try {
    const r = await post("/api/ui/assistant", payload);
    m = { role: "bot", text: r.answer, source: r.source, note: r.note, facts: r.facts, items: r.items,
          cases: p.police ? r.case_ids : null, analyzed: r.action === "analyzed" ? r.case_id : null };
    if (r.action === "analyzed" && !p.police) ctxCase.value = r.case_id;   // follow-up questions are about this case
  } catch (e) {
    m = { role: "bot", text: e.message, source: "rules", note: "" };
  }
  busy.value = false;
  msgs.value.push(m);
  typeOut(msgs.value[msgs.value.length - 1]);
}

// Reveal the reply as if typed: fast, at most ~1.2 s, and instant for people who prefer reduced motion.
const reduce = typeof window !== "undefined" && window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
function typeOut(m) {
  if (reduce || !m.text) { scroll(); if (autoSpeak.value && m.text) speak(m.text, msgs.value.indexOf(m)); return; }
  const full = m.text, step = Math.max(2, Math.ceil(full.length / 70));
  m.typing = true; m.shown = "";
  let n = 0;
  const t = setInterval(() => {
    n = Math.min(full.length, n + step);
    m.shown = full.slice(0, n);
    scroll();
    if (n >= full.length) { clearInterval(t); m.typing = false; m.shown = undefined; scroll(); if (autoSpeak.value) speak(full, msgs.value.indexOf(m)); }
  }, 16);
}
</script>

<style scoped>
.launcher { position: fixed; right: 20px; bottom: 20px; z-index: 30; display: inline-flex; align-items: center; gap: 8px; font: 500 14px var(--sans);
  padding: 11px 16px; border-radius: var(--r); border: 1px solid var(--ink); background: var(--ink); color: var(--paper); cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, .12); }
.launcher:hover { background: var(--ink-2); }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--muted); }
.dot.on { background: var(--brass); }
.drawer { position: fixed; right: 16px; bottom: 16px; top: 76px; width: min(420px, calc(100vw - 32px)); z-index: 30; display: flex; flex-direction: column;
  box-shadow: 0 8px 28px rgba(0, 0, 0, .14); }
.dh { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; padding: 12px 14px; border-bottom: 1px solid var(--rule); }
.t { font-weight: 600; }
.x { background: none; border: 0; font-size: 22px; line-height: 1; color: var(--muted); cursor: pointer; padding: 0 4px; }
.x:hover { color: var(--ink); }
.lang { display: flex; border: 1px solid var(--rule-strong); border-radius: var(--r); overflow: hidden; }
.lang button { font: 500 12px var(--sans); background: none; border: 0; padding: 4px 8px; cursor: pointer; color: var(--muted); }
.lang button.on { background: var(--ink); color: var(--paper); }
.log { flex: 1; overflow-y: auto; padding: 14px; display: grid; gap: 10px; align-content: start; }
.intro { color: var(--ink-2); background: var(--sunk); padding: 10px 12px; border-radius: var(--r); }
.intro p { margin: 0; }
.msg { display: flex; }
.msg.user { justify-content: flex-end; }
.bubble { max-width: 92%; padding: 9px 12px; border-radius: var(--r); font-size: 14px; }
.user .bubble { background: var(--ink); color: var(--paper); }
.bot .bubble { background: var(--sunk); border: 1px solid var(--rule); }
.txt { margin: 0; white-space: pre-wrap; word-break: break-word; }
.typing { display: inline-flex; gap: 4px; align-items: center; padding: 12px 14px; }
.typing span { width: 7px; height: 7px; border-radius: 50%; background: var(--muted); animation: blink 1.2s infinite ease-in-out both; }
.typing span:nth-child(2) { animation-delay: .15s; }
.typing span:nth-child(3) { animation-delay: .3s; }
@keyframes blink { 0%, 80%, 100% { opacity: .25; transform: translateY(0); } 40% { opacity: 1; transform: translateY(-3px); } }
.caret { display: inline-block; width: 2px; height: 1em; background: var(--ink-2); margin-left: 2px; vertical-align: -2px; animation: caret .8s steps(2) infinite; }
@keyframes caret { 50% { opacity: 0; } }
@media (prefers-reduced-motion: reduce) { .typing span, .caret, .mic.on { animation: none; } }
.items { margin: 8px 0 0; padding-left: 18px; font-size: 13px; }
.items li { margin: 3px 0; }
.cases { margin-top: 6px; display: flex; flex-wrap: wrap; gap: 4px 8px; }
.open { margin-top: 8px; }
.meta { margin-top: 6px; }
.src { font-weight: 600; }
.src.ai { color: var(--brass); }
.src.rules { color: var(--ink-2); }
.facts { margin-top: 4px; color: var(--ink-2); }
.facts summary { cursor: pointer; color: var(--muted); }
.facts ul { margin: 4px 0; padding-left: 18px; }
.sugg { display: flex; flex-wrap: wrap; gap: 6px; padding: 8px 14px 0; }
.chip-b { font: 13px var(--sans); background: var(--surface); border: 1px solid var(--rule-strong); border-radius: 999px; padding: 4px 10px; cursor: pointer; color: var(--ink-2); }
.chip-b:hover { border-color: var(--ink); color: var(--ink); }
.ctx { padding: 6px 14px 0; color: var(--muted); }
.link { background: none; border: 0; color: var(--ink-2); text-decoration: underline; cursor: pointer; font: inherit; }
.in { display: flex; gap: 8px; padding: 10px 14px 14px; align-items: flex-end; }
.ico { display: inline-grid; place-items: center; width: 32px; height: 32px; border: 1px solid var(--rule-strong); border-radius: var(--r);
  background: var(--surface); color: var(--ink-2); cursor: pointer; flex: none; }
.ico:hover { border-color: var(--ink); color: var(--ink); }
.ico.on { background: var(--ink); color: var(--paper); border-color: var(--ink); }
.mic { width: 40px; height: 40px; }
.mic.on { background: var(--high); border-color: var(--high); color: #fff; animation: pulse 1.2s infinite; }
@keyframes pulse { 50% { box-shadow: 0 0 0 4px var(--high-bg); } }
.say { background: none; border: 0; padding: 0; margin-left: 10px; font: 500 12px var(--sans); color: var(--ink-2); cursor: pointer;
  text-decoration: underline; text-decoration-color: var(--rule-strong); text-underline-offset: 3px; }
.say:hover { color: var(--ink); }
.micerr { margin: -8px 14px 10px; color: var(--high); }
.in textarea { min-height: 44px; max-height: 120px; font-size: 14px; }
@media (max-width: 640px) { .drawer { top: 12px; right: 8px; bottom: 8px; width: calc(100vw - 16px); } .launcher { right: 12px; bottom: 12px; } }
</style>
