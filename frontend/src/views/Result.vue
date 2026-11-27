<!-- /r/<id>: a citizen's result: verdict, advice, Detection / Details / Relations / Report tabs, PDF, "Check again". -->
<template>
  <main class="wrap page">
    <p v-if="error" class="alert err">{{ error }}</p>
    <p v-else-if="!c" class="empty">Loading result…</p>
    <template v-else>
      <div class="crumbs small"><RouterLink to="/">Check something else</RouterLink></div>
      <div v-if="$route.query.cached && !rechecked" class="alert cached small">
        <span>This exact input was checked before, so you are seeing that result (first checked {{ c.created }} UTC,
          checked {{ c.times_checked }} time(s) in all). Police labels and rule changes since then are always taken into account.</span>
        <button v-if="c.kind !== 'apk'" class="btn ghost sm" :disabled="rechecking" @click="recheck">{{ rechecking ? 'Checking…' : 'Check again now' }}</button>
      </div>
      <p v-if="recheckErr" class="alert err small">{{ recheckErr }}</p>
      <VerdictHeader :c="c" />
      <AdviceBlock :advice="c.advice" :level="c.level" />

      <section class="panel">
        <div class="seg tabs" role="tablist">
          <button v-for="t in tabs" :key="t.k" :class="{ on: tab === t.k }" @click="tab = t.k" role="tab">{{ t.label }}</button>
        </div>
        <div class="panel-b">
          <DetectionList v-if="tab === 'detection'" :findings="c.findings" />
          <CaseDetails v-else-if="tab === 'details'" :c="c" />
          <div v-else-if="tab === 'relations'">
            <p v-if="c.parent_id" class="small">Followed from case <RouterLink :to="`/r/${c.parent_id}`" class="num">#{{ c.parent_id }}</RouterLink>: {{ c.origin }}</p>
            <table v-if="c.children.length" class="tbl">
              <thead><tr><th>Case</th><th>Risk</th><th>What</th><th>Why it was followed</th></tr></thead>
              <tbody><tr v-for="k in c.children" :key="k.id">
                <td><RouterLink :to="`/r/${k.id}`" class="num">#{{ k.id }}</RouterLink></td><td><LevelTag :level="k.level" /></td>
                <td class="t-trunc">{{ k.title }}</td><td class="small muted">{{ k.origin }}</td></tr></tbody>
            </table>
            <p v-if="!c.parent_id && !c.children.length" class="empty">This check did not lead to other scans. Turn on deep scan to follow links and apps.</p>
          </div>
          <form v-else class="report" @submit.prevent="sendReport">
            <p v-if="c.reports" class="small">Reported {{ c.reports }} time(s) already.</p>
            <p class="small muted">A report puts this case in the police review queue and raises its priority. It never blocks anything by itself.</p>
            <label class="f" for="note">Where did you receive it? Did you lose money?</label>
            <textarea id="note" v-model="note" rows="3" maxlength="1000"></textarea>
            <label class="f" for="contact" style="margin-top:12px">Contact (optional; leave blank to stay anonymous)</label>
            <input id="contact" v-model="contact" type="text" maxlength="120" />
            <div class="row" style="margin-top:14px">
              <button class="btn" :disabled="sending">Send to police review</button>
              <span v-if="sent" class="small" style="color:var(--low)">Thank you. Your report was added to the review queue.</span>
              <span v-if="repErr" class="small" style="color:var(--high)">{{ repErr }}</span>
            </div>
          </form>
        </div>
      </section>

      <div class="row">
        <a v-if="!isProto" class="btn ghost" :href="c.pdf">Download PDF report</a>
        <RouterLink class="btn ghost" to="/">Check something else</RouterLink>
      </div>
    </template>
  </main>
</template>

<script setup>
import { ref, watch } from "vue";
import { useRouter } from "vue-router";
import VerdictHeader from "../components/VerdictHeader.vue";
import AdviceBlock from "../components/AdviceBlock.vue";
import DetectionList from "../components/DetectionList.vue";
import CaseDetails from "../components/CaseDetails.vue";
import LevelTag from "../components/LevelTag.vue";
import { get, isProto, post } from "../api.js";

const p = defineProps({ id: String });
const c = ref(null), error = ref(""), tab = ref("detection");
const note = ref(""), contact = ref(""), sending = ref(false), sent = ref(false), repErr = ref("");
const rechecking = ref(false), rechecked = ref(false), recheckErr = ref("");
const router = useRouter();
async function recheck() {
  rechecking.value = true; recheckErr.value = "";
  try { const r = await post(`/api/ui/case/${p.id}/recheck`); rechecked.value = true; router.push(`/r/${r.id}`); }
  catch (e) { recheckErr.value = e.message; } finally { rechecking.value = false; }
}
const tabs = [{ k: "detection", label: "Detection" }, { k: "details", label: "Details" }, { k: "relations", label: "Relations" }, { k: "report", label: "Report to police" }];

async function load() {
  c.value = null; error.value = ""; tab.value = "detection"; rechecked.value = false;
  try { c.value = await get(`/api/ui/case/${p.id}`); } catch (e) { error.value = e.status === 404 ? "This result does not exist." : e.message; }
}
async function sendReport() {
  sending.value = true; repErr.value = "";
  try { await post(`/api/ui/case/${p.id}/report`, { note: note.value, contact: contact.value }); sent.value = true; c.value.reports++; note.value = ""; }
  catch (e) { repErr.value = e.message; } finally { sending.value = false; }
}
watch(() => p.id, load, { immediate: true });
</script>

<style scoped>
.page { padding-top: 24px; display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; }
.crumbs a { color: var(--muted); }
.tabs { padding: 0 10px; }
.report { max-width: 640px; }
.cached { display: flex; justify-content: space-between; align-items: center; gap: 14px; border-left-color: var(--brass); }
</style>
