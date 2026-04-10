<template>
  <v-dialog v-model="dialog" max-width="560" persistent>
    <v-card>
      <v-card-title class="text-h6 pa-5 pb-3">
        Přidat nový zdroj
      </v-card-title>

      <v-card-text class="px-5 pb-2">
        <v-text-field
          v-model="form.name"
          label="Název zdroje"
          placeholder="Např. EUR-Lex"
          :rules="[rules.required]"
          class="mb-3"
        />
        <v-text-field
          v-model="form.url"
          label="URL"
          placeholder="https://..."
          :rules="[rules.required, rules.url]"
          class="mb-3"
        />
        <v-text-field
          v-model="form.frequency"
          label="Frekvence"
          placeholder="Denně / Týdně / Měsíčně"
          class="mb-3"
        />
        <v-select
          v-model="form.strategy"
          label="Strategie"
          :items="['HTTP', 'SCREENSHOT', 'API', 'PDF']"
        />
      </v-card-text>

      <v-card-actions class="px-5 pb-5">
        <v-btn variant="text" @click="close">Zrušit</v-btn>
        <v-spacer />
        <v-btn
          color="primary"
          :loading="loading"
          :disabled="!isValid"
          @click="submit"
        >
          Přidat zdroj
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { sourceService } from '@/services/sourceService'

const props = defineProps({
  modelValue: Boolean,
})
const emit = defineEmits(['update:modelValue', 'created'])

const dialog = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const loading = ref(false)
const form = ref({
  name: '',
  url: '',
  frequency: '',
  strategy: 'HTTP',
})

const rules = {
  required: (v) => !!v || 'Povinné pole',
  url: (v) => {
    if (!v) return true
    try { new URL(v); return true } catch { return 'Neplatná URL' }
  },
}

const isValid = computed(() => form.value.name && form.value.url)

function close() {
  dialog.value = false
  form.value = { name: '', url: '', frequency: '', strategy: 'HTTP' }
}

async function submit() {
  loading.value = true
  try {
    await sourceService.createSource({
      name: form.value.name,
      base_url: form.value.url,
    })
    emit('created')
    close()
  } catch (err) {
    console.error('Failed to create source:', err)
  } finally {
    loading.value = false
  }
}

watch(() => props.modelValue, (v) => {
  if (!v) {
    form.value = { name: '', url: '', frequency: '', strategy: 'HTTP' }
  }
})
</script>
