<template>
  <v-container fluid class="pa-6">
    <div class="d-flex align-center justify-space-between mb-6">
      <h1 class="text-h4 font-weight-bold text-primary">Source Management</h1>
      <v-btn color="primary" prepend-icon="mdi-plus" @click="dialog = true">New source</v-btn>
    </div>

    <v-card class="elevation-1 border rounded-lg mb-6 pa-4">
      <div class="text-h4 font-weight-bold">{{ sources.length }}</div>
      <div class="text-subtitle-2 text-grey-darken-1">Registered sources</div>
    </v-card>

    <v-text-field
      v-model="search"
      prepend-inner-icon="mdi-magnify"
      placeholder="Search sources..."
      variant="outlined"
      density="comfortable"
      class="mb-6 bg-white rounded-lg"
      hide-details
    />

    <v-card class="elevation-1 rounded-lg border mb-8">
      <v-table>
        <thead>
          <tr class="bg-grey-lighten-4">
            <th class="text-left py-3">ID</th>
            <th class="text-left py-3">NAME</th>
            <th class="text-left py-3">BASE URL</th>
            <th class="text-left py-3">ACTIONS</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="source in filteredSources" :key="source.id" class="border-b">
            <td class="py-3">{{ source.id }}</td>
            <td class="py-3 font-weight-medium">{{ source.name }}</td>
            <td class="py-3 text-grey-darken-2">{{ source.base_url }}</td>
            <td class="py-3">
              <div class="d-flex align-center ga-2">
                <v-btn
                  color="primary"
                  variant="tonal"
                  size="small"
                  prepend-icon="mdi-cloud-upload-outline"
                  @click="goToIngest(source)"
                >
                  Run ingest
                </v-btn>
                <v-btn
                  color="error"
                  variant="tonal"
                  size="small"
                  icon
                  @click="confirmDelete(source)"
                  title="Smazat zdroj"
                >
                  <v-icon size="small">mdi-delete-outline</v-icon>
                </v-btn>
              </div>
            </td>
          </tr>
          <tr v-if="!loading && filteredSources.length === 0">
            <td colspan="4" class="py-6 text-center text-grey">No sources found.</td>
          </tr>
        </tbody>
      </v-table>
    </v-card>

    <v-dialog v-model="dialog" max-width="500">
      <v-card class="rounded-xl">
        <v-card-title class="pa-6 pb-2 text-h6 font-weight-bold">Add source</v-card-title>
        <v-card-text class="px-6 py-2">
          <v-text-field v-model="newSource.name" label="Name" variant="outlined" density="comfortable" class="mb-4" />
          <v-text-field v-model="newSource.url" label="Base URL" placeholder="https://..." variant="outlined" density="comfortable" class="mb-2" />
          <v-alert v-if="error" type="error" variant="tonal" density="compact">{{ error }}</v-alert>
        </v-card-text>
        <v-card-actions class="pa-6 pt-2">
          <v-spacer />
          <v-btn variant="outlined" class="rounded-lg px-4" @click="dialog = false">Cancel</v-btn>
          <v-btn color="primary" variant="flat" class="rounded-lg px-4" @click="addSource" :loading="saving">Add source</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Confirm Delete Dialog -->
    <v-dialog v-model="deleteDialog" max-width="420">
      <v-card class="rounded-xl">
        <v-card-title class="pa-6 pb-2 text-h6 font-weight-bold">Smazat zdroj</v-card-title>
        <v-card-text class="px-6 py-2">
          Opravdu chcete smazat zdroj <strong>{{ sourceToDelete?.name }}</strong>? Tato akce je nevratná.
        </v-card-text>
        <v-card-actions class="pa-6 pt-2">
          <v-spacer />
          <v-btn variant="outlined" class="rounded-lg px-4" @click="deleteDialog = false">Zrušit</v-btn>
          <v-btn color="error" variant="flat" class="rounded-lg px-4" @click="deleteSource" :loading="deleting">Smazat</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/plugins/axios'

const router = useRouter()
const search = ref('')
const dialog = ref(false)
const saving = ref(false)
const loading = ref(false)
const error = ref('')
const sources = ref([])
const deleteDialog = ref(false)
const deleting = ref(false)
const sourceToDelete = ref(null)

const newSource = ref({
  name: '',
  url: '',
})

const filteredSources = computed(() => {
  if (!search.value) return sources.value
  const low = search.value.toLowerCase()
  return sources.value.filter((s) => {
    return (
      String(s.id).includes(low) ||
      (s.name || '').toLowerCase().includes(low) ||
      (s.base_url || '').toLowerCase().includes(low)
    )
  })
})

onMounted(async () => {
  await fetchSources()
})

function parseApiError(err) {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length > 0) {
    return detail[0]?.msg || err.message
  }
  return err?.message || 'Unknown error'
}

async function fetchSources() {
  loading.value = true
  try {
    const res = await api.get('/ingest/sources')
    sources.value = Array.isArray(res.data) ? res.data : []
  } catch (err) {
    error.value = `Failed to load sources: ${parseApiError(err)}`
  } finally {
    loading.value = false
  }
}

function goToIngest(source) {
  router.push({
    path: '/ingest',
    query: {
      source_id: String(source.id),
      url: source.base_url,
    },
  })
}

function confirmDelete(source) {
  sourceToDelete.value = source
  deleteDialog.value = true
}

async function deleteSource() {
  if (!sourceToDelete.value) return
  deleting.value = true
  try {
    await api.delete(`/ingest/sources/${sourceToDelete.value.id}`)
    deleteDialog.value = false
    sourceToDelete.value = null
    await fetchSources()
  } catch (err) {
    error.value = `Failed to delete source: ${parseApiError(err)}`
  } finally {
    deleting.value = false
  }
}

async function addSource() {
  error.value = ''
  saving.value = true
  try {
    const payload = {
      name: newSource.value.name,
      base_url: newSource.value.url,
      permission_type: 'public',
    }
    const res = await api.post('/ingest/sources', payload)
    const createdId = res.data?.source_id

    dialog.value = false
    newSource.value = { name: '', url: '' }
    await fetchSources()

    if (createdId) {
      const created = sources.value.find((s) => s.id === createdId)
      if (created) {
        goToIngest(created)
      }
    }
  } catch (err) {
    error.value = `Failed to create source: ${parseApiError(err)}`
  } finally {
    saving.value = false
  }
}
</script>
