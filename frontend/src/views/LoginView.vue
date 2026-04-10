<template>
  <v-container class="fill-height pa-0" fluid style="background: linear-gradient(135deg, #e0e7ff 0%, #ffffff 100%);">
    <v-row align="center" justify="center" class="ma-0 w-100 h-100">
      <v-col cols="12" sm="8" md="5" lg="4" class="d-flex justify-center">
        <v-card class="elevation-12 rounded-xl w-100" style="overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04) !important;">
          <!-- Header Banner -->
          <div class="bg-primary pt-8 pb-10 text-center position-relative" style="background: linear-gradient(135deg, #4f46e5 0%, #8b5cf6 100%);">
            <v-icon size="72" color="white" class="mb-4 opacity-90">mdi-robot-outline</v-icon>
            <h2 class="text-h4 font-weight-bold text-white mb-1">AI Asistent</h2>
            <div class="text-subtitle-1 text-white opacity-80">Interní RAG Vyhledávání</div>
            
            <!-- Curvy wave separator (optional CSS shape) -->
            <div class="position-absolute w-100" style="bottom: -2px; left: 0; line-height: 0;">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 320" style="width: 100%; height: 40px; transform: rotate(180deg);" preserveAspectRatio="none">
                <path fill="#ffffff" fill-opacity="1" d="M0,96L80,112C160,128,320,160,480,165.3C640,171,800,149,960,122.7C1120,96,1280,64,1360,48L1440,32L1440,320L1360,320C1280,320,1120,320,960,320C800,320,640,320,480,320C320,320,160,320,80,320L0,320Z"></path>
              </svg>
            </div>
          </div>
          
          <v-card-text class="pa-8 pt-6">
            <h3 class="text-h6 font-weight-bold text-grey-darken-3 mb-6 text-center">Přihlášení do systému</h3>
            <v-form @submit.prevent="handleLogin" ref="form">
              <v-text-field
                v-model="username"
                label="Uživatelské jméno"
                prepend-inner-icon="mdi-account-outline"
                type="text"
                required
                variant="outlined"
                class="mb-3"
                density="comfortable"
                bg-color="grey-lighten-4"
              ></v-text-field>

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
              ></v-text-field>

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
                Přihlásit se
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

const username = ref('user')
const password = ref('user123')
const loading = ref(false)
const error = ref('')

const accounts = {
  admin: { u: 'admin', p: 'admin123' },
  curator: { u: 'curator', p: 'curator123' },
  analyst: { u: 'analyst', p: 'analyst123' },
  user: { u: 'user', p: 'user123' }
}

const fill = (role) => {
  username.value = accounts[role].u
  password.value = accounts[role].p
}

const handleLogin = async () => {
  if (!username.value || !password.value) return
  
  loading.value = true
  error.value = ''
  
  try {
    await authStore.login(username.value, password.value)
    router.push('/')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Neplatné přihlašovací údaje.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.opacity-90 {
  opacity: 0.9;
}
.opacity-80 {
  opacity: 0.8;
}
</style>
