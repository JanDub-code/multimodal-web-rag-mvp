<template>
  <div class="compliance-page">
    <h1 class="page-title">Compliance</h1>

    <!-- Enforcement Status -->
    <v-card class="pa-5 mb-6">
      <div class="d-flex align-center justify-space-between flex-wrap ga-3">
        <div>
          <h3 class="section-title mb-1">Režim compliance</h3>
          <p class="text-muted">
            {{ complianceStore.isEnforced
              ? 'Enforcement je zapnutý — citlivé akce vyžadují potvrzení.'
              : 'Dev mode — akce se provádějí bez potvrzení se záznamem bypass.' }}
          </p>
        </div>
        <v-chip
          :color="complianceStore.isEnforced ? 'success' : 'warning'"
          size="large"
          :prepend-icon="complianceStore.isEnforced ? 'mdi-shield-check' : 'mdi-shield-off-outline'"
          variant="tonal"
        >
          {{ complianceStore.isEnforced ? 'Enforcement ON' : 'Dev Mode' }}
        </v-chip>
      </div>
    </v-card>

    <!-- Pending Confirmations (from store) -->
    <v-card class="pa-5 mb-6" v-if="localConfirmations.length">
      <h3 class="section-title">Poslední potvrzení (tato session)</h3>
      <v-table density="compact">
        <thead>
          <tr>
            <th>Čas</th>
            <th>Uživatel</th>
            <th>Akce</th>
            <th>Operation ID</th>
            <th>Stav</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(c, i) in localConfirmations" :key="i">
            <td class="text-secondary">{{ formatTime(c.timestamp) }}</td>
            <td>{{ c.user }}</td>
            <td>{{ c.action }}</td>
            <td><code style="font-size: 0.75rem;">{{ c.operation_id }}</code></td>
            <td>
              <v-chip
                :color="c.compliance_bypassed ? 'warning' : 'success'"
                size="x-small"
                label
              >
                {{ c.compliance_bypassed ? 'BYPASS' : 'CONFIRMED' }}
              </v-chip>
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-card>

    <!-- Historical Confirmations -->
    <v-card class="pa-5">
      <h3 class="section-title">Historie potvrzení</h3>

      <div v-if="loading" class="text-center pa-6">
        <v-progress-circular indeterminate color="primary" />
      </div>

      <v-table v-else-if="history.length" density="compact">
        <thead>
          <tr>
            <th>Čas</th>
            <th>Uživatel</th>
            <th>Akce</th>
            <th>Operation ID</th>
            <th>Důvod</th>
            <th>Stav</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="entry in history" :key="entry.id">
            <td class="text-secondary">{{ formatTime(entry.timestamp) }}</td>
            <td>{{ entry.user }}</td>
            <td>{{ entry.action }}</td>
            <td><code style="font-size: 0.75rem;">{{ entry.operation_id }}</code></td>
            <td class="text-secondary">{{ entry.reason || '–' }}</td>
            <td>
              <v-chip
                :color="entry.compliance_bypassed ? 'warning' : 'success'"
                size="x-small"
                label
              >
                {{ entry.compliance_bypassed ? 'BYPASS' : 'CONFIRMED' }}
              </v-chip>
            </td>
          </tr>
        </tbody>
      </v-table>

      <div v-else class="text-center pa-6 text-muted">
        Žádná historie potvrzení.
      </div>
    </v-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useComplianceStore } from '@/stores/compliance'
import { complianceService } from '@/services/complianceService'

const complianceStore = useComplianceStore()
const loading = ref(false)
const history = ref([])

const localConfirmations = computed(() => complianceStore.confirmations)

onMounted(async () => {
  loading.value = true
  try {
    const data = await complianceService.getHistory()
    history.value = data || []
  } catch (err) {
    console.error('Failed to load compliance history:', err)
  } finally {
    loading.value = false
  }
})

function formatTime(ts) {
  return new Date(ts).toLocaleString('cs-CZ')
}
</script>

<style lang="scss" scoped>
.compliance-page {
  max-width: 1000px;

  code {
    background: $bg-body;
    padding: 2px 6px;
    border-radius: 4px;
  }
}
</style>
