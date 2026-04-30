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

function parseBody(data) {
  if (data instanceof URLSearchParams) {
    return Object.fromEntries(data.entries())
  }
  if (typeof data === 'string') {
    try {
      return JSON.parse(data)
    } catch {
      return Object.fromEntries(new URLSearchParams(data))
    }
  }
  return data || {}
}

function rejectWith(status, detail) {
  return Promise.reject({
    response: { status, data: { detail } },
  })
}

function ensureComplianceOrReject(payload, actionType) {
  if (!mockSettings.compliance_enforcement) return null
  if (payload?.compliance_confirmed === true) return null
  return rejectWith(
    422,
    `Compliance confirmation is required for action '${actionType}' when enforcement is enabled.`
  )
}

function pushComplianceHistory(payload, actionType, operationId) {
  const confirmed = payload?.compliance_confirmed === true || payload?.confirmed === true
  const nowIso = new Date().toISOString()

  mockComplianceHistory.unshift({
    id: Date.now(),
    user: localStorage.getItem('username') || 'user',
    action: actionType,
    timestamp: nowIso,
    operation_id: operationId,
    reason: payload?.compliance_reason || payload?.reason || '',
    confirmed,
    compliance_bypassed: confirmed ? false : true,
    request_id: `req-${Date.now()}`,
  })
}

