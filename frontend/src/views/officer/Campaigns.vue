<!-- /officer/campaigns: groups of cases that share a phone, UPI ID, domain, wallet or app. -->
<template>
  <h1>Campaigns</h1>
  <p class="muted lede">Cases are grouped when they share a phone number, UPI ID, domain, wallet, bot token, e-mail or app. Each group is likely one operation.</p>
  <p v-if="error" class="alert err">{{ error }}</p>
  <p v-else-if="!list" class="empty">Loading…</p>
  <p v-else-if="!list.length" class="empty panel">No campaigns yet. They appear once two or more cases share an identifier.</p>
  <section v-for="(g, n) in list" :key="n" class="panel">
    <div class="panel-h">
      <h2>Campaign {{ n + 1 }} <span class="muted num">· {{ g.size }} cases</span></h2>
      <span class="small"><span class="num" :class="{ hot: high(g) }">{{ high(g) }}</span> high or confirmed</span>
    </div>
    <div class="panel-b">
      <div class="eyebrow">Shared identifiers</div>
      <div class="ids"><span v-for="s in g.shared" :key="s.type + s.value" class="chip"><small>{{ s.type }}</small>{{ s.value }} <small class="num">×{{ s.cases.length }}</small></span></div>
      <div class="eyebrow" style="margin-top:10px">Cases</div>
      <div class="cases">
        <RouterLink v-for="(cid, i) in g.cases" :key="cid" :to="`/officer/case/${cid}`" class="cs"><LevelTag :level="g.levels[i]" /> <span class="num">#{{ cid }}</span></RouterLink>
      </div>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from "vue";
import LevelTag from "../../components/LevelTag.vue";
import { get } from "../../api.js";
const list = ref(null), error = ref("");
const high = (g) => g.levels.filter((l) => l === "High" || l === "Confirmed fraud").length;
onMounted(async () => { try { list.value = (await get("/api/ui/police/campaigns")).campaigns; } catch (e) { error.value = e.message; } });
</script>

<style scoped>
.lede { max-width: 80ch; }
.hot { color: var(--high); font-weight: 500; }
.ids { margin-top: 6px; }
.cases { display: flex; flex-wrap: wrap; gap: 8px 14px; margin-top: 6px; }
.cs { text-decoration: none; display: inline-flex; align-items: center; gap: 6px; font-size: 13px; }
.cs:hover .num { text-decoration: underline; }
</style>
