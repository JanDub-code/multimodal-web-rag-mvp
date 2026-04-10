import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useComplianceStore = defineStore('compliance', () => {
  const enforcementEnabled = ref(localStorage.getItem('compliance_enforcement') === 'true')

  const confirmations = ref([])

  const isEnforced = computed(() => enforcementEnabled.value)

  function setEnforcement(value) {
    enforcementEnabled.value = value
    localStorage.setItem('compliance_enforcement', String(value))
  }

  function addConfirmation(confirmation) {
    confirmations.value.unshift({
      ...confirmation,
      timestamp: new Date().toISOString(),
    })
  }

  function getConfirmations() {
    return confirmations.value
  }

  return {
    enforcementEnabled,
    isEnforced,
    confirmations,
    setEnforcement,
    addConfirmation,
    getConfirmations,
  }
})
