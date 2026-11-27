<!-- /officer/graph: the whole link graph, optionally focused on one case. -->
<template>
  <h1>Link graph</h1>
  <p class="muted lede">Cases (circles) joined to the phone numbers, UPI IDs, domains, wallets and apps they share (diamonds). Dashed arrows are scans that were
    followed automatically. Click a node for details, double-click a case to open it.</p>
  <form class="row" @submit.prevent="apply">
    <input v-model="focus" type="text" inputmode="numeric" placeholder="Focus on case number" class="focus" aria-label="Focus on case number" />
    <label class="check"><input type="checkbox" v-model="all" /> Include identifiers seen only once</label>
    <button class="btn ghost">Update</button>
    <button v-if="url !== base" type="button" class="btn ghost" @click="reset">Reset</button>
  </form>
  <GraphView :url="url" :focus="applied" />
</template>

<script setup>
import { ref } from "vue";
import GraphView from "../../components/GraphView.vue";
const base = "/api/ui/police/graph";
const focus = ref(""), all = ref(false), url = ref(base), applied = ref("");
function apply() {
  const q = new URLSearchParams();
  if (/^\d+$/.test(focus.value.trim())) q.set("case", focus.value.trim());
  if (all.value) q.set("all", "1");
  applied.value = q.get("case") || "";
  url.value = q.toString() ? `${base}?${q}` : base;
}
function reset() { focus.value = ""; all.value = false; apply(); }
</script>

<style scoped>
.lede { max-width: 80ch; }
.focus { max-width: 220px; }
.row .check { margin: 0; }
</style>
