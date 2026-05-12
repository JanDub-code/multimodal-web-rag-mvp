@description('Azure region for the redeployed Container App.')
param location string = resourceGroup().location

@description('Short lowercase deployment prefix. Must match the existing stack prefix.')
param prefix string = 'xdubrag'

@secure()
@description('Postgres password for the app user.')
param postgresPassword string

var safePrefix = toLower(prefix)
var envName = '${safePrefix}-env'
var postgresAppName = '${safePrefix}-postgres'

resource env 'Microsoft.App/managedEnvironments@2024-03-01' existing = {
  name: envName
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
        minReplicas: 1
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

output postgresInternalHost string = postgresAppName