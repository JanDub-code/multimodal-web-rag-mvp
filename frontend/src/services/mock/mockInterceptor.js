import {
  mockUsers,
  mockAuditLog,
  mockSources,
  mockIncidents,
  mockSettings,
  mockComplianceHistory,
  mockQueryResponse,
  mockDashboardStats,
  mockIngestResult,
  mockChatSessions,
} from './mockData'

function delay(ms = 300) {
  return new Promise((resolve) => setTimeout(resolve, ms + Math.random() * 400))
}

function matchUrl(url, pattern) {
  return url.includes(pattern)
}

/**
 * Install mock interceptor on an Axios instance.
 * Every matched request returns mock data; unmatched ones pass through.
 */
export function useMockInterceptor(axiosInstance) {
  axiosInstance.interceptors.request.use(async (config) => {
    const url = config.url || ''
    const method = (config.method || 'get').toLowerCase()
    let mockResponse = null

    // ─── AUTH ───
    if (matchUrl(url, '/auth/login') && method === 'post') {
      await delay(400)
      const body = config.data
      let parsed = {}
      if (body instanceof URLSearchParams) {
        parsed = Object.fromEntries(body.entries())
      } else if (typeof body === 'string') {
        parsed = Object.fromEntries(new URLSearchParams(body))
      } else {
        parsed = body || {}
      }
      const user = Object.values(mockUsers).find(
        (u) => u.username === parsed.username && u.password === parsed.password
      )
      if (user) {
        mockResponse = {
          access_token: user.access_token,
          refresh_token: 'mock-refresh-token',
          token_type: 'bearer',
          role: user.role,
          username: user.username,
        }
      } else {
        return Promise.reject({
          response: { status: 401, data: { detail: 'Invalid credentials' } },
        })
      }
    }

    // ─── AUDIT ───
    if (matchUrl(url, '/audit') && method === 'get') {
      await delay()
      mockResponse = mockAuditLog
    }

    // ─── SOURCES ───
    if (matchUrl(url, '/ingest/sources') && method === 'get') {
      await delay()
      mockResponse = mockSources.map((s) => ({
        id: s.id,
        name: s.name,
        base_url: s.base_url,
      }))
    }

    if (matchUrl(url, '/sources') && !matchUrl(url, '/ingest/sources') && method === 'get') {
      await delay()
      mockResponse = {
        sources: mockSources,
        incidents: mockIncidents,
        stats: mockDashboardStats,
      }
    }

    if (matchUrl(url, '/ingest/sources') && method === 'post') {
      await delay(500)
      const data = typeof config.data === 'string' ? JSON.parse(config.data) : config.data
      const newSource = {
        source_id: mockSources.length + 1,
        name: data.name,
      }
      mockResponse = newSource
    }

    // ─── INGEST ───
    if (matchUrl(url, '/ingest/run') && method === 'post') {
      await delay(1500)
      const data = typeof config.data === 'string' ? JSON.parse(config.data) : config.data
      mockResponse = {
        ...mockIngestResult,
        source_id: data.source_id,
        url: data.url,
        operation_id: data.operation_id || `op-${Date.now()}`,
      }
    }

    // ─── CHAT SESSIONS ───
    if (matchUrl(url, '/chat/sessions') && method === 'get') {
      await delay(200)
      mockResponse = mockChatSessions.map((s) => ({
        id: s.id,
        title: s.title,
        updated_at: s.updated_at
      }))
    }

    if (matchUrl(url, '/chat/sessions') && method === 'post') {
      await delay(200)
      const data = typeof config.data === 'string' ? JSON.parse(config.data) : config.data
      const newSession = {
        id: `session-${Date.now()}`,
        title: data.title || 'Nová konverzace',
        updated_at: new Date().toISOString(),
        messages: []
      }
      mockChatSessions.unshift(newSession)
      mockResponse = newSession
    }

    const sessionMatch = url.match(/\/chat\/sessions\/([^/]+)$/)
    if (sessionMatch && method === 'get') {
      await delay(200)
      const sessionId = sessionMatch[1]
      const session = mockChatSessions.find(s => s.id === sessionId)
      if (session) {
        mockResponse = session
      } else {
        return Promise.reject({ response: { status: 404, data: { detail: 'Session not found' } } })
      }
    }

    // ─── QUERY / CHAT ───
    if (matchUrl(url, '/query') && method === 'post') {
      await delay(1200)
      const data = typeof config.data === 'string' ? JSON.parse(config.data) : config.data
      
      let answerData = data.mode === 'no-rag' ? mockQueryResponse.noRag : mockQueryResponse.rag
      
      const newAiMessage = {
        id: `msg-${Date.now()}`,
        role: 'ai',
        content: answerData.answer,
        citations: answerData.citations || [],
        timestamp: new Date().toISOString(),
        operation_id: data.operation_id
      }
      
      // If sessionId is provided, prepend the user message and append AI message to that session
      if (data.session_id) {
        const session = mockChatSessions.find(s => s.id === data.session_id)
        if (session) {
          session.messages.push({
            id: `msg-u-${Date.now()}`,
            role: 'user',
            content: data.query,
            timestamp: new Date().toISOString()
          })
          session.messages.push(newAiMessage)
          session.updated_at = new Date().toISOString()
        }
      }
      
      mockResponse = { ...answerData, message: newAiMessage, operation_id: data.operation_id }
    }

    // ─── SETTINGS ───
    if (matchUrl(url, '/settings') && method === 'get') {
      await delay()
      mockResponse = mockSettings
    }

    if (matchUrl(url, '/settings') && method === 'put') {
      await delay(500)
      mockResponse = { status: 'ok', message: 'Nastavení uloženo' }
    }

    // ─── COMPLIANCE ───
    if (matchUrl(url, '/compliance/history') && method === 'get') {
      await delay()
      mockResponse = mockComplianceHistory
    }

    if (matchUrl(url, '/compliance/confirm') && method === 'post') {
      await delay(300)
      mockResponse = { status: 'ok', confirmed: true }
    }

    // ─── DASHBOARD ───
    if (matchUrl(url, '/dashboard/stats') && method === 'get') {
      await delay()
      mockResponse = mockDashboardStats
    }

    // ─── INCIDENTS ───
    if (matchUrl(url, '/incidents') && method === 'get') {
      await delay()
      mockResponse = mockIncidents
    }

    if (matchUrl(url, '/incidents') && method === 'post') {
      await delay(400)
      mockResponse = { status: 'resolved' }
    }

    // ─── HEALTH ───
    if (matchUrl(url, '/health')) {
      mockResponse = {
        status: 'ok',
        components: {
          api: { status: 'up' },
          postgres: { status: 'up' },
          qdrant: { status: 'up' },
          llm: { status: 'up', required: false },
        },
      }
    }

    if (mockResponse !== null) {
      // Cancel the real request and return mock
      const error = new Error('MOCK')
      error.__isMock = true
      error.__mockData = mockResponse
      return Promise.reject(error)
    }

    return config
  })

  // Response interceptor to handle mock responses
  axiosInstance.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.__isMock) {
        return Promise.resolve({
          data: error.__mockData,
          status: 200,
          statusText: 'OK (Mock)',
          headers: {},
          config: error.config || {},
        })
      }
      return Promise.reject(error)
    }
  )
}
