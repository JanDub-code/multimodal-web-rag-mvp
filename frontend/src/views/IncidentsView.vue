<template>
  <v-container fluid class="pa-6">
    <!-- Header -->
    <div class="d-flex align-center justify-space-between mb-6">
      <h1 class="text-h4 font-weight-bold text-primary">Správa incidentů</h1>
      <v-chip
        :color="openCount > 0 ? 'error' : 'success'"
        variant="tonal"
        size="large"
        prepend-icon="mdi-alert-circle-outline"
      >
        {{ openCount }} otevřených
      </v-chip>
    </div>

    <!-- Filter tabs -->
    <v-tabs v-model="statusFilter" class="mb-6" color="primary">
      <v-tab value="all">Všechny</v-tab>
      <v-tab value="open">
        Otevřené
        <Transition name="badge-fade">
          <v-badge
            v-if="openCount > 0"
            :key="openCount"
            :content="openCount"
            color="error"
            inline
            class="ml-2"
          />
        </Transition>
      </v-tab>
      <v-tab value="resolved">Vyřešené</v-tab>
    </v-tabs>

    <!-- Table -->
    <v-card class="elevation-1 rounded-lg border mb-8">
      <v-table>
        <thead>
          <tr class="bg-grey-lighten-4">
            <th class="text-left py-3">ID</th>
            <th class="text-left py-3">TYP</th>
            <th class="text-left py-3">ZDROJ</th>
            <th class="text-left py-3">URL</th>
            <th class="text-left py-3">ZÁVAŽNOST</th>
            <th class="text-left py-3">STAV</th>
            <th class="text-left py-3">VYTVOŘENO</th>
            <th class="text-left py-3">AKCE</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="8" class="py-8 text-center">
              <v-progress-circular indeterminate color="primary" />
            </td>
          </tr>
          <tr v-else-if="filteredIncidents.length === 0">
            <td colspan="8" class="py-6 text-center text-grey">Žádné incidenty nenalezeny.</td>
          </tr>
          <tr
            v-for="inc in filteredIncidents"
            :key="inc.id"
            class="border-b incident-row"
            :class="{ 'open-incident': inc.status === 'open' }"
          >
            <td class="py-3 text-grey-darken-1">#{{ inc.id }}</td>
            <td class="py-3">
              <v-chip size="small" color="warning" variant="tonal" prepend-icon="mdi-alert-outline">
                {{ inc.type }}
              </v-chip>
            </td>
            <td class="py-3 font-weight-medium">{{ inc.source_name || `zdroj #${inc.source_id}` }}</td>
            <td class="py-3 text-grey-darken-2" style="max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              <a :href="inc.url" target="_blank" class="text-primary text-decoration-none">{{ inc.url }}</a>
            </td>
            <td class="py-3">
              <v-chip size="small" :color="severityColor(inc.severity)" variant="tonal">
                {{ inc.severity }}
              </v-chip>
            </td>
            <td class="py-3">
              <v-chip
                size="small"
                :color="inc.status === 'open' ? 'error' : 'success'"
                variant="tonal"
              >
                {{ inc.status === 'open' ? 'Otevřený' : 'Vyřešený' }}
              </v-chip>
            </td>
            <td class="py-3 text-grey text-caption">{{ formatTs(inc.created_ts) }}</td>
            <td class="py-3">
              <div class="d-flex align-center ga-2">
                <v-btn
                  v-if="inc.status === 'open'"
                  color="success"
                  variant="flat"
                  size="small"
                  prepend-icon="mdi-check-circle"
                  class="font-weight-bold"
                  @click="openResolveDialog(inc)"
                >
                  Vyřešit
                </v-btn>
                <v-btn
                  v-if="canDelete"
                  color="error"
                  variant="text"
                  size="small"
                  icon
                  @click="openDeleteDialog(inc)"
                  title="Smazat incident"
                >
                  <v-icon size="small">mdi-delete-outline</v-icon>
                </v-btn>
              </div>
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-card>

    <!-- Resolve Dialog -->
    <v-dialog v-model="resolveDialog" max-width="480">
      <v-card class="rounded-xl">
        <v-card-title class="pa-6 pb-2 text-h6 font-weight-bold">Vyřešit incident</v-card-title>
        <v-card-text class="px-6 py-2">
          <p class="mb-4 text-grey-darken-2">
            Incident <strong>#{{ selectedIncident?.id }}</strong> —
            <span class="text-caption">{{ selectedIncident?.url }}</span>
          </p>
          <v-textarea
            v-model="resolveNote"
            label="Poznámka k řešení (volitelné)"
            variant="outlined"
            rows="3"
            hide-details
          />
          <v-alert v-if="resolveError" type="error" variant="tonal" density="compact" class="mt-3">
            {{ resolveError }}
          </v-alert>
        </v-card-text>
        <v-card-actions class="pa-6 pt-2 flex-column ga-2">
          <v-btn
            color="success"
            variant="flat"
            size="large"
            block
            class="font-weight-bold py-3"
            :loading="resolving"
            @click="resolveIncident"
          >
            <template #loader>
              <v-progress-circular indeterminate size="18" width="2" class="mr-2" />
              Řeším…
            </template>
            <v-icon start>mdi-check-circle</v-icon>
            Označit jako vyřešený
          </v-btn>
          <v-btn variant="outlined" block @click="resolveDialog = false">Zrušit</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Dialog -->
    <v-dialog v-model="deleteDialog" max-width="420">
      <v-card class="rounded-xl">
        <v-card-title class="pa-6 pb-2 text-h6 font-weight-bold">Smazat incident</v-card-title>
        <v-card-text class="px-6 py-2">
          Opravdu chcete smazat incident <strong>#{{ selectedIncident?.id }}</strong>? Tato akce je nevratná.
        </v-card-text>
        <v-card-actions class="pa-6 pt-2">
          <v-spacer />
          <v-btn variant="outlined" class="rounded-lg px-4" @click="deleteDialog = false">Zrušit</v-btn>
          <v-btn color="error" variant="flat" class="rounded-lg px-4" :loading="deleting" @click="deleteIncident">
            Smazat
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Toast snackbar after resolve -->
    <v-snackbar
      v-model="resolveToast"
      color="success"
      location="bottom center"
      :timeout="3500"
      rounded="pill"
      elevation="4"
    >
      <v-icon class="mr-2">mdi-check-circle</v-icon>
      {{ resolveToastMessage }}
    </v-snackbar>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/store/auth'
