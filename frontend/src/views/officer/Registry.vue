<!-- /officer/registry: add or remove police labels (confirmed fraud / verified official) directly. -->
<template>
  <h1>Registry</h1>
  <p class="muted">Identifiers confirmed by officers. These override the rules for every case that contains them.</p>
  <form class="panel add" @submit.prevent="add">
    <select v-model="f.type" aria-label="Type"><option v-for="t in types" :key="t">{{ t }}</option></select>
    <input v-model="f.value" type="text" placeholder="Value, e.g. +919876543210 or bad-site.xyz" aria-label="Value" required />
    <select v-model="f.label" aria-label="Label"><option value="confirmed_fraud">Confirmed fraud</option><option value="verified_official">Verified official</option></select>
    <input v-model="f.note" type="text" placeholder="Note or FIR no." aria-label="Note" maxlength="200" />
    <button class="btn">Add</button>
  </form>
  <p v-if="error" class="alert err">{{ error }}</p>
  <section class="panel">
    <p v-if="!labels" class="empty">Loading…</p>
    <p v-else-if="!labels.length" class="empty">The registry is empty.</p>
    <div v-else class="scroll-x">
      <table class="tbl">
        <thead><tr><th>Identifier</th><th>Label</th><th>Note</th><th>By</th><th>When (UTC)</th><th></th></tr></thead>
        <tbody><tr v-for="l in labels" :key="l.type + l.value">
          <td><span class="muted small">{{ l.type }}</span><br><span class="mono">{{ l.value }}</span></td>
          <td><span class="lv" :class="l.label === 'confirmed_fraud' ? 'lv-conf' : 'lv-ok'">{{ l.label === 'confirmed_fraud' ? 'Confirmed fraud' : 'Verified official' }}</span></td>
          <td class="small">{{ l.note }}</td><td class="small">{{ l.by_user }}</td><td class="num small muted">{{ l.ts }}</td>
          <td><button class="btn ghost sm" @click="remove(l)">Remove</button></td>
        </tr></tbody>
      </table>
    </div>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { get, post } from "../../api.js";
const labels = ref(null), types = ref([]), error = ref("");
const f = reactive({ type: "phone", value: "", label: "confirmed_fraud", note: "" });
async function load() {
  try { const r = await get("/api/ui/police/registry"); labels.value = r.labels; types.value = r.types; } catch (e) { error.value = e.message; }
}
async function add() {
  error.value = "";
  try { await post("/api/ui/police/registry", { ...f }); f.value = ""; f.note = ""; await load(); } catch (e) { error.value = e.message; }
}
async function remove(l) {
  if (!confirm(`Remove ${l.value} from the registry? Future scans will no longer be overridden.`)) return;
  try { await post("/api/ui/police/registry/delete", { type: l.type, value: l.value }); await load(); } catch (e) { error.value = e.message; }
}
onMounted(load);
</script>

<style scoped>
.add { display: grid; grid-template-columns: 150px 2fr 170px 1fr auto; gap: 10px; padding: 12px; }
@media (max-width: 900px) { .add { grid-template-columns: 1fr 1fr; } }
</style>
