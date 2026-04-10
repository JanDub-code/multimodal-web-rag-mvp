<template>
  <v-container class="fill-height pa-0" fluid style="background: linear-gradient(135deg, #e0e7ff 0%, #ffffff 100%);">
    <v-row align="center" justify="center" class="ma-0 w-100 h-100">
      <v-col cols="12" sm="8" md="5" lg="4" class="d-flex justify-center">
        <v-card class="elevation-12 rounded-xl w-100" style="overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04) !important;">
          <div class="bg-primary pt-8 pb-10 text-center position-relative" style="background: linear-gradient(135deg, #4f46e5 0%, #8b5cf6 100%);">
            <v-icon size="72" color="white" class="mb-4 opacity-90">mdi-robot-outline</v-icon>
            <h2 class="text-h4 font-weight-bold text-white mb-1">AI Asistent</h2>
            <div class="text-subtitle-1 text-white opacity-80">Interni RAG vyhledavani</div>
          </div>

          <v-card-text class="pa-8 pt-6">
            <h3 class="text-h6 font-weight-bold text-grey-darken-3 mb-6 text-center">Prihlaseni do systemu</h3>
            <v-form @submit.prevent="handleLogin">
              <v-select
                v-model="selectedAccount"
                label="Ucet (dev)"
                :items="accountOptions"
                item-title="label"
                item-value="key"
                prepend-inner-icon="mdi-account-switch"
                variant="outlined"
                class="mb-3"
                density="comfortable"
                bg-color="grey-lighten-4"
                @update:model-value="applyAccount"
              />

              <v-text-field
                v-model="username"
                label="Uzivatelske jmeno"
                prepend-inner-icon="mdi-account-outline"
                type="text"
                required
                variant="outlined"
                class="mb-3"
                density="comfortable"
                bg-color="grey-lighten-4"
              />

              <v-text-field
                v-model="password"
                label="Heslo"
                prepend-inner-icon="mdi-lock-outline"
                type="password"
                required
                variant="outlined"
                class="mb-6"
                density="comfortable"
                bg-color="grey-lighten-4"
              />

              <v-alert v-if="error" type="error" variant="tonal" class="mb-6 rounded-lg text-caption">
                {{ error }}
              </v-alert>

              <v-btn
                type="submit"
                color="primary"
                block
                size="x-large"
                class="font-weight-bold text-white rounded-lg mb-6"
                elevation="2"
                :loading="loading"
              >
                Prihlasit se
              </v-btn>
            </v-form>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('admin')
const password = ref('admin123')
const selectedAccount = ref('admin')
const loading = ref(false)
const error = ref('')

const accountOptions = [
  { key: 'admin', label: 'Admin (plny pristup)', username: 'admin', password: 'admin123' },
  { key: 'curator', label: 'Curator (ingest + zdroje)', username: 'curator', password: 'curator123' },
  { key: 'analyst', label: 'Analyst (dotazy + analyza)', username: 'analyst', password: 'analyst123' },
  { key: 'user', label: 'User (dotazy)', username: 'user', password: 'user123' },
]

function applyAccount(key) {
  const account = accountOptions.find((item) => item.key === key)
  if (!account) return
  username.value = account.username
  password.value = account.password
}

async function handleLogin() {
  if (!username.value || !password.value) return

  loading.value = true
  error.value = ''

  try {
    await authStore.login(username.value, password.value)
    router.push('/')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Neplatne prihlasovaci udaje.'
  } finally {
    loading.value = false
  }
}

applyAccount('admin')
</script>

<style scoped>
.opacity-90 {
  opacity: 0.9;
}
.opacity-80 {
  opacity: 0.8;
}
</style>
