<!-- /officer/cases: search and filter all cases; CSV export. -->
<template>
  <h1>Cases</h1>
  <form class="panel filters" @submit.prevent="apply">
    <input v-model="f.q" type="text" placeholder="Search phone, UPI ID, domain, text or case number" aria-label="Search" />
    <select v-model="f.level" aria-label="Risk"><option value="">Any risk</option><option v-for="l in LEVELS" :key="l">{{ l }}</option></select>
    <select v-model="f.kind" aria-label="Type"><option value="">Any type</option><option v-for="(lab, k) in KIND_LABEL" :key="k" :value="k">{{ lab }}</option></select>
    <select v-model="f.status" aria-label="Status"><option value="">Any status</option><option v-for="(lab, k) in STATUS" :key="k" :value="k">{{ lab }}</option></select>
    <label class="check"><input type="checkbox" v-model="f.flagged" /> Reported by citizens</label>
    <button class="btn">Search</button>
  </form>
  <section class="panel">
    <div class="panel-h"><span class="muted small">{{ rows ? rows.length + ' case(s)' : 'Loading…' }}</span><a v-if="!isProto" href="/police/export.csv" class="small">Export all as CSV</a></div>
    <p v-if="error" class="alert err">{{ error }}</p>
    <CaseTable v-else-if="rows" :rows="rows" empty="No cases match these filters." />
  </section>
</template>

<script setup>
import { reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import CaseTable from "../../components/CaseTable.vue";
import { get, isProto, KIND_LABEL } from "../../api.js";

const route = useRoute(), router = useRouter();
const LEVELS = ["Confirmed fraud", "High", "Medium", "Low", "Verified official", "Not enough data"];
const STATUS = { open: "Open", reviewed: "Reviewed", closed: "Closed", false_positive: "False positive" };
const f = reactive({ q: "", level: "", kind: "", status: "", flagged: false });
const rows = ref(null), error = ref("");

function apply() {
  const q = {};
  for (const k of ["q", "level", "kind", "status"]) if (f[k]) q[k] = f[k];
  if (f.flagged) q.flagged = "1";
  router.push({ path: "/officer/cases", query: q });
}
async function load() {
  Object.assign(f, { q: route.query.q || "", level: route.query.level || "", kind: route.query.kind || "", status: route.query.status || "", flagged: route.query.flagged === "1" });
  rows.value = null; error.value = "";
  try { rows.value = (await get("/api/ui/police/cases?" + new URLSearchParams(route.query))).rows; } catch (e) { error.value = e.message; }
}
watch(() => route.query, load, { immediate: true });
</script>

<style scoped>
.filters { display: grid; grid-template-columns: minmax(220px, 2fr) repeat(3, minmax(120px, 1fr)) auto auto; gap: 10px; align-items: center; padding: 12px; }
.filters .check { margin: 0; white-space: nowrap; }
@media (max-width: 1000px) { .filters { grid-template-columns: 1fr 1fr; } }
</style>
