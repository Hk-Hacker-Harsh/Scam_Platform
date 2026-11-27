<!-- /officer (overview): totals, risk mix, cases per day, citizen reports waiting, latest cases, top identifiers. -->
<template>
  <p v-if="error" class="alert err">{{ error }}</p>
  <p v-else-if="!d" class="empty">Loading…</p>
  <template v-else>
    <div class="head">
      <h1>Overview</h1>
      <RouterLink to="/officer/new" class="btn">New analysis</RouterLink>
    </div>

    <section class="panel kpis">
      <div v-for="k in kpis" :key="k.l" class="kpi" :class="k.c">
        <div class="v num">{{ k.v }}</div><div class="l">{{ k.l }}</div>
      </div>
    </section>

    <div class="grid-2">
      <section class="panel">
        <div class="panel-h"><h2>Risk mix</h2><span class="muted small num">{{ s.total }} cases</span></div>
        <div class="panel-b">
          <div class="stackbar" aria-hidden="true">
            <i v-for="l in levelRows" :key="l.k" :class="'b-' + l.c" :style="{ width: l.pct + '%' }" :title="`${l.k}: ${l.n}`"></i>
          </div>
          <table class="tbl compact">
            <tbody><tr v-for="l in levelRows" :key="l.k"><td><LevelTag :level="l.k" /></td><td class="num r">{{ l.n }}</td><td class="num r muted">{{ l.pct }}%</td></tr></tbody>
          </table>
          <div class="eyebrow" style="margin-top:14px">By input type</div>
          <div class="kinds"><span v-for="(n, k) in s.by_kind" :key="k" class="chip"><small>{{ KIND_LABEL[k] || k }}</small>{{ n }}</span></div>
        </div>
      </section>
      <section class="panel">
        <div class="panel-h"><h2>Cases per day</h2><span class="muted small">last 14 days with activity</span></div>
        <div class="panel-b">
          <p v-if="!s.by_day.length" class="empty">No data yet.</p>
          <div v-else class="cols" role="img" :aria-label="'Cases per day: ' + s.by_day.map(d => d.d + ' ' + d.n).join(', ')">
            <div v-for="d in s.by_day" :key="d.d" class="col" :title="`${d.d}: ${d.n}`">
              <span class="cv num">{{ d.n }}</span>
              <i :style="{ height: (d.n / maxDay * 100) + '%' }"></i>
              <span class="cl num">{{ d.d.slice(5) }}</span>
            </div>
          </div>
        </div>
      </section>
    </div>

    <section class="panel">
      <div class="panel-h"><h2>Citizen-reported, waiting for review</h2><RouterLink to="/officer/cases?flagged=1&status=open" class="small">All</RouterLink></div>
      <CaseTable :rows="d.queue" empty="No open citizen reports." />
    </section>
    <section class="panel">
      <div class="panel-h"><h2>Latest cases</h2><RouterLink to="/officer/cases" class="small">All cases</RouterLink></div>
      <CaseTable :rows="d.recent" />
    </section>
    <section class="panel">
      <div class="panel-h"><h2>Most-seen identifiers</h2><RouterLink to="/officer/heatlist" class="small">Full heat-list</RouterLink></div>
      <HeatTable :rows="d.heat" />
    </section>
  </template>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import CaseTable from "../../components/CaseTable.vue";
import HeatTable from "../../components/HeatTable.vue";
import LevelTag from "../../components/LevelTag.vue";
import { get, KIND_LABEL, LEVEL_CLASS } from "../../api.js";

const d = ref(null), error = ref("");
const s = computed(() => d.value.stats);
onMounted(async () => { try { d.value = await get("/api/ui/police/overview"); } catch (e) { error.value = e.message; } });
const kpis = computed(() => [
  { l: "Cases", v: s.value.total }, { l: "Today", v: s.value.today },
  { l: "High or confirmed", v: s.value.high, c: "bad" }, { l: "Reported, open", v: s.value.flagged, c: "warn" },
  { l: "Confirmed-fraud identifiers", v: s.value.labels },
]);
const ORDER = ["Confirmed fraud", "High", "Medium", "Low", "Verified official", "Not enough data"];
const levelRows = computed(() => ORDER.filter((k) => s.value.by_level[k]).map((k) => ({
  k, n: s.value.by_level[k], c: LEVEL_CLASS[k], pct: Math.round(s.value.by_level[k] / (s.value.total || 1) * 100) })));
const maxDay = computed(() => Math.max(1, ...s.value.by_day.map((x) => x.n)));
</script>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: center; }
.kpis { display: grid; grid-template-columns: repeat(5, 1fr); }
.kpi { padding: 16px 18px; }
.kpi + .kpi { border-left: 1px solid var(--rule); }
.kpi .v { font-size: 28px; font-weight: 500; line-height: 1.1; }
.kpi .l { font-size: 12px; color: var(--muted); margin-top: 4px; }
.kpi.bad .v { color: var(--high); } .kpi.warn .v { color: var(--brass); }
.stackbar { display: flex; height: 10px; background: var(--sunk); margin-bottom: 12px; }
.stackbar i { display: block; height: 100%; }
.b-high { background: var(--high); } .b-conf { background: var(--conf); } .b-med { background: var(--med); }
.b-low { background: var(--low); } .b-ok { background: var(--ok); } .b-nd { background: var(--nd); }
.compact td { padding: 6px 4px; }
.r { text-align: right; width: 60px; }
.kinds { margin-top: 8px; }
.cols { display: flex; align-items: flex-end; gap: 6px; height: 190px; padding-top: 18px; }
.col { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%; min-width: 0; }
.col i { display: block; width: 100%; max-width: 28px; background: var(--ink-2); min-height: 2px; }
.cv { font-size: 11px; color: var(--muted); margin-bottom: 3px; }
.cl { font-size: 10px; color: var(--muted); margin-top: 5px; white-space: nowrap; }
@media (max-width: 720px) { .kpis { grid-template-columns: repeat(2, 1fr); } .kpi + .kpi { border-left: 0; } .kpi { border-bottom: 1px solid var(--rule); } }
</style>
