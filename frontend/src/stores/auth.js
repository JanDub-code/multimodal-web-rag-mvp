import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const role = ref(localStorage.getItem('role') || '')
  const username = ref(localStorage.getItem('username') || '')

  const isLoggedIn = computed(() => !!token.value)

  const roleLabels = {
    Admin: 'ADMIN',
    Curator: 'CURATOR',
    Analyst: 'ANALYST',
    User: 'USER',
  }

  const roleLabel = computed(() => roleLabels[role.value] || role.value)

  function login(data) {
    token.value = data.access_token
    role.value = data.role
    username.value = data.username || ''
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('role', data.role)
    localStorage.setItem('username', data.username || '')
  }

  function logout() {
    token.value = ''
    role.value = ''
    username.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('role')
    localStorage.removeItem('username')
  }

  function hasRole(...roles) {
    return roles.includes(role.value)
  }

  return {
    token,
    role,
    username,
    isLoggedIn,
    roleLabel,
    login,
    logout,
    hasRole,
  }
})
