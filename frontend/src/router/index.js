import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/store/auth'

import LoginView from '@/views/LoginView.vue'
import DashboardView from '@/views/DashboardView.vue'
import ChatView from '@/views/ChatView.vue'
import QueryView from '@/views/QueryView.vue'
import AuditView from '@/views/AuditView.vue'
import SourcesView from '@/views/SourcesView.vue'
import IngestView from '@/views/IngestView.vue'
import SettingsView from '@/views/SettingsView.vue'
import ExperimentsView from '@/views/ExperimentsView.vue'
import ComplianceView from '@/views/ComplianceView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
    },
    {
      path: '/',
      redirect: '/chat',
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: DashboardView,
      meta: { requiresAuth: true },
    },
    {
      path: '/chat',
      name: 'chat',
      component: ChatView,
      meta: { requiresAuth: true },
    },
    {
      path: '/query',
      name: 'query',
      component: QueryView,
      meta: { requiresAuth: true },
    },
    {
      path: '/audit',
      name: 'audit',
      component: AuditView,
      meta: { requiresAuth: true, roles: ['admin'] },
    },
    {
      path: '/sources',
      name: 'sources',
      component: SourcesView,
      meta: { requiresAuth: true, roles: ['admin', 'curator'] },
    },
    {
      path: '/ingest',
      name: 'ingest',
      component: IngestView,
      meta: { requiresAuth: true, roles: ['admin', 'curator'] },
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView,
      meta: { requiresAuth: true, roles: ['admin'] },
    },
    {
      path: '/experiments',
      name: 'experiments',
      component: ExperimentsView,
      meta: { requiresAuth: true, roles: ['analyst'] },
    },
    {
      path: '/compliance',
      name: 'compliance',
      component: ComplianceView,
      meta: { requiresAuth: true, roles: ['admin', 'curator', 'analyst', 'user'] },
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/chat',
    },
  ],
})

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()

  if (to.name === 'login' && auth.isAuthenticated) {
    next('/chat')
    return
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    next('/login')
    return
  }

  const routeRoles = Array.isArray(to.meta.roles) ? to.meta.roles : []
  if (routeRoles.length > 0 && !auth.hasRole(...routeRoles)) {
    next('/chat')
    return
  }

  next()
})

export default router
