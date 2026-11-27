// Light / dark theme. Light is the default; the choice is remembered in this browser only.
// Imported first in main.js so the theme is set before the page draws (no dark flash).
import { ref } from "vue";

const KEY = "satark-theme";

function saved() {
  try { return localStorage.getItem(KEY); } catch { return null; }   // storage can be blocked (private mode)
}

const forced = import.meta.env.MODE === "proto" ? new URLSearchParams(location.search).get("theme") : null;   // prototype screenshots
export const theme = ref((forced || saved()) === "dark" ? "dark" : "light");
document.documentElement.setAttribute("data-theme", theme.value);

export function setTheme(t) {
  theme.value = t === "dark" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", theme.value);
  try { localStorage.setItem(KEY, theme.value); } catch { /* not remembered; still applied */ }
}

export const toggleTheme = () => setTheme(theme.value === "dark" ? "light" : "dark");
