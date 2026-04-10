import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import pinia from './store'
import vuetify from './plugins/vuetify'
import { useAuthStore } from './store/auth'
import axios from 'axios'
import '@/assets/styles/main.scss'

const app = createApp(App)

app.use(pinia)
app.use(router)
app.use(vuetify)

const authStore = useAuthStore()
authStore.initializeAuth()

axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      authStore.logout()
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

app.mount('#app')
