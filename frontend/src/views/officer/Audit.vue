<!-- /officer/audit: every sign-in, label, status change, re-scan, export and assistant question, newest first. -->
<template>
  <h1>Audit log</h1>
  <p class="muted">Every sign-in, label, status change, re-scan and export. Most recent first.</p>
  <p v-if="error" class="alert err">{{ error }}</p>
  <section class="panel">
    <p v-if="!rows" class="empty">Loading…</p>
    <p v-else-if="!rows.length" class="empty">No entries.</p>
    <div v-else class="scroll-x">
      <table class="tbl">
        <thead><tr><th>When (UTC)</th><th>User</th><th>Action</th><th>Target</th><th>Detail</th></tr></thead>
        <tbody><tr v-for="r in rows" :key="r.id">
          <td class="num small muted">{{ r.ts }}</td><td>{{ r.user }}</td>
          <td><span class="act" :class="{ warn: r.action === 'login_failed', bad: r.action === 'confirmed_fraud' }">{{ r.action.replace(/_/g, ' ') }}</span></td>
          <td class="mono small">{{ r.target }}</td><td class="small">{{ r.detail }}</td>
        </tr></tbody>
      </table>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { get } from "../../api.js";
const rows = ref(null), error = ref("");
onMounted(async () => { try { rows.value = (await get("/api/ui/police/audit")).rows; } catch (e) { error.value = e.message; } });
</script>

<style scoped>
.act { font-size: 13px; }
.act.warn { color: var(--med); font-weight: 500; }
.act.bad { color: var(--high); font-weight: 500; }
</style>
