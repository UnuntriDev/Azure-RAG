# Deployment (stage 4)

Infrastructure-as-code for hosting the app on Azure. This **provisions the hosting layer**
(identity, ACR, Postgres, Key Vault, Container Apps, Static Web App) and **reuses the stage-1
data services** (Azure OpenAI, AI Search, Blob) that already exist from `docs/azure-setup.md` —
those are passed in as parameters, not recreated.

> These are deploy-ready artifacts. Nothing here runs automatically and nothing has been
> provisioned yet — running the commands below incurs Azure cost.

## What gets created

| Resource | Module | Notes |
|---|---|---|
| User-assigned managed identity | inline in `main.bicep` | one identity for both ACR pull + Key Vault read |
| Log Analytics workspace | `modules/loganalytics.bicep` | Container Apps logs |
| Container Registry (ACR, Basic) | `modules/registry.bicep` | admin user off; `AcrPull` granted to the identity |
| Postgres Flexible Server 16 | `modules/postgres.bicep` | `Standard_B1ms` Burstable, TLS enforced |
| Key Vault (RBAC) | `modules/keyvault.bicep` | holds the 4 runtime secrets; `Secrets User` granted to the identity |
| Container Apps environment | `modules/containerenv.bicep` | wired to Log Analytics |
| Backend Container App | `modules/backend.bicep` | pulls image via identity, reads secrets via identity |
| Static Web App (Free) | `modules/staticwebapp.bicep` | hosts the Next.js static export |

**Secret flow:** secrets live only in Key Vault. The backend reads them through the managed
identity (`keyVaultUrl` secret refs) — no keys in env vars, no service-principal password
anywhere. That's the whole point of the user-assigned identity.

## Prerequisites

- `az` CLI logged in (`az login`) with rights on the target subscription.
- A resource group: `az group create -n <rg> -l westeurope`.
- The stage-1 service values from `docs/azure-setup.md`: OpenAI endpoint, Search endpoint, and
  the three secret keys.

## 1. Deploy the infrastructure

Secrets come from your shell (never committed — see `main.bicepparam`). Set them, then deploy:

```bash
export PG_ADMIN_PASSWORD='<choose-a-strong-password>'
export AZURE_OPENAI_API_KEY='...'
export AZURE_SEARCH_API_KEY='...'
export AZURE_STORAGE_CONNECTION_STRING='...'

# Fill the endpoint placeholders in infra/main.bicepparam first
az deployment group create \
  -g <rg> \
  -f infra/main.bicep \
  -p infra/main.bicepparam
```

The first deploy uses a **placeholder backend image** (`backendImage` default) so it succeeds
before any image exists. CI replaces it on the first backend build.

Grab the outputs you'll need next:

```bash
az deployment group show -g <rg> -n main \
  --query properties.outputs \
  -o jsonc
```

Relevant outputs: `registryName`, `backendAppName`, `backendUrl`, `staticWebAppName`,
`staticWebAppUrl`, `keyVaultName`, `identityClientId`.

## 2. Wire up CI/CD (GitHub Actions)

Two workflows deploy on push to `main`: `.github/workflows/backend.yml` (build image in ACR →
roll the Container App) and `frontend.yml` (build static export → upload to SWA).

**Backend — OIDC auth (no stored secret).** Create a federated credential on the identity (or a
dedicated app registration) for this repo, grant it `Contributor` + `AcrPush` on the RG, then set:

- Secrets: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`
- Variables: `AZURE_RESOURCE_GROUP`, `ACR_NAME` (= `registryName`), `BACKEND_APP_NAME` (= `backendAppName`)

**Frontend — SWA deploy token.**

```bash
az staticwebapp secrets list \
  --name <staticWebAppName> -g <rg> \
  --query properties.apiKey -o tsv
```

- Secret: `AZURE_STATIC_WEB_APPS_API_TOKEN` (the token above)
- Variable: `BACKEND_URL` (= `backendUrl`) — baked into the bundle at build time as `NEXT_PUBLIC_API_URL`

## 3. Close the CORS loop

The backend starts with `corsOrigins` empty (the SWA URL isn't known until after deploy).
Once you have `staticWebAppUrl`, set it and redeploy:

```bash
# in infra/main.bicepparam
param corsOrigins = 'https://<name>.azurestaticapps.net'
```

Re-run the `az deployment group create` from step 1. Bicep is declarative — it only updates the
backend's CORS setting.

> **If you enable Google auth here:** the SWA frontend and the Container App backend are on
> different domains, so the session cookie is **cross-site**. A `SameSite=Lax` cookie won't be
> sent on those requests — set `COOKIE_SAMESITE=none` **and** `COOKIE_SECURE=true` on the backend
> (both already HTTPS), or auth will silently fail in production. See the *Session cookie* group
> in `.env.example`.

## Notes

- **TLS to Postgres:** the backend sets `DB_SSL_REQUIRE=true`, which makes asyncpg negotiate TLS
  (`connect_args={"ssl": "require"}`). Flexible Server enforces TLS, so this is required in Azure.
  Locally it stays `false` (docker Postgres has no TLS).
- **DB migrations:** run Alembic against the Flexible Server (open the firewall to your IP or run
  from the Container App) before first real use.
- **Validate without deploying:** `az bicep build -f infra/main.bicep` compiles all modules and
  catches errors with zero cost.
