# Azure provisioning (stage 1)

Stage 1 talks to three live Azure services. This sets them up via **az CLI** and maps the
outputs to `.env`. The AI Search *index* is created by app code (the indexer), so here we only
create the *service*.

## Prerequisites

- An Azure subscription.
- [az CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) installed, then:
  ```bash
  az login
  az account set --subscription "<your-subscription-id>"
  ```
- Azure OpenAI access on the subscription (generally available; if your tenant still gates it,
  request access in the portal first).

## 0. Variables + resource group

Pick a region where **both** `gpt-4o-mini` and `text-embedding-3-small` are available
(e.g. `swedencentral`, `eastus2`).

```bash
RG=rag-rg
LOC=swedencentral
OPENAI=rag-openai-$RANDOM
SEARCH=rag-search-$RANDOM
STORAGE=ragstore$RANDOM          # storage names: lowercase, 3-24 chars, no dashes

az group create -n $RG -l $LOC
```

## 1. Azure OpenAI + model deployments

```bash
# Create the account
az cognitiveservices account create \
  -n $OPENAI -g $RG -l $LOC \
  --kind OpenAI --sku S0 --yes

# Check which model versions are available in this region, then plug them into --model-version
az cognitiveservices account list-models -n $OPENAI -g $RG \
  --query "[?contains(name,'gpt-4o-mini') || contains(name,'text-embedding-3-small')].{name:name,version:version}" -o table

# Chat deployment (deployment name = what goes in AZURE_OPENAI_CHAT_DEPLOYMENT)
az cognitiveservices account deployment create \
  -n $OPENAI -g $RG \
  --deployment-name gpt-4o-mini \
  --model-name gpt-4o-mini --model-version 2024-07-18 --model-format OpenAI \
  --sku-name Standard --sku-capacity 20

# Embedding deployment
az cognitiveservices account deployment create \
  -n $OPENAI -g $RG \
  --deployment-name text-embedding-3-small \
  --model-name text-embedding-3-small --model-version 1 --model-format OpenAI \
  --sku-name Standard --sku-capacity 50

# Outputs → .env
az cognitiveservices account show -n $OPENAI -g $RG --query properties.endpoint -o tsv
az cognitiveservices account keys list -n $OPENAI -g $RG --query key1 -o tsv
```
→ `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`.
`AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small`.

> If `--model-version` is rejected, use a version from the `list-models` output above.

## 2. Azure AI Search

```bash
az search service create -n $SEARCH -g $RG -l $LOC --sku basic --partition-count 1 --replica-count 1

# Outputs → .env
echo "https://$SEARCH.search.windows.net"
az search admin-key show --service-name $SEARCH -g $RG --query primaryKey -o tsv
```
→ `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_API_KEY`.
`AZURE_SEARCH_INDEX_NAME=rag-chunks` (the app creates the index on first ingest).

> `basic` SKU supports vector + hybrid search. The free tier works for tiny tests but is limited.

## 3. Azure Blob Storage

```bash
az storage account create -n $STORAGE -g $RG -l $LOC --sku Standard_LRS --kind StorageV2

CONN=$(az storage account show-connection-string -n $STORAGE -g $RG --query connectionString -o tsv)
az storage container create --name documents --connection-string "$CONN"

echo "$CONN"
```
→ `AZURE_STORAGE_CONNECTION_STRING` (the `echo` value), `AZURE_STORAGE_CONTAINER=documents`.

## 4. Optional services (auth, cache, telemetry)

All optional — the app runs without them (auth off, caching/queue off, no telemetry).

**Google OAuth** (not an Azure resource → [Google Cloud Console](https://console.cloud.google.com)):
APIs & Services → Credentials → Create OAuth client ID → *Web application*. Add your frontend
origin (`http://localhost:3000` for dev) under *Authorized JavaScript origins*. Copy the client ID.
→ `GOOGLE_CLIENT_ID` (backend) **and** `NEXT_PUBLIC_GOOGLE_CLIENT_ID` (frontend) — same value.

**Redis** (caching + ingestion queue) — Azure Cache for Redis:
```bash
REDIS=rag-redis-$RANDOM
az redis create -n $REDIS -g $RG -l $LOC --sku Basic --vm-size c0
KEY=$(az redis list-keys -n $REDIS -g $RG --query primaryKey -o tsv)
echo "rediss://:$KEY@$REDIS.redis.cache.windows.net:6380"   # TLS port 6380
```
→ `REDIS_URL`.

**Application Insights** (OpenTelemetry traces):
```bash
az extension add -n application-insights
APPI=rag-appi-$RANDOM
az monitor app-insights component create --app $APPI -g $RG -l $LOC
az monitor app-insights component show --app $APPI -g $RG --query connectionString -o tsv
```
→ `APPLICATIONINSIGHTS_CONNECTION_STRING`.

## 5. Fill `.env`

```bash
cp .env.example .env   # then paste the values from the steps above
```

## Teardown (avoid charges)

```bash
az group delete -n $RG --yes --no-wait
```
