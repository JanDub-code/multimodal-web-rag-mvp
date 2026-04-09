import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useComplianceStore } from '@/stores/compliance'
import { useAuthStore } from '@/stores/auth'

describe('Compliance Guard', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('enforcement ON: store records confirmed confirmation', () => {
    const store = useComplianceStore()
    store.setEnforcement(true)
    expect(store.isEnforced).toBe(true)

    store.addConfirmation({
      user: 'admin',
      action: 'ingest.run',
      operation_id: 'op-test-1',
      reason: 'test reason',
      confirmed: true,
      compliance_bypassed: false,
    })

    expect(store.confirmations.length).toBe(1)
    expect(store.confirmations[0].confirmed).toBe(true)
    expect(store.confirmations[0].compliance_bypassed).toBe(false)
  })

  it('enforcement OFF (dev mode): store records bypass flag', () => {
    const store = useComplianceStore()
    store.setEnforcement(false)
    expect(store.isEnforced).toBe(false)

    store.addConfirmation({
      user: 'curator',
      action: 'query.execute',
      operation_id: 'op-test-2',
      reason: '',
      confirmed: false,
      compliance_bypassed: true,
    })

    expect(store.confirmations.length).toBe(1)
    expect(store.confirmations[0].compliance_bypassed).toBe(true)
  })

  it('enforcement toggle changes state immediately', () => {
    const store = useComplianceStore()

    store.setEnforcement(true)
    expect(store.isEnforced).toBe(true)

    store.setEnforcement(false)
    expect(store.isEnforced).toBe(false)

    store.setEnforcement(true)
    expect(store.isEnforced).toBe(true)
  })

  it('enforcement persists in localStorage', () => {
    const store = useComplianceStore()

    store.setEnforcement(true)
    expect(localStorage.getItem('compliance_enforcement')).toBe('true')

    store.setEnforcement(false)
    expect(localStorage.getItem('compliance_enforcement')).toBe('false')
  })

  it('confirmations include timestamp', () => {
    const store = useComplianceStore()

    store.addConfirmation({
      user: 'admin',
      action: 'ingest.run',
      operation_id: 'op-test-ts',
      reason: '',
      confirmed: true,
      compliance_bypassed: false,
    })

    expect(store.confirmations[0].timestamp).toBeDefined()
    expect(new Date(store.confirmations[0].timestamp).getTime()).toBeGreaterThan(0)
  })

  it('multiple confirmations are prepended (newest first)', () => {
    const store = useComplianceStore()

    store.addConfirmation({ user: 'a', action: 'first', operation_id: 'op-1', reason: '', confirmed: true, compliance_bypassed: false })
    store.addConfirmation({ user: 'b', action: 'second', operation_id: 'op-2', reason: '', confirmed: true, compliance_bypassed: false })

    expect(store.confirmations[0].action).toBe('second')
    expect(store.confirmations[1].action).toBe('first')
  })

  it('audit record contains who/when/what/request_id/operation_id', () => {
    const store = useComplianceStore()

    store.addConfirmation({
      user: 'jan.novak',
      action: 'ingest.run',
      operation_id: 'op-audit-check',
      reason: 'scheduled crawl',
      confirmed: true,
      compliance_bypassed: false,
    })

    const record = store.confirmations[0]
    expect(record.user).toBe('jan.novak')
    expect(record.timestamp).toBeDefined()
    expect(record.action).toBe('ingest.run')
    expect(record.operation_id).toBe('op-audit-check')
    expect(record.reason).toBe('scheduled crawl')
  })
})
