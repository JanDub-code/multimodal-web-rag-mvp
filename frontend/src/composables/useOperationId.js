/**
 * Auto-generate operation IDs for traceability.
 * Every action gets a unique operation_id (UUIDv4).
 * Batch operations also get a batch_id.
 */
export function useOperationId() {
  function newUuid() {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID()
    }
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`
  }

  function generateOperationId() {
    return `op-${newUuid()}`
  }

  function generateBatchId() {
    return `batch-${newUuid()}`
  }

  function generateRowId(batchId, index) {
    return `${batchId}-row-${index}`
  }

  return {
    generateOperationId,
    generateBatchId,
    generateRowId,
  }
}
