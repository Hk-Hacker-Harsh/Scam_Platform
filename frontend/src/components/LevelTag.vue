<!-- Small coloured risk label (High, Medium, Low, Confirmed fraud, Verified official). -->
<template><span class="lv" :class="'lv-' + (LEVEL_CLASS[level] || 'nd')">{{ level }}</span></template>
<script setup>
import { LEVEL_CLASS } from "../api.js";
defineProps({ level: String });
</script>
