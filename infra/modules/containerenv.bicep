// Container Apps managed environment — the shared runtime that the backend app runs in.
// Wired to Log Analytics for log/metric capture.

@description('Azure region for the environment.')
param location string

@description('Environment name.')
param name string

@description('Name of the Log Analytics workspace to attach (must already exist).')
param logAnalyticsName string

// `existing` reference: read the workspace's id + shared key here so the secret never
// leaves this module as an output. Ordering is guaranteed because main passes the
// workspace's name output, making this module depend on the workspace deployment.
resource law 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: logAnalyticsName
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: name
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: law.properties.customerId
        sharedKey: law.listKeys().primarySharedKey
      }
    }
  }
}

output id string = environment.id
output name string = environment.name
