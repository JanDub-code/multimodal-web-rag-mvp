<template>
  <div class="chat-layout">
    <!-- Sessions Sidebar -->
    <v-card 
      class="chat-sidebar" 
      :class="{ 'sidebar-mobile-hidden': !showMobileHistory }"
      elevation="0"
    >
      <div class="pa-3 d-none d-md-block">
        <v-btn color="primary" block prepend-icon="mdi-plus" @click="startNewSession">
          Nová konverzace
        </v-btn>
      </div>
      <v-divider />
      <v-list density="compact" nav class="pa-2">
        <v-list-item
          v-for="session in sessions"
          :key="session.id"
          :title="session.title"
          :active="currentSessionId === session.id"
          @click="loadSession(session.id)"
          rounded="lg"
          class="mb-1"
        >
          <template #prepend>
            <v-icon size="small">mdi-message-outline</v-icon>
          </template>
        </v-list-item>
        <div v-if="!sessions.length && !loadingSessions" class="text-caption text-center pa-4 text-muted">
          Žádná historie
        </div>
      </v-list>
    </v-card>

    <!-- Main Chat Area -->
    <div class="chat-main">
      <!-- Header -->
      <div class="chat-header">
        <!-- Desktop Header -->
        <div class="d-none d-md-flex justify-space-between align-center w-100">
          <h2 class="text-h6">{{ currentSessionTitle }}</h2>
          <div class="d-flex align-center ga-3">
            <v-select
              v-model="mode"
              :items="modeOptions"
              item-title="label"
              item-value="value"
              density="compact"
              variant="outlined"
              hide-details
              style="min-width: 180px"
            />
            <v-select
              v-model="topK"
              :items="[3, 5, 10, 15]"
              prefix="Top "
              density="compact"
              variant="outlined"
              hide-details
              style="min-width: 120px"
            />
          </div>
        </div>

        <!-- Mobile Header -->
        <div class="d-flex d-md-none flex-column w-100 ga-3">
          <div class="d-flex align-center justify-space-between">
            <v-btn icon="mdi-menu" variant="text" @click="showMobileHistory = !showMobileHistory" />
            <v-btn color="primary" prepend-icon="mdi-plus" variant="flat" @click="startNewSession" class="text-none">Nová konverzace</v-btn>
          </div>
          <div class="d-flex align-center ga-2">
            <v-select
              v-model="mode"
              :items="modeOptions"
              item-title="label"
              item-value="value"
              density="compact"
              variant="outlined"
              hide-details
              class="flex-grow-1"
            />
            <v-select
              v-model="topK"
              :items="[3, 5, 10, 15]"
              prefix="Top "
              density="compact"
              variant="outlined"
              hide-details
              style="min-width: 100px"
            />
          </div>
        </div>
      </div>

      <!-- Messages Window -->
      <div class="chat-messages" ref="messagesContainer">
        <!-- Empty State -->
        <div v-if="!messages.length" class="empty-state">
          <v-icon size="64" color="grey-lighten-2" class="mb-4">mdi-forum-outline</v-icon>
          <h3>Jak vám mohu pomoci?</h3>
          <p class="text-muted text-center mt-2" style="max-width: 400px">
            Jsem připraven odpovídat na dotazy na základě dokumentů ve vybraných zdrojích (RAG mód) nebo fungovat jako běžný jazykový model.
          </p>
        </div>

        <!-- Message List -->
        <div 
          v-for="msg in messages" 
          :key="msg.id" 
          :class="['message-wrapper', msg.role === 'user' ? 'message-wrapper--user' : 'message-wrapper--ai']"
        >
          <div class="message-bubble">
            <div class="message-bubble__content">{{ msg.content }}</div>
            
            <!-- Citations (AI only) -->
            <div v-if="msg.citations?.length" class="message-citations">
              <v-chip 
                v-for="cit in msg.citations" 
                :key="cit.index" 
                color="info" 
                size="small" 
                variant="tonal"
                class="mr-1 mt-2"
                :href="cit.url"
                target="_blank"
              >
                [{{ cit.index }}] Zdroj
              </v-chip>
            </div>
            
            <div class="message-bubble__meta text-caption text-disabled mt-1">
              {{ formatTime(msg.timestamp) }}
              <span v-if="msg.operation_id" class="ml-2">| op: {{ msg.operation_id }}</span>
            </div>
          </div>
        </div>

        <!-- Loading Indicator -->
        <div v-if="loading" class="message-wrapper message-wrapper--ai my-4">
           <v-progress-circular indeterminate color="primary" size="24" class="ml-4" />
        </div>
      </div>

      <!-- Input Area -->
      <div class="chat-input-area">
        <v-textarea
          v-model="queryText"
          placeholder="Zadejte svůj dotaz zde..."
          variant="outlined"
          rows="1"
          auto-grow
          hide-details
          class="chat-input"
          @keydown.enter.prevent="runQuery"
        >
          <template #append-inner>
            <v-btn 
              icon="mdi-send" 
              variant="text" 
              color="primary" 
              :disabled="!queryText.trim() || loading"
              @click="runQuery"
            />
          </template>
        </v-textarea>
      </div>
    </div>

    <!-- Compliance Dialog -->
    <ComplianceDialog
      :model-value="compliance.showDialog.value"
      :action-type="compliance.pendingActionType.value"
      :operation-id="compliance.pendingOperationId.value"
      @confirm="(reason) => compliance.confirmCompliance(reason)"
      @cancel="compliance.cancelCompliance()"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, computed } from 'vue'
import { queryService } from '@/services/queryService'
import { useCompliance } from '@/composables/useCompliance'
import ComplianceDialog from '@/components/compliance/ComplianceDialog.vue'

