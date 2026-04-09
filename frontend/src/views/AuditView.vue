<template>
  <div class="audit-page">
    <h1 class="page-title">Audit Log</h1>

    <!-- Filters -->
   <v-card class="pa-5 mb-6">
  <v-row align="center" dense>
    <v-col cols="12" sm="6" md="2">
      <v-text-field
        v-model="filters.dateFrom"
        label="Datum od"
        type="date"
        density="compact"
        hide-details
      />
    </v-col>

    <v-col cols="12" sm="6" md="2">
      <v-text-field
        v-model="filters.dateTo"
        label="Datum do"
        type="date"
        density="compact"
        hide-details
      />
    </v-col>

    <v-col cols="12" sm="6" md="2">
      <v-select
        v-model="filters.role"
        label="Oprávnění"
        :items="roleOptions"
        density="compact"
        clearable
        hide-details
      />
    </v-col>

    <v-col cols="12" sm="6" md="2">
      <v-select
        v-model="filters.eventType"
        label="Typ události"
        :items="eventTypeOptions"
        density="compact"
        clearable
        hide-details
      />
    </v-col>

    <v-col cols="12" sm="6" md="2" class="d-flex align-center">
      <v-btn
        color="primary"
        prepend-icon="mdi-filter-outline"
        @click="applyFilters"
        class="w-100"
        height="40"
      >
        Filter
      </v-btn>
    </v-col>
  </v-row>
</v-card>

    <!-- Audit Table -->
    <v-card>
      <v-table class="audit-table">
        <thead>
          <tr>
            <th>ČAS</th>
            <th>AKTÉR</th>
            <th>OPRÁVNĚNÍ</th>
            <th>TYP UDÁLOSTI</th>
            <th>DETAIL</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="entry in filteredLogs" :key="entry.id">
            <td class="audit-table__time">{{ formatTime(entry.ts) }}</td>
            <td class="audit-table__actor">{{ entry.actor }}</td>
            <td>
              <span :class="['role-chip', `role-chip--${entry.role.toLowerCase()}`]">
                {{ entry.role.toUpperCase() }}
              </span>
            </td>
            <td>
              <span :class="['event-chip', `event-chip--${entry.event_category}`]">
                {{ entry.event_type }}
              </span>
            </td>
            <td class="audit-table__detail">{{ entry.detail }}</td>
          </tr>
        </tbody>
      </v-table>

      <div v-if="filteredLogs.length === 0" class="text-center pa-8 text-muted">
        Žádné záznamy odpovídající filtru.
      </div>
    </v-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { auditService } from '@/services/auditService'

const logs = ref([])
const loading = ref(false)

const filters = ref({
  dateFrom: '2026-03-01',
  dateTo: '2026-03-11',
  role: null,
  eventType: null,
})

const roleOptions = ['Všichni', 'Admin', 'Curator', 'Analyst', 'User', 'System']
const eventTypeOptions = [
  'Vše',
  'THRESHOLD CHANGE',
  'TEST RUN',
  'LOGIN',
  'CAPTCHA ERROR',
  'INGEST',
  'QUERY',
  'COMPLIANCE CONFIRM',
]

const filteredLogs = computed(() => {
  let result = [...logs.value]

  if (filters.value.role && filters.value.role !== 'Všichni') {
    result = result.filter((l) => l.role === filters.value.role)
  }

  if (filters.value.eventType && filters.value.eventType !== 'Vše') {
    result = result.filter((l) => l.event_type === filters.value.eventType)
  }

  return result
})

onMounted(async () => {
  await loadLogs()
})

async function loadLogs() {
  loading.value = true
  try {
    const data = await auditService.getAuditLogs(filters.value)
    logs.value = data || []
  } catch (err) {
    console.error('Failed to load audit logs:', err)
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  loadLogs()
}

function formatTime(ts) {
  const d = new Date(ts)
  return d.toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
</script>

<style lang="scss" scoped>
.audit-page {
  // ...
}

.audit-table {
  th {
    font-size: $font-size-xs !important;
    font-weight: $font-weight-semibold !important;
    color: $text-muted !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 2px solid $border-color !important;
    padding: $space-base $space-base !important;
  }

  td {
    padding: $space-md $space-base !important;
    font-size: $font-size-base;
    border-bottom: 1px solid $border-light !important;
  }

  &__time {
    color: $text-secondary;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  &__actor {
    font-weight: $font-weight-medium;
    color: $text-primary;
  }

  &__detail {
    color: $text-secondary;
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
</style>
