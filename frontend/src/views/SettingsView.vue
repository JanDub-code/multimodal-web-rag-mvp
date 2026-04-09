<template>
  <div class="settings-page">
    <h1 class="page-title">Systémová nastavení</h1>

    <!-- AI / LLM Settings -->
    <v-card class="pa-6 mb-6">
      <h3 class="section-title">AI / LLM nastavení</h3>
      <v-row>
        <v-col cols="12" sm="6">
          <v-text-field
            v-model="settings.llm_provider"
            label="LLM provider"
            density="comfortable"
          />
        </v-col>
      </v-row>
      <v-row>
        <v-col cols="12" sm="6">
          <v-text-field
            v-model.number="settings.max_context_window"
            label="Max context window"
            type="number"
            density="comfortable"
          />
        </v-col>
      </v-row>
      <v-row>
        <v-col cols="12" sm="6">
          <v-text-field
            v-model.number="settings.rate_limit_per_user"
            label="Rate limit per user"
            type="number"
            density="comfortable"
          />
        </v-col>
      </v-row>
    </v-card>

    <!-- Retention Policies -->
    <v-card class="pa-6 mb-6">
      <h3 class="section-title">Retenční politiky</h3>
      <v-row align="center" class="mb-2">
        <v-col cols="12" sm="6">
          <span class="text-secondary">Raw evidence (HTML/screenshot/PDF)</span>
        </v-col>
        <v-col cols="12" sm="6">
          <v-select
            v-model="settings.retention.raw_evidence"
            :items="retentionOptions"
            density="compact"
          />
        </v-col>
      </v-row>
      <v-row align="center" class="mb-2">
        <v-col cols="12" sm="6">
          <span class="text-secondary">Audit logy</span>
        </v-col>
        <v-col cols="12" sm="6">
          <v-select
            v-model="settings.retention.audit_logs"
            :items="retentionOptions"
            density="compact"
          />
        </v-col>
      </v-row>
      <v-row align="center">
        <v-col cols="12" sm="6">
          <span class="text-secondary">Vektorový index snapshot</span>
        </v-col>
        <v-col cols="12" sm="6">
          <v-select
            v-model="settings.retention.vector_snapshot"
            :items="retentionOptions"
            density="compact"
          />
        </v-col>
      </v-row>
    </v-card>

    <!-- Compliance Enforcement -->
    <v-card class="pa-6 mb-6">
      <h3 class="section-title">Compliance</h3>
      <v-row align="center">
        <v-col cols="12" sm="6">
          <span class="text-secondary">Compliance enforcement</span>
          <p class="text-muted" style="font-size: 0.8rem; margin-top: 4px;">
            Pokud je zapnuto, citlivé akce vyžadují explicitní potvrzení.
          </p>
        </v-col>
        <v-col cols="12" sm="6">
          <v-switch
            v-model="complianceEnforcement"
            :label="complianceEnforcement ? 'Enforcement ON' : 'Dev Mode (OFF)'"
            color="primary"
            density="comfortable"
            hide-details
            @update:model-value="toggleCompliance"
          />
        </v-col>
      </v-row>
    </v-card>

    <!-- Save -->
    <div class="d-flex justify-end">
      <v-btn
        color="primary"
        size="large"
        :loading="saving"
        prepend-icon="mdi-content-save-outline"
        @click="saveSettings"
      >
        Uložit nastavení
      </v-btn>
    </div>

    <v-snackbar v-model="snackbar" color="success" :timeout="3000">
      Nastavení bylo úspěšně uloženo.
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { settingsService } from '@/services/settingsService'
import { useComplianceStore } from '@/stores/compliance'

const complianceStore = useComplianceStore()
const saving = ref(false)
const snackbar = ref(false)

const settings = ref({
  llm_provider: '',
  max_context_window: 0,
  rate_limit_per_user: 0,
  retention: {
    raw_evidence: '60 dní',
    audit_logs: '60 dní',
    vector_snapshot: '60 dní',
  },
})

const complianceEnforcement = ref(complianceStore.isEnforced)

const retentionOptions = ['30 dní', '60 dní', '90 dní', '180 dní', '365 dní', 'Neomezeně']

onMounted(async () => {
  try {
    const data = await settingsService.getSettings()
    settings.value = {
      ...settings.value,
      ...data,
      retention: { ...settings.value.retention, ...data.retention },
    }
    complianceEnforcement.value = data.compliance_enforcement ?? complianceStore.isEnforced
  } catch (err) {
    console.error('Failed to load settings:', err)
  }
})

function toggleCompliance(value) {
  complianceStore.setEnforcement(value)
}

async function saveSettings() {
  saving.value = true
  try {
    await settingsService.saveSettings(settings.value)
    snackbar.value = true
  } catch (err) {
    console.error('Failed to save settings:', err)
  } finally {
    saving.value = false
  }
}
</script>

<style lang="scss" scoped>
.settings-page {
  max-width: 800px;
}
</style>
