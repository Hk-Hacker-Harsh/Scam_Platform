// All website pages and their addresses. Officer pages (/officer/...) need a signed-in officer; others are public.
import { createRouter, createWebHashHistory, createWebHistory } from "vue-router";
import { session } from "./api.js";

import Home from "./views/Home.vue";
import Result from "./views/Result.vue";
import Catalogue from "./views/Catalogue.vue";
import HowItWorks from "./views/HowItWorks.vue";
import Login from "./views/Login.vue";
import OfficerLayout from "./views/officer/Layout.vue";
import Overview from "./views/officer/Overview.vue";
import Cases from "./views/officer/Cases.vue";
import CaseView from "./views/officer/CaseView.vue";
import NewAnalysis from "./views/officer/NewAnalysis.vue";
import Graph from "./views/officer/Graph.vue";
import Campaigns from "./views/officer/Campaigns.vue";
import Heatlist from "./views/officer/Heatlist.vue";
import Registry from "./views/officer/Registry.vue";
import Audit from "./views/officer/Audit.vue";
import NotFound from "./views/NotFound.vue";

export const router = createRouter({
  history: import.meta.env.MODE === "proto" ? createWebHashHistory() : createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: "/", component: Home, meta: { title: "Check a suspicious message or link" } },
    { path: "/r/:id(\\d+)", component: Result, props: true, meta: { title: "Result" } },
    { path: "/catalogue", component: Catalogue, meta: { title: "Check catalogue" } },
    { path: "/how-it-works", component: HowItWorks, meta: { title: "How it works" } },
    { path: "/officer/login", component: Login, meta: { title: "Officer sign-in" } },
    {
      path: "/officer", component: OfficerLayout, meta: { police: true },
      children: [
        { path: "", component: Overview, meta: { title: "Overview" } },
        { path: "cases", component: Cases, meta: { title: "Cases" } },
        { path: "case/:id(\\d+)", component: CaseView, props: true, meta: { title: "Case" } },
        { path: "new", component: NewAnalysis, meta: { title: "New analysis" } },
        { path: "graph", component: Graph, meta: { title: "Link graph" } },
        { path: "campaigns", component: Campaigns, meta: { title: "Campaigns" } },
        { path: "heatlist", component: Heatlist, meta: { title: "Heat-list" } },
        { path: "registry", component: Registry, meta: { title: "Registry" } },
        { path: "audit", component: Audit, meta: { title: "Audit log" } },
      ],
    },
    { path: "/:rest(.*)*", component: NotFound, meta: { title: "Not found" } },
  ],
});

router.beforeEach((to) => {
  if (to.matched.some((r) => r.meta.police) && !session.user) {
    return { path: "/officer/login", query: { next: to.fullPath } };
  }
});

router.afterEach((to) => {
  document.title = `${to.meta.title || "Satark"} · Satark`;
});
