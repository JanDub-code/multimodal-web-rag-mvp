<template>
  <div class="dashboard">
    <h1 class="page-title">Dashboard</h1>

    <!-- Stats Cards -->
    <v-row class="mb-6">
      <v-col cols="12" sm="6" md="3">
        <div class="stat-card">
          <div class="stat-card__value">{{ stats.totalSources }}</div>
          <div class="stat-card__label">Registrované zdroje</div>
        </div>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <router-link to="/incidents" style="text-decoration: none;">
          <div class="stat-card stat-card--clickable">
            <div class="stat-card__value stat-card__value--accent">{{ stats.openIncidents }}</div>
            <div class="stat-card__label">Otevřené incidenty <v-icon size="14" class="ml-1">mdi-arrow-right</v-icon></div>
          </div>
        </router-link>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <div class="stat-card">
          <div class="stat-card__value">{{ formatDate(stats.lastCrawl) }}</div>
          <div class="stat-card__label">Poslední sběr</div>
        </div>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <div class="stat-card">
          <div class="stat-card__value">{{ formatDate(stats.nextCrawl) }}</div>
          <div class="stat-card__label">Příští sběr</div>
        </div>
      </v-col>
    </v-row>

    <!-- Quick Actions + Recent Activity -->
    <v-row>
      <v-col cols="12" md="5">
        <v-card class="pa-5">
          <h3 class="section-title">Rychlé akce</h3>
          <div class="quick-actions">
            <v-btn
              v-if="canQuery"
              color="primary"
              prepend-icon="mdi-chat-plus-outline"
              block
              class="mb-3"
              to="/chat"
            >
              Nový dotaz
            </v-btn>
            <v-btn
              v-if="canIngest"
              color="secondary"
              prepend-icon="mdi-cloud-upload-outline"
              block
              class="mb-3"
              to="/ingest"
            >
              Spustit ingest
            </v-btn>
            <v-btn
              v-if="canManageSources"
              variant="outlined"
              prepend-icon="mdi-alert-circle-outline"
              block
              class="mb-3"
              to="/incidents"
            >
              Správa incidentů
            </v-btn>
            <v-btn
              v-if="canManageSources"
              variant="outlined"
              prepend-icon="mdi-database-plus-outline"
              block
              class="mb-3"
              to="/sources"
            >
              Správa zdrojů
            </v-btn>
            <v-btn
              variant="outlined"
              prepend-icon="mdi-clipboard-check-outline"
              block
              to="/compliance"
            >
              Compliance
            </v-btn>
          </div>
        </v-card>
      </v-col>

      <v-col cols="12" md="7">
        <v-card class="pa-5">
          <h3 class="section-title">Poslední aktivita</h3>
          <v-list density="compact" class="recent-activity">
            <v-list-item
              v-for="entry in recentAudit"
              :key="entry.id"
              class="recent-activity__item"
            >
              <template #prepend>
                <span :class="['event-chip', `event-chip--${entry.event_category}`]">
                  {{ entry.event_type }}
                </span>
              </template>
              <v-list-item-title class="recent-activity__detail">
                {{ entry.detail }}
              </v-list-item-title>
              <template #append>
                <span class="recent-activity__time">
                  {{ formatTime(entry.ts) }}
                </span>
              </template>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuth } from '@/composables/useAuth'
import { auditService } from '@/services/auditService'
import api from '@/plugins/axios'

const { canQuery, canIngest, canManageSources } = useAuth()

const stats = ref({
  totalSources: '—',
  openIncidents: '—',
  lastCrawl: null,
  nextCrawl: null,
})
const recentAudit = ref([])

onMounted(async () => {
  try {
    const [statsRes, logsRes] = await Promise.allSettled([
      api.get('/dashboard/stats'),
      auditService.getAuditLogs(),
    ])
    if (statsRes.status === 'fulfilled') {
      stats.value = statsRes.value.data
    }
    if (logsRes.status === 'fulfilled') {
      recentAudit.value = (logsRes.value || []).slice(0, 6)
    }
  } catch (err) {
    console.error('Dashboard load error:', err)
  }
})

function formatTime(ts) {
  const d = new Date(ts)
  return d.toLocaleString('cs-CZ', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' })
}

function formatDate(dateString) {
  if (!dateString || dateString === '–') return '–'
  const d = new Date(dateString)
  if (isNaN(d.getTime())) return dateString
  // If the value contains a time component, show date + time
  if (dateString.includes('T') || dateString.includes(' ')) {
    return d.toLocaleString('cs-CZ', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }
  return d.toLocaleDateString('cs-CZ')
}
</script>

<style lang="scss" scoped>
.dashboard {
  padding: $space-base $space-lg;

  @media (max-width: 599px) {
    padding: $space-base;
  }

  // Stats row is global styled

  .quick-actions {
    .v-btn {
      justify-content: flex-start;
      text-transform: none;
      font-weight: $font-weight-medium;
    }
  }

  .stat-card--clickable {
    cursor: pointer;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 16px rgba(0,0,0,0.10);
    }
  }

  .recent-activity {
    &__item {
      border-bottom: 1px solid $border-light;
      padding: $space-sm 0;

      &:last-child {
        border-bottom: none;
      }
    }

    &__detail {
      font-size: $font-size-sm;
      color: $text-secondary;
      margin-left: $space-sm;
    }

    &__time {
      font-size: $font-size-xs;
      color: $text-muted;
      white-space: nowrap;
    }
  }
}
</style>
