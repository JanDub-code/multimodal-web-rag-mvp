import api from '@/plugins/axios'

export const queryService = {
  async getSessions() {
    const response = await api.get('/chat/sessions')
    return response.data
  },

  async getSession(id) {
    const response = await api.get(`/chat/sessions/${id}`)
    return response.data
  },

  async createSession(title = 'Nová konverzace') {
    const response = await api.post('/chat/sessions', { title })
    return response.data
  },

  async query(text, mode = 'rag', topK = 5, operationId = null, sessionId = null) {
    const response = await api.post('/query/', {
      query: text,
      mode,
      top_k: topK,
      operation_id: operationId,
      session_id: sessionId
    })
    return response.data
  },
}
