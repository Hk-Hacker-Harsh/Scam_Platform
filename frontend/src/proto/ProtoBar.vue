<!-- Prototype-only banner: says the data is sample data and switches the wireframe view (grey outlines, no colour). -->
<template>
  <div class="proto">
    <span><b>Prototype</b> · runs offline on sample data recorded from the Satark engine · nothing is sent anywhere</span>
    <button type="button" @click="toggle" :aria-pressed="wire">{{ wire ? "Show design" : "Wireframe view" }}</button>
  </div>
</template>

<script setup>
import { ref } from "vue";
import "./wire.css";

const qs = new URLSearchParams(location.search);
const wire = ref(qs.get("wire") === "1");
document.documentElement.classList.toggle("wire", wire.value);

// screenshot helpers (prototype only): ?tab=details opens that tab, ?scroll=900 scrolls the page down
setTimeout(() => {
  const tab = (qs.get("tab") || "").toLowerCase();
  if (tab) [...document.querySelectorAll(".seg button")].find((b) => b.textContent.trim().toLowerCase().startsWith(tab))?.click();
  if (qs.get("scroll")) setTimeout(() => window.scrollTo(0, +qs.get("scroll")), 200);
}, 1200);
function toggle() {
  wire.value = !wire.value;
  document.documentElement.classList.toggle("wire", wire.value);
}
</script>

<style scoped>
.proto { display: flex; justify-content: center; align-items: center; gap: 14px; flex-wrap: wrap; padding: 6px 16px;
  background: var(--brass-soft); color: var(--ink-2); font-size: 12.5px; border-bottom: 1px solid var(--rule); }
.proto b { color: var(--ink); }
.proto button { font: 500 12px var(--sans); border: 1px solid var(--rule-strong); background: var(--surface); color: var(--ink);
  border-radius: var(--r); padding: 3px 10px; cursor: pointer; }
</style>
