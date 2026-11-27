// Speech for the assistant.
// Read aloud: the browser's speechSynthesis with the voices installed on the computer (Windows has English, and Hindi
// once the Hindi language pack is added). Works offline.
// Voice input: the browser's SpeechRecognition. In Chrome and Edge this sends the audio to the browser maker's speech
// service, so it needs internet; it is only offered where the browser supports it.
import { ref } from "vue";

export const canSpeak = typeof window !== "undefined" && "speechSynthesis" in window;
const Rec = typeof window !== "undefined" ? (window.SpeechRecognition || window.webkitSpeechRecognition) : null;
export const canListen = !!Rec;

export const speaking = ref(null);     // id of the message being read, or null
export const listening = ref(false);

const isHindi = (t) => /[ऀ-ॿ]/.test(t);

function pickVoice(lang) {
  const vs = window.speechSynthesis.getVoices();
  return vs.find((v) => v.lang === lang) || vs.find((v) => v.lang.startsWith(lang.slice(0, 2))) || null;
}

export function speak(text, id) {
  if (!canSpeak || !text) return;
  window.speechSynthesis.cancel();
  if (speaking.value === id) { speaking.value = null; return; }   // second click stops
  const lang = isHindi(text) ? "hi-IN" : "en-IN";
  const u = new SpeechSynthesisUtterance(text.replace(/#(\d+)/g, "case $1"));
  u.lang = lang;
  const v = pickVoice(lang);
  if (v) u.voice = v;
  u.rate = 0.98;
  u.onend = u.onerror = () => { if (speaking.value === id) speaking.value = null; };
  speaking.value = id;
  window.speechSynthesis.speak(u);
}

export function stopSpeaking() {
  if (canSpeak) window.speechSynthesis.cancel();
  speaking.value = null;
}

let rec = null;
export function listen(lang, onText, onDone) {
  if (!Rec) return;
  if (rec) { rec.stop(); return; }
  stopSpeaking();
  rec = new Rec();
  rec.lang = lang === "hi" ? "hi-IN" : "en-IN";
  rec.interimResults = true;
  rec.maxAlternatives = 1;
  let final = "";
  rec.onresult = (e) => {
    let interim = "";
    for (let i = e.resultIndex; i < e.results.length; i++) {
      if (e.results[i].isFinal) final += e.results[i][0].transcript;
      else interim += e.results[i][0].transcript;
    }
    onText((final + interim).trim());
  };
  rec.onerror = (e) => { listening.value = false; rec = null; onDone(null, e.error); };
  rec.onend = () => { listening.value = false; const r = rec; rec = null; if (r) onDone(final.trim()); };
  listening.value = true;
  rec.start();
}

// some browsers load the voice list late
if (canSpeak) window.speechSynthesis.onvoiceschanged = () => {};
