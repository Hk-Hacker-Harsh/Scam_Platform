<!-- Heat-list table: identifiers with how many cases, repeats, high-risk cases, reports and police labels. -->
<template>
  <p v-if="!rows.length" class="empty">No identifiers yet.</p>
  <div v-else class="scroll-x">
    <table class="tbl">
      <thead><tr><th>Identifier</th><th class="r">Cases</th><th class="r" title="All submissions, including repeats of the same input">Seen</th><th class="r">High</th><th class="r">Reported</th><th>Last seen (UTC)</th><th>Police label</th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.type + r.value">
          <td><span class="muted small t">{{ r.type }}</span> <span class="mono">{{ r.value }}</span></td>
          <td class="num r">{{ r.n }}</td>
          <td class="num r muted">{{ r.seen || r.n }}</td>
          <td class="num r" :class="{ hot: r.high }">{{ r.high }}</td>
          <td class="num r">{{ r.flagged || 0 }}</td>
          <td class="num small muted">{{ r.last_seen }}</td>
          <td><span v-if="r.label" class="lv" :class="r.label === 'confirmed_fraud' ? 'lv-conf' : 'lv-ok'">{{ r.label === 'confirmed_fraud' ? 'Confirmed fraud' : 'Verified official' }}</span></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
<script setup>
defineProps({ rows: Array });
</script>
<style scoped>
.r { text-align: right; }
.t { display: inline-block; min-width: 56px; }
.hot { color: var(--high); font-weight: 500; }
</style>
