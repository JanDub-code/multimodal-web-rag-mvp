import api from '@/plugins/axios'

export const complianceService = {
  async getHistory() {
    const response = await api.get('/compliance/history')
    return response.data
  },

  async confirm(data) {
    const response = await api.post('/compliance/confirm', data)
    return response.data
  },
}
