<!-- / (home): intro, the checker form, what is checked, and the 1930 helpline box. -->
<template>
  <main class="wrap home">
    <section class="intro">
      <div class="eyebrow">Free check · no sign-in</div>
      <h1>Got a message, link or app you are not sure about? Check it before you act.</h1>
      <p class="lede">Paste an SMS or WhatsApp message, a link, a screenshot with a QR code, an Android app or an e-mail.
        You get a risk level, the exact reasons, and what to do next, in English and Hindi.</p>
    </section>

    <div class="layout">
      <Checker :initial="$route.query.tab || 'message'" />

      <aside class="stack side">
        <section class="panel">
          <div class="panel-h"><h2>What is checked</h2></div>
          <ul class="panel-b list">
            <li><b>Links</b>: look-alike domains, hidden redirects, shorteners, page forms that ask for PINs.</li>
            <li><b>Messages</b>: OTP requests, fake KYC, digital arrest, job and investment scams.</li>
            <li><b>Phone and UPI</b>: numbers posing as bank helplines, UPI IDs with bank names.</li>
            <li><b>Apps</b>: SMS reading, screen control, hidden icons, servers inside the app.</li>
            <li><b>Police records</b>: anything officers have confirmed as fraud.</li>
          </ul>
          <div class="panel-b foot small"><RouterLink to="/catalogue">See all {{ n || '' }} checks</RouterLink></div>
        </section>
        <section class="panel help">
          <div class="panel-b">
            <div class="eyebrow">Already paid or shared an OTP?</div>
            <div class="big num">1930</div>
            <p class="small">Call the national cyber-crime helpline right away and report at <span class="mono">cybercrime.gov.in</span>.
              Tell your bank to block the card or UPI.</p>
            <p class="small" lang="hi">पैसे कट गए हैं तो तुरंत 1930 पर कॉल करें।</p>
          </div>
        </section>
      </aside>
    </div>
  </main>
</template>

<script setup>
import { onMounted, ref } from "vue";
import Checker from "../components/Checker.vue";
import { get } from "../api.js";
const n = ref(0);
onMounted(async () => { try { n.value = (await get("/api/ui/checks")).implemented; } catch { /* optional */ } });
</script>

<style scoped>
.home { padding-top: 36px; }
.intro { max-width: 760px; margin-bottom: 24px; }
.intro h1 { font-size: 32px; line-height: 1.18; margin: 8px 0 12px; letter-spacing: -0.02em; }
.lede { font-size: 16px; color: var(--ink-2); max-width: 64ch; }
.layout { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 24px; align-items: start; }
.list { margin: 0; padding: 14px 18px 4px 34px; display: grid; gap: 8px; font-size: 14px; color: var(--ink-2); }
.foot { padding-top: 6px; }
.help { border-left: 3px solid var(--high); }
.big { font-size: 34px; font-weight: 500; color: var(--high); line-height: 1.1; margin: 4px 0 6px; }
@media (max-width: 900px) { .layout { grid-template-columns: minmax(0, 1fr); } .intro h1 { font-size: 26px; } }
</style>
