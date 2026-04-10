<template>
  <v-navigation-drawer
    v-model="appStore.sidebarOpen"
    :width="240"
    class="sidebar"
  >
    <!-- Logo / Title -->
    <div class="sidebar__header">
      <v-icon color="primary" size="28" class="mr-2">mdi-cube-outline</v-icon>
      <span class="sidebar__title" style="font-size: 1.1rem; line-height: 1.2;">Local Multimodal MVP</span>
    </div>

    <v-divider class="mx-4 mb-2" />

    <!-- Navigation Items -->
    <v-list density="comfortable" nav class="sidebar__nav">
      <v-list-item
        v-for="item in visibleItems"
        :key="item.path"
        :to="item.path"
        :prepend-icon="item.icon"
        :title="item.title"
        :active="isActive(item.path)"
        rounded="lg"
        class="sidebar__item"
        color="primary"
      />
    </v-list>

    <template #append>
      <div class="sidebar__footer">
        <v-divider class="mb-3" />
        <div class="sidebar__user">
          <v-avatar size="36" color="primary" class="mr-3">
            <v-icon color="white" size="20">mdi-account</v-icon>
          </v-avatar>
          <div class="sidebar__user-info">
            <div class="sidebar__username">{{ authStore.username || 'User' }}</div>
            <v-chip
              :color="roleColor"
              size="x-small"
              label
              class="sidebar__role-chip"
            >
              {{ authStore.roleLabel }}
            </v-chip>
          </div>
        </div>
      </div>
    </template>
  </v-navigation-drawer>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'

const authStore = useAuthStore()
const appStore = useAppStore()
const route = useRoute()

const isMobile = computed(() => window.innerWidth < 600)

const allItems = [
  { title: 'Chat', icon: 'mdi-chat-plus-outline', path: '/chat', roles: ['Admin', 'Curator', 'Analyst', 'User'] },
  { title: 'Audit', icon: 'mdi-shield-check-outline', path: '/audit', roles: ['Admin'] },
  { title: 'Správa zdrojů', icon: 'mdi-database-outline', path: '/sources', roles: ['Admin', 'Curator'] },
  { title: 'Systémová nastavení', icon: 'mdi-cog-outline', path: '/settings', roles: ['Admin'] },
  { title: 'Experimenty', icon: 'mdi-flask-outline', path: '/experiments', roles: ['Analyst'] },
  { title: 'Compliance', icon: 'mdi-clipboard-check-outline', path: '/compliance', roles: ['Admin', 'Curator', 'Analyst', 'User'] },
]

const visibleItems = computed(() =>
  allItems.filter((item) => item.roles.includes(authStore.role))
)

const roleColor = computed(() => {
  const colors = {
    Admin: '#7C4DFF',
    Curator: '#2196F3',
    Analyst: '#5C6BC0',
    User: '#4CAF50',
  }
  return colors[authStore.role] || '#9E9E9E'
})

function isActive(path) {
  return route.path === path
}
</script>

<style lang="scss" scoped>
.sidebar {
  background: $bg-sidebar !important;
  border-right: 1px solid $border-color !important;

  &__header {
    display: flex;
    align-items: center;
    padding: $space-lg $space-base $space-base;
  }

  &__title {
    font-size: $font-size-lg;
    font-weight: $font-weight-bold;
    color: $text-primary;
    letter-spacing: -0.5px;
  }

  &__nav {
    padding: 0 $space-sm;
  }

  &__item {
    margin-bottom: 2px;
    font-size: $font-size-base;
    font-weight: $font-weight-medium;
    border-radius: $border-radius !important;
    transition: all $transition-fast;

    &:hover {
      background: $bg-hover;
    }
  }

  &__footer {
    padding: 0 $space-base $space-base;
  }

  &__user {
    display: flex;
    align-items: center;
    padding: $space-sm;
  }

  &__user-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  &__username {
    font-size: $font-size-sm;
    font-weight: $font-weight-semibold;
    color: $text-primary;
  }

  &__role-chip {
    font-size: 10px !important;
    font-weight: $font-weight-bold;
    letter-spacing: 0.5px;
  }
}
</style>
