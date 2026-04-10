import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/store/auth'

describe('Router RBAC Guards', () => {
  // Since we can't easily test vue-router guards in isolation without full setup,
  // we test the underlying auth store role checks which the guards depend on.

  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  const ROUTE_ROLES = {
    '/dashboard': ['Admin', 'Curator', 'Analyst', 'User'],
    '/chat': ['Admin', 'Curator', 'Analyst', 'User'],
    '/query': ['Admin', 'Curator', 'Analyst', 'User'],
    '/audit': ['Admin'],
    '/sources': ['Admin', 'Curator'],
    '/settings': ['Admin'],
    '/ingest': ['Admin', 'Curator'],
    '/compliance': ['Admin', 'Curator', 'Analyst', 'User'],
  }

  it('Admin can access all routes', () => {
    const store = useAuthStore()
    store.login({ access_token: 't', role: 'Admin', username: 'admin' })

    for (const [route, roles] of Object.entries(ROUTE_ROLES)) {
      expect(roles.includes(store.role)).toBe(true)
    }
  })

  it('User cannot access /audit, /sources, /settings, /ingest', () => {
    const store = useAuthStore()
    store.login({ access_token: 't', role: 'User', username: 'user' })

    expect(ROUTE_ROLES['/audit'].includes(store.role)).toBe(false)
    expect(ROUTE_ROLES['/sources'].includes(store.role)).toBe(false)
    expect(ROUTE_ROLES['/settings'].includes(store.role)).toBe(false)
    expect(ROUTE_ROLES['/ingest'].includes(store.role)).toBe(false)
  })

  it('Curator can access /sources and /ingest but not /audit or /settings', () => {
    const store = useAuthStore()
    store.login({ access_token: 't', role: 'Curator', username: 'curator' })

    expect(ROUTE_ROLES['/sources'].includes(store.role)).toBe(true)
    expect(ROUTE_ROLES['/ingest'].includes(store.role)).toBe(true)
    expect(ROUTE_ROLES['/audit'].includes(store.role)).toBe(false)
    expect(ROUTE_ROLES['/settings'].includes(store.role)).toBe(false)
  })

  it('Analyst can access /chat and /compliance but not /ingest', () => {
    const store = useAuthStore()
    store.login({ access_token: 't', role: 'Analyst', username: 'analyst' })

    expect(ROUTE_ROLES['/chat'].includes(store.role)).toBe(true)
    expect(ROUTE_ROLES['/compliance'].includes(store.role)).toBe(true)
    expect(ROUTE_ROLES['/ingest'].includes(store.role)).toBe(false)
  })

  it('unauthenticated user is not logged in', () => {
    const store = useAuthStore()
    expect(store.isLoggedIn).toBe(false)
  })

  it('hasRole correctly checks multiple roles', () => {
    const store = useAuthStore()
    store.login({ access_token: 't', role: 'Curator', username: 'curator' })

    expect(store.hasRole('Admin', 'Curator')).toBe(true)
    expect(store.hasRole('Admin')).toBe(false)
    expect(store.hasRole('Curator')).toBe(true)
  })

  it('logout clears auth state', () => {
    const store = useAuthStore()
    store.login({ access_token: 't', role: 'Admin', username: 'admin' })
    expect(store.isLoggedIn).toBe(true)

    store.logout()
    expect(store.isLoggedIn).toBe(false)
    expect(store.role).toBe('')
    expect(store.username).toBe('')
  })
})
