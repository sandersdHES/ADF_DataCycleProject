# ADF_DataCycleProject — Deployment runbook

End-to-end deploy of the `dev` environment via GitHub Actions + OIDC.

The workflow deploys a full, ephemeral stack (ADF + ADLS + SQL + Key Vault + Databricks + monitoring), smoke-tests it, then tears it back down to $0 via [`destroy-dev.yml`](../.github/workflows/destroy-dev.yml). Round-trip cost for a deploy + verify + teardown is well under $1.

---

## Prerequisites

- Azure subscription with `Owner` rights (needed for the role assignments the Bicep creates)
- GitHub repo admin rights
- Locally installed for manual operations only (the CI path needs none of these):
  - Azure CLI ≥ 2.61
  - Bicep CLI (`az bicep install`)
  - Databricks CLI ≥ 0.200
  - `sqlpackage` (for manual bacpac work)

---

## One-time setup

### 1. Create the AAD app + federated credential (OIDC)

```bash
# 1. Create the app registration
APP_ID=$(az ad app create --display-name "gh-datacycle-oidc" --query appId -o tsv)
SP_ID=$(az ad sp create --id "$APP_ID" --query id -o tsv)

# 2. Grant Owner on the subscription (needed because Bicep issues role assignments)
az role assignment create \
  --assignee "$APP_ID" \
  --role "Owner" \
  --scope "/subscriptions/<SUBSCRIPTION_ID>"

# 3. Federated credential for the dev environment
az ad app federated-credential create \
  --id "$APP_ID" \
  --parameters '{
    "name": "gh-datacycle-dev",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:<OWNER>/ADF_DataCycleProject:environment:dev",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

### 2. Create GitHub Environment `dev` and add secrets

Settings → Environments → New environment → `dev`. Add the following secrets (scoped to the environment):

| Secret | Purpose |
|---|---|
| `AZURE_CLIENT_ID` | `appId` of the OIDC app registration |
| `AZURE_TENANT_ID` | AAD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Target subscription |
| `SQL_ADMIN_PASSWORD` | Bootstrap password for SQL admin login (also used by the bacpac import step) |
| `DATABRICKS_TOKEN` | PAT with workspace-admin rights — used by CLI, ADF linked service `AzureDatabricks`, and `LS_Databricks_Silver` |
| `ADLS_ACCOUNT_KEY` | Storage account key wired into ADF linked service `LS_ADLS_Bronze` |
| `SAC_CONNECTION_STRING` | Azure File Share connection string for `LS_AzureFileShare_SAC` |
| `DATABRICKS_USER` | Email under `/Repos/<user>/` — must match the paths referenced by ADF `DatabricksNotebook` activities |
| `ADMIN_VM_PASSWORD` | Seeded into KV secret `Admin-VM-Password` |
| `ON_PREM_VM_PASSWORD` | Seeded into KV secret `Student-VM-Password` |
| `KNIME_SECRET`, `KNIME_APP_ID`, `KNIME_API_SECRET`, `SAC_PASSWORD` | Seeded into KV secrets |

---

## Deploy

Either push a change to `main` under `infrastructure/**`, `adf/**`, `sql/**`, `config/**`, `databricks/**`, or `scripts/**`, **or** trigger `deploy-dev.yml` manually from the Actions tab.

Pipeline order:

1. **provision-azure** — `azure/arm-deploy@v2` runs `infrastructure/main.bicep` at subscription scope. Uploads `config/*.json` to the `config` container.
2. **provision-databricks** — runs `scripts/deploy_databricks.sh` to create secret scope, cluster, and Repo. Emits cluster ID.
3. **deploy-adf** — `Azure/data-factory-export-action` builds ARM from source JSON, then `Azure/data-factory-deploy-action` deploys it (handles trigger stop/start and SAS staging automatically).
4. **deploy-sql** — if the DB has no tables, imports `infrastructure/exported/DataCycleDB.bacpac` via `sqlpackage`. Always runs `sql/deploy_schema.sql` (idempotent).
5. **post-deploy-summary** — writes ADF/SQL/Databricks URLs and the SHIR auth key to `$GITHUB_STEP_SUMMARY`.

---

## Post-deploy manual steps

Done once per fresh environment:

- **ADF git integration** — open ADF Studio → Manage → Git configuration → point at the repo `main` branch, `adf/` folder. Not Bicep-managed (circular dep).
- **Install SHIR** — copy the auth key from the deploy summary and register the on-prem Windows VM's Self-hosted Integration Runtime node against it.
- **Verify triggers** — `TRG_Daily_0715` and `TRG_Daily_0930` should be `Started` (the deploy action starts them back up at the end).

---

## Local manual deploy (optional)

Not the recommended path, but for quick iteration:

```bash
az deployment sub create \
  --name "datacycle-dev-$(date -u +%s)" \
  --location switzerlandnorth \
  --template-file infrastructure/main.bicep \
  --parameters infrastructure/parameters/dev.parameters.json \
  --parameters @.env.dev.json
```

`.env.dev.json` is gitignored and holds the secret-param overrides locally.

---

## Teardown (primary path)

Actions → **Destroy (dev)** → Run workflow → type `DESTROY` in the confirm field → Run.

The workflow:

1. Deletes `datacycle-rg-dev` (async).
2. Deletes the Databricks managed RG (auto-named, defaults to `databricks-rg-datacycle-dev`).
3. Purges soft-deleted `kv-datacycle-dev` so the name can be reused on the next deploy.

Verify with `az group show -n datacycle-rg-dev` — expect `NotFound` after a few minutes.

### Manual fallback

```bash
az group delete --name datacycle-rg-dev --yes --no-wait
az group delete --name databricks-rg-datacycle-dev --yes --no-wait
az keyvault purge --name kv-datacycle-dev --location switzerlandnorth
```

---

## Adding `prod` later

1. Duplicate `parameters/dev.parameters.json` → `parameters/prod.parameters.json` with new names (`datacycle-rg-prod`, `kv-datacycle-prod`, etc.).
2. Create a GitHub Environment `prod` with required reviewers + secret values.
3. Create an additional federated credential on the AAD app with subject `repo:<OWNER>/ADF_DataCycleProject:environment:prod`.
4. Add `.github/workflows/deploy-prod.yml` triggered on a tag (e.g. `v*.*.*`) mirroring `deploy-dev.yml` but with `environment: prod` and the prod parameters file.

---

## Known limitations

- **Notebook absolute paths.** ADF `DatabricksNotebook` activities reference absolute paths under `/Repos/<user>/ADF_DataCycleProject/...`. `scripts/deploy_databricks.sh` creates the Repo under `/Repos/${DATABRICKS_USER}/`, so that secret must be set to a user whose path matches the pipelines; otherwise the notebook paths must be updated in ADF Studio after first deploy.
- **ADF git integration is manual.** Setting `repoConfiguration` in Bicep would create a circular dep with this repo.
- **`adf/publish_config.json`** is now unused (ARM is built in CI from source JSON — no `adf_publish` branch). Safe to remove in a follow-up PR.
- **`dim_date` / `dim_time` populators.** The DDL creates the shells; populating is handled by a separate process (see `databricks/notebooks/silver_gold_dimensions.py` comments referencing `step1a_calculated_dimensions.sql`).
