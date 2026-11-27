<!-- Top of every result: detection ring, risk level and reason, score, counts, and flags per category. -->
<template>
  <section class="panel verdict" :class="'v-' + cls">
    <div class="ring">
      <RiskMeter :flagged="c.meter.flagged" :ran="c.meter.ran" :level="c.level" caption="checks flagged" />
    </div>
    <div class="main">
      <div class="eyebrow">{{ KIND_LABEL[c.kind] || c.kind }} · case <span class="num">#{{ c.id }}</span></div>
      <h1>{{ headline }}</h1>
      <p class="why">{{ c.why }}</p>
      <p class="title mono" :title="c.title">{{ c.title }}</p>
      <dl class="facts">
        <div><dt>Score</dt><dd><span class="num">{{ Math.round(c.score) }}</span><span class="muted">/100</span>
          <span class="bar" aria-hidden="true"><i :style="{ width: Math.min(100, c.score) + '%' }" /></span></dd></div>
        <div><dt>Strong signals</dt><dd class="num">{{ c.meter.hard }}</dd></div>
        <div><dt>Checks run</dt><dd><span class="num">{{ c.meter.ran }}</span><span class="muted"> of {{ c.meter.total }}</span></dd></div>
        <div><dt>Times checked</dt><dd class="num">{{ c.times_checked || 1 }}</dd></div>
        <div><dt>Citizen reports</dt><dd class="num">{{ c.reports }}</dd></div>
        <div><dt>Checked</dt><dd class="num small">{{ c.created }} UTC</dd></div>
      </dl>
    </div>
    <div class="side">
      <div class="eyebrow">By category</div>
      <ul class="cats">
        <li v-for="g in c.meter.groups.filter(g => g.ran)" :key="g.group">
          <span class="cn">{{ g.group }}</span>
          <span class="cb" aria-hidden="true"><i :style="{ width: (g.flagged / g.ran * 100) + '%' }" :class="{ hard: g.hard }" /></span>
          <span class="cv num" :class="{ hit: g.flagged }">{{ g.flagged }}/{{ g.ran }}</span>
        </li>
      </ul>
      <div class="basis small muted" v-if="c.basis !== 'rules'">
        Decided by {{ c.basis === 'police' ? 'a police label' : 'the official registry' }}, not by the rules.
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from "vue";
import RiskMeter from "./RiskMeter.vue";
import { KIND_LABEL, LEVEL_CLASS } from "../api.js";

const p = defineProps({ c: Object });
const cls = computed(() => LEVEL_CLASS[p.c.level] || "nd");
const headline = computed(() => ["High", "Medium", "Low"].includes(p.c.level) ? `${p.c.level} risk` : p.c.level);
</script>

<style scoped>
.verdict { display: grid; grid-template-columns: auto minmax(0, 1fr) 260px; gap: 28px; padding: 24px; border-top: 3px solid var(--v); }
.v-high { --v: var(--high); } .v-conf { --v: var(--conf); } .v-med { --v: var(--med); } .v-low { --v: var(--low); } .v-ok { --v: var(--ok); } .v-nd { --v: var(--nd); }
.ring { display: grid; align-content: start; }
h1 { color: var(--v); font-size: 30px; margin: 4px 0 6px; }
.why { color: var(--ink-2); max-width: 60ch; }
.title { color: var(--muted); font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; margin: 0; }
.main { min-width: 0; }
.facts { display: flex; flex-wrap: wrap; gap: 8px 28px; margin: 16px 0 0; padding-top: 14px; border-top: 1px solid var(--rule); }
.facts dt { font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); font-weight: 600; }
.facts dd { margin: 2px 0 0; font-size: 15px; display: flex; align-items: center; gap: 4px; }
.bar { display: inline-block; width: 70px; height: 5px; background: var(--sunk); margin-left: 8px; }
.bar i { display: block; height: 100%; background: var(--v); }
.side { border-left: 1px solid var(--rule); padding-left: 24px; }
.cats { list-style: none; margin: 8px 0 0; padding: 0; display: grid; gap: 7px; }
.cats li { display: grid; grid-template-columns: 92px 1fr 42px; align-items: center; gap: 10px; font-size: 13px; }
.cn { color: var(--ink-2); }
.cb { height: 6px; background: var(--sunk); }
.cb i { display: block; height: 100%; background: var(--med); }
.cb i.hard { background: var(--high); }
.cv { text-align: right; color: var(--muted); font-size: 12px; }
.cv.hit { color: var(--ink); font-weight: 500; }
.basis { margin-top: 12px; }
@media (max-width: 900px) {
  .verdict { grid-template-columns: auto minmax(0, 1fr); }
  .side { grid-column: 1 / -1; border-left: 0; padding-left: 0; border-top: 1px solid var(--rule); padding-top: 14px; }
}
@media (max-width: 560px) {
  .verdict { grid-template-columns: minmax(0, 1fr); padding: 18px; gap: 16px; }
  .ring { justify-items: start; }
}
</style>
