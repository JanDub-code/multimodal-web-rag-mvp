@description('Azure region for Container Apps and storage.')
param location string = resourceGroup().location

@description('Short lowercase deployment prefix. Use letters, numbers, hyphen. Example: xdubrag. Keep it <=20 characters so derived Container Apps Job names stay valid.')
param prefix string = 'xdubrag'

@description('Azure Container Registry login server, for example myacr.azurecr.io.')
param acrLoginServer string

@description('Azure Container Registry username.')
param acrUsername string

@secure()
@description('Azure Container Registry password.')
param acrPassword string

@description('Backend API image tag.')
param apiImage string

@description('Frontend image tag.')
param frontendImage string

@description('Alembic migration job image tag.')
param migrateImage string

@secure()
@description('FastAPI/JWT secret key.')
param appSecretKey string

@secure()
@description('Postgres password for the app user.')
param postgresPassword string

@secure()
@description('Optional OpenCode API key. Leave blank if you only want the UI/API without generation calls.')
param opencodeApiKey string = ''

@description('Whether apps should start running immediately after deployment. false = minReplicas 0 everywhere.')
param startEnabled bool = false

@description('Seed demo users during the migration job.')
param seedDemoUsers bool = true

@secure()
@description('Demo admin password used by the migration/seed job.')
param demoAdminPassword string

@secure()
@description('Demo curator password used by the migration/seed job.')
param demoCuratorPassword string

@secure()
@description('Demo analyst password used by the migration/seed job.')
param demoAnalystPassword string

@secure()
@description('Demo user password used by the migration/seed job.')
param demoUserPassword string

var safePrefix = toLower(prefix)
var compactPrefix = replace(safePrefix, '-', '')
var envName = '${safePrefix}-env'
var logName = '${safePrefix}-law'
var storageAccountName = take('${compactPrefix}${uniqueString(resourceGroup().id, safePrefix)}', 24)
var postgresAppName = '${safePrefix}-postgres'
var qdrantAppName = '${safePrefix}-qdrant'
var apiAppName = '${safePrefix}-api'
var frontendAppName = '${safePrefix}-frontend'
var migrateJobName = '${safePrefix}-migrate'
var minOn = startEnabled ? 1 : 0
var databaseUrl = 'postgresql+psycopg://app:${postgresPassword}@${postgresAppName}:5432/multimodal_mvp'
var apiInternalFqdn = '${apiAppName}.internal.${env.properties.defaultDomain}'
var qdrantInternalFqdn = '${qdrantAppName}.internal.${env.properties.defaultDomain}'
var commonRegistry = [
  {
    server: acrLoginServer
    username: acrUsername
    passwordSecretRef: 'acr-password'
  }
]
var commonAcrSecret = [
  {
    name: 'acr-password'
    value: acrPassword
  }
]
var opencodeSecret = empty(opencodeApiKey) ? [] : [
  {
    name: 'opencode-api-key'
    value: opencodeApiKey
  }
]
var opencodeEnv = empty(opencodeApiKey) ? [] : [
  {
    name: 'OPENCODE_API_KEY_RUNTIME'
    secretRef: 'opencode-api-key'
  }
]

resource log 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logName
  location: location
  properties: {
    retentionInDays: 30
    sku: {
      name: 'PerGB2018'
    }
  }
}

resource env 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: envName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: log.properties.customerId
        sharedKey: log.listKeys().primarySharedKey
      }
    }
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource fileService 'Microsoft.Storage/storageAccounts/fileServices@2023-05-01' = {
  parent: storage
  name: 'default'
}

resource qdrantShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01' = {
  parent: fileService
  name: 'qdrantdata'
  properties: {
    shareQuota: 32
  }
}

resource evidenceShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01' = {
  parent: fileService
  name: 'evidence'
  properties: {
    shareQuota: 16
  }
}

resource fastembedShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01' = {
  parent: fileService
  name: 'fastembed'
  properties: {
    shareQuota: 16
  }
}

resource qdrantStorage 'Microsoft.App/managedEnvironments/storages@2024-03-01' = {
  parent: env
  name: 'qdrantdata'
  properties: {
    azureFile: {
      accountName: storage.name
      accountKey: storage.listKeys().keys[0].value
      shareName: qdrantShare.name
      accessMode: 'ReadWrite'
    }
  }
}