import api from '@/plugins/axios'

const authStore = useAuthStore()
const canDelete = computed(() => authStore.isAdmin)

const incidents = ref([])
const sources = ref([])
const loading = ref(false)
const statusFilter = ref('all')

const resolveDialog = ref(false)
const resolving = ref(false)
const resolveNote = ref('')
const resolveError = ref('')
const selectedIncident = ref(null)

const deleteDialog = ref(false)
const deleting = ref(false)

const resolveToast = ref(false)
const resolveToastMessage = ref('')

const openCount = computed(() => incidents.value.filter((i) => i.status === 'open').length)

const filteredIncidents = computed(() => {
  if (statusFilter.value === 'open') return incidents.value.filter((i) => i.status === 'open')
  if (statusFilter.value === 'resolved') return incidents.value.filter((i) => i.status === 'resolved')
  return incidents.value
})

onMounted(async () => {
  await fetchIncidents()
})

async function fetchIncidents() {
  loading.value = true
  try {
    const res = await api.get('/incidents/')
    incidents.value = Array.isArray(res.data) ? res.data : []
  } catch (err) {
    console.error('Failed to load incidents', err)
  } finally {
    loading.value = false
  }
}

function openResolveDialog(inc) {
  selectedIncident.value = inc
  resolveNote.value = ''
  resolveError.value = ''
  resolveDialog.value = true
}

async function resolveIncident() {
  if (!selectedIncident.value) return
  resolving.value = true
  resolveError.value = ''
  const incId = selectedIncident.value.id
  try {
    await api.put(`/incidents/${incId}/resolve`, {
      resolution_note: resolveNote.value,
    })
    resolveDialog.value = false
    await fetchIncidents()
    resolveToastMessage.value = `✓ Incident #${incId} byl vyřešen`
    resolveToast.value = true
  } catch (err) {
    resolveError.value = err?.response?.data?.detail || 'Chyba při řešení incidentu'
  } finally {
    resolving.value = false
  }
}

function openDeleteDialog(inc) {
  selectedIncident.value = inc
  deleteDialog.value = true
}

async function deleteIncident() {
  if (!selectedIncident.value) return
  deleting.value = true
  try {
    await api.delete(`/incidents/${selectedIncident.value.id}`)
    deleteDialog.value = false
    await fetchIncidents()
  } catch (err) {
    console.error('Failed to delete incident', err)
  } finally {
    deleting.value = false
  }
}

function formatTs(ts) {
  if (!ts) return '—'
  return new Date(ts).toLocaleString('cs-CZ', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function severityColor(sev) {
  if (sev === 'high') return 'error'
  if (sev === 'low') return 'info'
  return 'warning'
}
</script>

<style scoped>
/* Hover highlight for open incident rows */
.incident-row.open-incident:hover {
  background-color: rgba(var(--v-theme-error), 0.07) !important;
  transition: background-color 0.15s ease;
}

/* Badge count fade+scale transition */
.badge-fade-enter-active,
.badge-fade-leave-active {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.badge-fade-enter-from,
.badge-fade-leave-to {
  opacity: 0;
  transform: scale(0.5);
}
</style>
