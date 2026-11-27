<!-- The input form: tabs for message, link, screenshot / QR, Android app and e-mail; sends it for analysis and opens
     the result. Used on the home page and on the officer "New analysis" page. -->
<template>
  <form class="panel checker" @submit.prevent="submit" novalidate>
    <div class="seg" role="tablist">
      <button v-for="t in TABS" :key="t.k" type="button" role="tab" :aria-selected="tab === t.k" :class="{ on: tab === t.k }" @click="setTab(t.k)">{{ t.label }}</button>
    </div>
    <div class="panel-b">
      <template v-if="tab === 'message'">
        <label class="f" for="msg">Message text: SMS, WhatsApp, Telegram. English, Hindi or Hinglish.</label>
        <textarea id="msg" v-model="text" rows="7" placeholder="Paste the full message, including any link and phone number"></textarea>
      </template>

      <template v-else-if="tab === 'url'">
        <label class="f" for="url">Link or domain</label>
        <input id="url" v-model="text" type="text" placeholder="hdfc-kyc-update.example/login" autocomplete="off" spellcheck="false" />
        <details class="more"><summary>Offline demo: paste the page HTML instead of fetching it</summary>
          <textarea v-model="pageHtml" rows="4" placeholder="Optional"></textarea></details>
      </template>

      <template v-else-if="tab === 'image'">
        <label class="f">Screenshot or photo of the message, payment page or QR code</label>
        <FileDrop accept=".png,.jpg,.jpeg,.webp,.bmp,image/*" v-model="file" hint="PNG, JPG or WEBP, up to 12 MB. Read in memory and not stored." />
        <p class="hint">{{ session.ocr ? 'Text (English and Hindi) is read and any QR code decoded.' : 'QR codes are decoded. Text reading (OCR) is not installed on this server, so add the message text below if there is one.' }}</p>
        <label class="f" for="imgtext" style="margin-top:12px">Message text from the screenshot (optional)</label>
        <textarea id="imgtext" v-model="text" rows="3"></textarea>
      </template>

      <template v-else-if="tab === 'apk'">
        <label class="f">Android app file (.apk)</label>
        <FileDrop accept=".apk" v-model="file" hint="Analysed statically. Never installed or run, and deleted right after analysis." />
        <template v-if="session.network">
          <div class="or"><span>or</span></div>
          <label class="f" for="apkurl">Link to an .apk (our server downloads it, up to 150 MB)</label>
          <input id="apkurl" v-model="apkUrl" type="url" placeholder="https://example.test/app.apk" />
        </template>
      </template>

      <template v-else-if="tab === 'email'">
        <label class="f">Original e-mail as a .eml file (Gmail: ⋮ → Download message)</label>
        <FileDrop accept=".eml,.txt" v-model="file" hint="Only the full original lets us read SPF / DKIM / DMARC results." />
        <label class="f" for="eml" style="margin-top:12px">…or paste the original with headers, or just the sender address</label>
        <textarea id="eml" v-model="text" rows="5" placeholder="From: …&#10;Authentication-Results: …&#10;Subject: …"></textarea>
      </template>

      <div v-if="session.network && tab !== 'apk'" class="opts">
        <label class="check"><input type="checkbox" v-model="online" /> <span>Look up domains online (DNS, domain age{{ tab === 'url' ? ', fetch the page' : '' }})</span></label>
        <label class="check" v-if="online"><input type="checkbox" v-model="deep" /> <span><b>Deep scan.</b> Follow what it leads to: APK links are downloaded and analysed, and servers found inside an APK are scanned. Results are linked as separate cases.</span></label>
      </div>
      <label class="check" v-if="session.network && tab === 'apk'"><input type="checkbox" v-model="deep" /> <span><b>Deep scan.</b> Also scan the servers and e-mail addresses found inside the app.</span></label>

      <div v-if="error" class="alert err" role="alert">{{ error }}</div>
      <div class="actions">
        <button class="btn" :disabled="busy">{{ busy ? 'Analysing…' : 'Analyse ' + TABS.find(t => t.k === tab).noun }}</button>
        <span class="muted small">Never share an OTP, PIN or password with anyone, not even someone claiming to be from a bank or the police.</span>
      </div>
    </div>
  </form>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import FileDrop from "./FileDrop.vue";
import { post, session } from "../api.js";

const props = defineProps({ police: Boolean, initial: { type: String, default: "message" } });
const router = useRouter();
const TABS = [
  { k: "message", label: "Message", noun: "message" },
  { k: "url", label: "Link", noun: "link" },
  { k: "image", label: "Screenshot / QR", noun: "screenshot" },
  { k: "apk", label: "Android app", noun: "app" },
  { k: "email", label: "E-mail", noun: "e-mail" },
];
const tab = ref(TABS.some((t) => t.k === props.initial) ? props.initial : "message");
const text = ref(""), pageHtml = ref(""), apkUrl = ref(""), file = ref(null);
const online = ref(true), deep = ref(false), busy = ref(false), error = ref("");

function setTab(k) { tab.value = k; error.value = ""; file.value = null; }

async function submit() {
  error.value = "";
  const fd = new FormData();
  fd.append("kind", tab.value);
  fd.append("text", text.value);
  if (tab.value === "url" && pageHtml.value) fd.append("page_html", pageHtml.value);
  if (tab.value === "apk" && apkUrl.value) fd.append("apk_url", apkUrl.value);
  if (file.value) fd.append("file", file.value, file.value.name);
  fd.append("online", session.network && (online.value || tab.value === "apk") ? "1" : "0");
  fd.append("deep", deep.value ? "1" : "0");
  if (props.police) fd.append("from_police", "1");
  busy.value = true;
  try {
    const r = await post("/api/ui/analyze", fd);
    router.push(props.police ? `/officer/case/${r.id}` : { path: `/r/${r.id}`, query: r.cached ? { cached: "1" } : {} });
  } catch (e) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}
</script>

<style scoped>
.checker .seg { padding: 0 10px; }
.more { margin-top: 10px; font-size: 13px; color: var(--muted); }
.more textarea { margin-top: 8px; min-height: 80px; }
.or { display: flex; align-items: center; gap: 10px; color: var(--muted); font-size: 12px; margin: 14px 0; }
.or::before, .or::after { content: ""; flex: 1; border-top: 1px solid var(--rule); }
.opts { margin-top: 6px; }
.actions { display: flex; align-items: center; gap: 16px; margin-top: 16px; flex-wrap: wrap; }
.actions .small { max-width: 52ch; }
.alert { margin-top: 12px; }
</style>
