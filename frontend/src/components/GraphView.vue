<!-- Link graph (Cytoscape): cases as circles, shared identifiers as diamonds, followed scans as dashed arrows.
     Loads static/cytoscape.min.js from the server, so it works offline. -->
<template>
  <div class="gwrap" :class="{ mini }">
    <div ref="el" class="g"></div>
    <p v-if="msg" class="empty overlay">{{ msg }}</p>
    <aside v-if="sel" class="tip panel">
      <template v-if="sel.kind === 'case'">
        <div class="eyebrow">Case <span class="num">#{{ sel.cid }}</span></div>
        <LevelTag :level="sel.level" />
        <p class="small t">{{ sel.title }}</p>
        <RouterLink :to="`/officer/case/${sel.cid}`" class="small">Open case</RouterLink>
      </template>
      <template v-else>
        <div class="eyebrow">{{ sel.itype }}</div>
        <p class="mono small t">{{ sel.id.split(':').slice(2).join(':') }}</p>
        <p class="small muted">In {{ sel.n }} case(s){{ sel.police ? ' · ' + sel.police.replace('_', ' ') : '' }}</p>
      </template>
    </aside>
    <div class="legend small">
      <span><i class="dot" style="background:var(--high)"></i>High / confirmed</span>
      <span><i class="dot" style="background:var(--med)"></i>Medium</span>
      <span><i class="dot" style="background:var(--low)"></i>Low</span>
      <span><i class="dot" style="background:var(--ok)"></i>Verified official</span>
      <span><i class="dia"></i>Shared identifier</span>
      <span><i class="line"></i>Followed automatically</span>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import LevelTag from "./LevelTag.vue";
import { get } from "../api.js";
import { theme } from "../theme.js";

const p = defineProps({ url: String, focus: [String, Number], mini: Boolean });
const el = ref(null), msg = ref("Loading…"), sel = ref(null);
const router = useRouter();
let cy = null;

function loadLib() {
  if (window.cytoscape) return Promise.resolve(window.cytoscape);
  return new Promise((ok, bad) => {
    const s = document.createElement("script");
    s.src = "/static/cytoscape.min.js";      // bundled with the server, works offline
    s.onload = () => ok(window.cytoscape);
    s.onerror = () => bad(new Error("graph library could not be loaded"));
    document.head.appendChild(s);
  });
}

async function draw() {
  msg.value = "Loading…"; sel.value = null;
  try {
    const [cytoscape, g] = await Promise.all([loadLib(), get(p.url)]);
    if (cy) cy.destroy();
    if (!g.nodes.length) { msg.value = "Nothing to draw yet. Cases appear once they share an identifier or one scan leads to another."; return; }
    msg.value = "";
    const css = getComputedStyle(document.documentElement), v = (n) => css.getPropertyValue(n).trim();
    const lc = { "High": v("--high"), "Confirmed fraud": v("--conf"), "Medium": v("--med"), "Low": v("--low"), "Verified official": v("--ok") };
    cy = cytoscape({
      container: el.value, elements: g.nodes.concat(g.edges), wheelSensitivity: 0.3, minZoom: 0.2, maxZoom: 3,
      style: [
        { selector: "node", style: { label: "data(label)", "font-size": 10, "font-family": "IBM Plex Mono, monospace", color: v("--ink-2"),
          "text-valign": "bottom", "text-margin-y": 4, "text-wrap": "ellipsis", "text-max-width": 120, "min-zoomed-font-size": 7 } },
        { selector: 'node[kind="case"]', style: { shape: "ellipse", width: 26, height: 26, "background-color": (n) => lc[n.data("level")] || v("--nd"),
          "border-width": (n) => (n.data("flagged") ? 3 : 0), "border-color": v("--brass") } },
        { selector: 'node[kind="identifier"]', style: { shape: "diamond", width: (n) => 14 + Math.min(n.data("n"), 8) * 3,
          height: (n) => 14 + Math.min(n.data("n"), 8) * 3, "background-color": v("--rule-strong") } },
        { selector: 'node[police="confirmed_fraud"]', style: { "border-width": 3, "border-color": v("--high"), "background-color": v("--ink") } },
        { selector: 'node[police="verified_official"]', style: { "border-width": 3, "border-color": v("--ok") } },
        { selector: "edge", style: { width: 1.2, "line-color": v("--rule-strong"), "curve-style": "bezier" } },
        { selector: 'edge[rel="followed"]', style: { "line-style": "dashed", "line-color": v("--ink-2"), "target-arrow-shape": "triangle",
          "target-arrow-color": v("--ink-2"), width: 1.6 } },
        { selector: ".dim", style: { opacity: 0.15 } },
        { selector: "node:selected", style: { "border-width": 3, "border-color": v("--ink") } },
      ],
      layout: { name: "cose", animate: false, nodeRepulsion: () => 9000, idealEdgeLength: () => 80, padding: 24, randomize: true },
    });
    // small networks: don't blow two nodes up to fill the whole box
    if (cy.zoom() > 1.1) { cy.zoom(1.1); cy.center(); }
    if (p.focus) cy.getElementById("c" + p.focus).select();
    cy.on("tap", "node", (e) => { cy.elements().addClass("dim"); e.target.closedNeighborhood().removeClass("dim"); sel.value = e.target.data(); });
    cy.on("tap", (e) => { if (e.target === cy) { cy.elements().removeClass("dim"); sel.value = null; } });
    cy.on("dbltap", 'node[kind="case"]', (e) => router.push(`/officer/case/${e.target.data("cid")}`));
  } catch (e) {
    msg.value = e.message;
  }
}

onMounted(draw);
watch(() => p.url, draw);
watch(theme, () => setTimeout(draw, 0));   // colours come from the theme's CSS variables
onBeforeUnmount(() => cy && cy.destroy());
</script>

<style scoped>
.gwrap { position: relative; border: 1px solid var(--rule); border-radius: var(--r); background: var(--surface); }
.g { height: 620px; }
.mini .g { height: 340px; }
.overlay { position: absolute; inset: 0; display: grid; place-content: center; }
.tip { position: absolute; top: 12px; right: 12px; width: 240px; padding: 12px 14px; display: grid; gap: 6px; }
.tip .t { margin: 0; word-break: break-word; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 16px; padding: 10px 14px; border-top: 1px solid var(--rule); color: var(--muted); }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
.dia { width: 8px; height: 8px; background: var(--rule-strong); transform: rotate(45deg); display: inline-block; }
.line { width: 16px; border-top: 1.5px dashed var(--ink-2); display: inline-block; }
</style>
