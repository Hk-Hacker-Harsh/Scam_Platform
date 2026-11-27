<!-- /officer/heatlist: the most-seen identifiers, filterable by type. -->
<template>
  <h1>Heat-list</h1>
  <p class="muted">Identifiers ranked by high-risk cases, repeat sightings and citizen reports.</p>
  <p v-if="error" class="alert err">{{ error }}</p>
  <section class="panel">
    <div class="panel-h"><input v-model="q" type="text" placeholder="Filter" class="flt" aria-label="Filter" />
      <select v-model="type" class="flt-t" aria-label="Type"><option value="">All types</option><option v-for="t in types" :key="t">{{ t }}</option></select></div>
    <p v-if="!rows" class="empty">Loading…</p>
    <HeatTable v-else :rows="shown" />
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import HeatTable from "../../components/HeatTable.vue";
import { get } from "../../api.js";
const rows = ref(null), error = ref(""), q = ref(""), type = ref("");
onMounted(async () => { try { rows.value = (await get("/api/ui/police/heatlist")).rows; } catch (e) { error.value = e.message; } });
const types = computed(() => [...new Set((rows.value || []).map((r) => r.type))].sort());
const shown = computed(() => rows.value.filter((r) => (!type.value || r.type === type.value) && (!q.value || r.value.includes(q.value.trim().toLowerCase()))));
</script>

<style scoped>
.flt { max-width: 280px; padding: 7px 10px; font-size: 13px; }
.flt-t { max-width: 180px; padding: 7px 10px; font-size: 13px; }
</style>
