<!-- The detection ring: flagged checks out of the checks that ran, coloured by the risk level. -->
<template>
  <figure class="meter" :class="'m-' + cls" :aria-label="`${flagged} of ${ran} checks flagged`">
    <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`" role="img" aria-hidden="true">
      <circle :cx="c" :cy="c" :r="r" class="track" :stroke-width="sw" fill="none" />
      <circle v-if="flagged" :cx="c" :cy="c" :r="r" class="arc" :stroke-width="sw" fill="none"
              :stroke-dasharray="`${dash} ${circ}`" :transform="`rotate(-90 ${c} ${c})`" />
    </svg>
    <div class="center">
      <div class="n num">{{ flagged }}</div>
      <div class="of num">/ {{ ran }}</div>
    </div>
    <figcaption v-if="caption">{{ caption }}</figcaption>
  </figure>
</template>

<script setup>
import { computed } from "vue";
import { LEVEL_CLASS } from "../api.js";

const p = defineProps({ flagged: Number, ran: Number, level: String, size: { type: Number, default: 132 }, caption: String });
const sw = computed(() => Math.max(6, p.size / 13));
const c = computed(() => p.size / 2);
const r = computed(() => p.size / 2 - sw.value / 2 - 1);
const circ = computed(() => 2 * Math.PI * r.value);
// even one flag must be visible on the ring
const dash = computed(() => (p.ran ? Math.max(p.flagged / p.ran, p.flagged ? 0.035 : 0) : 0) * circ.value);
const cls = computed(() => LEVEL_CLASS[p.level] || "nd");
</script>

<style scoped>
.meter { position: relative; margin: 0; display: inline-grid; justify-items: center; gap: 6px; }
.track { stroke: var(--sunk); }
.arc { stroke: var(--m); stroke-linecap: butt; }
.center { position: absolute; top: 0; left: 0; right: 0; height: v-bind('size + "px"'); display: grid; place-content: center; text-align: center; line-height: 1; }
.n { font-size: v-bind('Math.round(size / 3.3) + "px"'); font-weight: 500; color: var(--m); }
.of { font-size: v-bind('Math.round(size / 9) + "px"'); color: var(--muted); margin-top: 4px; }
figcaption { font-size: 12px; color: var(--muted); text-align: center; }
.m-high { --m: var(--high); } .m-conf { --m: var(--conf); } .m-med { --m: var(--med); }
.m-low { --m: var(--low); } .m-ok { --m: var(--ok); } .m-nd { --m: var(--nd); }
</style>
