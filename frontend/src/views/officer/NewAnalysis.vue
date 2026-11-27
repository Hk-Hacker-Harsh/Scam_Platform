<!-- /officer/new: the checker form; cases made here are marked police-submitted and always run fresh. -->
<template>
  <h1>New analysis</h1>
  <p class="muted">Cases created here are marked as police-submitted and open straight in the case view.</p>
  <Checker police />
</template>
<script setup>
import Checker from "../../components/Checker.vue";
</script>
