<!-- "Detection" tab: every check grouped by category with Flagged strong / weak, Clean, Not applicable or Skipped,
     and the exact evidence for each flag. -->
<template>
  <div>
    <div class="toolbar">
      <div class="seg mini" role="tablist">
        <button :class="{ on: view === 'flagged' }" @click="view = 'flagged'">Flagged <span class="num">{{ flagged.length }}</span></button>
        <button :class="{ on: view === 'ran' }" @click="view = 'ran'">All that ran <span class="num">{{ ranList.length }}</span></button>
        <button :class="{ on: view === 'all' }" @click="view = 'all'">Everything <span class="num">{{ findings.length }}</span></button>
      </div>
      <input v-model="q" type="text" class="search" placeholder="Filter checks" aria-label="Filter checks" />
    </div>

    <p v-if="!shown.length" class="empty">{{ view === 'flagged' ? 'No check flagged this input. That is not a guarantee of safety.' : 'No checks match.' }}</p>

    <div v-for="g in grouped" :key="g.group" class="grp">
      <div class="gh"><span class="eyebrow">{{ g.group }}</span><span class="muted small num">{{ g.items.filter(f => f.status === 'fired' && f.weight > 0).length }} flagged</span></div>
      <ul class="grid">
        <li v-for="f in g.items" :key="f.id" :class="'s-' + kind(f)">
          <button class="row-b" @click="open[f.id] = !open[f.id]" :aria-expanded="!!open[f.id]">
            <span class="cname">{{ humanCheck(f.id) }}</span>
            <span class="st">{{ label(f) }}</span>
          </button>
          <div v-if="open[f.id] || (kind(f) !== 'clean' && kind(f) !== 'na' && kind(f) !== 'skip' && view === 'flagged')" class="det">
            <div v-if="f.detail" class="what mono">{{ f.detail }}</div>
            <div class="desc muted">{{ f.desc }}</div>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from "vue";
import { humanCheck } from "../api.js";

const p = defineProps({ findings: Array });
const view = ref("flagged");
const q = ref("");
const open = reactive({});
const ORDER = ["Intelligence", "URL", "Domain", "Website", "Message", "Email", "Phone", "Payment", "APK"];

const flagged = computed(() => p.findings.filter((f) => f.status === "fired" && f.weight > 0));
const ranList = computed(() => p.findings.filter((f) => f.status === "fired" || f.status === "clear"));
const shown = computed(() => {
  const base = view.value === "flagged" ? flagged.value : view.value === "ran" ? ranList.value : p.findings;
  const s = q.value.trim().toLowerCase();
  return s ? base.filter((f) => (f.id + " " + f.desc + " " + (f.detail || "")).toLowerCase().includes(s)) : base;
});
const rank = (f) => ({ hard: 0, soft: 1, info: 2, error: 3, clean: 4, skip: 5, na: 6 })[kind(f)];
const grouped = computed(() => {
  const m = {};
  for (const f of shown.value) (m[f.group] ||= []).push(f);
  return Object.keys(m).sort((a, b) => (ORDER.indexOf(a) + 99) % 99 - (ORDER.indexOf(b) + 99) % 99)
    .map((g) => ({ group: g, items: m[g].sort((a, b) => rank(a) - rank(b) || b.weight - a.weight) }));
});

function kind(f) {
  if (f.status === "fired") return f.weight > 0 ? (f.tier === "H" ? "hard" : "soft") : "info";
  return { clear: "clean", na: "na", skipped: "skip", error: "error" }[f.status] || "na";
}
function label(f) {
  return { hard: "Flagged · strong", soft: "Flagged · weak", info: "Note", clean: "Clean", na: "Not applicable", skip: "Skipped (offline)", error: "Error" }[kind(f)];
}
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 8px; }
.seg.mini { border-bottom: 0; }
.seg.mini button { padding: 8px 10px; font-size: 13px; }
.seg.mini .num { color: var(--muted); margin-left: 4px; font-size: 12px; }
.search { max-width: 220px; padding: 7px 10px; font-size: 13px; }
.grp + .grp { margin-top: 18px; }
.gh { display: flex; justify-content: space-between; align-items: baseline; padding: 0 2px 6px; border-bottom: 1px solid var(--rule); }
.grid { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: 1fr 1fr; column-gap: 28px; }
.grid li { border-bottom: 1px solid var(--rule); }
.row-b { width: 100%; display: flex; justify-content: space-between; align-items: center; gap: 12px; padding: 9px 2px; background: none; border: 0;
  font: inherit; color: inherit; text-align: left; cursor: pointer; }
.row-b:hover .cname { text-decoration: underline; text-decoration-color: var(--rule-strong); text-underline-offset: 3px; }
.cname { font-size: 14px; }
.st { font-size: 12.5px; white-space: nowrap; display: inline-flex; align-items: center; gap: 6px; }
.st::before { content: ""; width: 8px; height: 8px; border-radius: 50%; border: 1.5px solid currentColor; }
.s-hard .st { color: var(--high); font-weight: 600; } .s-hard .st::before { background: currentColor; }
.s-soft .st { color: var(--med); font-weight: 600; } .s-soft .st::before { background: currentColor; }
.s-clean .st { color: var(--low); }
.s-na .st, .s-skip .st, .s-info .st { color: var(--muted); }
.s-na .cname, .s-skip .cname { color: var(--muted); }
.s-error .st { color: var(--med); }
.det { padding: 0 2px 10px; font-size: 13px; }
.what { background: var(--sunk); padding: 6px 8px; border-radius: 3px; margin-bottom: 4px; word-break: break-word; font-size: 12.5px; }
.s-hard .what { border-left: 2px solid var(--high); } .s-soft .what { border-left: 2px solid var(--med); }
@media (max-width: 720px) { .grid { grid-template-columns: 1fr; } }
</style>
