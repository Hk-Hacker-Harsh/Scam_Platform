<!-- /catalogue: every check with its strength, whether it needs internet, and whether it is live or planned. -->
<template>
  <main class="wrap page">
    <div>
      <div class="eyebrow">Check catalogue</div>
      <h1>{{ data ? data.implemented : '…' }} checks run today, {{ data ? data.total - data.implemented : '…' }} planned</h1>
      <p class="lede">Each check is a small rule with a stated reason. <b>Strong</b> checks can decide a High result when they are decisive or backed by
        another signal. <b>Weak</b> checks only add up and cap at Medium. Checks marked <i>online</i> need internet lookups and are skipped offline.</p>
    </div>
    <div class="row filters">
      <input v-model="q" type="text" placeholder="Filter by name or description" aria-label="Filter checks" />
      <label class="check"><input type="checkbox" v-model="liveOnly" /> Live checks only</label>
    </div>
    <section v-for="g in groups" :key="g.name" class="panel">
      <div class="panel-h"><h2>{{ g.name }}</h2><span class="muted small num">{{ g.rows.filter(r => r.implemented).length }} / {{ g.rows.length }} live</span></div>
      <div class="scroll-x">
        <table class="tbl">
          <thead><tr><th>Check</th><th>Strength</th><th>Online</th><th>Status</th></tr></thead>
          <tbody>
            <tr v-for="r in g.rows" :key="r.id">
              <td><div>{{ humanCheck(r.id) }}</div><div class="small muted">{{ r.desc }}</div></td>
              <td class="small">{{ { H: 'Strong', S: 'Weak', L: 'Info / linking' }[r.tier] }}</td>
              <td class="small">{{ r.net === 'Y' ? 'online' : '' }}</td>
              <td><span class="st" :class="r.implemented ? 'live' : 'plan'">{{ r.implemented ? 'Live' : 'Planned' }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { get, humanCheck } from "../api.js";
const data = ref(null), q = ref(""), liveOnly = ref(false);
onMounted(async () => { data.value = await get("/api/ui/checks"); });
const groups = computed(() => {
  if (!data.value) return [];
  const s = q.value.trim().toLowerCase(), m = {};
  for (const r of data.value.checks) {
    if (liveOnly.value && !r.implemented) continue;
    if (s && !(r.id + " " + r.desc).toLowerCase().includes(s)) continue;
    (m[r.group] ||= []).push(r);
  }
  return Object.entries(m).map(([name, rows]) => ({ name, rows }));
});
</script>

<style scoped>
.page { padding-top: 32px; display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; }
h1 { margin: 6px 0 10px; }
.lede { color: var(--ink-2); max-width: 75ch; }
.filters input { max-width: 340px; }
.st { font-size: 12px; font-weight: 600; }
.st.live { color: var(--low); } .st.plan { color: var(--muted); }
</style>