resource evidenceStorage 'Microsoft.App/managedEnvironments/storages@2024-03-01' = {
  parent: env
  name: 'evidence'
  properties: {
    azureFile: {
      accountName: storage.name
      accountKey: storage.listKeys().keys[0].value
      shareName: evidenceShare.name
      accessMode: 'ReadWrite'
    }
  }
}

resource fastembedStorage 'Microsoft.App/managedEnvironments/storages@2024-03-01' = {
  parent: env
  name: 'fastembed'
  properties: {
    azureFile: {
      accountName: storage.name
      accountKey: storage.listKeys().keys[0].value
      shareName: fastembedShare.name
      accessMode: 'ReadWrite'
    }
  }
}

resource postgres 'Microsoft.App/containerApps@2024-03-01' = {
  name: postgresAppName
  location: location
  properties: {
    environmentId: env.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: false
        targetPort: 5432
        exposedPort: 5432
        transport: 'tcp'
      }
      secrets: [
        {
          name: 'postgres-password'
          value: postgresPassword
        }
      ]
    }
    template: {
      terminationGracePeriodSeconds: 60
      containers: [
        {
          name: 'postgres'
          image: 'postgres:16'
          env: [
            {
              name: 'POSTGRES_USER'
              value: 'app'
            }
            {
              name: 'POSTGRES_DB'
              value: 'multimodal_mvp'
            }
            {
              name: 'POSTGRES_PASSWORD'
              secretRef: 'postgres-password'
            }
            {
              name: 'PGDATA'
              value: '/var/lib/postgresql/data/pgdata'
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          volumeMounts: [
            {
              volumeName: 'pgdata'
              mountPath: '/var/lib/postgresql/data'
            }
          ]
        }
      ]
      scale: {
        minReplicas: minOn
        maxReplicas: 1
        rules: [
          {
            name: 'tcp-5432'
            tcp: {
              metadata: {
                concurrentConnections: '50'
              }
            }
          }
        ]
      }
      volumes: [
        {
          name: 'pgdata'
          storageType: 'EmptyDir'
        }
      ]
    }
  }
}

resource qdrant 'Microsoft.App/containerApps@2024-03-01' = {
  name: qdrantAppName
  dependsOn: [
    qdrantStorage
  ]
  location: location
  properties: {
    environmentId: env.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: false
        targetPort: 6333
        transport: 'auto'
      }
    }
    template: {
      terminationGracePeriodSeconds: 60
      containers: [
        {
          name: 'qdrant'
          image: 'qdrant/qdrant:v1.15.5'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          volumeMounts: [
            {
              volumeName: 'qdrantdata'
              mountPath: '/qdrant/storage'
            }
          ]
        }
      ]
      scale: {
        minReplicas: minOn
        maxReplicas: 1
        rules: [
          {
            name: 'http-6333'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
      volumes: [
        {
          name: 'qdrantdata'
          storageName: qdrantStorage.name
          storageType: 'AzureFile'
        }
      ]
    }
  }
}

resource api 'Microsoft.App/containerApps@2024-03-01' = {
  name: apiAppName
  dependsOn: [
    evidenceStorage
    fastembedStorage
    postgres
    qdrant
  ]
  location: location
  properties: {
    environmentId: env.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: false
        targetPort: 8000
        transport: 'auto'
      }
      registries: commonRegistry
      secrets: concat(commonAcrSecret, opencodeSecret, [
        {
          name: 'app-secret-key'
          value: appSecretKey
        }
        {
          name: 'database-url'
          value: databaseUrl
        }
      ])
    }
    template: {
      terminationGracePeriodSeconds: 60
      containers: [
        {
          name: 'api'
          image: apiImage
          env: concat([
            {
              name: 'APP_NAME'
              value: 'Multimodal RAG MVP'
            }
            {
              name: 'APP_HOST'
              value: '0.0.0.0'
            }
            {
              name: 'APP_PORT'
              value: '8000'
            }
            {
              name: 'APP_SECRET_KEY'
              secretRef: 'app-secret-key'
            }
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
            {
              name: 'QDRANT_URL'
              value: 'https://${qdrantInternalFqdn}:443'
            }
            {
              name: 'RETRIEVAL_WARMUP_ON_STARTUP'
              value: 'false'
            }
            {
              name: 'EVIDENCE_DIR'
              value: '/app/data/evidence'
            }
            {
              name: 'SCREENSHOT_DIR'
              value: '/app/data/evidence/screenshots'
            }
            {
              name: 'DOM_SNAPSHOT_DIR'
              value: '/app/data/evidence/dom'
            }
          ], opencodeEnv)
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
          volumeMounts: [
            {
              volumeName: 'evidence'
              mountPath: '/app/data/evidence'
            }
            {
              volumeName: 'fastembed'
              mountPath: '/root/.cache'
            }
          ]
          probes: [
            {
              type: 'Startup'
              httpGet: {
                path: '/health'
                port: 8000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 15
              periodSeconds: 15
              timeoutSeconds: 10
              failureThreshold: 20
            }
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 60
              periodSeconds: 30
              timeoutSeconds: 10
              failureThreshold: 5
            }
          ]
        }
      ]
      scale: {
        minReplicas: minOn
        maxReplicas: 1
        rules: [
          {
            name: 'http-8000'
            http: {
              metadata: {
                concurrentRequests: '20'
              }
            }
          }
        ]
      }
      volumes: [
        {
          name: 'evidence'
          storageName: evidenceStorage.name
          storageType: 'AzureFile'
        }
        {
          name: 'fastembed'
          storageName: fastembedStorage.name
          storageType: 'AzureFile'
        }
      ]
    }
  }
}

