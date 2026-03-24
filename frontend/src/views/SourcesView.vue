<template>
  <v-container fluid class="pa-6">
    <div class="d-flex align-center justify-space-between mb-6">
      <h1 class="text-h4 font-weight-bold text-primary">Správa zdrojů</h1>
      <v-btn color="primary" prepend-icon="mdi-plus" @click="dialog = true">Nový zdroj</v-btn>
    </div>

    <!-- Stats Cards -->
    <v-row class="mb-4">
      <v-col cols="12" md="3">
        <v-card class="elevation-1 border rounded-lg h-100 pa-4">
          <div class="text-h4 font-weight-bold">{{ sources.length }}</div>
          <div class="text-subtitle-2 text-grey-darken-1">Registrované zdroje</div>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card class="elevation-1 border rounded-lg h-100 pa-4">
          <div class="text-h4 font-weight-bold text-error">{{ incidents.length }}</div>
          <div class="text-subtitle-2 text-grey-darken-1">Otevřené incidenty</div>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card class="elevation-1 border rounded-lg h-100 pa-4">
          <div class="text-h5 font-weight-bold mt-1">{{ lastCrawlDate }}</div>
          <div class="text-subtitle-2 text-grey-darken-1 mt-1">Poslední sběr</div>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card class="elevation-1 border rounded-lg h-100 pa-4">
          <div class="text-h5 font-weight-bold mt-1">{{ nextCrawlDate }}</div>
          <div class="text-subtitle-2 text-grey-darken-1 mt-1">PříštÍ sběr</div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Search -->
    <v-text-field
      v-model="search"
      prepend-inner-icon="mdi-magnify"
      placeholder="Hledat zdroje..."
      variant="outlined"
      density="comfortable"
      class="mb-6 bg-white rounded-lg"
      hide-details
    ></v-text-field>

    <!-- Sources Table -->
    <v-card class="elevation-1 rounded-lg border mb-8">
      <v-table>
        <thead>
          <tr class="bg-grey-lighten-4">
            <th class="text-left font-weight-bold text-subtitle-2 text-grey-darken-1 py-3">URL</th>
            <th class="text-left font-weight-bold text-subtitle-2 text-grey-darken-1 py-3">STRATEGIE</th>
            <th class="text-left font-weight-bold text-subtitle-2 text-grey-darken-1 py-3">STAV</th>
            <th class="text-left font-weight-bold text-subtitle-2 text-grey-darken-1 py-3">FREKVENCE</th>
            <th class="text-left font-weight-bold text-subtitle-2 text-grey-darken-1 py-3">POSLEDNÍ SBĚR</th>
            <th class="text-left font-weight-bold text-subtitle-2 text-grey-darken-1 py-3">AKCE</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="source in filteredSources" :key="source.id" class="border-b">
            <td class="py-3 font-weight-medium">{{ source.url }}</td>
            <td class="py-3">
              <v-chip :color="source.strategy === 'HTTP' ? 'warning' : 'accent'" size="small" variant="tonal" class="font-weight-bold">
                {{ source.strategy }}
              </v-chip>
            </td>
            <td class="py-3">
              <v-chip :color="source.status === 'OK' ? 'success' : 'error'" size="small" class="font-weight-bold" :variant="source.status === 'OK' ? 'tonal' : 'flat'">
                {{ source.status }}
              </v-chip>
            </td>
            <td class="py-3 text-grey-darken-2">{{ source.frequency }}</td>
            <td class="py-3 text-grey-darken-2">{{ source.lastCrawl }}</td>
            <td class="py-3">
              <v-btn icon="mdi-pencil" variant="tonal" color="primary" size="x-small" class="mr-2" @click="editSource(source)"></v-btn>
              <v-btn icon="mdi-delete" variant="tonal" color="error" size="x-small" @click="deleteSource(source.id)"></v-btn>
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-card>

    <!-- Incidents -->
    <v-card class="elevation-1 rounded-lg border">
      <v-card-title class="font-weight-bold px-6 py-4 bg-grey-lighten-4">
        Fronta incidentů
      </v-card-title>
      <v-divider></v-divider>
      <v-list lines="one" class="pa-0">
        <v-list-item v-for="incident in incidents" :key="incident.id" class="border-b px-6 py-3">
          <div class="d-flex align-center w-100">
            <v-chip color="error" size="small" variant="flat" class="mr-4 font-weight-bold px-2">{{ incident.type }}</v-chip>
            <div class="text-body-2 font-weight-medium">{{ incident.url }}</div>
            <v-spacer></v-spacer>
            <v-btn color="primary" variant="flat" size="small" class="mr-2 px-4 rounded-lg">Detail</v-btn>
            <v-btn color="success" icon="mdi-check" variant="flat" size="small" class="rounded-lg"></v-btn>
          </div>
        </v-list-item>
      </v-list>
    </v-card>

    <!-- Add Source Modal -->
    <v-dialog v-model="dialog" max-width="500">
      <v-card class="rounded-xl">
        <v-card-title class="pa-6 pb-2 text-h6 font-weight-bold">Přidat nový zdroj</v-card-title>
        <v-card-text class="px-6 py-2">
          <div class="text-subtitle-2 font-weight-bold mb-1">Název zdroje</div>
          <v-text-field v-model="newSource.name" placeholder="Např. EUR-Lex" variant="outlined" density="comfortable" class="mb-4"></v-text-field>
          
          <div class="text-subtitle-2 font-weight-bold mb-1">URL</div>
          <v-text-field v-model="newSource.url" placeholder="https://..." variant="outlined" density="comfortable" class="mb-4"></v-text-field>
          
          <div class="text-subtitle-2 font-weight-bold mb-1">Frekvence</div>
          <v-text-field v-model="newSource.frequency" placeholder="Denně / Týdně / Měsíčně" variant="outlined" density="comfortable" class="mb-4"></v-text-field>
          
          <div class="text-subtitle-2 font-weight-bold mb-1">Strategie</div>
          <v-select v-model="newSource.strategy" :items="['HTTP', 'SCREENSHOT', 'RENDERED_DOM']" variant="outlined" density="comfortable"></v-select>
        </v-card-text>
        <v-card-actions class="pa-6 pt-2">
          <v-spacer></v-spacer>
          <v-btn variant="outlined" class="rounded-lg px-4" @click="dialog = false">Zrušit</v-btn>
          <v-btn color="primary" variant="flat" class="rounded-lg px-4" @click="addSource" :loading="saving">Přidat zdroj</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

  </v-container>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'

