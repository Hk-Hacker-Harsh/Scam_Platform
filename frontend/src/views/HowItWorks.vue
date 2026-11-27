<!-- /how-it-works: the four steps (extract, check, link, confirm) and how each risk level is decided. -->
<template>
  <main class="wrap page">
    <div class="eyebrow">How it works</div>
    <h1>Rules decide. Officers confirm. Nothing is called “safe”.</h1>
    <div class="cols">
      <section v-for="s in steps" :key="s.t" class="step">
        <div class="n num">{{ s.n }}</div>
        <h2>{{ s.t }}</h2>
        <p>{{ s.d }}</p>
      </section>
    </div>
    <section class="panel">
      <div class="panel-h"><h2>How a risk level is decided</h2></div>
      <div class="panel-b">
        <table class="tbl">
          <tbody>
            <tr><td><span class="lv lv-conf">Confirmed fraud</span></td><td>An identifier in the input (phone, UPI ID, domain, app) was marked as fraud by the police team. This overrides the rules.</td></tr>
            <tr><td><span class="lv lv-high">High</span></td><td>A decisive signal (for example a request for your OTP, a call-forwarding code, a digital-arrest threat), or two strong signals, or one strong signal backed by another warning sign.</td></tr>
            <tr><td><span class="lv lv-med">Medium</span></td><td>Several weak signs, or a single strong sign with nothing else backing it up.</td></tr>
            <tr><td><span class="lv lv-low">Low</span></td><td>No strong warning signs from the checks that could run. Not a guarantee.</td></tr>
            <tr><td><span class="lv lv-ok">Verified official</span></td><td>All links are on the official registry (RBI-listed banks, government and published brand domains), or an officer verified it.</td></tr>
          </tbody>
        </table>
      </div>
    </section>
  </main>
</template>

<script setup>
const steps = [
  { n: "01", t: "Extract", d: "Links, phone numbers, UPI IDs, e-mails, wallets and app details are pulled out of what you submit. APKs are parsed, never installed or run." },
  { n: "02", t: "Check", d: "Around a hundred small rules look at each part. Every rule that fires says exactly what it saw, so the result can be explained and challenged." },
  { n: "03", t: "Link", d: "Identifiers are compared with earlier cases. The same UPI ID or number across many reports points to one campaign." },
  { n: "04", t: "Confirm", d: "Officers review reported cases and mark identifiers as confirmed fraud or verified official. Every action is in the audit log." },
];
</script>

<style scoped>
.page { padding-top: 32px; display: grid; grid-template-columns: minmax(0, 1fr); gap: 20px; }
h1 { max-width: 30ch; font-size: 30px; letter-spacing: -0.02em; }
.cols { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0; border-top: 1px solid var(--ink); }
.step { padding: 16px 20px 8px 0; }
.step + .step { padding-left: 20px; border-left: 1px solid var(--rule); }
.n { color: var(--brass); font-size: 13px; margin-bottom: 8px; }
.step p { color: var(--ink-2); font-size: 14px; margin-top: 6px; }
.tbl td:first-child { width: 170px; }
@media (max-width: 860px) { .cols { grid-template-columns: 1fr 1fr; } .step:nth-child(3) { border-left: 0; padding-left: 0; } }
@media (max-width: 520px) { .cols { grid-template-columns: 1fr; } .step + .step { border-left: 0; padding-left: 0; border-top: 1px solid var(--rule); } }
</style>
