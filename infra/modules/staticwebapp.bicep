// Static Web App — hosts the Next.js frontend. Created empty here (Free SKU); the actual
// build + upload happens from the GitHub Action using the deployment token (read after
// provisioning with `az staticwebapp secrets list`). NEXT_PUBLIC_API_URL is injected at
// build time in CI, not stored on the resource.

@description('Azure region for the Static Web App (e.g. westeurope).')
param location string

@description('Static Web App name.')
param name string

resource site 'Microsoft.Web/staticSites@2023-12-01' = {
  name: name
  location: location
  sku: {
    name: 'Free'
    tier: 'Free'
  }
  properties: {
    // Repo is wired by the GitHub Action via deployment token, not by this resource.
    allowConfigFileUpdates: true
  }
}

output defaultHostname string = site.properties.defaultHostname
output name string = site.name
