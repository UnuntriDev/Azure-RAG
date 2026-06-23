// Postgres Flexible Server — metadata only, vectors in AI Search. Burstable B1ms for demo cost.

@description('Azure region for the server.')
param location string

@description('Server name (globally unique, lowercase).')
param name string

@description('Administrator login.')
param administratorLogin string

@description('Administrator password.')
@secure()
param administratorPassword string

@description('Initial database name created on the server.')
param databaseName string = 'rag'

resource server 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: name
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorPassword
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
  }
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: server
  name: databaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// Allow other Azure services (the Container App) to reach the server. The 0.0.0.0
// "Azure services" rule is the standard demo shortcut; for production, prefer VNet
// integration + private endpoint instead of this rule.
resource allowAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = {
  parent: server
  name: 'AllowAllAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

output fqdn string = server.properties.fullyQualifiedDomainName
output databaseName string = database.name
output name string = server.name
