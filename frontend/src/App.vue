<template>
  <v-app>
    <v-layout class="app-shell">
      <v-navigation-drawer
        v-if="authStore.isAuthenticated"
        :model-value="true"
        :width="248"
        permanent
        class="bg-indigo-lighten-5 border-r"
      >
        <div class="pa-4 pt-6 d-flex flex-column align-center">
          <v-icon size="48" color="primary">mdi-robot-outline</v-icon>
          <h2 class="text-h6 mt-2 primary--text font-weight-bold">AI Asistent</h2>
        </div>

        <v-list density="compact" nav class="mt-4">
          <v-list-item to="/dashboard" prepend-icon="mdi-view-dashboard-outline" title="Dashboard" base-color="primary" />
          <v-list-item to="/chat" prepend-icon="mdi-chat-processing-outline" title="Chat" base-color="primary" />

          <v-list-item v-if="authStore.isAdmin" to="/audit" prepend-icon="mdi-lock-outline" title="Audit" base-color="primary" />

          <v-list-item v-if="authStore.isCurator" to="/sources" prepend-icon="mdi-database-outline" title="Sprava zdroju" base-color="primary" />
          <v-list-item v-if="authStore.isCurator" to="/ingest" prepend-icon="mdi-cloud-upload-outline" title="Ingest" base-color="primary" />

          <v-list-item to="/compliance" prepend-icon="mdi-clipboard-check-outline" title="Compliance" base-color="primary" />

          <v-list-item v-if="authStore.isAnalyst" to="/experiments" prepend-icon="mdi-flask-outline" title="Experimenty" base-color="primary" />

          <v-list-item v-if="authStore.isAdmin" to="/settings" prepend-icon="mdi-cog-outline" title="Systemova nastaveni" base-color="primary" />
        </v-list>

        <template #append>
          <div class="pa-4 border-t d-flex align-center">
            <v-avatar color="primary" class="mr-3" size="40">
              <span class="text-white">{{ userInitial }}</span>
            </v-avatar>
            <div class="flex-grow-1">
              <div class="font-weight-bold">{{ authStore.username || 'user' }}</div>
              <v-chip size="x-small" :color="roleColor" class="mt-1 font-weight-bold" label>
                {{ authStore.roleLabel || 'UNKNOWN' }}
              </v-chip>
            </div>
            <v-btn icon="mdi-logout" variant="text" size="small" @click="logout" color="error" />
          </div>
        </template>
      </v-navigation-drawer>

      <v-main class="bg-grey-lighten-4">
        <router-view />
      </v-main>
    </v-layout>
  </v-app>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'

const authStore = useAuthStore()
const router = useRouter()

const roleColor = computed(() => {
  const role = authStore.roleNormalized
  if (role === 'admin') return 'error'
  if (role === 'analyst') return 'accent'
  if (role === 'user') return 'info'
  if (role === 'curator') return 'success'
  return 'secondary'
})

const userInitial = computed(() => {
  const name = authStore.username || ''
  return name ? name.charAt(0).toUpperCase() : '?'
})

const logout = () => {
  authStore.logout()
  router.push('/login')
}
</script>

<style>
html,
body {
  font-family: 'Inter', 'Roboto', sans-serif !important;
}

.v-application {
  background-color: #f8fafc !important;
}

.app-shell {
  min-height: 100vh;
}

.border-r {
  border-right: 1px solid #e2e8f0;
}

.border-t {
  border-top: 1px solid #e2e8f0;
}

.v-btn.bg-primary {
  color: #ffffff !important;
}

.v-table th {
  background-color: #f1f5f9 !important;
  color: #475569 !important;
  text-transform: uppercase;
  font-size: 0.75rem !important;
  letter-spacing: 0.05em;
  border-bottom: 2px solid #e2e8f0 !important;
}

.v-table td {
  border-bottom: 1px solid #f1f5f9 !important;
}
</style>
