<template>
  <v-container fluid class="pa-6">
    <div class="d-flex align-center mb-6">
      <h1 class="text-h4 font-weight-bold text-primary">Systémová nastavení</h1>
    </div>

    <!-- AI / LLM nastavení -->
    <v-card class="mb-6 elevation-1 rounded-lg border">
      <v-card-title class="font-weight-bold px-6 py-4 bg-grey-lighten-4">
        AI / LLM nastavení
      </v-card-title>
      <v-divider></v-divider>
      <v-card-text class="px-6 py-4">
        <v-row align="center" class="mb-2">
          <v-col cols="4"><div class="text-subtitle-1 font-weight-medium">LLM provider</div></v-col>
          <v-col cols="8"><v-text-field v-model="settings.llmProvider" variant="outlined" density="compact" hide-details></v-text-field></v-col>
        </v-row>
        <v-row align="center" class="mb-2">
          <v-col cols="4"><div class="text-subtitle-1 font-weight-medium">Max context window</div></v-col>
          <v-col cols="8"><v-text-field v-model="settings.maxContext" type="number" variant="outlined" density="compact" hide-details></v-text-field></v-col>
        </v-row>
        <v-row align="center">
          <v-col cols="4"><div class="text-subtitle-1 font-weight-medium">Rate limit per user</div></v-col>
          <v-col cols="8"><v-text-field v-model="settings.rateLimit" type="number" variant="outlined" density="compact" hide-details></v-text-field></v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Retenční politiky -->
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
        <v-btn color="primary" variant="flat" size="large" @click="saveSettings" :loading="saving">Uložit změny</v-btn>
      </v-card-actions>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'

const settings = ref({
  llmProvider: 'GPT',
  maxContext: 4096,
  rateLimit: 30,
  retentionEvidence: '60 dní',
  retentionAudit: '60 dní',
  retentionVector: '60 dní'
})

const retentionOptions = ['30 dní', '60 dní', '90 dní', '1 rok']
const saving = ref(false)

const saveSettings = () => {
  saving.value = true
  setTimeout(() => { saving.value = false }, 500)
}
</script>
