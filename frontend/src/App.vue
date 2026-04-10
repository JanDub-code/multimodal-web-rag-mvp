<template>
  <v-app>
    <v-navigation-drawer v-if="authStore.isAuthenticated" app class="bg-indigo-lighten-5 border-r">
      <div class="pa-4 pt-6 d-flex flex-column align-center">
        <!-- Logo or placeholder -->
        <v-icon size="48" color="primary">mdi-robot-outline</v-icon>
        <h2 class="text-h6 mt-2 primary--text font-weight-bold">AI Asistent</h2>
      </div>

      <v-list density="compact" nav class="mt-4">
        <v-list-item to="/" prepend-icon="mdi-chat-processing-outline" title="Chat" base-color="primary"></v-list-item>
        
        <v-list-item v-if="authStore.isAdmin" to="/audit" prepend-icon="mdi-lock-outline" title="Audit" base-color="primary"></v-list-item>
        
        <v-list-item v-if="authStore.isCurator" to="/sources" prepend-icon="mdi-database-outline" title="Správa zdrojů" base-color="primary"></v-list-item>
        <v-list-item v-if="authStore.isCurator" to="/ingest" prepend-icon="mdi-cloud-upload-outline" title="Ingest" base-color="primary"></v-list-item>
        
        <v-list-item v-if="authStore.isAnalyst" to="/experiments" prepend-icon="mdi-flask-outline" title="Experimenty" base-color="primary"></v-list-item>
        
        <v-list-item v-if="authStore.isAdmin" to="/settings" prepend-icon="mdi-cog-outline" title="Systémová nastavení" base-color="primary"></v-list-item>
      </v-list>

      <template v-slot:append>
        <div class="pa-4 border-t d-flex align-center">
          <v-avatar color="primary" class="mr-3" size="40">
            <span class="text-white">{{ authStore.user.charAt(0).toUpperCase() }}</span>
          </v-avatar>
          <div class="flex-grow-1">
            <div class="font-weight-bold">{{ authStore.user }}</div>
            <v-chip size="x-small" :color="roleColor" class="mt-1 font-weight-bold" label>
              {{ authStore.role.toUpperCase() }}
            </v-chip>
          </div>
          <v-btn icon="mdi-logout" variant="text" size="small" @click="logout" color="error"></v-btn>
        </div>
      </template>
    </v-navigation-drawer>

    <v-main class="bg-grey-lighten-4">
      <router-view></router-view>
    </v-main>
  </v-app>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'

const authStore = useAuthStore()
const router = useRouter()

const roleColor = computed(() => {
  const role = authStore.role.toLowerCase()
  if (role === 'admin') return 'error'
  if (role === 'analyst') return 'accent'
  if (role === 'user') return 'info'
  if (role === 'curator') return 'success'
  return 'secondary'
})

const logout = () => {
  authStore.logout()
  router.push('/login')
}
</script>

<style>
/* Basic Global Overrides matching sleek aesthetic */
html, body {
  font-family: 'Inter', 'Roboto', sans-serif !important;
}
.v-application {
  background-color: #f8fafc !important; /* Tailwind slate-50 */
}
.border-r {
  border-right: 1px solid #e2e8f0;
}
.border-t {
  border-top: 1px solid #e2e8f0;
}

/* Global button text color override for primary variant */
.v-btn.bg-primary {
  color: #ffffff !important;
}

/* More beautiful table headers globally */
.v-table th {
  background-color: #f1f5f9 !important; /* Tailwind slate-100 */
  color: #475569 !important; /* Tailwind slate-600 */
  text-transform: uppercase;
  font-size: 0.75rem !important;
  letter-spacing: 0.05em;
  border-bottom: 2px solid #e2e8f0 !important;
}
.v-table td {
  border-bottom: 1px solid #f1f5f9 !important;
}
</style>
