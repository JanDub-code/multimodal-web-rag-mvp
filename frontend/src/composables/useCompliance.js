import { ref } from 'vue'
import { useComplianceStore } from '@/stores/compliance'
import { useAuthStore } from '@/stores/auth'
import { useOperationId } from './useOperationId'

/**
 * Compliance guard composable.
 * Returns a function that wraps sensitive actions with compliance checks.
 */
export function useCompliance() {
  const complianceStore = useComplianceStore()
  const authStore = useAuthStore()
  const { generateOperationId } = useOperationId()

  const showDialog = ref(false)
  const pendingAction = ref(null)
  const pendingActionType = ref('')
  const pendingOperationId = ref('')

  /**
   * Guard a sensitive action with compliance confirmation.
   * @param {string} actionType - e.g. 'ingest.run', 'query.execute'
   * @param {Function} action - The action to execute after confirmation
   * @returns {Promise} - resolves when action completes or is cancelled
   */
  function guardAction(actionType, action) {
    const operationId = generateOperationId()
    pendingOperationId.value = operationId

    if (!complianceStore.isEnforced) {
      // Dev mode: run action directly, but log bypass
      complianceStore.addConfirmation({
        user: authStore.username,
        action: actionType,
        operation_id: operationId,
        reason: '',
        confirmed: false,
        compliance_bypassed: true,
      })
      return action(operationId)
    }

    // Enforcement mode: show dialog
    pendingAction.value = action
    pendingActionType.value = actionType
    showDialog.value = true

    return new Promise((resolve, reject) => {
      pendingAction.value = async (opId) => {
        try {
          const result = await action(opId)
          resolve(result)
        } catch (err) {
          reject(err)
        }
      }
    })
  }

  function confirmCompliance(reason = '') {
    const operationId = pendingOperationId.value
    complianceStore.addConfirmation({
      user: authStore.username,
      action: pendingActionType.value,
      operation_id: operationId,
      reason,
      confirmed: true,
      compliance_bypassed: false,
    })
    showDialog.value = false
    if (pendingAction.value) {
      pendingAction.value(operationId)
    }
    pendingAction.value = null
  }

  function cancelCompliance() {
    showDialog.value = false
    pendingAction.value = null
    pendingActionType.value = ''
    pendingOperationId.value = ''
  }

  return {
    showDialog,
    pendingActionType,
    pendingOperationId,
    guardAction,
    confirmCompliance,
    cancelCompliance,
  }
}
