import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const sidebarOpen = ref(true)
  const sidebarMini = ref(false)

  function toggleSidebar() {
    sidebarOpen.value = !sidebarOpen.value
  }

  function setSidebarOpen(value) {
    sidebarOpen.value = value
  }

  return {
    sidebarOpen,
    sidebarMini,
    toggleSidebar,
    setSidebarOpen,
  }
})
