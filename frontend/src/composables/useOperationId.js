import { v4 as uuidv4 } from 'uuid'

/**
 * Auto-generate operation IDs for traceability.
 * Every action gets a unique operation_id (UUIDv4).
 * Batch operations also get a batch_id.
 */
export function useOperationId() {
  function generateOperationId() {
    return `op-${uuidv4()}`
  }

  function generateBatchId() {
    return `batch-${uuidv4()}`
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
