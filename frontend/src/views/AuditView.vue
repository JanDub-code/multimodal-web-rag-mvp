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
          <v-select :items="['Všichni', 'ADMIN', 'ANALYST', 'USER', 'SYSTEM']" v-model="filters.role" variant="outlined" density="compact" hide-details></v-select>
        </div>
        
        <div style="width: 200px" class="mr-4">
          <div class="text-caption font-weight-medium mb-1">Typ události</div>
          <v-select :items="['Vše', 'THRESHOLD CHANGE', 'TEST RUN', 'LOGIN', 'CAPTCHA ERROR']" v-model="filters.type" variant="outlined" density="compact" hide-details></v-select>
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
            <td class="py-3">{{ item.time }}</td>
            <td class="py-3">{{ item.actor }}</td>
            <td class="py-3">
              <v-chip :color="getRoleColor(item.role)" size="small" class="font-weight-bold" label>{{ item.role }}</v-chip>
            </td>
            <td class="py-3">
              <v-chip :color="getTypeColor(item.type)" size="small" class="font-weight-medium" variant="tonal">{{ item.type }}</v-chip>
            </td>
            <td class="py-3">{{ item.detail }}</td>
          </tr>
        </tbody>
      </v-table>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref, computed } from 'vue'

const filters = ref({
  dateFrom: '2026-03-01',
  dateTo: '2026-03-11',
  role: 'Všichni',
  type: 'Vše'
})

const appliedFilters = ref({ ...filters.value })

const auditData = ref([
  { id: 1, date: '2026-03-11', time: '2026-03-11 10:45:12', actor: 'jan.novak', role: 'ADMIN', type: 'THRESHOLD CHANGE', detail: 'změna z 75% -> 80%' },
  { id: 2, date: '2026-03-11', time: '2026-03-11 10:45:12', actor: 'eva.curator', role: 'ANALYST', type: 'TEST RUN', detail: 'Spouštěn test ob-8f92' },
  { id: 3, date: '2026-03-05', time: '2026-03-05 09:30:00', actor: 'petr.curator', role: 'USER', type: 'LOGIN', detail: 'Login in...' },
  { id: 4, date: '2026-02-20', time: '2026-02-20 16:20:00', actor: 'petr.curator', role: 'SYSTEM', type: 'CAPTCHA ERROR', detail: 'URL blocked' }
])

const currentItems = computed(() => {
  return auditData.value.filter(item => {
    const f = appliedFilters.value
    if (f.role !== 'Všichni' && item.role !== f.role) return false
    if (f.type !== 'Vše' && item.type !== f.type) return false
    
    if (f.dateFrom && item.date < f.dateFrom) return false
    if (f.dateTo && item.date > f.dateTo) return false
    
    return true
  })
})

const getRoleColor = (role) => {
  switch (role) {
    case 'ADMIN': return 'error'
    case 'ANALYST': return 'accent'
    case 'USER': return 'info'
    case 'SYSTEM': return 'red-darken-4'
    default: return 'grey'
  }
}

const getTypeColor = (type) => {
  switch (type) {
    case 'THRESHOLD CHANGE': return 'warning'
    case 'TEST RUN': return 'accent'
    case 'LOGIN': return 'info'
    case 'CAPTCHA ERROR': return 'error'
    default: return 'grey'
  }
}

const filterData = () => {
  appliedFilters.value = { ...filters.value }
}
</script>
