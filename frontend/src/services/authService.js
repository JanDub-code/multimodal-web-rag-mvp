import api from '@/plugins/axios'

export const authService = {
  async login(username, password) {
    const body = new URLSearchParams()
    body.append('username', username)
    body.append('password', password)
    const response = await api.post('/auth/login', body, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    return response.data
  },

  async refresh(refreshToken) {
    const response = await api.post('/auth/refresh', { refresh_token: refreshToken })
    return response.data
  },

  async logout(refreshToken) {
    const response = await api.post('/auth/logout', { refresh_token: refreshToken })
    return response.data
  },
}
