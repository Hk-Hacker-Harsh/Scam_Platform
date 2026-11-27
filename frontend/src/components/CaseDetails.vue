<!-- "Details" tab of a case: identifiers found (copyable), screenshot / QR info, redirect chain and APK facts. -->
<template>
  <div class="stack">
    <section>
      <div class="eyebrow">Identifiers found</div>
      <p v-if="!c.ids.length" class="muted small">None found.</p>
      <table v-else class="tbl ids">
        <tbody>
          <tr v-for="i in c.ids" :key="i.type + i.value">
            <td class="t">{{ TYPE[i.type] || i.type }}</td>
            <td class="mono v">{{ i.value }}</td>
            <td class="cp"><button class="btn ghost sm" @click="copy(i.value)">{{ copied === i.value ? 'Copied' : 'Copy' }}</button></td>
          </tr>
        </tbody>
      </table>
    </section>

    <section v-if="m.image">
      <div class="eyebrow">Screenshot</div>
      <p class="small">{{ m.image.qr.length }} QR code(s) decoded. Text reading (OCR): {{ m.image.ocr_used ? 'used' : 'not available on this server' }}.</p>
      <div v-for="q in m.image.qr" :key="q" class="chip">{{ q }}</div>
    </section>

    <section v-if="m.redirects && m.redirects.length">
      <div class="eyebrow">Redirect chain</div>
      <ol class="chain mono small"><li v-for="r in m.redirects" :key="r">{{ r }}</li></ol>
    </section>
    <div v-if="m.fetch_note" class="alert err small">The page could not be fetched: {{ m.fetch_note }}</div>
    <div v-if="m.address_only" class="alert small">Only the sender address was provided, so spoofing (SPF / DKIM / DMARC) could not be checked.</div>

    <section v-if="a">
      <div class="eyebrow">Android app</div>
      <table class="tbl kv">
        <tbody>
          <tr v-if="m.downloaded_from"><th>Downloaded from</th><td class="mono">{{ m.downloaded_from }}</td></tr>
          <tr><th>Package</th><td class="mono">{{ a.package || '—' }}</td></tr>
          <tr><th>App name</th><td>{{ a.label || '—' }} <span class="muted">{{ a.version }}</span></td></tr>
          <tr v-if="a.framework"><th>Built with</th><td>{{ a.framework }}</td></tr>
          <tr><th>SHA-256</th><td class="mono small">{{ a.sha256 }}</td></tr>
          <tr><th>Size</th><td class="num">{{ (a.size / 1048576).toFixed(2) }} MB</td></tr>
          <tr><th>min / target SDK</th><td class="num">{{ a.min_sdk ?? '—' }} / {{ a.target_sdk ?? '—' }}</td></tr>
          <tr><th>Signature</th><td>{{ (a.signed_v || []).join(', ') || 'unknown' }} · {{ a.cert && a.cert.subject || 'no certificate read' }}</td></tr>
          <tr v-if="a.launcher !== undefined && a.launcher !== null"><th>Launcher icon</th><td>{{ a.launcher ? 'Yes' : 'None: the app can stay hidden' }}</td></tr>
          <tr v-if="a.cleartext !== undefined && a.cleartext !== null"><th>Plain http allowed</th><td>{{ a.cleartext ? 'Yes' : 'No' }}</td></tr>
          <tr v-if="a.component_perms && a.component_perms.length"><th>Component rights</th><td class="mono small">{{ a.component_perms.join(', ') }}</td></tr>
          <tr v-if="a.api_refs && a.api_refs.length"><th>Code uses</th><td>{{ a.api_refs.map(x => x.replace(/_/g, ' ')).join(', ') }}</td></tr>
          <tr v-if="a.packers && a.packers.length"><th>Packer libraries</th><td class="mono small">{{ a.packers.join(', ') }}</td></tr>
          <tr v-if="a.hidden_payloads && a.hidden_payloads.length"><th>Code hidden in assets</th><td class="mono small">{{ a.hidden_payloads.join(', ') }}</td></tr>
          <tr><th>Permissions <span class="num">({{ a.perms.length }})</span></th>
            <td><span v-for="p in a.perms" :key="p" class="chip" :class="{ danger: DANGER.has(p) }">{{ p }}</span></td></tr>
          <tr v-if="a.dex_count !== undefined"><th>Analysed</th>
            <td>{{ a.dex_count }} DEX file(s) and {{ a.scanned_files }} asset / resource file(s)<span v-if="a.limited"> · manifest could not be parsed: {{ a.error }}</span></td></tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
const p = defineProps({ c: Object });
const m = computed(() => p.c.meta || {});
const a = computed(() => m.value.apk);
const copied = ref("");
const TYPE = { domain: "Domain", phone: "Phone", upi: "UPI ID", email: "E-mail", crypto: "Crypto wallet", ip: "IP address", tgbot: "Telegram bot",
  apk_sha256: "APK hash", apk_package: "APK package", ifsc: "IFSC", gstin: "GSTIN" };
const DANGER = new Set(["READ_SMS", "RECEIVE_SMS", "SEND_SMS", "READ_CONTACTS", "READ_CALL_LOG", "SYSTEM_ALERT_WINDOW", "BIND_ACCESSIBILITY_SERVICE",
  "REQUEST_INSTALL_PACKAGES", "BIND_DEVICE_ADMIN", "RECORD_AUDIO", "CAMERA", "QUERY_ALL_PACKAGES", "MANAGE_EXTERNAL_STORAGE"]);
async function copy(v) {
  try { await navigator.clipboard.writeText(v); copied.value = v; setTimeout(() => (copied.value = ""), 1500); } catch { /* clipboard blocked */ }
}
</script>

<style scoped>
.ids .t { width: 130px; color: var(--muted); font-size: 13px; }
.ids .v { word-break: break-all; }
.ids .cp { width: 1%; text-align: right; }
.kv th { text-transform: none; letter-spacing: 0; font-size: 13px; font-weight: 500; color: var(--muted); width: 170px; vertical-align: top; padding-top: 11px; }
.chip.danger { border-color: var(--high); color: var(--high); background: var(--high-bg); }
.chain { margin: 6px 0 0; padding-left: 20px; word-break: break-all; }
.eyebrow { margin-bottom: 6px; }
</style>
