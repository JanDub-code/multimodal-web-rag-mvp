import { describe, it, expect } from 'vitest'
import { useOperationId } from '@/composables/useOperationId'

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

describe('Operation ID', () => {
  it('generates unique operation_id with op- prefix', () => {
    const { generateOperationId } = useOperationId()
    const id = generateOperationId()
    expect(id).toMatch(/^op-/)
  })

  it('operation_id contains valid UUIDv4', () => {
    const { generateOperationId } = useOperationId()
    const id = generateOperationId()
    const uuid = id.replace('op-', '')
    expect(uuid).toMatch(UUID_REGEX)
  })

  it('every call generates a unique id', () => {
    const { generateOperationId } = useOperationId()
    const ids = new Set()
    for (let i = 0; i < 100; i++) {
      ids.add(generateOperationId())
    }
    expect(ids.size).toBe(100)
  })

  it('generates batch_id with batch- prefix', () => {
    const { generateBatchId } = useOperationId()
    const batchId = generateBatchId()
    expect(batchId).toMatch(/^batch-/)
    const uuid = batchId.replace('batch-', '')
    expect(uuid).toMatch(UUID_REGEX)
  })

  it('generates row_id from batch_id and index', () => {
    const { generateBatchId, generateRowId } = useOperationId()
    const batchId = generateBatchId()
    const rowId = generateRowId(batchId, 5)
    expect(rowId).toBe(`${batchId}-row-5`)
  })

  it('batch operations produce unique batch_ids', () => {
    const { generateBatchId } = useOperationId()
    const id1 = generateBatchId()
    const id2 = generateBatchId()
    expect(id1).not.toBe(id2)
  })
})
