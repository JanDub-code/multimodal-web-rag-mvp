import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/store/auth'

import LoginView from '@/views/LoginView.vue'
import ChatView from '@/views/ChatView.vue'
import AuditView from '@/views/AuditView.vue'
import SourcesView from '@/views/SourcesView.vue'
import SettingsView from '@/views/SettingsView.vue'
import ExperimentsView from '@/views/ExperimentsView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView
    },
    {
      path: '/',
      name: 'chat',
      component: ChatView,
      meta: { requiresAuth: true }
    },
    {
      path: '/audit',
      name: 'audit',
      component: AuditView,
      meta: { requiresAuth: true, role: 'admin' }
    },
    {
      path: '/sources',
      name: 'sources',
      component: SourcesView,
      meta: { requiresAuth: true, role: 'curator' }
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView,
      meta: { requiresAuth: true, role: 'admin' }
    },
    {
      path: '/experiments',
      name: 'experiments',
      component: ExperimentsView,
      meta: { requiresAuth: true, role: 'analyst' }
    }
  ]
})

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    next('/login')
  } else if (to.meta.role) {
    // RBAC check
    if (to.meta.role === 'admin' && !auth.isAdmin) next('/')
    else if (to.meta.role === 'curator' && !auth.isCurator) next('/')
    else if (to.meta.role === 'analyst' && !auth.isAnalyst) next('/')
    else next()
  } else {
    next()
  }
})

export default router
