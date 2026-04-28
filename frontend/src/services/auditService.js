import api from '@/plugins/axios'

export const auditService = {
  async getAuditLogs(filters = {}) {
    const response = await api.get('/audit/', { params: filters })
    return response.data
  },
}