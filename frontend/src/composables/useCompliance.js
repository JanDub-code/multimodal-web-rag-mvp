import { ref } from 'vue'
import { useComplianceStore } from '@/stores/compliance'
import { useAuthStore } from '@/store/auth'
import { complianceService } from '@/services/complianceService'
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
  const pendingReject = ref(null)
  const pendingActionType = ref('')
  const pendingOperationId = ref('')
  const modeSynced = ref(false)

  async function syncModeOnce() {
    if (modeSynced.value) return
    try {
      const data = await complianceService.getMode()
      if (typeof data?.enforcement === 'boolean') {
        complianceStore.setEnforcement(data.enforcement, {
          source: data.source || 'api',
        })
      }
    } catch (err) {
      // Keep local mode if API mode cannot be fetched.
      console.warn('Compliance mode sync failed, using local mode.', err)
    } finally {
      modeSynced.value = true
    }
  }

  function toActionContext({ operationId, confirmed, bypassed, reason }) {
    return {
      operationId,
      complianceConfirmed: confirmed,
      complianceBypassed: bypassed,
      complianceReason: reason,
    }
  }

  function clearPendingState() {
    pendingAction.value = null
    pendingReject.value = null
    pendingActionType.value = ''
    pendingOperationId.value = ''
  }

  /**
   * Guard a sensitive action with compliance confirmation.
   * @param {string} actionType - e.g. 'ingest.run', 'query.execute'
   * @param {Function} action - The action to execute after confirmation
   * @returns {Promise} - resolves when action completes or is cancelled
   */
  async function guardAction(actionType, action) {
    await syncModeOnce()

    const operationId = generateOperationId()
    pendingOperationId.value = operationId

    if (!complianceStore.isEnforced) {
      // Dev mode: run action directly, but log bypass
      const actionContext = toActionContext({
        operationId,
        confirmed: false,
        bypassed: true,
        reason: '',
      })
      complianceStore.addConfirmation({
        user: authStore.username,
        action: actionType,
        operation_id: operationId,
        reason: '',
        confirmed: false,
        compliance_bypassed: true,
      })
      return action(actionContext)
    }

    // Enforcement mode: show dialog
    pendingAction.value = action
    pendingActionType.value = actionType
    showDialog.value = true

    return new Promise((resolve, reject) => {
      pendingReject.value = reject
      pendingAction.value = async (actionContext) => {
        try {
          const result = await action(actionContext)
          resolve(result)
        } catch (err) {
          reject(err)
        } finally {
          clearPendingState()
        }
      }
    })
  }

  function confirmCompliance(reason = '') {
    const operationId = pendingOperationId.value
    const normalizedReason = String(reason || '').trim()
    complianceStore.addConfirmation({
      user: authStore.username,
      action: pendingActionType.value,
      operation_id: operationId,
      reason: normalizedReason,
      confirmed: true,
      compliance_bypassed: false,
    })
    showDialog.value = false
    if (pendingAction.value) {
      pendingAction.value(
        toActionContext({
          operationId,
          confirmed: true,
          bypassed: false,
          reason: normalizedReason,
        })
      )
    } else {
      clearPendingState()
    }
  }

  function cancelCompliance() {
    showDialog.value = false
    if (pendingReject.value) {
      pendingReject.value(new Error('Compliance confirmation cancelled.'))
    }
    clearPendingState()
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
