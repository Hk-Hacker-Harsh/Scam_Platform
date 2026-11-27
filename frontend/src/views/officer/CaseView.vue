<!-- /officer/case/<id>: one case for officers: status, re-scan, PDF, labels per identifier (confirmed fraud /
     verified official), linked cases, detection, details, network, stored input and citizen reports. -->
<template>
  <p v-if="error" class="alert err">{{ error }}</p>
  <p v-else-if="!c" class="empty">Loading case…</p>
  <template v-else>
    <div class="actions">
      <RouterLink to="/officer/cases" class="small muted">All cases</RouterLink>
      <div class="row">
        <label class="small muted" for="st">Status</label>
        <select id="st" v-model="status" class="st" @change="setStatus">
          <option value="open">Open</option><option value="reviewed">Reviewed</option><option value="closed">Closed</option><option value="false_positive">False positive</option>
        </select>
        <button v-if="c.kind !== 'apk'" class="btn ghost sm" :disabled="busy" @click="rescan">Re-scan with latest labels</button>
        <a v-if="!isProto" class="btn ghost sm" :href="c.pdf">PDF report</a>
      </div>
    </div>
    <p v-if="msg" class="alert ok">{{ msg }}</p>

    <VerdictHeader :c="c" />

    <section class="panel">
      <div class="panel-h"><h2>Police verdict on identifiers</h2></div>
      <div class="panel-b">
        <p class="small muted">Confirmed fraud makes every future case that contains the identifier “Confirmed fraud”. Verified official clears it. Both are audited.</p>
        <p v-if="!linkable.length" class="empty">No linkable identifiers in this case.</p>
        <div v-else class="scroll-x">
          <table class="tbl">
            <thead><tr><th>Identifier</th><th>Current label</th><th>Officer action</th></tr></thead>
            <tbody>
              <tr v-for="i in linkable" :key="i.type + i.value">
                <td class="idv"><span class="muted small">{{ i.type }}</span><br><span class="mono">{{ i.value }}</span></td>
                <td>
                  <template v-if="labelOf(i)">
                    <span class="lv" :class="labelOf(i).label === 'confirmed_fraud' ? 'lv-conf' : 'lv-ok'">{{ labelOf(i).label === 'confirmed_fraud' ? 'Confirmed fraud' : 'Verified official' }}</span>
                    <div class="small muted">{{ labelOf(i).by_user }} · {{ (labelOf(i).ts || '').slice(0, 10) }}</div>
                  </template>
                  <span v-else class="muted">—</span>
                </td>
                <td class="acts">
                  <input v-model="notes[i.type + i.value]" type="text" maxlength="200" placeholder="Note: FIR no. or source" class="note" :aria-label="'Note for ' + i.value" />
                  <div class="btns">
                    <button class="btn danger sm" :disabled="busy" @click="label(i, 'confirmed_fraud')">Confirmed fraud</button>
                    <button class="btn ghost sm" :disabled="busy" @click="label(i, 'verified_official')">Verified official</button>
                    <button v-if="labelOf(i)" class="btn ghost sm" :disabled="busy" @click="label(i, 'clear')">Clear</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <section class="panel" v-if="c.linked.length">
      <div class="panel-h"><h2>Linked cases</h2><span class="muted small">share at least one identifier</span></div>
      <div class="scroll-x">
        <table class="tbl">
          <thead><tr><th>Case</th><th>Risk</th><th>Shared</th></tr></thead>
          <tbody><tr v-for="l in c.linked" :key="l.case_id">
            <td><RouterLink :to="`/officer/case/${l.case_id}`" class="num">#{{ l.case_id }}</RouterLink> <span class="muted small">{{ KIND_LABEL[l.kind] }}</span></td>
            <td><LevelTag :level="l.level" /></td>
            <td><span v-for="v in l.via" :key="v.join(':')" class="chip"><small>{{ v[0] }}</small>{{ v[1] }}</span></td>
          </tr></tbody>
        </table>
      </div>
    </section>

    <section class="panel">
      <div class="seg tabs"><button v-for="t in tabs" :key="t.k" :class="{ on: tab === t.k }" @click="tab = t.k">{{ t.label }}</button></div>
      <div class="panel-b">
        <DetectionList v-if="tab === 'detection'" :findings="c.findings" />
        <CaseDetails v-else-if="tab === 'details'" :c="c" />
        <GraphView v-else-if="tab === 'graph'" :url="`/api/ui/police/graph?case=${c.id}`" :focus="c.id" mini />
        <div v-else-if="tab === 'input'"><pre class="input">{{ c.content }}</pre></div>
        <div v-else>
          <p v-if="!c.report_list.length" class="empty">No citizen reports for this case.</p>
          <div v-for="r in c.report_list" :key="r.id" class="rep">
            <div class="small muted num">{{ r.ts }}<span v-if="r.contact"> · {{ r.contact }}</span></div>
            <p>{{ r.note || '(no note)' }}</p>
          </div>
        </div>
      </div>
    </section>

    <section class="panel" v-if="c.parent_id || c.children.length">
      <div class="panel-h"><h2>Followed scans</h2></div>
      <div class="panel-b small">
        <p v-if="c.parent_id">Followed from <RouterLink :to="`/officer/case/${c.parent_id}`" class="num">#{{ c.parent_id }}</RouterLink>: {{ c.origin }}</p>
        <p v-for="k in c.children" :key="k.id"><RouterLink :to="`/officer/case/${k.id}`" class="num">#{{ k.id }}</RouterLink> <LevelTag :level="k.level" /> {{ k.title }} <span class="muted">({{ k.origin }})</span></p>
      </div>
    </section>
  </template>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import VerdictHeader from "../../components/VerdictHeader.vue";
