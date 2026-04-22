<template>
  <v-container fluid class="pa-6">
    <div class="d-flex align-center mb-6">
      <h1 class="text-h4 font-weight-bold text-primary">Audit Log</h1>
    </div>

    <!-- Filters -->
    <v-card class="mb-6 elevation-1 rounded-lg border">
      <v-card-text class="d-flex align-center flex-wrap gap-4 py-3">
        <div style="width: 200px" class="mr-4">
          <div class="text-caption font-weight-medium mb-1">Datum od</div>
          <v-text-field type="date" v-model="filters.dateFrom" variant="outlined" density="compact" hide-details></v-text-field>
        </div>
        
        <div style="width: 200px" class="mr-4">
          <div class="text-caption font-weight-medium mb-1">Datum do</div>
          <v-text-field type="date" v-model="filters.dateTo" variant="outlined" density="compact" hide-details></v-text-field>
        </div>
        
        <div style="width: 200px" class="mr-4">
          <div class="text-caption font-weight-medium mb-1">Oprávnění</div>
          <v-select :items="uniqueRoles" v-model="filters.role" variant="outlined" density="compact" hide-details></v-select>
        </div>
        
        <div style="width: 200px" class="mr-4">
          <div class="text-caption font-weight-medium mb-1">Typ události</div>
          <v-select :items="uniqueTypes" v-model="filters.type" variant="outlined" density="compact" hide-details></v-select>
        </div>

        <div class="mt-5">
          <v-btn color="primary" prepend-icon="mdi-filter" @click="filterData">Filter</v-btn>
        </div>
      </v-card-text>
    </v-card>

    <!-- Table -->
    <v-card class="elevation-1 rounded-lg border">
      <v-table>
        <thead>
          <tr>
            <th class="text-left font-weight-bold text-subtitle-2 text-grey-darken-1 align-middle py-3">ČAS</th>
            <th class="text-left font-weight-bold text-subtitle-2 text-grey-darken-1 align-middle py-3">AKTÉR</th>
            <th class="text-left font-weight-bold text-subtitle-2 text-grey-darken-1 align-middle py-3">OPRÁVNĚNÍ</th>
            <th class="text-left font-weight-bold text-subtitle-2 text-grey-darken-1 align-middle py-3">TYP UDÁLOSTI</th>
            <th class="text-left font-weight-bold text-subtitle-2 text-grey-darken-1 align-middle py-3">DETAIL</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in currentItems" :key="item.id">
            <td class="py-3">{{ formatTime(item.ts) }}</td>
            <td class="py-3">{{ item.actor }}</td>
            <td class="py-3">
              <v-chip :color="getRoleColor(item.role)" size="small" class="font-weight-bold" label>{{ item.role }}</v-chip>
            </td>
            <td class="py-3">
              <v-chip :color="getTypeColor(item.event_type)" size="small" class="font-weight-medium" variant="tonal">{{ item.event_type }}</v-chip>
            </td>
            <td class="py-3">{{ item.detail }}</td>
          </tr>
        </tbody>
      </v-table>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { auditService } from '@/services/auditService'

const filters = ref({
  dateFrom: '',
  dateTo: '',
  role: 'Všichni',
  type: 'Vše'
})

const appliedFilters = ref({ ...filters.value })

const auditData = ref([])

const predefinedTypes = ['THRESHOLD CHANGE', 'TEST RUN', 'LOGIN', 'CAPTCHA ERROR', 'COMPLIANCE CONFIRM', 'INGEST', 'QUERY']
const uniqueTypes = computed(() => {
  const types = new Set([
    ...predefinedTypes,
    ...auditData.value.map(item => item.event_type?.toUpperCase()).filter(Boolean)
  ])
  return ['Vše', ...Array.from(types).sort()]
})

const predefinedRoles = ['ADMIN', 'ANALYST', 'USER', 'CURATOR', 'SYSTEM']
const uniqueRoles = computed(() => {
  const roles = new Set([
    ...predefinedRoles,
    ...auditData.value.map(item => item.role?.toUpperCase()).filter(Boolean)
  ])
  return ['Všichni', ...Array.from(roles).sort()]
})

const loadData = async () => {
  try {
    const logs = await auditService.getAuditLogs()
    auditData.value = logs || []
  } catch (err) {
    console.error('Failed to load audit logs:', err)
  }
}

onMounted(() => {
  loadData()
})

const currentItems = computed(() => {
  return auditData.value.filter(item => {
    const f = appliedFilters.value
    if (f.role !== 'Všichni' && item.role?.toUpperCase() !== f.role.toUpperCase() && item.role !== f.role) return false
    if (f.type !== 'Vše' && item.event_type?.toUpperCase() !== f.type.toUpperCase() && item.event_type !== f.type) return false
    
    if (f.dateFrom && item.ts < f.dateFrom) return false
    if (f.dateTo && item.ts.substring(0, 10) > f.dateTo) return false
    
    return true
  })
})

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return d.toLocaleString('cs-CZ', { hour: '2-digit', minute: '2-digit', second: '2-digit', day: '2-digit', month: '2-digit', year: 'numeric' })
}

const getRoleColor = (role) => {
  if (!role) return 'grey'
  switch (role.toUpperCase()) {
    case 'ADMIN': return 'error'
    case 'ANALYST': return 'accent'
    case 'USER': return 'info'
    case 'CURATOR': return 'warning'
    case 'SYSTEM': return 'red-darken-4'
    default: return 'grey'
  }
}

const getTypeColor = (type) => {
  if (!type) return 'grey'
  switch (type.toUpperCase()) {
    case 'THRESHOLD CHANGE': return 'warning'
    case 'TEST RUN': return 'accent'
    case 'LOGIN': return 'info'
    case 'CAPTCHA ERROR': return 'error'
    case 'COMPLIANCE CONFIRM': return 'success'
    case 'INGEST': return 'primary'
    case 'QUERY': return 'secondary'
    default: return 'grey'
  }
}

const filterData = () => {
  appliedFilters.value = { ...filters.value }
}
</script>
