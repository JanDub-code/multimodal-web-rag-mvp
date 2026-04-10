import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useComplianceStore = defineStore('compliance', () => {
  const enforcementEnabled = ref(localStorage.getItem('compliance_enforcement') === 'true')
  const modeSource = ref('local')

  const confirmations = ref([])

  const isEnforced = computed(() => enforcementEnabled.value)

  function setEnforcement(value, options = {}) {
    const { persist = true, source = 'local' } = options
    enforcementEnabled.value = Boolean(value)
    modeSource.value = source
    if (persist) {
      localStorage.setItem('compliance_enforcement', String(enforcementEnabled.value))
    }
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
    modeSource,
    isEnforced,
    confirmations,
    setEnforcement,
    addConfirmation,
    getConfirmations,
  }
})
