import api from '@/plugins/axios'

export const complianceService = {
  async getMode() {
    const response = await api.get('/compliance/mode')
    return response.data
  },

  async setMode(enforcement) {
    const response = await api.put('/compliance/mode', { enforcement })
    return response.data
  },

  async getHistory() {
    const response = await api.get('/compliance/history')
    return response.data
  },

  async confirm(data) {
    const response = await api.post('/compliance/confirm', data)
    return response.data
  },
}
