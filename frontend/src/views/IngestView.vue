<template>
  <div class="ingest-page">
    <h1 class="page-title">Ingest</h1>

    <v-card class="pa-5 mb-6">
      <h3 class="section-title">Single ingest</h3>

      <v-row>
        <v-col cols="12" sm="6">
          <v-select
            v-model="selectedSource"
            label="Source"
            :items="sources"
            item-title="label"
            item-value="id"
            density="comfortable"
            :loading="sourcesLoading"
            @update:model-value="syncUrl"
          />
        </v-col>
        <v-col cols="12" sm="6">
          <v-text-field
            v-model="ingestUrl"
            label="URL to ingest"
            placeholder="https://..."
            density="comfortable"
          />
        </v-col>
      </v-row>

      <v-alert
        v-if="scopeWarning"
        type="warning"
        variant="tonal"
        density="compact"
        class="mb-4"
      >
        URL is outside the selected source scope.
      </v-alert>

      <div class="d-flex justify-end">
        <v-btn
          color="primary"
          :loading="ingestLoading"
          :disabled="!selectedSource || !ingestUrl"
          prepend-icon="mdi-cloud-upload-outline"
          @click="runSingleIngest"
        >
          Run ingest
        </v-btn>
      </div>

      <v-alert
        v-if="ingestResult"
        :type="ingestResult.status === 'completed' ? 'success' : 'error'"
        variant="tonal"
        class="mt-4"
      >
        <div><strong>Status:</strong> {{ ingestResult.status }}</div>
        <div><strong>Chunks:</strong> {{ ingestResult.chunks_created }}</div>
        <div><strong>Quality:</strong> {{ ingestResult.quality_score }}</div>
        <div><strong>Operation ID:</strong> <code>{{ ingestResult.operation_id }}</code></div>
      </v-alert>
    </v-card>

    <v-card class="pa-5">
      <h3 class="section-title">Batch ingest</h3>
      <p class="text-muted mb-4">
        Enter one URL per line for batch ingest.
      </p>

      <v-select
        v-model="batchSource"
        label="Source"
        :items="sources"
        item-title="label"
        item-value="id"
        density="comfortable"
        class="mb-3"
        style="max-width: 400px"
      />

      <v-textarea
        v-model="batchUrls"
        label="URLs (one per line)"
        placeholder="https://example.com/page-1&#10;https://example.com/page-2&#10;https://example.com/page-3"
        rows="5"
        variant="outlined"
        class="mb-3"
      />

      <div class="d-flex align-center justify-space-between flex-wrap ga-3">
        <span v-if="batchId" class="text-muted" style="font-size: 0.8rem;">
          Batch ID: <code>{{ batchId }}</code>
        </span>
        <v-btn
          color="secondary"
          :loading="batchLoading"
          :disabled="!batchUrls.trim() || !batchSource"
          prepend-icon="mdi-cloud-upload-outline"
          @click="runBatchIngest"
        >
          Run batch ingest
        </v-btn>
      </div>

      <div v-if="batchResults" class="mt-4">
        <h4 class="mb-2">Batch results</h4>
        <v-table density="compact">
          <thead>
            <tr>
              <th>Row</th>
              <th>URL</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in batchResults.results" :key="r.row_id">
              <td>{{ r.row_id }}</td>
              <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis;">{{ r.url }}</td>
              <td>
                <v-chip :color="r.status === 'ok' ? 'success' : 'error'" size="x-small" label>
                  {{ r.status }}
                </v-chip>
              </td>
            </tr>
          </tbody>
        </v-table>
      </div>
    </v-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ingestService } from '@/services/ingestService'

const route = useRoute()
const sources = ref([])
const sourcesLoading = ref(false)
const selectedSource = ref(null)
const ingestUrl = ref('')
const ingestLoading = ref(false)
const ingestResult = ref(null)
const scopeWarning = ref(false)

const batchSource = ref(null)
const batchUrls = ref('')
const batchLoading = ref(false)
const batchResults = ref(null)
const batchId = ref('')

onMounted(async () => {
  sourcesLoading.value = true
  try {
    const data = await ingestService.getSourceList()
    sources.value = (data || []).map((s) => ({
      id: s.id,
      label: `${s.id} - ${s.name} (${s.base_url})`,
      base_url: s.base_url,
    }))
    prefillFromRoute()
  } catch (err) {
    console.error('Failed to load sources:', err)
  } finally {
    sourcesLoading.value = false
  }
})

function prefillFromRoute() {
  const sourceIdRaw = route.query.source_id
  const urlRaw = route.query.url

  const sourceId = typeof sourceIdRaw === 'string' ? Number(sourceIdRaw) : null
  if (sourceId && sources.value.some((s) => s.id === sourceId)) {
    selectedSource.value = sourceId
    syncUrl()
  }

  if (typeof urlRaw === 'string' && urlRaw.trim()) {
    ingestUrl.value = urlRaw.trim()
  }
}

function syncUrl() {
  const source = sources.value.find((s) => s.id === selectedSource.value)
  if (source) {
    ingestUrl.value = source.base_url
    scopeWarning.value = false
  }
}

async function runSingleIngest() {
  ingestResult.value = null
  ingestLoading.value = true
  try {
    const operationId = `ingest-${Date.now()}`
    const data = await ingestService.runIngest(selectedSource.value, ingestUrl.value, operationId)
    ingestResult.value = data
  } catch (err) {
    console.error('Ingest failed:', err)
  } finally {
    ingestLoading.value = false
  }
}

async function runBatchIngest() {
  batchResults.value = null
  batchLoading.value = true
  batchId.value = `batch-${Date.now()}`
  try {
    const urls = batchUrls.value.split('\n').map((u) => u.trim()).filter(Boolean)
    const data = await ingestService.runBatchIngest(batchSource.value, urls, batchId.value)
    batchResults.value = data
  } catch (err) {
    console.error('Batch ingest failed:', err)
  } finally {
    batchLoading.value = false
  }
}
</script>

<style lang="scss" scoped>
.ingest-page {
  max-width: 900px;
}
</style>
