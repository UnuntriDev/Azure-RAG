// Azure Container Registry — holds the backend image that the Container App pulls.
// Admin user stays disabled; the Container App pulls via its managed identity (AcrPull),
// which is the credential-free path we want for a portfolio "best practices" story.

@description('Azure region for the registry.')
param location string

@description('Registry name (globally unique, alphanumeric, 5-50 chars).')
param name string

@description('Principal (object) id of the identity that pulls images.')
param pullPrincipalId string

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: name
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
  }
}

// Built-in role "AcrPull" — lets the Container App's managed identity pull images.
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource pullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, pullPrincipalId, acrPullRoleId)
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: pullPrincipalId
    principalType: 'ServicePrincipal'
  }
}

output loginServer string = registry.properties.loginServer
output name string = registry.name
