# TODO

Next steps to go live with the slimmed ADF-only CI/CD path.

## 1. Transfer subscription billing ownership

Azure Portal → **Subscription** → **Transfer billing ownership** to the company account.

Everything stays in place — ADLS data, SQL, Databricks workspace, Key Vault secrets, SHIR registration, ADF pipelines. No rebuild needed.

## 2. Wire up the ADF deploy workflow

### Why not an App Registration?

Creating an **App Registration** is an Azure AD tenant operation — it requires the
"Application Developer" role (or Global Admin), which IT departments typically restrict.

### Recommended: User-Assigned Managed Identity (UAMI)

A UAMI is an **Azure resource** (not an Azure AD object). You can create it yourself
with Owner rights on your subscription — no IT involvement needed. `azure/login@v2`
supports it natively; **no workflow changes required**.

#### Step 1 — Create the UAMI and federated credential

```bash
RG_NAME=<your-rg>            # the RG that contains group3-df
SUBSCRIPTION_ID=<your-sub-id>

# Create the identity (Azure resource — no AAD admin needed)
az identity create \
  --name gh-datacycle-oidc \
  --resource-group "$RG_NAME"

# Capture its client ID
CLIENT_ID=$(az identity show \
  --name gh-datacycle-oidc \
  --resource-group "$RG_NAME" \
  --query clientId -o tsv)

# Capture its principal ID (for the role assignment)
PRINCIPAL_ID=$(az identity show \
  --name gh-datacycle-oidc \
  --resource-group "$RG_NAME" \
  --query principalId -o tsv)

# Grant Contributor on the RG (enough for ADF deploy)
az role assignment create \
  --assignee-object-id "$PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RG_NAME"

# Add the federated credential — ties this identity to GitHub Actions + the prod environment
az identity federated-credential create \
  --name gh-datacycle-prod \
  --identity-name gh-datacycle-oidc \
  --resource-group "$RG_NAME" \
  --issuer "https://token.actions.githubusercontent.com" \
  --subject "repo:sandersdHES/ADF_DataCycleProject:environment:prod" \
  --audiences "api://AzureADTokenExchange"
```

> **Output you need:** `CLIENT_ID` from the `az identity show` command above
> (looks like a UUID, e.g. `12345678-abcd-...`). Keep it for the next step.

#### Step 2 — Create GitHub Environment `prod`

Settings → Environments → New environment → **`prod`**.

**Secrets** (scoped to the environment):

- [ ] `AZURE_CLIENT_ID` — the `CLIENT_ID` from Step 1
- [ ] `AZURE_TENANT_ID` — your Azure AD tenant ID (`az account show --query tenantId -o tsv`)
- [ ] `AZURE_SUBSCRIPTION_ID` — your subscription ID (`az account show --query id -o tsv`)

**Variables** (same environment — *not* secrets, plain text is fine):

- [ ] `AZURE_RESOURCE_GROUP` — the RG containing `group3-df`
- [ ] `AZURE_ADF_NAME` — `group3-df`

---

> **Alternative — ask IT (if UAMI creation is also restricted)**
> Ask your IT admin to run the commands in Step 1 and hand back the `CLIENT_ID`.
> Everything in Step 2 you still do yourself. This is a single 10-minute task for them.

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
