<template>
  <v-container fluid class="pa-6" style="height: calc(100vh - 48px);">
    <v-row class="h-100 ma-0">
      
      <!-- Chat History Sidebar (Left) -->
      <v-col cols="12" md="3" lg="2" class="d-flex flex-column border-r pr-6 h-100" style="background-color: transparent;">
        <v-btn color="primary" @click="createNewChat">Nový chat</v-btn>
        
        <div class="text-caption text-grey-darken-1 font-weight-bold my-3 ls-1">Historie</div>
        
        <v-list density="compact" class="bg-transparent pa-0">
          <v-list-item
            v-for="(topic, i) in history"
            :key="i"
            class="mb-2 rounded-lg border cursor-pointer"
            :class="activeTopic === i ? 'bg-primary text-white' : 'bg-white'"
            elevation="0"
            @click="switchChat(i)"
          >
            <v-list-item-title class="text-body-2 font-weight-medium" :class="activeTopic === i ? 'text-white' : 'text-grey-darken-3'">{{ topic.title }}</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-col>

      <!-- Main Chat Area (Right) -->
      <v-col cols="12" md="9" lg="10" class="d-flex flex-column h-100 pl-md-8">
        
        <!-- Header: Title + Export -->
        <div class="d-flex align-center justify-space-between mb-4">
          <h1 class="text-h4 font-weight-bold text-grey-darken-4">Chat</h1>
          <v-btn color="primary" @click="() => console.log('todo')">Export</v-btn>
        </div>

        <!-- RAG / noRAG Toggle -->
        <div class="mb-6">
          <v-btn-toggle v-model="mode" mandatory rounded="xl" density="compact" class="elevation-0 border">
            <v-btn value="rag" :color="mode === 'rag' ? 'primary' : 'transparent'" :class="mode === 'rag' ? 'text-white' : 'text-grey-darken-1'" class="font-weight-bold px-6 text-caption">RAG</v-btn>
            <v-btn value="norag" :color="mode === 'norag' ? 'primary' : 'transparent'" :class="mode === 'norag' ? 'text-white' : 'text-grey-darken-1'" class="font-weight-bold px-6 text-caption">noRAG</v-btn>
          </v-btn-toggle>
        </div>

        <!-- Input Box Area -->
        <v-card class="elevation-0 border rounded-xl bg-grey-lighten-4 pa-4 mb-6 position-relative">
          <v-textarea
            v-model="inputRaw"
            placeholder="Zadejte dotaz..."
            variant="plain"
            hide-details
            auto-grow
            rows="3"
            class="text-body-1"
            bg-color="transparent"
            @keydown.enter.prevent="handleEnter"
          ></v-textarea>
          
          <div class="d-flex justify-space-between align-end mt-2">
            <BaseButton icon="mdi-cog-outline" variant="text" color="grey-darken-1" size="small"></BaseButton>
            
            <BaseButton
              color="#1e293b" 
              icon="mdi-send"
              variant="flat"
              class="rounded-circle"
              size="40"
              :disabled="!inputRaw.trim() || loading"
              @click="sendMessage"
            >
              <v-icon size="small">mdi-play</v-icon>
            </BaseButton>
          </div>
        </v-card>

        <!-- Dynamic Answer Area -->
        <div class="flex-grow-1" style="overflow-y: auto;">
          <v-card v-if="loading" class="elevation-0 border rounded-xl bg-grey-lighten-4 pa-6 mb-4 d-flex align-center">
             <v-progress-circular indeterminate color="primary" size="24" class="mr-4"></v-progress-circular>
             <span class="text-grey-darken-1 font-weight-medium">Zpracovávám odpověď...</span>
          </v-card>

          <v-card v-else-if="lastAnswer" class="elevation-0 border rounded-xl bg-grey-lighten-4 pa-6 mb-4">
            <!-- Odpověď Tělo -->
            <div class="text-caption font-weight-bold text-grey-darken-1 mb-4 ls-1">ODPOVĚĎ</div>
            <div class="text-body-1 text-grey-darken-3" style="line-height: 1.7; white-space: pre-wrap;">
              {{ lastAnswer.content }}
            </div>
            
            <!-- Divider -->
            <v-divider class="my-6"></v-divider>
            
            <!-- Citace / Důkazy -->
            <div class="text-caption font-weight-bold text-grey-darken-1 mb-4 ls-1">CITACE / DŮKAZY</div>
            
            <div v-if="!lastAnswer.citations || lastAnswer.citations.length === 0" class="text-body-2 text-grey">
              Nebyly nalezeny žádné citace.
            </div>

            <v-list v-else bg-color="transparent" density="compact" class="pa-0">
              <v-list-item v-for="(cit, idx) in lastAnswer.citations" :key="idx" class="px-0 py-2 border-b" :class="{'border-0': idx === lastAnswer.citations.length - 1}">
                <template v-slot:prepend>
                  <div class="text-caption font-weight-bold text-grey-darken-1 mr-4">[{{ cit.index || (idx + 1) }}]</div>
                </template>
                <v-list-item-title class="text-body-2 font-weight-bold text-grey-darken-3">{{ cit.title || cit.url || 'Zdroj' }}</v-list-item-title>
                <v-list-item-subtitle class="text-caption text-grey-darken-1 mt-1">{{ cit.date || '2026-03-24' }}</v-list-item-subtitle>
                <template v-slot:append>
                  <v-btn icon="mdi-link-variant" variant="text" size="small" color="grey-lighten-1" :href="cit.url || '#'" target="_blank"></v-btn>
                </template>
              </v-list-item>
            </v-list>
          </v-card>

        </div>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'
