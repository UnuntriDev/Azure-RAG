// FastAPI Container App. Image pulled from ACR, secrets read from Key Vault — both via managed identity.

@description('Azure region.')
param location string

@description('Container App name.')
param name string

@description('Managed environment resource id.')
param environmentId string

@description('User-assigned managed identity resource id (ACR pull + KV read).')
param identityId string

@description('ACR login server, e.g. myreg.azurecr.io.')
param registryLoginServer string

@description('Full image reference, e.g. myreg.azurecr.io/azure-rag-backend:abc123.')
param image string

@description('Key Vault URI, e.g. https://myvault.vault.azure.net/.')
param vaultUri string

// ── Non-secret app configuration ──
param azureOpenaiEndpoint string
param azureOpenaiApiVersion string
param azureOpenaiChatDeployment string
param azureOpenaiEmbeddingDeployment string
param azureSearchEndpoint string
param azureSearchIndexName string
param azureStorageContainer string
@description('Comma-separated allowed CORS origins (set to the deployed frontend URL).')
param corsOrigins string
param logLevel string = 'INFO'

var secrets = [
  { name: 'database-url', keyVaultUrl: '${vaultUri}secrets/database-url', identity: identityId }
  { name: 'azure-openai-api-key', keyVaultUrl: '${vaultUri}secrets/azure-openai-api-key', identity: identityId }
  { name: 'azure-search-api-key', keyVaultUrl: '${vaultUri}secrets/azure-search-api-key', identity: identityId }
  { name: 'azure-storage-connection-string', keyVaultUrl: '${vaultUri}secrets/azure-storage-connection-string', identity: identityId }
]

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        stickySessions: {
          affinity: 'none'
        }
      }
      registries: [
        {
          server: registryLoginServer
          identity: identityId
        }
      ]
      secrets: secrets
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: image
          resources: {
            cpu: json('0.5')
            memory: '1.0Gi'
          }
          env: [
            { name: 'DATABASE_URL', secretRef: 'database-url' }
            { name: 'DB_SSL_REQUIRE', value: 'true' }
            { name: 'AZURE_OPENAI_ENDPOINT', value: azureOpenaiEndpoint }
            { name: 'AZURE_OPENAI_API_KEY', secretRef: 'azure-openai-api-key' }
            { name: 'AZURE_OPENAI_API_VERSION', value: azureOpenaiApiVersion }
            { name: 'AZURE_OPENAI_CHAT_DEPLOYMENT', value: azureOpenaiChatDeployment }
            { name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT', value: azureOpenaiEmbeddingDeployment }
            { name: 'AZURE_SEARCH_ENDPOINT', value: azureSearchEndpoint }
            { name: 'AZURE_SEARCH_API_KEY', secretRef: 'azure-search-api-key' }
            { name: 'AZURE_SEARCH_INDEX_NAME', value: azureSearchIndexName }
            { name: 'AZURE_STORAGE_CONNECTION_STRING', secretRef: 'azure-storage-connection-string' }
            { name: 'AZURE_STORAGE_CONTAINER', value: azureStorageContainer }
            { name: 'CORS_ORIGINS', value: corsOrigins }
            { name: 'LOG_LEVEL', value: logLevel }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
        rules: [
          {
            name: 'http-scale'
            http: {
              metadata: {
                concurrentRequests: '20'
              }
            }
          }
        ]
      }
    }
  }
}

output fqdn string = app.properties.configuration.ingress.fqdn
output name string = app.name
