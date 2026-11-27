<!-- /officer/login: officer sign-in (rate-limited and audited on the server). -->
<template>
  <main class="wrap page">
    <form class="panel box" @submit.prevent="submit">
      <div class="panel-b">
        <div class="eyebrow">Authorised officers only</div>
        <h1>Sign in</h1>
        <label class="f" for="u">Username</label>
        <input id="u" v-model="username" type="text" autocomplete="username" autofocus />
        <label class="f" for="p" style="margin-top:12px">Password</label>
        <input id="p" v-model="password" type="password" autocomplete="current-password" />
        <p v-if="error" class="alert err" role="alert">{{ error }}</p>
        <button class="btn full" :disabled="busy">{{ busy ? 'Signing in…' : 'Sign in' }}</button>
        <p class="hint">Every sign-in and action is written to the audit log.</p>
        <p v-if="isProto" class="hint"><b>Prototype:</b> any username and password opens the officer dashboard.</p>
      </div>
    </form>
  </main>
</template>

<script setup>
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { isProto, post, session } from "../api.js";
const username = ref(""), password = ref(""), error = ref(""), busy = ref(false);
const route = useRoute(), router = useRouter();
async function submit() {
  busy.value = true; error.value = "";
  try {
    const r = await post("/api/ui/login", { username: username.value, password: password.value });
    Object.assign(session, { user: r.user, role: r.role, csrf: r.csrf });
    const next = typeof route.query.next === "string" && route.query.next.startsWith("/officer") ? route.query.next : "/officer";
    router.push(next);
  } catch (e) { error.value = e.message; } finally { busy.value = false; password.value = ""; }
}
</script>

<style scoped>
.page { padding-top: 56px; display: grid; place-items: center; }
.box { width: 100%; max-width: 380px; }
h1 { margin: 6px 0 18px; }
.alert { margin: 14px 0 0; }
.full { width: 100%; margin-top: 18px; padding: 12px; }
</style>