import { useAuthStore } from '@/store/auth'

const mode = ref('rag')
const inputRaw = ref('')
const loading = ref(false)

const authStore = useAuthStore()

const history = ref([
  { id: 1, title: 'TOPIC 1', messages: [{ role: 'assistant', content: 'Výsledek pro TOPIC 1' }] },
  { id: 2, title: 'TOPIC 2', messages: [{ role: 'user', content: 'Dotaz 2' }, { role: 'assistant', content: 'Odpověď pro TOPIC 2' }] }
])
const activeTopic = ref(0)
const messages = computed(() => {
  return history.value[activeTopic.value]?.messages || []
})

const createNewChat = () => {
  const newId = history.value.length + 1
  history.value.unshift({ id: newId, title: `TOPIC ${newId}`, messages: [] })
  activeTopic.value = 0
}

const switchChat = (index) => {
  activeTopic.value = index
}

const handleEnter = (e) => {
  if (!e.shiftKey) {
    sendMessage()
  } else {
    inputRaw.value += '\n'
  }
}

const lastAnswer = computed(() => {
  if (messages.value.length === 0) return null;
  const assistantMessages = messages.value.filter(m => m.role === 'assistant');
  if (assistantMessages.length === 0) return null;
  return assistantMessages[assistantMessages.length - 1];
})

const sendMessage = async () => {
  const text = inputRaw.value.trim()
  if (!text || loading.value) return
  
  history.value[activeTopic.value].messages.push({ role: 'user', content: text })
  inputRaw.value = ''
  loading.value = true
  
  try {
    const response = await axios.post('/api/query/', {
      query: text,
      mode: mode.value.toLowerCase(),
      top_k: 5
    })
    
    // Convert citations array if provided
    let cits = response.data.citations || [];
    
    history.value[activeTopic.value].messages.push({
      role: 'assistant',
      content: response.data.answer || 'Žádná odpověd nebyla vygenerována.',
      citations: cits
    })
  } catch (error) {
    history.value[activeTopic.value].messages.push({
      role: 'assistant',
      content: 'Chyba serveru: ' + (error.response?.data?.detail || error.message)
    })
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.ls-1 {
  letter-spacing: 0.05em;
}
.v-btn-toggle .v-btn {
  border: none !important;
}
</style>
