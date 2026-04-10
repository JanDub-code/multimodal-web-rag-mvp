import api from '@/plugins/axios'

export const ingestService = {
  async getSourceList() {
    const response = await api.get('/ingest/sources')
    return response.data
  },

  async runIngest(sourceId, url, operationId) {
    const response = await api.post('/ingest/run', {
      source_id: sourceId,
      url,
      operation_id: operationId,
    })
    return response.data
  },

  async runBatchIngest(sourceId, urls, batchId) {
    const results = []
    for (let i = 0; i < urls.length; i++) {
      const rowId = `${batchId}-row-${i + 1}`
      try {
        const result = await api.post('/ingest/run', {
          source_id: sourceId,
          url: urls[i],
          operation_id: rowId,
          batch_id: batchId,
          row_id: i + 1,
        })
        results.push({ url: urls[i], status: 'ok', data: result.data, row_id: i + 1 })
      } catch (err) {
        results.push({ url: urls[i], status: 'error', error: err.message, row_id: i + 1 })
      }
    }
    return { batch_id: batchId, results }
  },
}
