<template>
  <div class="sources-page">
    <div class="sources-page__header">
      <h1 class="page-title mb-0">Správa zdrojů</h1>
      <v-btn color="primary" prepend-icon="mdi-plus" @click="showAddDialog = true">
        Nový zdroj
      </v-btn>
    </div>

    <!-- Stats Cards -->
    <v-row class="mb-6">
      <v-col cols="6" md="3">
        <div class="stat-card">
          <div class="stat-card__value">{{ sourceData.stats?.totalSources || 0 }}</div>
          <div class="stat-card__label">Registrované zdroje</div>
        </div>
      </v-col>
      <v-col cols="6" md="3">
        <div class="stat-card">
          <div class="stat-card__value stat-card__value--accent">{{ sourceData.incidents?.length || 0 }}</div>
          <div class="stat-card__label">Otevřené incidenty</div>
        </div>
      </v-col>
      <v-col cols="6" md="3">
        <div class="stat-card">
          <div class="stat-card__value">{{ formatDate(sourceData.stats?.lastCrawl) }}</div>
          <div class="stat-card__label">Poslední sběr</div>
        </div>
      </v-col>
      <v-col cols="6" md="3">
        <div class="stat-card">
          <div class="stat-card__value">{{ formatDate(sourceData.stats?.nextCrawl) }}</div>
          <div class="stat-card__label">Příští sběr</div>
        </div>
      </v-col>
    </v-row>

    <!-- Search -->
    <v-text-field
      v-model="search"
      placeholder="Hledat zdroje..."
      prepend-inner-icon="mdi-magnify"
      variant="outlined"
      density="compact"
      class="mb-4"
      style="max-width: 500px"
      hide-details
    />

    <!-- Sources Table -->
    <v-card class="mb-6">
      <div class="table-responsive">
        <v-table class="sources-table">
          <thead>
          <tr>
            <th>URL</th>
            <th>STRATEGIE</th>
            <th>STAV</th>
            <th>FREKVENCE</th>
            <th>POSLEDNÍ SBĚR</th>
            <th>AKCE</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="source in filteredSources" :key="source.id">
            <td class="sources-table__url">{{ source.url }}</td>
            <td>
              <span :class="['strategy-chip', `strategy-chip--${source.strategy.toLowerCase()}`]">
                {{ source.strategy }}
              </span>
            </td>
            <td>
              <span :class="['status-chip', `status-chip--${source.status.toLowerCase()}`]">
                {{ source.status }}
              </span>
            </td>
            <td>{{ source.frequency }}</td>
            <td>{{ formatDate(source.last_crawl) }}</td>
            <td>
              <v-btn icon="mdi-pencil-outline" variant="text" size="small" color="primary" />
              <v-btn icon="mdi-delete-outline" variant="text" size="small" color="error" />
            </td>
          </tr>
        </tbody>
        </v-table>
      </div>
    </v-card>

    <!-- Incident Queue -->
    <v-card class="pa-5">
      <h3 class="section-title">Fronta incidentů</h3>
      <div v-if="sourceData.incidents?.length === 0" class="text-muted text-center pa-4">
        Žádné otevřené incidenty.
      </div>
      <div
        v-for="incident in sourceData.incidents"
        :key="incident.id"
        class="incident-row"
      >
        <div class="incident-row__left">
          <span class="status-chip status-chip--captcha">{{ incident.type }}</span>
          <span class="incident-row__url">{{ incident.url }}</span>
        </div>
        <div class="incident-row__actions d-flex align-stretch ga-2">
          <v-btn color="error" height="32" class="text-none" variant="flat">Detail</v-btn>
          <v-btn color="success" icon="mdi-check" height="32" width="32" variant="flat" />
        </div>
      </div>
    </v-card>

    <!-- Add Source Dialog -->
    <AddSourceDialog v-model="showAddDialog" @created="loadSources" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { sourceService } from '@/services/sourceService'
import AddSourceDialog from '@/components/sources/AddSourceDialog.vue'

const showAddDialog = ref(false)
const search = ref('')

const sourceData = ref({
  sources: [],
  incidents: [],
  stats: {},
})

const filteredSources = computed(() => {
  if (!search.value) return sourceData.value.sources || []
  const q = search.value.toLowerCase()
  return (sourceData.value.sources || []).filter(
    (s) => s.url.toLowerCase().includes(q) || s.name.toLowerCase().includes(q)
  )
})

onMounted(async () => {
  await loadSources()
})

async function loadSources() {
  try {
    const data = await sourceService.getSources()
    sourceData.value = data
  } catch (err) {
    console.error('Failed to load sources:', err)
  }
}

function formatDate(dateString) {
  if (!dateString || dateString === '–') return '–'
  const parts = dateString.split('-')
  if (parts.length === 3) {
    return `${parts[2]}.${parts[1]}.${parts[0]}`
  }
  const d = new Date(dateString)
  return isNaN(d.getTime()) ? dateString : d.toLocaleDateString('cs-CZ')
}
</script>

<style lang="scss" scoped>
.sources-page {
  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: $space-lg;
    flex-wrap: wrap;
    gap: $space-base;
  }
}

.table-responsive {
  width: 100%;
  overflow-x: auto;
}

.sources-table {
  th {
    font-size: $font-size-xs !important;
    font-weight: $font-weight-semibold !important;
    color: $text-muted !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 2px solid $border-color !important;
    padding: $space-base !important;
  }

  td {
    padding: $space-md $space-base !important;
    font-size: $font-size-base;
    border-bottom: 1px solid $border-light !important;
  }

  &__url {
    font-weight: $font-weight-medium;
    color: $text-primary;
  }
}

.incident-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $space-md 0;
  border-bottom: 1px solid $border-light;

  &:last-child {
    border-bottom: none;
  }

  &__left {
    display: flex;
    align-items: center;
    gap: $space-base;
  }

  &__url {
    font-size: $font-size-base;
    color: $text-secondary;
  }

  &__actions {
    display: flex;
    gap: $space-sm;
  }
}
</style>
