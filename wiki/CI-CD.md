# CI/CD

[[Home]] > CI/CD

Two GitHub Actions workflows automate ADF validation and deployment. Both are in [`.github/workflows/`](https://github.com/sandersdHES/ADF_DataCycleProject/tree/main/.github/workflows).

A third workflow — SQL schema + security deployment — is prepared but not yet active. See [SQL Deploy (future)](#sql-deploy-future) below.

---

## Workflows at a glance

| Workflow | File | Trigger | What it does |
|---|---|---|---|
| **Validate** | `validate.yml` | Pull request touching `adf/**` | Checks ADF source JSON consistency |
| **Deploy ADF** | `deploy-adf.yml` | Push to `main` touching `adf/**` | Exports ARM from source JSON, deploys to `group3-df` |

---

## `validate.yml` — PR gate

Runs [`Azure/data-factory-validate-action@v1.1.4`](https://github.com/Azure/data-factory-validate-action) against the `adf/` directory on any pull request that touches `adf/**`.

Catches broken cross-references between pipelines, datasets, and linked services before merge.

---

## `deploy-adf.yml` — push to main

Triggered when `adf/**` files change on `main`.

1. **Export ARM** — `Azure/data-factory-export-action@v1.2.1` builds `ARMTemplateForFactory.json` from the source JSON in `adf/`. No `adf_publish` branch required.
2. **Deploy** — `Azure/data-factory-deploy-action@v1.2.0` stops active triggers, deploys the linked-template master (SAS-staged), then restarts triggers.

---

## Authentication — OIDC with User-Assigned Managed Identity

The workflows authenticate to Azure via **OpenID Connect (OIDC)** using a **User-Assigned Managed Identity (UAMI)** named `gh-datacycle-oidc`.

### Why UAMI instead of an App Registration?

An App Registration is an Azure AD tenant object — creating one requires the "Application Developer" role (or Global Admin), which IT departments typically restrict. A UAMI is an **Azure resource** that any subscription Owner can create without IT involvement. `azure/login@v2` supports both identically — the workflow needs no changes if the identity type changes.

### UAMI configuration

The identity `gh-datacycle-oidc` lives in the same resource group as `group3-df` and carries:

- **Contributor** role on the resource group (sufficient for ADF ARM deploys)
- A **federated credential** pinned to `repo:sandersdHES/ADF_DataCycleProject:environment:prod` — only GitHub Actions jobs running under the `prod` environment can request a token for it

The same UAMI is also registered inside ADF as a **credential object** (`adf/credential/gh-datacycle-oidc.json`), which allows ADF linked services to reference it explicitly. `LS_ADLS_Bronze` uses it for OAuth2/RBAC authentication to ADLS Gen2 — no account key needed.

### Create the UAMI (one-time setup)

```bash
RG_NAME=<your-rg>
SUBSCRIPTION_ID=<your-sub-id>

az identity create \
  --name gh-datacycle-oidc \
  --resource-group "$RG_NAME"

CLIENT_ID=$(az identity show \
  --name gh-datacycle-oidc --resource-group "$RG_NAME" --query clientId -o tsv)

PRINCIPAL_ID=$(az identity show \
  --name gh-datacycle-oidc --resource-group "$RG_NAME" --query principalId -o tsv)

az role assignment create \
  --assignee-object-id "$PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RG_NAME"

az identity federated-credential create \
  --name gh-datacycle-prod \
  --identity-name gh-datacycle-oidc \
  --resource-group "$RG_NAME" \
  --issuer "https://token.actions.githubusercontent.com" \
  --subject "repo:sandersdHES/ADF_DataCycleProject:environment:prod" \
  --audiences "api://AzureADTokenExchange"
```

---

## GitHub Environment `prod` — required values

Create under **Settings → Environments → New environment → `prod`**.

### Secrets (scoped to the environment)

| Secret | Value |
|---|---|
| `AZURE_CLIENT_ID` | Client ID (UUID) of the `gh-datacycle-oidc` UAMI |
| `AZURE_TENANT_ID` | Azure AD tenant ID (`az account show --query tenantId -o tsv`) |
| `AZURE_SUBSCRIPTION_ID` | Target subscription ID (`az account show --query id -o tsv`) |

### Variables (plain text — not secrets)

| Variable | Value |
|---|---|
| `AZURE_RESOURCE_GROUP` | Resource group containing `group3-df` |
| `AZURE_ADF_NAME` | `group3-df` |

No SQL credentials are stored in GitHub.

---

## Dependabot

`.github/dependabot.yml` runs **weekly updates** for the GitHub Actions ecosystem, keeping `Azure/data-factory-*-action` pinned versions current.

---

## SQL Deploy (future)

`infrastructure/future/workflows/deploy-sql.yml` is a ready-to-activate workflow that deploys `sql/deploy_schema.sql` then `sql/deploy_security.sql` to DevDB on every push to `main` that touches `sql/**`.

It is **not yet in `.github/workflows/`** because the `gh-datacycle-oidc` UAMI still needs an explicit `Key Vault Secrets User` role assignment on the Key Vault (Key Vault uses a separate RBAC plane — `Contributor` on the resource group does not grant `getSecret`).

### How to activate

1. Grant the UAMI `Key Vault Secrets User` on the vault:

```bash
az role assignment create \
  --assignee-object-id <UAMI_PRINCIPAL_ID> \
  --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets User" \
  --scope "/subscriptions/<SUB_ID>/resourceGroups/<RG>/providers/Microsoft.KeyVault/vaults/DataCycleGroup3Keys"
```

2. Ensure the Azure SQL firewall allows GitHub Actions runner IPs, or enable **Allow Azure services** on the SQL server.

3. Move the workflow file into place:

```bash
mv infrastructure/future/workflows/deploy-sql.yml .github/workflows/deploy-sql.yml
```

The workflow fetches `Admin-SQL-Password` from Key Vault at runtime via the OIDC token — no SQL credentials are stored in GitHub. The `deploy_schema.sql` step includes a 3-attempt retry loop to handle serverless DB resume (can take up to 60 s).

---

## What is NOT in CI

Infrastructure changes (Bicep, Databricks cluster) are not part of day-to-day CI. See [[Infrastructure and IaC]] for the full-rebuild path.

---

*For the secrets consumed at runtime (Key Vault, ADLS), see [[Secrets and Configuration]].*
