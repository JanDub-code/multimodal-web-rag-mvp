<template>
  <v-container class="login-page" fluid>
    <div class="login-wrapper">
      <v-card class="login-card" elevation="8">
        <div class="login-card__header">
          <v-icon color="primary" size="48" class="mb-3">mdi-cube-outline</v-icon>
          <h1 class="login-card__title">Local Multimodal MVP</h1>
          <p class="login-card__subtitle">Multimodal Document Intelligence</p>
        </div>

        <v-card-text class="login-card__body">
          <v-select
            v-model="selectedAccount"
            label="Účet (dev)"
            :items="accountOptions"
            item-title="label"
            item-value="key"
            variant="outlined"
            density="comfortable"
            prepend-inner-icon="mdi-account-switch"
            class="mb-1"
            @update:model-value="applyAccount"
          />
          <v-text-field
            v-model="form.username"
            label="Uživatelské jméno"
            prepend-inner-icon="mdi-account-outline"
            :error-messages="error"
            autofocus
            @keyup.enter="handleLogin"
          />
          <v-text-field
            v-model="form.password"
            label="Heslo"
            :type="showPassword ? 'text' : 'password'"
            prepend-inner-icon="mdi-lock-outline"
            :append-inner-icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'"
            @click:append-inner="showPassword = !showPassword"
            @keyup.enter="handleLogin"
          />
          <v-btn
            color="primary"
            size="large"
            block
            :loading="loading"
            class="mt-2"
            @click="handleLogin"
          >
            Přihlásit se
          </v-btn>
        </v-card-text>
      </v-card>
    </div>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { authService } from '@/services/authService'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const error = ref('')
const showPassword = ref(false)
const selectedAccount = ref('admin')

const form = ref({
  username: 'admin',
  password: 'admin123',
})

const accountOptions = [
  { key: 'admin', label: 'Admin (plný přístup)', username: 'admin', password: 'admin123' },
  { key: 'curator', label: 'Curator (ingest + zdroje)', username: 'curator', password: 'curator123' },
  { key: 'analyst', label: 'Analyst (dotazy + analýza)', username: 'analyst', password: 'analyst123' },
  { key: 'user', label: 'User (dotazy)', username: 'user', password: 'user123' },
]

function applyAccount(key) {
  const account = accountOptions.find((a) => a.key === key)
  if (account) {
    form.value.username = account.username
    form.value.password = account.password
  }
}

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    const data = await authService.login(form.value.username, form.value.password)
    authStore.login({
      access_token: data.access_token,
      role: data.role,
      username: form.value.username,
    })
    router.push('/dashboard')
  } catch (err) {
    error.value = err?.response?.data?.detail || 'Přihlášení selhalo'
  } finally {
    loading.value = false
  }
}

// Pre-select admin account
applyAccount('admin')
</script>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-wrapper {
  width: 100%;
  max-width: 440px;
  padding: $space-base;
}

.login-card {
  border-radius: $border-radius-xl !important;
  overflow: hidden;
  border: none !important;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3) !important;

  &__header {
    text-align: center;
    padding: $space-2xl $space-xl $space-lg;
    background: linear-gradient(135deg, rgba($primary, 0.05), rgba($accent, 0.05));
  }

  &__title {
    font-size: $font-size-2xl;
    font-weight: $font-weight-bold;
    color: $text-primary;
    margin-bottom: $space-xs;
  }

  &__subtitle {
    font-size: $font-size-sm;
    color: $text-secondary;
    letter-spacing: 1px;
    text-transform: uppercase;
  }

  &__body {
    padding: $space-lg $space-xl $space-2xl;
  }
}
</style>
