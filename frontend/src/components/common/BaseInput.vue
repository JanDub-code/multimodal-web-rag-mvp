<template>
  <v-text-field
    v-bind="$attrs"
    variant="outlined"
    density="comfortable"
    bg-color="grey-lighten-4"
    class="mb-3"
  >
    <template v-for="(_, slot) in $slots" v-slot:[slot]="scope">
      <slot :name="slot" v-bind="scope || {}" />
    </template>
  </v-text-field>
</template>

<script setup>
/** 
 * BaseInput
 * A standardized text field wrapping Vuetify's v-text-field
 * with preferred density, variant, and background colors.
 */
</script>
