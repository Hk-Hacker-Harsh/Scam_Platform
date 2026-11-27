// Website entry point: sets the theme, loads fonts and styles, asks the server who is signed in, then starts Vue.
import "./theme.js";   // first: sets light / dark before anything draws
import { createApp } from "vue";
import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/500.css";
import "@fontsource/ibm-plex-sans/600.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "./styles.css";
import App from "./App.vue";
import { router } from "./router.js";
import { loadSession } from "./api.js";

loadSession().catch(() => {}).finally(() => {
  createApp(App).use(router).mount("#app");
});
