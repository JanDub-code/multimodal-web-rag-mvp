<template>
  <v-container fluid class="pa-6">
    <div class="d-flex align-center mb-6">
      <h1 class="text-h4 font-weight-bold text-primary">Systémová nastavení</h1>
    </div>

    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
      {{ error }}
    </v-alert>

    <v-card class="elevation-1 rounded-lg border">
      <v-card-title class="font-weight-bold px-6 py-4 bg-grey-lighten-4">
        Retenční politiky
      </v-card-title>
      <v-divider></v-divider>
      <v-card-text class="px-6 py-4">
        <v-row align="center" class="mb-2">
          <v-col cols="4"><div class="text-subtitle-1 font-weight-medium">Raw evidence (HTML/screenshot/PDF)</div></v-col>
          <v-col cols="8">
            <v-select :items="retentionOptions" v-model="settings.retentionEvidence" variant="outlined" density="compact" hide-details></v-select>
          </v-col>
        </v-row>
        <v-row align="center" class="mb-2">
          <v-col cols="4"><div class="text-subtitle-1 font-weight-medium">Audit logy</div></v-col>
          <v-col cols="8">
            <v-select :items="retentionOptions" v-model="settings.retentionAudit" variant="outlined" density="compact" hide-details></v-select>
          </v-col>
        </v-row>
        <v-row align="center">
          <v-col cols="4"><div class="text-subtitle-1 font-weight-medium">Vektorový index snapshot</div></v-col>
          <v-col cols="8">
            <v-select :items="retentionOptions" v-model="settings.retentionVector" variant="outlined" density="compact" hide-details></v-select>
          </v-col>
        </v-row>
      </v-card-text>
      <v-divider></v-divider>
      <v-card-actions class="px-6 py-4">
        <v-spacer></v-spacer>
        <v-btn color="primary" variant="flat" size="large" @click="saveSettings" :loading="saving" :disabled="loading">Uložit změny</v-btn>
      </v-card-actions>
    </v-card>

    <v-snackbar v-model="saved" color="success" timeout="2500">
      Změny uloženy.
    </v-snackbar>
  </v-container>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { settingsService } from '@/services/settingsService'

const defaultSettings = {
  retentionEvidence: '60 dní',
  retentionAudit: '60 dní',
  retentionVector: '60 dní'
}

const settings = ref({ ...defaultSettings })

const retentionOptions = ['30 dní', '60 dní', '90 dní', '1 rok']
const loading = ref(false)
const saving = ref(false)
const saved = ref(false)
const error = ref('')

const applyApiSettings = (data) => {
  const retention = data?.retention || {}
  settings.value = {
    retentionEvidence: retention.raw_evidence || defaultSettings.retentionEvidence,
    retentionAudit: retention.audit_logs || defaultSettings.retentionAudit,
    retentionVector: retention.vector_snapshot || defaultSettings.retentionVector,
  }
}

const toApiPayload = () => ({
  retention: {
    raw_evidence: settings.value.retentionEvidence,
    audit_logs: settings.value.retentionAudit,
    vector_snapshot: settings.value.retentionVector,
  },
})

const loadSettings = async () => {
  loading.value = true
  error.value = ''
  try {
    applyApiSettings(await settingsService.getSettings())
  } catch (err) {
    error.value = err.response?.data?.detail || 'Nastavení se nepodařilo načíst.'
  } finally {
    loading.value = false
  }
}

const saveSettings = async () => {
  saving.value = true
  error.value = ''
  saved.value = false
  try {
    applyApiSettings(await settingsService.saveSettings(toApiPayload()))
    saved.value = true
  } catch (err) {
    error.value = err.response?.data?.detail || 'Nastavení se nepodařilo uložit.'
  } finally {
    saving.value = false
  }
}

onMounted(loadSettings)
</script>
