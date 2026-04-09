import api from '@/plugins/axios'

export const sourceService = {
  async getSources() {
    const response = await api.get('/sources')
    return response.data
  },

  async createSource(data) {
    const response = await api.post('/ingest/sources', data)
    return response.data
  },

  async deleteSource(id) {
    const response = await api.delete(`/sources/${id}`)
    return response.data
  },

  async getIncidents() {
    const response = await api.get('/incidents')
    return response.data
  },

  async resolveIncident(id) {
    const response = await api.post(`/incidents/${id}/resolve`)
    return response.data
  },
}
