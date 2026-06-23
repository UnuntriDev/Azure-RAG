// Parameter file for main.bicep. Fill in the reused stage-1 service values (they come from
// docs/azure-setup.md outputs). Secrets are pulled from environment variables so nothing
// secret is committed — set them in your shell before `az deployment group create`:
//
//   export PG_ADMIN_PASSWORD='...'
//   export AZURE_OPENAI_API_KEY='...'
//   export AZURE_SEARCH_API_KEY='...'
//   export AZURE_STORAGE_CONNECTION_STRING='...'

using 'main.bicep'

param namePrefix = 'azurerag'
param staticWebAppLocation = 'westeurope'

// ── Postgres ──
param postgresAdminLogin = 'ragadmin'
param postgresAdminPassword = readEnvironmentVariable('PG_ADMIN_PASSWORD')

// ── Reused stage-1 services — fill endpoints, keys come from env ──
param azureOpenaiEndpoint = 'https://<your-openai>.openai.azure.com/'
param azureOpenaiApiKey = readEnvironmentVariable('AZURE_OPENAI_API_KEY')
param azureSearchEndpoint = 'https://<your-search>.search.windows.net'
param azureSearchApiKey = readEnvironmentVariable('AZURE_SEARCH_API_KEY')
param azureStorageConnectionString = readEnvironmentVariable('AZURE_STORAGE_CONNECTION_STRING')

// Set after the first deploy to the Static Web App URL (CORS). Leave blank initially.
param corsOrigins = ''
