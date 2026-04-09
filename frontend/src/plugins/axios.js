import axios from 'axios'
import { useMockInterceptor } from '@/services/mock/mockInterceptor'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor: attach auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor: handle 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('role')
      localStorage.removeItem('username')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Apply mock interceptor for local testing ONLY if VITE_USE_MOCK is explicitly true
if (import.meta.env.VITE_USE_MOCK === 'true') {
  useMockInterceptor(api)
}

export default api
