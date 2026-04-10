<template>
  <v-dialog v-model="props.modelValue" max-width="560" persistent>
    <v-card class="compliance-dialog">
      <v-card-title class="compliance-dialog__title">
        <v-icon color="warning" class="mr-2">mdi-shield-alert-outline</v-icon>
        Compliance potvrzení
      </v-card-title>

      <v-card-text class="compliance-dialog__body">
        <v-alert type="info" variant="tonal" density="compact" class="mb-4">
          <strong>Akce:</strong> {{ actionLabel }}
        </v-alert>

        <div class="compliance-dialog__text mb-4">
          Potvrzuji, že jsem oprávněn/a provést tuto akci v souladu s platnými
          interními pravidly a předpisy o zpracování dat. Beru na vědomí, že tato
          akce bude zaznamenána v auditním logu.
        </div>

        <v-text-field
          v-model="reason"
          label="Důvod / poznámka (volitelné)"
          placeholder="Např. pravidelný sběr dat, testování..."
          variant="outlined"
          density="comfortable"
          hide-details
          class="mb-4"
        />

        <div class="compliance-dialog__meta">
          <div><strong>Operátor:</strong> {{ username }}</div>
          <div><strong>Čas:</strong> {{ currentTime }}</div>
          <div><strong>Operation ID:</strong> <code>{{ operationId }}</code></div>
        </div>

        <v-checkbox
          v-model="confirmed"
          label="Souhlasím s výše uvedeným potvrzením"
          color="primary"
          density="comfortable"
          hide-details
          class="mt-4"
        />
      </v-card-text>

      <v-card-actions class="compliance-dialog__actions">
        <v-btn variant="text" @click="$emit('cancel')">Zrušit</v-btn>
        <v-spacer />
        <v-btn
          color="primary"
          :disabled="!confirmed"
          @click="$emit('confirm', reason)"
        >
          <v-icon left class="mr-1">mdi-check</v-icon>
          Potvrdit a pokračovat
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

const props = defineProps({
  modelValue: Boolean,
  actionType: { type: String, default: '' },
  operationId: { type: String, default: '' },
})

defineEmits(['cancel', 'confirm'])

const authStore = useAuthStore()
const reason = ref('')
const confirmed = ref(false)

const username = computed(() => authStore.username || 'neznámý')
const currentTime = computed(() => new Date().toLocaleString('cs-CZ'))

const actionLabels = {
  'ingest.run': 'Spuštění ingestu dat',
  'query.execute': 'Spuštění dotazu',
  'source.create': 'Vytvoření nového zdroje',
  'source.delete': 'Smazání zdroje',
  'settings.update': 'Změna systémového nastavení',
}

const actionLabel = computed(() => actionLabels[props.actionType] || props.actionType)
</script>

<style lang="scss" scoped>
.compliance-dialog {
  &__title {
    display: flex;
    align-items: center;
    font-size: $font-size-lg;
    font-weight: $font-weight-semibold;
    padding: $space-lg $space-lg $space-base;
  }

  &__body {
    padding: 0 $space-lg $space-base;
  }

  &__text {
    font-size: $font-size-base;
    line-height: 1.6;
    color: $text-secondary;
    background: $bg-body;
    padding: $space-base;
    border-radius: $border-radius;
    border-left: 3px solid $primary;
  }

  &__meta {
    font-size: $font-size-sm;
    color: $text-secondary;
    display: flex;
    flex-direction: column;
    gap: $space-xs;

    code {
      background: $bg-body;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: $font-size-xs;
    }
  }

  &__actions {
    padding: $space-base $space-lg $space-lg;
  }
}
</style>
