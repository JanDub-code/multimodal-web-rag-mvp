<template>
  <v-app>
    <template v-if="isLoginPage">
      <router-view />
    </template>
    <template v-else>
      <AppSidebar />
      <v-main class="app-main">
        <AppToolbar />
        <div class="app-content">
          <ComplianceBanner />
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </div>
      </v-main>
    </template>
  </v-app>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppToolbar from '@/components/layout/AppToolbar.vue'
import ComplianceBanner from '@/components/compliance/ComplianceBanner.vue'

const route = useRoute()
const isLoginPage = computed(() => route.name === 'Login')
</script>

<style lang="scss">
@use '@/assets/styles/main.scss';

.app-main {
  background: $bg-body;
  min-height: 100vh;
}

.app-content {
  padding: $space-lg $space-xl;
  max-width: 1400px;

  @media (max-width: 599px) {
    padding: $space-base;
  }
}
</style>