const compliance = useCompliance()

// State
const sessions = ref([])
const messages = ref([])
const currentSessionId = ref(null)
const loadingSessions = ref(true)
const loading = ref(false)
const messagesContainer = ref(null)
const showMobileHistory = ref(false)

// Inputs
const queryText = ref('')
const mode = ref('rag')
const topK = ref(5)

const modeOptions = [
  { label: 'RAG Mód', value: 'rag' },
  { label: 'No-RAG Mód', value: 'no-rag' },
]

const currentSessionTitle = computed(() => {
  if (currentSessionId.value) {
    const s = sessions.value.find(s => s.id === currentSessionId.value)
    return s ? s.title : 'Konverzace'
  }
  return 'Nová konverzace'
})

onMounted(async () => {
  await loadSessions()
})

async function loadSessions() {
  loadingSessions.value = true
  try {
    const data = await queryService.getSessions()
    sessions.value = data || []
  } catch (err) {
    console.error('Failed to load sessions', err)
  } finally {
    loadingSessions.value = false
  }
}

function startNewSession() {
  currentSessionId.value = null
  messages.value = []
  queryText.value = ''
}

async function loadSession(id) {
  currentSessionId.value = id
  loading.value = true
  try {
    const data = await queryService.getSession(id)
    messages.value = data.messages || []
    scrollToBottom()
  } catch (err) {
    console.error('Failed to load session details', err)
  } finally {
    loading.value = false
  }
}

async function runQuery() {
  const text = queryText.value.trim()
  if (!text) return

  // Optimistic User Message UI update
  const optimisticId = `temp-${Date.now()}`
  messages.value.push({
    id: optimisticId,
    role: 'user',
    content: text,
    timestamp: new Date().toISOString()
  })
  
  queryText.value = ''
  scrollToBottom()
  loading.value = true

  try {
    let targetSessionId = currentSessionId.value
    await compliance.guardAction('query.execute', async (actionContext) => {
      const operationId = actionContext.operationId

      // Session creation is best-effort. Query execution must not depend on it.
      if (!targetSessionId) {
        try {
          const newTitle = text.length > 25 ? text.substring(0, 25) + '...' : text
          const newSess = await queryService.createSession(newTitle)
          targetSessionId = newSess.id
          currentSessionId.value = targetSessionId
          sessions.value.unshift(newSess)
        } catch (sessionErr) {
          console.warn('Failed to create session before query, proceeding without session:', sessionErr)
        }
      }

      // Execute query
      const data = await queryService.query(
        text,
        mode.value,
        topK.value,
        operationId,
        targetSessionId,
        actionContext
      )

      const assistantMessage = data?.message || {
        id: `msg-a-${Date.now()}`,
        role: 'ai',
        content: data?.answer || 'Žádná odpověď nebyla vygenerována.',
        citations: Array.isArray(data?.citations) ? data.citations : [],
        timestamp: new Date().toISOString(),
        operation_id: data?.operation_id || operationId,
      }

      messages.value.push(assistantMessage)
    })
  } catch (err) {
    const wasCancelled = String(err?.message || '').toLowerCase().includes('cancelled')
    if (wasCancelled) {
      messages.value = messages.value.filter((m) => m.id !== optimisticId)
      return
    }

    console.error('Query failed:', err)
    messages.value.push({
      id: `msg-e-${Date.now()}`,
      role: 'ai',
      content: `Chyba serveru: ${formatApiError(err)}`,
      timestamp: new Date().toISOString(),
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

function formatTime(ts) {
  return new Date(ts).toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit' })
}

function formatApiError(error) {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0]
    if (first?.msg) return first.msg
  }
  return error?.message || 'Neočekávaná chyba'
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.chat-layout {
  display: flex;
  height: calc(100vh - #{$toolbar-height} - 48px);
  gap: $space-base;
  
  @media (max-width: 768px) {
    flex-direction: column;
    height: auto;
    min-height: calc(100vh - #{$toolbar-height} - 48px);
  }
}

.chat-sidebar {
  width: 250px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border: 1px solid $border-color !important;
  background: $bg-sidebar;
  
  @media (max-width: 768px) {
    width: 100%;
    max-height: 250px;
    z-index: 10;
    
    &.sidebar-mobile-hidden {
      display: none !important;
    }
  }
}

.chat-main {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  background: $bg-card;
  border-radius: $border-radius-lg;
  border: 1px solid $border-color;
  box-shadow: $shadow-card;
  overflow: hidden;
}

.chat-header {
  padding: $space-base $space-lg;
  border-bottom: 1px solid $border-light;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-messages {
  flex-grow: 1;
  padding: $space-lg;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: $space-md;

  .empty-state {
    margin: auto;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
  }
}

.message-wrapper {
  display: flex;
  width: 100%;
  
  &--user {
    justify-content: flex-end;
    
    .message-bubble {
      background: $primary;
      color: white;
      border-bottom-right-radius: 4px;

      &__meta {
        color: rgba(255, 255, 255, 0.7) !important;
      }
    }
  }

  &--ai {
    justify-content: flex-start;
    
    .message-bubble {
      background: $bg-body;
      border: 1px solid $border-color;
      border-bottom-left-radius: 4px;
    }
  }
}

.message-bubble {
  max-width: 75%;
  padding: $space-md;
  border-radius: $border-radius-lg;
  font-size: $font-size-base;
  line-height: 1.5;
  white-space: pre-wrap;

  &__content {
    word-break: break-word;
  }
}

.chat-input-area {
  padding: $space-md $space-lg;
  border-top: 1px solid $border-light;
  background: $bg-body;

  .chat-input {
    background: white;
    border-radius: $border-radius-lg;
  }
}
</style>
