<!-- File picker with drag-and-drop, used for screenshots, APKs and .eml files. -->
<template>
  <label class="drop" :class="{ over, has: modelValue }" @dragover.prevent="over = true" @dragleave="over = false" @drop.prevent="onDrop">
    <input type="file" :accept="accept" @change="onPick" />
    <span v-if="modelValue" class="file"><span class="mono">{{ modelValue.name }}</span> <span class="muted num">{{ size }}</span></span>
    <span v-else><b>Choose a file</b> or drop it here</span>
    <span class="hint">{{ hint }}</span>
  </label>
</template>

<script setup>
import { computed, ref } from "vue";
const p = defineProps({ modelValue: Object, accept: String, hint: String });
const emit = defineEmits(["update:modelValue"]);
const over = ref(false);
const size = computed(() => p.modelValue ? (p.modelValue.size > 1048576 ? (p.modelValue.size / 1048576).toFixed(1) + " MB" : Math.ceil(p.modelValue.size / 1024) + " KB") : "");
function onPick(e) { emit("update:modelValue", e.target.files[0] || null); }
function onDrop(e) { over.value = false; emit("update:modelValue", e.dataTransfer.files[0] || null); }
</script>

<style scoped>
.drop { display: grid; gap: 4px; place-items: center; text-align: center; padding: 22px 16px; border: 1px dashed var(--rule-strong); border-radius: var(--r);
  background: var(--sunk); cursor: pointer; font-size: 14px; position: relative; }
.drop:hover, .drop.over { border-color: var(--ink-2); }
.drop.has { border-style: solid; background: var(--surface); }
.drop input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
.drop:focus-within { outline: 2px solid var(--focus); outline-offset: 2px; }
.file { word-break: break-all; }
</style>
