// Provisions hosting layer (identity, ACR, Postgres, Key Vault, Container Apps, SWA).
// Reuses stage-1 data services (OpenAI, AI Search, Blob) passed as params.
// Deploy: az deployment group create -g <rg> -f infra/main.bicep -p infra/main.bicepparam

targetScope = 'resourceGroup'

@description('Short prefix for resource names (lowercase letters/digits).')
@minLength(3)
@maxLength(10)
param namePrefix string = 'azurerag'

@description('Primary region for the app resources.')
param location string = resourceGroup().location

@description('Region for the Static Web App (limited set; e.g. westeurope, eastus2).')
param staticWebAppLocation string = 'westeurope'

// ── Postgres admin ──
@description('Postgres administrator login.')
param postgresAdminLogin string = 'ragadmin'

@description('Postgres administrator password.')
@secure()
param postgresAdminPassword string

param databaseName string = 'rag'

// ── Reused stage-1 services (from docs/azure-setup.md) ──
param azureOpenaiEndpoint string
@secure()
param azureOpenaiApiKey string
param azureOpenaiApiVersion string = '2024-10-21'
param azureOpenaiChatDeployment string = 'gpt-4o-mini'
param azureOpenaiEmbeddingDeployment string = 'text-embedding-3-small'

param azureSearchEndpoint string
@secure()
param azureSearchApiKey string
param azureSearchIndexName string = 'rag-chunks'

@secure()
param azureStorageConnectionString string
param azureStorageContainer string = 'documents'

@description('Allowed CORS origin(s) for the backend. Set to the Static Web App URL after first deploy, e.g. https://<name>.azurestaticapps.net')
param corsOrigins string = ''

@description('Container image the backend runs. CI overrides this per build; the placeholder lets the first infra deploy succeed before an image exists.')
param backendImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

// Deterministic, globally-unique-ish suffix derived from the RG.
var suffix = take(uniqueString(resourceGroup().id), 8)
var registryName = '${namePrefix}acr${suffix}'
var keyVaultName = '${namePrefix}kv${suffix}'
var postgresName = '${namePrefix}-pg-${suffix}'
var lawName = '${namePrefix}-law-${suffix}'
var envName = '${namePrefix}-env'
var backendName = '${namePrefix}-backend'
var staticWebAppName = '${namePrefix}-web-${suffix}'
var identityName = '${namePrefix}-id'

// Created before the Container App so role assignments can reference its principalId.
resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
}

module logAnalytics 'modules/loganalytics.bicep' = {
  name: 'logAnalytics'
  params: {
    location: location
    name: lawName
  }
}

module registry 'modules/registry.bicep' = {
  name: 'registry'
  params: {
    location: location
    name: registryName
    pullPrincipalId: identity.properties.principalId
  }
}

module postgres 'modules/postgres.bicep' = {
  name: 'postgres'
  params: {
    location: location
    name: postgresName
    administratorLogin: postgresAdminLogin
    administratorPassword: postgresAdminPassword
    databaseName: databaseName
  }
}

module keyVault 'modules/keyvault.bicep' = {
  name: 'keyVault'
  params: {
    location: location
    name: keyVaultName
    readerPrincipalId: identity.properties.principalId
    databaseUrl: 'postgresql+asyncpg://${postgresAdminLogin}:${postgresAdminPassword}@${postgres.outputs.fqdn}:5432/${databaseName}'
    azureOpenaiApiKey: azureOpenaiApiKey
    azureSearchApiKey: azureSearchApiKey
    azureStorageConnectionString: azureStorageConnectionString
  }
}

module containerEnv 'modules/containerenv.bicep' = {
  name: 'containerEnv'
  params: {
    location: location
    name: envName
    logAnalyticsName: logAnalytics.outputs.name
  }
}

module backend 'modules/backend.bicep' = {
  name: 'backend'
  params: {
    location: location
    name: backendName
    environmentId: containerEnv.outputs.id
    identityId: identity.id
    registryLoginServer: registry.outputs.loginServer
    image: backendImage
    vaultUri: keyVault.outputs.vaultUri
    azureOpenaiEndpoint: azureOpenaiEndpoint
    azureOpenaiApiVersion: azureOpenaiApiVersion
    azureOpenaiChatDeployment: azureOpenaiChatDeployment
    azureOpenaiEmbeddingDeployment: azureOpenaiEmbeddingDeployment
    azureSearchEndpoint: azureSearchEndpoint
    azureSearchIndexName: azureSearchIndexName
    azureStorageContainer: azureStorageContainer
    corsOrigins: corsOrigins
  }
}

module staticWebApp 'modules/staticwebapp.bicep' = {
  name: 'staticWebApp'
  params: {
    location: staticWebAppLocation
    name: staticWebAppName
  }
}

// ── Outputs wired into CI / post-deploy config ──
output registryLoginServer string = registry.outputs.loginServer
output registryName string = registryName
output backendFqdn string = backend.outputs.fqdn
output backendUrl string = 'https://${backend.outputs.fqdn}'
output backendAppName string = backendName
output staticWebAppName string = staticWebAppName
output staticWebAppUrl string = 'https://${staticWebApp.outputs.defaultHostname}'
output keyVaultName string = keyVaultName
output identityClientId string = identity.properties.clientId
