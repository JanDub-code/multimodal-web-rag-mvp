import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

export function useAuth() {
  const authStore = useAuthStore()

  const isAdmin = computed(() => authStore.role === 'Admin')
  const isCurator = computed(() => authStore.role === 'Curator')
  const isAnalyst = computed(() => authStore.role === 'Analyst')
  const isUser = computed(() => authStore.role === 'User')

  const canIngest = computed(() => authStore.hasRole('Admin', 'Curator'))
  const canManageSources = computed(() => authStore.hasRole('Admin', 'Curator'))
  const canViewAudit = computed(() => authStore.hasRole('Admin'))
  const canManageSettings = computed(() => authStore.hasRole('Admin'))
  const canQuery = computed(() => authStore.hasRole('Admin', 'Curator', 'Analyst', 'User'))
  const canViewExperiments = computed(() => authStore.hasRole('Analyst'))

  return {
    isAdmin,
    isCurator,
    isAnalyst,
    isUser,
    canIngest,
    canManageSources,
    canViewAudit,
    canManageSettings,
    canQuery,
    canViewExperiments,
  }
}
