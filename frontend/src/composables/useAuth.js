import { computed } from 'vue'
import { useAuthStore } from '@/store/auth'

export function useAuth() {
  const authStore = useAuthStore()

  const isAdmin = computed(() => authStore.isAdmin)
  const isCurator = computed(() => authStore.isCurator)
  const isAnalyst = computed(() => authStore.isAnalyst)
  const isUser = computed(() => authStore.isUser)

  const canIngest = computed(() => authStore.hasRole('admin', 'curator'))
  const canManageSources = computed(() => authStore.hasRole('admin', 'curator'))
  const canViewAudit = computed(() => authStore.hasRole('admin'))
  const canManageSettings = computed(() => authStore.hasRole('admin'))
  const canQuery = computed(() => authStore.hasRole('admin', 'curator', 'analyst', 'user'))
  const canViewExperiments = computed(() => authStore.hasRole('analyst'))

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
