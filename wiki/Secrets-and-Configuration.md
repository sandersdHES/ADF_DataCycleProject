# Secrets and Configuration

[[Home]] > Secrets and Configuration

---

## Principle

All runtime credentials live in **Azure Key Vault** (`DataCycleGroup3Keys`). Nothing sensitive is stored in git or GitHub secrets. GitHub secrets contain only OIDC identity values (client/tenant/subscription IDs) — no application passwords.

---

## Azure Key Vault — `DataCycleGroup3Keys`

Accessed by:
- **ADF** via the `LS_AKV` linked service (Key Vault reference pattern)
- **Databricks** via the `keyvault-scope` secret scope
- **CI `deploy-sql` job** via the OIDC token at deploy time

| Secret name | Consumer | Purpose |
|---|---|---|
| `Databricks-Access-Token` | ADF `LS_Databricks_Silver` | PAT for the Databricks job-cluster linked service |
| `adls-access-key` | All gold-writing notebooks | ADLS account key (used for JDBC writes where OAuth isn't wired) |
| `Admin-SQL-Password` | All gold-writing notebooks, `LS_DevDB_Gold`, CI `deploy-sql` job | Azure SQL admin password — also used as the `dev.admin.sql` contained user password on fresh deploys |
| `Admin-VM-Password` | `LS_BellevueBooking_LocalServer`, `LS_BellevueConso_LocalServer`, `LS_Solarlogs_LocalServer`, `LS_SFTP_LocalServer` | On-prem VM admin credential |
| `Student-VM-Password` | Same linked services | On-prem VM student credential |
| `knime` | `Run_Knime` Web activities | KNIME Server username |
| `knimeappid` | `Run_Knime` Web activities | KNIME application ID |
| `knimeappsecret` | `Run_Knime` Web activities | KNIME application secret |
| `sacpassword` | `LS_AzureFileShare_SAC` | SAC Azure File Share connection password |

---

## ADLS configuration files

Stored in the `config/` container of `adlsbellevuegrp3`. Also version-controlled in [`config/`](https://github.com/sandersdHES/ADF_DataCycleProject/tree/main/config) in this repo.

### `ml_models_config.json`

Stores metadata for the two ML models (`PV_PROD_V1`, `CONS_V1`): model name, version, feature list, and notes.

- **Read** by `silver_gold_dimensions.py` to seed / update `dim_prediction_model`
- **Written back** by `ml_load_predictions.py` whenever KNIME reports new feature metadata

### `electricity_tariff_config.json`

```json
{ "tariff_chf_per_kwh": 0.15 }
```

Read by `silver_gold_dimensions.py` to seed `ref_electricity_tariff`. The SQL computed columns (`RetailValue_CHF`, `CostCHF`) currently use a hard-coded `0.15` literal — all three sources must be updated together on a tariff change. See [[Known Limitations and Roadmap]].

---

## GitHub Environment `prod` — OIDC values only

| Secret | Content |
|---|---|
| `AZURE_CLIENT_ID` | Client ID of the `gh-datacycle-oidc` UAMI |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Target subscription ID |

These are OIDC token request parameters — not application credentials. The `deploy-sql` CI job uses these to authenticate and then fetches `Admin-SQL-Password` from Key Vault at runtime. See [[CI-CD]] for the full setup.

---

## ADF linked service credentials

ADF linked services use one of two patterns:

- **`encryptedCredential`** — credential encrypted by ADF and stored in the linked service JSON. Cannot be read back in plaintext; rotation requires re-entering in ADF Studio.
- **Key Vault reference** — linked service references a Key Vault secret by name via `LS_AKV`. Rotation is done by updating the secret value in Key Vault; no ADF change needed.

Neither pattern stores credentials in git.

---

## SQL security objects

Roles, the base contained user, and RLS are deployed from `sql/deploy_security.sql`. Per-person users are added with `sql/provision_user.sql`. See **[[Security and User Management]]** for the full model.

The `ref_user_division_access` table (Director / Teacher ↔ DivisionKey mapping for RLS) is **not populated by CI**. The `provision_user.sql` script writes one row each time a Director or Teacher is onboarded — administrators run it per person, outside the CI pipeline. Initial passwords passed to that script are not stored in git or Key Vault; communicate them out-of-band and rotate via `ALTER USER … WITH PASSWORD` after first login.