import DetectionList from "../../components/DetectionList.vue";
import CaseDetails from "../../components/CaseDetails.vue";
import GraphView from "../../components/GraphView.vue";
import LevelTag from "../../components/LevelTag.vue";
import { get, isProto, post, KIND_LABEL } from "../../api.js";

const p = defineProps({ id: String });
const router = useRouter();
const c = ref(null), error = ref(""), msg = ref(""), busy = ref(false), status = ref("open"), tab = ref("detection");
const notes = reactive({});
const tabs = computed(() => [{ k: "detection", label: "Detection" }, { k: "details", label: "Details" }, { k: "graph", label: "Network" },
  { k: "input", label: "Stored input" }, { k: "reports", label: `Citizen reports (${c.value ? c.value.report_list.length : 0})` }]);
const linkable = computed(() => c.value.ids.filter((i) => c.value.link_types.includes(i.type)));
const labelOf = (i) => c.value.labels.find((l) => l.type === i.type && l.value === i.value);

async function load(keepMsg) {
  error.value = ""; if (!keepMsg) msg.value = "";
  try { c.value = await get(`/api/ui/police/case/${p.id}`); status.value = c.value.status; } catch (e) { error.value = e.message; }
}
async function act(fn, done) {
  busy.value = true;
  try { await fn(); msg.value = done; await load(true); } catch (e) { error.value = e.message; } finally { busy.value = false; }
}
const setStatus = () => act(() => post(`/api/ui/police/case/${p.id}/status`, { status: status.value }), "Status updated.");
const label = (i, lab) => act(() => post(`/api/ui/police/case/${p.id}/label`, { type: i.type, value: i.value, label: lab, note: notes[i.type + i.value] || "" }),
  `${i.value} ${lab === "clear" ? "label cleared" : "marked " + lab.replace("_", " ")}.`);
async function rescan() {
  busy.value = true;
  try { const r = await post(`/api/ui/police/case/${p.id}/rescan`); router.push(`/officer/case/${r.id}`); } catch (e) { error.value = e.message; } finally { busy.value = false; }
}
watch(() => p.id, () => { tab.value = "detection"; load(); }, { immediate: true });
</script>

<style scoped>
.actions { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.st { width: auto; padding: 6px 8px; font-size: 13px; }
.tabs { padding: 0 10px; }
.idv { width: 42%; word-break: break-all; }
.note { padding: 6px 8px; font-size: 13px; margin-bottom: 6px; }
.acts { min-width: 260px; }
.btns { display: flex; flex-wrap: wrap; gap: 6px; }
.rep { border-bottom: 1px solid var(--rule); padding: 8px 0; }
</style>
