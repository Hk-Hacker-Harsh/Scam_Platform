<!-- Page frame: header with navigation and theme button, the current page, the assistant panel and the 1930 footer. -->
<template>
  <ProtoBar v-if="isProto" />
  <header class="top">
    <div class="wrap bar">
      <RouterLink to="/" class="brand" aria-label="Satark home">
        <span class="mark" aria-hidden="true">S</span>
        <span class="name">Satark</span>
        <span class="sub">Rajasthan Police · R4C PS01 prototype</span>
      </RouterLink>
      <nav class="nav">
        <RouterLink to="/" exact-active-class="on">Check</RouterLink>
        <RouterLink to="/catalogue" active-class="on">Checks</RouterLink>
        <RouterLink to="/how-it-works" active-class="on">How it works</RouterLink>
        <button class="theme" type="button" @click="toggleTheme" :aria-label="theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'"
                :title="theme === 'dark' ? 'Light theme' : 'Dark theme'">
          <svg v-if="theme === 'dark'" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><circle cx="12" cy="12" r="4.5" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M12 2.5v2.2M12 19.3v2.2M2.5 12h2.2M19.3 12h2.2M5.3 5.3l1.6 1.6M17.1 17.1l1.6 1.6M5.3 18.7l1.6-1.6M17.1 6.9l1.6-1.6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
          <svg v-else viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>
        </button>
        <RouterLink v-if="session.user" to="/officer" class="officer" active-class="on">Officer dashboard</RouterLink>
        <RouterLink v-else to="/officer/login" class="officer">Officer sign-in</RouterLink>
      </nav>
    </div>
  </header>

  <RouterView />
  <AssistantPanel v-if="showAssistant" :key="assistantPolice ? 'police' : 'citizen'" :police="assistantPolice" :case-id="assistantCase" />

  <footer class="foot">
    <div class="wrap foot-in">
      <div>
        <strong>Lost money to a fraud?</strong> Call <span class="num">1930</span> immediately or report at
        <span class="mono">cybercrime.gov.in</span>. The first hour matters.
      </div>
      <div class="muted small">Decision-support prototype for the R4C Hackathon 2026. Sample and synthetic data only. Rules decide the verdict; officers confirm.</div>
    </div>
  </footer>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import AssistantPanel from "./components/AssistantPanel.vue";
import { isProto, session } from "./api.js";
import ProtoBar from "./proto/ProtoBar.vue";
import { theme, toggleTheme } from "./theme.js";

const route = useRoute();
// Officer pages get the police assistant (database questions); everything else gets the citizen assistant.
const assistantPolice = computed(() => route.path.startsWith("/officer") && !!session.user);
const showAssistant = computed(() => route.path !== "/officer/login");
const assistantCase = computed(() => (/^\/(r|officer\/case)\/\d+$/.test(route.path) ? route.params.id : null));
</script>

<style scoped>
.top { background: var(--surface); border-bottom: 1px solid var(--rule); position: sticky; top: 0; z-index: 20; }
.bar { display: flex; align-items: center; justify-content: space-between; gap: 16px; height: 60px; }
.brand { display: flex; align-items: center; gap: 10px; text-decoration: none; min-width: 0; }
.mark { width: 28px; height: 28px; border-radius: 4px; background: var(--ink); color: var(--brass); display: grid; place-items: center;
  font: 600 16px var(--mono); flex: none; }
.name { font-weight: 600; font-size: 17px; letter-spacing: -0.01em; }
.sub { font-size: 12px; color: var(--muted); border-left: 1px solid var(--rule-strong); padding-left: 10px; white-space: nowrap; }
.nav { display: flex; align-items: center; gap: 4px; }
.nav a { text-decoration: none; font-size: 14px; color: var(--ink-2); padding: 8px 10px; border-radius: var(--r); white-space: nowrap; }
.nav a:hover { background: var(--sunk); color: var(--ink); }
.nav a.on { color: var(--ink); box-shadow: inset 0 -2px 0 var(--brass); border-radius: 0; }
.nav .officer { border: 1px solid var(--rule-strong); margin-left: 6px; }
.theme { display: inline-grid; place-items: center; width: 34px; height: 34px; border: 1px solid transparent; border-radius: var(--r);
  background: none; color: var(--ink-2); cursor: pointer; margin-left: 4px; }
.theme:hover { background: var(--sunk); color: var(--ink); border-color: var(--rule); }
.nav .officer.on { box-shadow: none; border-color: var(--ink); border-radius: var(--r); }
@media (max-width: 860px) { .sub { display: none; } }
@media (max-width: 640px) {
  .bar { height: auto; padding-top: 10px; padding-bottom: 6px; flex-direction: column; align-items: flex-start; gap: 6px; }
  .nav { width: 100%; overflow-x: auto; margin-left: -10px; }
  .nav .officer { margin-left: auto; }
}
.foot { border-top: 1px solid var(--rule); margin-top: 56px; background: var(--surface); }
.foot-in { padding-top: 20px; padding-bottom: 28px; display: grid; gap: 6px; font-size: 14px; }
</style>
