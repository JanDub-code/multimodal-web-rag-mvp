import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresAuth: false, layout: 'none' },
  },
  {
    path: '/',
    redirect: '/chat',
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { requiresAuth: true, roles: ['Admin'] }, // Deprecated gracefully
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/QueryView.vue'),
    meta: { requiresAuth: true, roles: ['Admin', 'Curator', 'Analyst', 'User'] },
  },
  {
    path: '/audit',
    name: 'Audit',
    component: () => import('@/views/AuditView.vue'),
    meta: { requiresAuth: true, roles: ['Admin'] },
  },
  {
    path: '/sources',
    name: 'Správa zdrojů',
    component: () => import('@/views/SourcesView.vue'),
    meta: { requiresAuth: true, roles: ['Admin', 'Curator'] },
  },
  {
    path: '/settings',
    name: 'Systémová nastavení',
    component: () => import('@/views/SettingsView.vue'),
    meta: { requiresAuth: true, roles: ['Admin'] },
  },
  {
    path: '/ingest',
    name: 'Ingest',
    component: () => import('@/views/IngestView.vue'),
    meta: { requiresAuth: true, roles: ['Admin', 'Curator'] },
  },
  {
    path: '/compliance',
    name: 'Compliance',
    component: () => import('@/views/ComplianceView.vue'),
    meta: { requiresAuth: true, roles: ['Admin', 'Curator', 'Analyst', 'User'] },
  },
  {
    path: '/experiments',
    name: 'Experimenty',
    component: () => import('@/views/ExperimentsView.vue'),
    meta: { requiresAuth: true, roles: ['Analyst'] },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth === false) {
    if (authStore.isLoggedIn && to.name === 'Login') {
      return next('/dashboard')
    }
    return next()
  }

  if (!authStore.isLoggedIn) {
    return next('/login')
  }

  const allowedRoles = to.meta.roles
  if (allowedRoles && !allowedRoles.includes(authStore.role)) {
    return next('/dashboard')
  }

  next()
})

export default router
