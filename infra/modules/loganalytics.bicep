// Log Analytics workspace — required backing store for the Container Apps environment
// (logs + metrics). Kept as its own module so the retention/SKU is easy to tune.

@description('Azure region for the workspace.')
param location string

@description('Workspace name.')
param name string

@description('Daily log retention in days (30 is the free floor).')
param retentionInDays int = 30

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: name
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: retentionInDays
  }
}

output id string = workspace.id
output customerId string = workspace.properties.customerId
output name string = workspace.name