const search = ref('')
const dialog = ref(false)
const saving = ref(false)

const sources = ref([
  { id: 1, url: 'google.com', strategy: 'HTTP', status: 'CAPTCHA', frequency: 'Denně', lastCrawl: '2026-03-08' },
  { id: 2, url: 'uis.mendelu.cz', strategy: 'SCREENSHOT', status: 'OK', frequency: 'Týdně', lastCrawl: '2026-03-08' },
])

const filteredSources = computed(() => {
  if (!search.value) return sources.value
  const low = search.value.toLowerCase()
  return sources.value.filter(s => s.url.toLowerCase().includes(low) || s.strategy.toLowerCase().includes(low))
})

const lastCrawlDate = computed(() => {
  if (sources.value.length === 0) return '-'
  return sources.value[0].lastCrawl || '2026-03-08'
})
const nextCrawlDate = computed(() => '2026-03-25')

const deleteSource = (id) => {
  sources.value = sources.value.filter(s => s.id !== id)
}

const editSource = (source) => {
  alert('Editační okno pro úpravu zdroje: ' + source.url)
}

const incidents = ref([
  { id: 1, type: 'CAPTCHA', url: 'protected-site.com/page-42' },
  { id: 2, type: 'CAPTCHA', url: 'protected-site.com/page-55' },
])

const newSource = ref({
  name: '',
  url: '',
  frequency: 'Denně',
  strategy: 'HTTP'
})

const fetchSources = async () => {
  try {
    const res = await axios.get('/api/ingest/sources')
    if (res.data && res.data.length > 0) {
      // Map API data to UI format
      const apiSources = res.data.map(s => ({
        id: s.id,
        url: s.base_url || s.name,
        strategy: s.strategy || 'HTTP',
        status: 'OK',
        frequency: 'Denně',
        lastCrawl: 'N/A'
      }))
      // Merge for demo purposes
      sources.value = [...sources.value, ...apiSources]
    }
  } catch (err) {
    console.error('Failed to fetch sources:', err)
  }
}

onMounted(() => {
  fetchSources()
})

const addSource = async () => {
  saving.value = true
  try {
    const res = await axios.post('/api/ingest/sources', {
      name: newSource.value.name,
      base_url: newSource.value.url
    })
    sources.value.push({
      id: res.data.source_id || Date.now(),
      url: newSource.value.url || newSource.value.name,
      strategy: newSource.value.strategy,
      status: 'OK',
      frequency: newSource.value.frequency,
      lastCrawl: 'Never'
    })
    dialog.value = false
    newSource.value = { name: '', url: '', frequency: 'Denně', strategy: 'HTTP' }
  } catch (err) {
    alert('Chyba při vytvoření zdroje: ' + (err.response?.data?.detail || err.message))
  } finally {
    saving.value = false
  }
}
</script>
