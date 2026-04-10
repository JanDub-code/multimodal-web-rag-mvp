import { defineStore } from 'pinia'
import axios from 'axios'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    role: localStorage.getItem('role') || '',
    user: localStorage.getItem('username') || '',
  }),
  getters: {
    isAuthenticated: (state) => !!state.token,
    isAdmin: (state) => state.role.toLowerCase() === 'admin',
    isCurator: (state) => state.role.toLowerCase() === 'curator' || state.role.toLowerCase() === 'admin',
    isAnalyst: (state) => state.role.toLowerCase() === 'analyst',
  },
  actions: {
    async login(username, password) {
      try {
        const formData = new URLSearchParams()
        formData.append('username', username)
        formData.append('password', password)
        const response = await axios.post('/api/auth/login', formData)
        
        this.token = response.data.access_token
        this.role = response.data.role
        this.user = username
        
        localStorage.setItem('token', this.token)
        localStorage.setItem('role', this.role)
        localStorage.setItem('username', this.user)
        
        axios.defaults.headers.common['Authorization'] = `Bearer ${this.token}`
        return true
      } catch (error) {
        console.error('Login failed', error)
        throw error
      }
    },
    logout() {
      this.token = ''
      this.role = ''
      this.user = ''
      localStorage.removeItem('token')
      localStorage.removeItem('role')
      localStorage.removeItem('username')
      delete axios.defaults.headers.common['Authorization']
    },
    initializeAuth() {
      if (this.token) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${this.token}`
      }
    }
  }
})
