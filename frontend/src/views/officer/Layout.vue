<!-- Frame of every officer page: who is signed in, the officer menu, CSV export and sign out. -->
<template>
  <div class="wrap shell">
    <aside class="side">
      <div class="who">
        <div class="eyebrow">Signed in</div>
        <div class="u">{{ session.user }} <span class="muted small">· {{ session.role }}</span></div>
      </div>
      <nav>
        <RouterLink v-for="l in links" :key="l.to" :to="l.to" :exact-active-class="l.exact ? 'on' : ''" :active-class="l.exact ? '' : 'on'">{{ l.label }}</RouterLink>
      </nav>
      <div class="bottom">
        <a v-if="!isProto" href="/police/export.csv" class="small">Export cases (CSV)</a>
        <button class="btn ghost sm" @click="logout">Sign out</button>
      </div>
    </aside>
    <main class="content"><RouterView /></main>
  </div>
</template>

<script setup>
import { useRouter } from "vue-router";
import { isProto, post, session } from "../../api.js";
const router = useRouter();
const links = [
  { to: "/officer", label: "Overview", exact: true },
  { to: "/officer/cases", label: "Cases" },
  { to: "/officer/new", label: "New analysis" },
  { to: "/officer/graph", label: "Link graph" },
  { to: "/officer/campaigns", label: "Campaigns" },
  { to: "/officer/heatlist", label: "Heat-list" },
  { to: "/officer/registry", label: "Registry" },
  { to: "/officer/audit", label: "Audit log" },
];
async function logout() {
  try { const r = await post("/api/ui/logout"); session.csrf = r.csrf; } catch { /* already signed out */ }
  session.user = null; session.role = null;
  router.push("/");
}
</script>

<style scoped>
.shell { display: grid; grid-template-columns: 200px minmax(0, 1fr); gap: 32px; padding-top: 24px; align-items: start; }
.side { position: sticky; top: 84px; display: grid; gap: 18px; }
.who .u { font-weight: 500; margin-top: 2px; }
nav { display: grid; border-top: 1px solid var(--rule); }
nav a { text-decoration: none; padding: 9px 10px; font-size: 14px; color: var(--ink-2); border-bottom: 1px solid var(--rule); border-left: 2px solid transparent; }
nav a:hover { background: var(--sunk); color: var(--ink); }
nav a.on { color: var(--ink); font-weight: 500; border-left-color: var(--brass); background: var(--surface); }
.bottom { display: grid; gap: 10px; justify-items: start; }
.content { min-width: 0; display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; }
@media (max-width: 860px) {
  .shell { grid-template-columns: minmax(0, 1fr); gap: 16px; }
  .side { position: static; }
  nav { display: flex; overflow-x: auto; scrollbar-width: none; border-top: 0; border-bottom: 1px solid var(--rule); }
  nav::-webkit-scrollbar { display: none; }
  nav a { border: 0; border-bottom: 2px solid transparent; white-space: nowrap; }
  nav a.on { border-bottom-color: var(--brass); }
  .who { display: none; }
  .bottom { grid-auto-flow: column; justify-content: space-between; align-items: center; }
}
</style>
