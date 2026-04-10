import api from '@/plugins/axios'

const LOCAL_SESSIONS_KEY = 'query_sessions_v1'
const SESSION_NOT_IMPLEMENTED_STATUS = new Set([404, 405])
let useLocalSessionsFallback = false

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
  return SESSION_NOT_IMPLEMENTED_STATUS.has(status)
}

function buildAiMessage(data, fallbackOperationId = null) {
  return {
    id: `msg-a-${Date.now()}`,
    role: 'ai',
    content: data?.answer || data?.message?.content || 'Žádná odpověď nebyla vygenerována.',
    citations: Array.isArray(data?.citations) ? data.citations : [],
    timestamp: new Date().toISOString(),
    operation_id: data?.operation_id || fallbackOperationId,
  }
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
    if (!useLocalSessionsFallback) {
      try {
        const response = await api.get('/chat/sessions')
        return response.data
      } catch (error) {
        if (!shouldFallbackToLocal(error)) throw error
        useLocalSessionsFallback = true
      }
    }

    return readLocalSessions().map(toSessionListItem)
  },

  async getSession(id) {
    if (!useLocalSessionsFallback) {
      try {
        const response = await api.get(`/chat/sessions/${id}`)
        return response.data
      } catch (error) {
        if (!shouldFallbackToLocal(error)) throw error
        useLocalSessionsFallback = true
      }
    }

    const session = readLocalSessions().find((s) => s.id === id)
    if (!session) {
      const notFound = new Error('Session not found')
      notFound.response = { status: 404 }
      throw notFound
    }

    return session
  },

  async createSession(title = 'Nová konverzace') {
    if (!useLocalSessionsFallback) {
      try {
        const response = await api.post('/chat/sessions', { title })
        return response.data
      } catch (error) {
        if (!shouldFallbackToLocal(error)) throw error
        useLocalSessionsFallback = true
      }
    }

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
  },

  async query(
    text,
    mode = 'rag',
    topK = 5,
    operationId = null,
    sessionId = null,
    compliance = {}
  ) {
    const response = await api.post('/query/', {
      query: text,
      mode,
      top_k: topK,
      operation_id: operationId,
      session_id: sessionId,
      compliance_confirmed: compliance.complianceConfirmed,
      compliance_bypassed: compliance.complianceBypassed,
      compliance_reason: compliance.complianceReason,
    })

    const data = response.data || {}
    const resolvedOperationId = data.operation_id || operationId
    const message = data.message || buildAiMessage(data, resolvedOperationId)

    if (useLocalSessionsFallback && sessionId) {
      appendLocalSessionMessages(sessionId, text, message)
    }

    return {
      ...data,
      operation_id: resolvedOperationId,
      message,
    }
  },
}
