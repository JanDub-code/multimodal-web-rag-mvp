<template>
  <v-btn
    v-bind="$attrs"
    :color="color || 'primary'"
    class="font-weight-bold rounded-lg"
    :class="{ 'text-white': isPrimaryOrFilled }"
  >
    <slot></slot>
  </v-btn>
</template>

<script setup>
import { computed, useAttrs } from 'vue'

const props = defineProps({
  color: {
    type: String,
    default: 'primary'
  }
})

const attrs = useAttrs()

// If variant is not text/outlined/plain and color is primary, force white text
const isPrimaryOrFilled = computed(() => {
  const variant = attrs.variant || 'elevated'
  return (props.color === 'primary' || props.color === '#1e293b') && 
         !['text', 'outlined', 'plain'].includes(variant)
})
</script>