function returnMock(mockResponse, config) {
  const error = new Error('MOCK')
  error.__isMock = true
  error.__mockData = mockResponse
  error.config = config
  return Promise.reject(error)
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

    // AUTH
    if (matchUrl(url, '/auth/login') && method === 'post') {
      await delay(400)
      const parsed = parseBody(config.data)
      const user = Object.values(mockUsers).find(
        (u) => u.username === parsed.username && u.password === parsed.password
      )
      if (!user) {
        return rejectWith(401, 'Invalid credentials')
      }
      mockResponse = {
        access_token: user.access_token,
        refresh_token: 'mock-refresh-token',
        token_type: 'bearer',
        role: user.role,
        username: user.username,
      }
    }

    // AUDIT
    if (matchUrl(url, '/audit') && method === 'get') {
      await delay()
      mockResponse = mockAuditLog
    }

    // SOURCES
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
      const data = parseBody(config.data)
      mockResponse = {
        source_id: mockSources.length + 1,
        name: data.name,
      }
    }

    // INGEST
    if (matchUrl(url, '/ingest/run') && method === 'post') {
      await delay(1200)
      const data = parseBody(config.data)
      const complianceError = ensureComplianceOrReject(data, 'ingest.run')
      if (complianceError) return complianceError

      const operationId = data.operation_id || `op-${Date.now()}`
      pushComplianceHistory(data, 'ingest.run', operationId)

      mockResponse = {
        ...mockIngestResult,
        source_id: data.source_id,
        url: data.url,
        operation_id: operationId,
        batch_id: data.batch_id || null,
        row_id: data.row_id || null,
        compliance_confirmed: data.compliance_confirmed === true,
        compliance_bypassed: data.compliance_confirmed === true ? false : true,
        compliance_reason: data.compliance_reason || '',
      }
    }

    // CHAT SESSIONS
    if (matchUrl(url, '/chat/sessions') && method === 'get') {
      await delay(200)
      mockResponse = mockChatSessions.map((s) => ({
        id: s.id,
        title: s.title,
        updated_at: s.updated_at,
      }))
    }

    if (matchUrl(url, '/chat/sessions') && method === 'post') {
      await delay(200)
      const data = parseBody(config.data)
      const newSession = {
        id: `session-${Date.now()}`,
        title: data.title || 'Nova konverzace',
        updated_at: new Date().toISOString(),
        messages: [],
      }
      mockChatSessions.unshift(newSession)
      mockResponse = newSession
    }

    const sessionMatch = url.match(/\/chat\/sessions\/([^/]+)$/)
    if (sessionMatch && method === 'get') {
      await delay(200)
      const sessionId = sessionMatch[1]
      const session = mockChatSessions.find((s) => s.id === sessionId)
      if (!session) {
        return rejectWith(404, 'Session not found')
      }
      mockResponse = session
    }

    // QUERY / CHAT
    if (matchUrl(url, '/query') && method === 'post') {
      await delay(1200)
      const data = parseBody(config.data)
      const complianceError = ensureComplianceOrReject(data, 'query.execute')
      if (complianceError) return complianceError

      const operationId = data.operation_id || `op-${Date.now()}`
      pushComplianceHistory(data, 'query.execute', operationId)

      const answerData = data.mode === 'no-rag' ? mockQueryResponse.noRag : mockQueryResponse.rag
      const newAiMessage = {
        id: `msg-${Date.now()}`,
        role: 'ai',
        content: answerData.answer,
        citations: answerData.citations || [],
        timestamp: new Date().toISOString(),
        operation_id: operationId,
      }

      if (data.session_id) {
        const session = mockChatSessions.find((s) => s.id === data.session_id)
        if (session) {
          session.messages.push({
            id: `msg-u-${Date.now()}`,
            role: 'user',
            content: data.query,
            timestamp: new Date().toISOString(),
          })
          session.messages.push(newAiMessage)
          session.updated_at = new Date().toISOString()
        }
      }

      mockResponse = {
        ...answerData,
        message: newAiMessage,
        operation_id: operationId,
        compliance_confirmed: data.compliance_confirmed === true,
        compliance_bypassed: data.compliance_confirmed === true ? false : true,
        compliance_reason: data.compliance_reason || '',
      }
    }

    // SETTINGS
    if (matchUrl(url, '/settings') && method === 'get') {
      await delay()
      mockResponse = mockSettings
    }

    if (matchUrl(url, '/settings') && method === 'put') {
      await delay(500)
      const data = parseBody(config.data)
      mockSettings.retention = {
        ...mockSettings.retention,
        ...(data.retention || {}),
      }
      mockResponse = mockSettings
    }

    // COMPLIANCE
    if (matchUrl(url, '/compliance/mode') && method === 'get') {
      await delay(100)
      mockResponse = {
        enforcement: Boolean(mockSettings.compliance_enforcement),
        source: 'mock-runtime',
      }
    }

    if (matchUrl(url, '/compliance/mode') && method === 'put') {
      await delay(100)
      const data = parseBody(config.data)
      mockSettings.compliance_enforcement = Boolean(data.enforcement)
      mockResponse = {
        enforcement: Boolean(mockSettings.compliance_enforcement),
        source: 'mock-runtime',
      }
    }

    if (matchUrl(url, '/compliance/history') && method === 'get') {
      await delay()
      mockResponse = mockComplianceHistory
    }

    if (matchUrl(url, '/compliance/confirm') && method === 'post') {
      await delay(300)
      const data = parseBody(config.data)
      if (mockSettings.compliance_enforcement && data.confirmed !== true) {
        return rejectWith(422, 'Compliance confirmation is required when enforcement is enabled.')
      }
      const operationId = data.operation_id || `op-${Date.now()}`
      pushComplianceHistory(data, data.action || 'unknown', operationId)
      mockResponse = {
        status: 'ok',
        enforcement: Boolean(mockSettings.compliance_enforcement),
        operation_id: operationId,
        action: data.action || 'unknown',
        reason: data.reason || '',
        confirmed: data.confirmed === true,
        compliance_bypassed: data.confirmed === true ? false : true,
      }
    }

    // DASHBOARD
    if (matchUrl(url, '/dashboard/stats') && method === 'get') {
      await delay()
      mockResponse = mockDashboardStats
    }

    // INCIDENTS
    if (matchUrl(url, '/incidents') && method === 'get') {
      await delay()
      mockResponse = mockIncidents
    }

    if (matchUrl(url, '/incidents') && method === 'post') {
      await delay(400)
      mockResponse = { status: 'resolved' }
    }

    // HEALTH
    if (matchUrl(url, '/health')) {
      mockResponse = {
        status: 'ok',
        components: {
          api: { status: 'up' },
          postgres: { status: 'up' },
          qdrant: { status: 'up' },
          ollama: { status: 'up', required: false },
        },
      }
    }

    if (mockResponse !== null) {
      return returnMock(mockResponse, config)
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
