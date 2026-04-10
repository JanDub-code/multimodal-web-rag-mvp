<template>
  <v-container fluid class="pa-6">
    <div class="d-flex align-center justify-space-between mb-6">
      <h1 class="text-h4 font-weight-bold text-primary">Experimenty</h1>
      <v-btn color="primary" prepend-icon="mdi-play" class="text-white font-weight-bold" @click="dialog = true">Nový experiment</v-btn>
    </div>

    <v-card class="elevation-1 rounded-lg border">
      <v-table>
        <thead>
          <tr>
            <th>ČAS</th>
            <th>AKTÉR</th>
            <th>NAME</th>
            <th>STAV</th>
            <th>AKCE</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in experiments" :key="item.id">
            <td class="py-3">{{ item.time }}</td>
            <td class="py-3">{{ item.actor }}</td>
            <td class="py-3 font-weight-medium">{{ item.name }}</td>
            <td class="py-3">
              <v-chip :color="item.status === 'RUNNING' ? 'info' : 'success'" size="small" class="font-weight-bold" variant="flat">
                {{ item.status }}
              </v-chip>
            </td>
            <td class="py-3">
              <BaseButton size="small" variant="tonal" color="primary" @click="openDetail(item)">Detail</BaseButton>
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-card>

    <!-- New Experiment Dialog -->
    <v-dialog v-model="dialog" max-width="500">
      <v-card class="rounded-xl">
        <v-card-title class="pa-6 pb-2 text-h6 font-weight-bold">Spustit nový experiment</v-card-title>
        <v-card-text class="px-6 py-2">
          <div class="text-subtitle-2 font-weight-bold mb-1">Název experimentu</div>
          <v-text-field v-model="newExp.name" placeholder="Např. Qwen 4B test" variant="outlined" density="comfortable" class="mb-4"></v-text-field>
          
          <div class="text-subtitle-2 font-weight-bold mb-1">Typ evaluace</div>
          <v-select v-model="newExp.type" :items="['RAG vs No-RAG', 'Chunking Size', 'Embedding Model']" variant="outlined" density="comfortable"></v-select>
        </v-card-text>
        <v-card-actions class="pa-6 pt-2">
          <v-spacer></v-spacer>
          <v-btn variant="outlined" class="rounded-lg px-4" @click="dialog = false">Zrušit</v-btn>
          <BaseButton color="primary" variant="flat" class="rounded-lg px-4" @click="startExperiment" :loading="saving">Spustit</BaseButton>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Detail Experimentu Dialog -->
    <v-dialog v-model="detailDialog" max-width="800">
      <v-card class="rounded-xl">
        <v-card-title class="pa-6 pb-2 text-h5 font-weight-bold d-flex align-center justify-space-between">
          Detail experimentu: {{ selectedExp?.name }}
          <v-btn icon="mdi-close" variant="text" @click="detailDialog = false"></v-btn>
        </v-card-title>
        <v-card-text class="px-6 py-4">
          <v-row>
             <v-col cols="12" md="4">
               <v-card class="bg-grey-lighten-4 elevation-0 pa-4 border rounded-lg text-center h-100">
                 <div class="text-overline font-weight-bold text-grey-darken-1">Přesnost (Accuracy)</div>
                 <div class="text-h4 font-weight-bold text-success mt-2">92 %</div>
               </v-card>
             </v-col>
             <v-col cols="12" md="4">
               <v-card class="bg-grey-lighten-4 elevation-0 pa-4 border rounded-lg text-center h-100">
                 <div class="text-overline font-weight-bold text-grey-darken-1">Odezva (Latency)</div>
                 <div class="text-h4 font-weight-bold text-info mt-2">1.4 s</div>
               </v-card>
             </v-col>
             <v-col cols="12" md="4">
               <v-card class="bg-grey-lighten-4 elevation-0 pa-4 border rounded-lg text-center h-100">
                 <div class="text-overline font-weight-bold text-grey-darken-1">Míra halucinací</div>
                 <div class="text-h4 font-weight-bold text-warning mt-2">3.2 %</div>
               </v-card>
             </v-col>
          </v-row>
          <v-divider class="my-6"></v-divider>
          <h3 class="text-h6 font-weight-bold mb-4">Metriky kvality odpovědí:</h3>
          <p class="text-body-1 text-grey-darken-3 mb-2"><strong>Odstranění halucinací: </strong> Splněno pomocí striktního system promptu a cross-encoder filtrace.</p>
          <p class="text-body-1 text-grey-darken-3 mb-2"><strong>Relevance kontextu (Recall): </strong> 88.5% (Zlepšení o +15% oproti baseline pomocí BM25 + Dense vector search).</p>
          <p class="text-body-1 text-grey-darken-3 mb-2"><strong>Ověření formátu: </strong> Citace aplikovány ve 100% testovaných use-cases.</p>
        </v-card-text>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import { useAuthStore } from '@/store/auth'

const auth = useAuthStore()
const dialog = ref(false)
const detailDialog = ref(false)
const saving = ref(false)
const selectedExp = ref(null)

const experiments = ref([
  { id: 1, time: '10:45:12', actor: 'jan', name: 'Embedding A/B: E5-large vs BGE-M3', status: 'RUNNING' },
  { id: 2, time: '10:45:12', actor: 'eva', name: 'Chunking: 512 vs 1024 tokenů', status: 'DONE' },
  { id: 3, time: '10:45:12', actor: 'petr', name: 'RAG vs No-RAG baseline', status: 'DONE' },
  { id: 4, time: '10:45:12', actor: 'petr', name: 'Hybrid retrieval: BM25 + Vector', status: 'DONE' },
])

const openDetail = (exp) => {
  selectedExp.value = exp
  detailDialog.value = true
}

const newExp = ref({ name: '', type: 'RAG vs No-RAG' })

const startExperiment = () => {
  saving.value = true
  setTimeout(() => {
    experiments.value.unshift({
      id: Date.now(),
      time: new Date().toLocaleTimeString('cs-CZ'),
      actor: auth.user || 'admin',
      name: newExp.value.name || `Nová evaluace: ${newExp.value.type}`,
      status: 'RUNNING'
    })
    saving.value = false
    dialog.value = false
    newExp.value.name = ''
  }, 800)
}
</script>
