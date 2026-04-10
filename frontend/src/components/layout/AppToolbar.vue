<template>
  <div class="toolbar">
    <div class="toolbar__left">
      <v-btn
        icon="mdi-menu"
        variant="text"
        size="small"
        class="d-md-none"
        @click="appStore.toggleSidebar()"
      />
    </div>
    <div class="toolbar__right">
      <v-chip
        v-if="complianceStore.isEnforced"
        color="success"
        size="small"
        prepend-icon="mdi-shield-check"
        variant="tonal"
        class="mr-3"
      >
        Enforcement ON
      </v-chip>
      <v-chip
        v-else
        color="warning"
        size="small"
        prepend-icon="mdi-shield-off-outline"
        variant="tonal"
        class="mr-3"
      >
        Dev Mode
      </v-chip>
      <v-btn
        icon="mdi-logout"
        variant="text"
        size="small"
        @click="handleLogout"
        title="Odhlásit se"
      />
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { useAppStore } from '@/stores/app'
import { useComplianceStore } from '@/stores/compliance'

const router = useRouter()
const authStore = useAuthStore()
const appStore = useAppStore()
const complianceStore = useComplianceStore()

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style lang="scss" scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $space-sm $space-xl;
  background: transparent;
  min-height: 48px;

  &__left {
    display: flex;
    align-items: center;
  }

  &__right {
    display: flex;
    align-items: center;
  }
}
</style>
