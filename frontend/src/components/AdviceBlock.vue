<!-- "What to do now" box on a result: advice in English and Hindi, plus the 1930 helpline strip for risky results. -->
<template>
  <section class="panel advice" :class="'a-' + cls">
    <div class="panel-h"><h2>What to do now</h2><span class="eyebrow">English · हिन्दी</span></div>
    <div class="panel-b cols">
      <ol><li v-for="(t, i) in advice.en" :key="'en' + i">{{ t }}</li></ol>
      <ol lang="hi" class="hi"><li v-for="(t, i) in advice.hi" :key="'hi' + i">{{ t }}</li></ol>
    </div>
    <div v-if="urgent" class="helpline">
      <span class="num big">1930</span>
      <span>National cyber-crime helpline. If money left your account, call now: banks can freeze it only in the first hours.</span>
    </div>
  </section>
</template>

<script setup>
import { computed } from "vue";
import { LEVEL_CLASS } from "../api.js";
const p = defineProps({ advice: Object, level: String });
const cls = computed(() => LEVEL_CLASS[p.level] || "nd");
const urgent = computed(() => ["High", "Confirmed fraud"].includes(p.level));
</script>

<style scoped>
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
ol { margin: 0; padding-left: 20px; display: grid; gap: 6px; font-size: 14px; }
.hi { font-size: 15px; }
.helpline { display: flex; align-items: center; gap: 16px; padding: 12px 18px; border-top: 1px solid var(--rule); background: var(--high-bg); color: var(--ink); font-size: 14px; }
.big { font-size: 26px; font-weight: 500; color: var(--high); }
@media (max-width: 720px) { .cols { grid-template-columns: 1fr; } }
</style>