resource frontend 'Microsoft.App/containerApps@2024-03-01' = {
  name: frontendAppName
  dependsOn: [
    api
  ]
  location: location
  properties: {
    environmentId: env.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 80
        transport: 'auto'
        allowInsecure: false
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      registries: commonRegistry
      secrets: commonAcrSecret
    }
    template: {
      terminationGracePeriodSeconds: 30
      containers: [
        {
          name: 'frontend'
          image: frontendImage
          env: [
            {
              name: 'API_UPSTREAM'
              value: 'https://${apiInternalFqdn}'
            }
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      scale: {
        minReplicas: minOn
        maxReplicas: 1
        rules: [
          {
            name: 'http-80'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
}

resource migrate 'Microsoft.App/jobs@2024-03-01' = {
  name: migrateJobName
  dependsOn: [
    postgres
    qdrant
  ]
  location: location
  properties: {
    environmentId: env.id
    configuration: {
      triggerType: 'Manual'
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
      replicaRetryLimit: 2
      replicaTimeout: 900
      registries: commonRegistry
      secrets: concat(commonAcrSecret, [
        {
          name: 'database-url'
          value: databaseUrl
        }
        {
          name: 'demo-admin-password'
          value: demoAdminPassword
        }
        {
          name: 'demo-curator-password'
          value: demoCuratorPassword
        }
        {
          name: 'demo-analyst-password'
          value: demoAnalystPassword
        }
        {
          name: 'demo-user-password'
          value: demoUserPassword
        }
      ])
    }
    template: {
      containers: [
        {
          name: 'migrate'
          image: migrateImage
          env: [
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
            {
              name: 'QDRANT_URL'
              value: 'https://${qdrantInternalFqdn}:443'
            }
            {
              name: 'SEED_DEMO_USERS'
              value: seedDemoUsers ? 'true' : 'false'
            }
            {
              name: 'DEMO_ADMIN_PASSWORD'
              secretRef: 'demo-admin-password'
            }
            {
              name: 'DEMO_CURATOR_PASSWORD'
              secretRef: 'demo-curator-password'
            }
            {
              name: 'DEMO_ANALYST_PASSWORD'
              secretRef: 'demo-analyst-password'
            }
            {
              name: 'DEMO_USER_PASSWORD'
              secretRef: 'demo-user-password'
            }
            {
              name: 'DB_STARTUP_TIMEOUT_SECONDS'
              value: '600'
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
    }
  }
}

output frontendUrl string = 'https://${frontend.properties.configuration.ingress.fqdn}'
output apiInternalUrl string = 'https://${apiInternalFqdn}'
output qdrantInternalUrl string = 'https://${qdrantInternalFqdn}:443'
output postgresInternalHost string = postgresAppName
output startCommand string = './scripts/azure-start.sh'
output stopCommand string = './scripts/azure-stop.sh'
