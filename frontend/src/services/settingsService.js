import api from '@/plugins/axios'

export const settingsService = {
  async getSettings() {
    const response = await api.get('/settings')
    return response.data
  },

  async saveSettings(data) {
    const response = await api.put('/settings', data)
    return response.data
  },
}
