// Key Vault — single home for the four runtime secrets. The backend Container App reads
// them through its managed identity (RBAC "Key Vault Secrets User"), so no secret value
// is ever baked into the image, the Container App definition, or git.

@description('Azure region for the vault.')
param location string

@description('Vault name (globally unique, 3-24 chars).')
param name string

@description('Principal (object) id of the identity allowed to read secrets.')
param readerPrincipalId string

@description('Full async DATABASE_URL incl. credentials and ?ssl=require.')
@secure()
param databaseUrl string

@description('Azure OpenAI API key.')
@secure()
param azureOpenaiApiKey string

@description('Azure AI Search admin key.')
@secure()
param azureSearchApiKey string

@description('Azure Blob Storage connection string.')
@secure()
param azureStorageConnectionString string

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: tenant().tenantId
    // RBAC instead of access policies — grants flow through role assignments below.
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
  }
}

// Built-in role "Key Vault Secrets User" — read secret values (not manage).
var secretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

resource readSecrets 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(vault.id, readerPrincipalId, secretsUserRoleId)
  scope: vault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', secretsUserRoleId)
    principalId: readerPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Secret names map 1:1 to the Container App secretRefs in backend.bicep.
resource databaseUrlSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: vault
  name: 'database-url'
  properties: {
    value: databaseUrl
  }
}

resource openaiKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: vault
  name: 'azure-openai-api-key'
  properties: {
    value: azureOpenaiApiKey
  }
}

resource searchKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: vault
  name: 'azure-search-api-key'
  properties: {
    value: azureSearchApiKey
  }
}

resource storageConnSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: vault
  name: 'azure-storage-connection-string'
  properties: {
    value: azureStorageConnectionString
  }
}

output vaultUri string = vault.properties.vaultUri
output name string = vault.name
