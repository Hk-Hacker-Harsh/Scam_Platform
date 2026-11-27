<!-- Table of cases (number, type, risk, input, status, time) used on the officer overview and the case list. -->
<template>
  <p v-if="!rows.length" class="empty">{{ empty }}</p>
  <div v-else class="scroll-x">
    <table class="tbl">
      <thead><tr><th>Case</th><th>Type</th><th>Risk</th><th>Input</th><th>Status</th><th>Received (UTC)</th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id" class="link" @click="$router.push(`/officer/case/${r.id}`)">
          <td><RouterLink :to="`/officer/case/${r.id}`" class="num" @click.stop>#{{ r.id }}</RouterLink></td>
          <td>{{ KIND_LABEL[r.kind] || r.kind }}</td>
          <td class="nw"><LevelTag :level="r.level" /> <span v-if="r.flagged" class="flag" title="Reported by a citizen">reported</span></td>
          <td class="t-trunc" :title="r.title">{{ r.title }}</td>
          <td class="small">{{ STATUS[r.status] || r.status }}</td>
          <td class="num small muted">{{ r.created }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import LevelTag from "./LevelTag.vue";
import { KIND_LABEL } from "../api.js";
defineProps({ rows: Array, empty: { type: String, default: "Nothing here yet." } });
const STATUS = { open: "Open", reviewed: "Reviewed", closed: "Closed", false_positive: "False positive" };
</script>

<style scoped>
.nw { white-space: nowrap; }
.flag { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--brass); font-weight: 600; margin-left: 4px; }
</style>
