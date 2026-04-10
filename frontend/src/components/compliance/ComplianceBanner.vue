<template>
  <div v-if="!complianceStore.isEnforced" class="compliance-banner">
    <v-icon color="warning" size="18">mdi-alert-outline</v-icon>
    <span>
      Compliance enforcement je <strong>vypnutý</strong> (dev mode).
      Akce budou provedeny bez potvrzení, ale budou zaznamenány s příznakem bypass.
    </span>
  </div>
</template>

<script setup>
import { useComplianceStore } from '@/stores/compliance'

const complianceStore = useComplianceStore()
</script>
