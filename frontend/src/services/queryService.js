import api from '@/plugins/axios'

const LOCAL_SESSIONS_KEY = 'query_sessions_v1'
const SESSION_NOT_IMPLEMENTED_STATUS = new Set([404, 405])
const USE_LOCAL_SESSIONS_ONLY = true
let useLocalSessionsFallback = USE_LOCAL_SESSIONS_ONLY

function readLocalSessions() {
  try {
    const raw = localStorage.getItem(LOCAL_SESSIONS_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeLocalSessions(sessions) {
  localStorage.setItem(LOCAL_SESSIONS_KEY, JSON.stringify(sessions))
}

function toSessionListItem(session) {
  return {
    id: session.id,
    title: session.title,
    updated_at: session.updated_at,
  }
}

function shouldFallbackToLocal(error) {
  const status = error?.response?.status
  if (SESSION_NOT_IMPLEMENTED_STATUS.has(status)) return true
  if (!status) return true
  if (status >= 500) return true
  return false
}

function buildAiMessage(data, fallbackOperationId = null) {
  return {
    id: `msg-a-${Date.now()}`,
    role: 'ai',
    content: data?.answer || data?.message?.content || 'Zadna odpoved nebyla vygenerovana.',
    citations: Array.isArray(data?.citations) ? data.citations : [],
    timestamp: new Date().toISOString(),
    operation_id: data?.operation_id || fallbackOperationId,
  }
}

function getLocalSession(id) {
  return readLocalSessions().find((s) => s.id === id)
}

function createLocalSession(title = 'Nova konverzace') {
  const newSession = {
    id: `local-${Date.now()}`,
    title,
    updated_at: new Date().toISOString(),
    messages: [],
  }

  const sessions = readLocalSessions()
  sessions.unshift(newSession)
  writeLocalSessions(sessions)
  return toSessionListItem(newSession)
}

function appendLocalSessionMessages(sessionId, queryText, aiMessage) {
  const sessions = readLocalSessions()
  const idx = sessions.findIndex((s) => s.id === sessionId)
  if (idx < 0) return

  const userMessage = {
    id: `msg-u-${Date.now()}`,
    role: 'user',
    content: queryText,
    timestamp: new Date().toISOString(),
  }

  const updated = {
    ...sessions[idx],
    messages: [...(sessions[idx].messages || []), userMessage, aiMessage],
    updated_at: new Date().toISOString(),
  }

  sessions.splice(idx, 1)
  sessions.unshift(updated)
  writeLocalSessions(sessions)
}

export const queryService = {
  async getSessions() {
    if (useLocalSessionsFallback) {
      return readLocalSessions().map(toSessionListItem)
    }

    try {
      const response = await api.get('/chat/sessions')
      return response.data
    } catch (error) {
      if (!shouldFallbackToLocal(error)) throw error
      useLocalSessionsFallback = true
      return readLocalSessions().map(toSessionListItem)
    }
  },

  async getSession(id) {
    if (useLocalSessionsFallback) {
      const session = getLocalSession(id)
      if (!session) {
        const notFound = new Error('Session not found')
        notFound.response = { status: 404 }
        throw notFound
      }
      return session
    }

    try {
      const response = await api.get(`/chat/sessions/${id}`)
      return response.data
    } catch (error) {
      if (!shouldFallbackToLocal(error)) throw error
      useLocalSessionsFallback = true

      const session = getLocalSession(id)
      if (!session) {
        const notFound = new Error('Session not found')
        notFound.response = { status: 404 }
        throw notFound
      }
      return session
    }
  },

  async createSession(title = 'Nova konverzace') {
    if (useLocalSessionsFallback) {
      return createLocalSession(title)
    }

    try {
      const response = await api.post('/chat/sessions', { title })
      return response.data
    } catch (error) {
      if (!shouldFallbackToLocal(error)) throw error
      useLocalSessionsFallback = true
      return createLocalSession(title)
    }
  },

  async query(
    text,
    mode = 'rag',
    topK = 5,
    model = null,
    operationId = null,
    sessionId = null,
    conversationHistory = [],
    compliance = {}
  ) {
    const response = await api.post(
      '/query/',
      {
        query: text,
        mode,
        top_k: topK,
        model,
        operation_id: operationId,
        conversation_history: conversationHistory,
        compliance_confirmed: compliance.complianceConfirmed,
        compliance_bypassed: compliance.complianceBypassed,
        compliance_reason: compliance.complianceReason,
      },
      {
        // Query generation can legitimately take longer than 30s.
        timeout: 0,
      }
    )

    const data = response.data || {}
    const resolvedOperationId = data.operation_id || operationId
    const message = data.message || buildAiMessage(data, resolvedOperationId)

    const isLocalSession = typeof sessionId === 'string' && sessionId.startsWith('local-')
    if ((useLocalSessionsFallback || isLocalSession) && sessionId) {
      appendLocalSessionMessages(sessionId, text, message)
    }

    return {
      ...data,
      operation_id: resolvedOperationId,
      message,
    }
  },
}
