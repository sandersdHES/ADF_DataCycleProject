# TODO

Next steps to go live with the slimmed ADF-only CI/CD path.

## 1. Transfer subscription billing ownership

Azure Portal → **Subscription** → **Transfer billing ownership** to the company account.

Everything stays in place — ADLS data, SQL, Databricks workspace, Key Vault secrets, SHIR registration, ADF pipelines. No rebuild needed.

## 2. Wire up the ADF deploy workflow

### Create AAD app + OIDC federated credential

```bash
APP_ID=$(az ad app create --display-name "gh-datacycle-oidc" --query appId -o tsv)
az ad sp create --id "$APP_ID"

# Role on the RG that contains group3-df (Contributor is enough for ADF deploy)
az role assignment create \
  --assignee "$APP_ID" \
  --role "Contributor" \
  --scope "/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RG_NAME>"

az ad app federated-credential create \
  --id "$APP_ID" \
  --parameters '{
    "name": "gh-datacycle-prod",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:<OWNER>/ADF_DataCycleProject:environment:prod",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

### Create GitHub Environment `prod`

Settings → Environments → New environment → `prod`.

**Secrets** (scoped to the environment):

- [ ] `AZURE_CLIENT_ID` — `appId` from the step above
- [ ] `AZURE_TENANT_ID`
- [ ] `AZURE_SUBSCRIPTION_ID`

**Variables** (same environment):

- [ ] `AZURE_RESOURCE_GROUP` — RG containing `group3-df`
- [ ] `AZURE_ADF_NAME` — `group3-df`

## 3. First deploy

Push any change under `adf/**` to `main` (or trigger `Deploy ADF` manually from the Actions tab). Workflow will:

1. Export ARM from `adf/` source JSON
2. Stop triggers, deploy linked-template master, restart triggers

Verify in ADF Studio that `TRG_Daily_0715` and `TRG_Daily_0930` are `Started`.

## 4. Housekeeping (optional, do anytime)

- [ ] Delete `adf/publish_config.json` — the `adf_publish` branch is no longer used
- [ ] Decide whether to consolidate the triplicated tariff (SQL computed columns vs. `ref_electricity_tariff` vs. `config/electricity_tariff_config.json`)
- [ ] Wire `PL_Bronze_MeteoFuture` into `PL_Ingest_Bronze` if future forecasts should flow end-to-end daily (currently orphaned)

## 5. Future (only if we ever need to rebuild from scratch)

See [infrastructure/DEPLOY.md](infrastructure/DEPLOY.md) and [TECHNICAL_GUIDE.md §11](TECHNICAL_GUIDE.md#11-future-proofing--unwired-reproducibility). Nothing to do here now.
