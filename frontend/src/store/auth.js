import { defineStore } from 'pinia'
import axios from 'axios'

function normalizeRole(role) {
  return String(role || '').trim().toLowerCase()
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    role: localStorage.getItem('role') || '',
    user: localStorage.getItem('username') || '',
  }),
  getters: {
    isAuthenticated: (state) => !!state.token,
    isLoggedIn: (state) => !!state.token,
    username: (state) => state.user,
    roleNormalized: (state) => normalizeRole(state.role),
    roleLabel: (state) => (state.role ? String(state.role).toUpperCase() : ''),
    isAdmin: (state) => normalizeRole(state.role) === 'admin',
    isCurator: (state) => {
      const role = normalizeRole(state.role)
      return role === 'curator' || role === 'admin'
    },
    isAnalyst: (state) => normalizeRole(state.role) === 'analyst',
    isUser: (state) => normalizeRole(state.role) === 'user',
  },
  actions: {
    setAuth(accessToken, role, username) {
      this.token = accessToken || ''
      this.role = role || ''
      this.user = username || ''

      localStorage.setItem('token', this.token)
      localStorage.setItem('role', this.role)
      localStorage.setItem('username', this.user)

      if (this.token) {
        axios.defaults.headers.common.Authorization = `Bearer ${this.token}`
      } else {
        delete axios.defaults.headers.common.Authorization
      }
    },
    async login(usernameOrPayload, password) {
      if (typeof usernameOrPayload === 'object' && usernameOrPayload !== null) {
        this.setAuth(
          usernameOrPayload.access_token || '',
          usernameOrPayload.role || '',
          usernameOrPayload.username || ''
        )
        return true
      }

      const username = String(usernameOrPayload || '')
      try {
        const formData = new URLSearchParams()
        formData.append('username', username)
        formData.append('password', password)
        const response = await axios.post('/api/auth/login', formData)

        this.setAuth(
          response.data.access_token,
          response.data.role,
          response.data.username || username
        )
        return true
      } catch (error) {
        console.error('Login failed', error)
        throw error
      }
    },
    hasRole(...roles) {
      const current = normalizeRole(this.role)
      return roles.map((role) => normalizeRole(role)).includes(current)
    },
    logout() {
      this.setAuth('', '', '')
      localStorage.removeItem('token')
      localStorage.removeItem('role')
      localStorage.removeItem('username')
    },
    initializeAuth() {
      if (this.token) {
        axios.defaults.headers.common.Authorization = `Bearer ${this.token}`
      }
    }
  }
})
