# Infrastructure and IaC

[[Home]] > Infrastructure and IaC

---

## Current state

The project currently runs on a **manually-provisioned Azure environment**. All IaC artifacts exist in the repo but are **intentionally unwired** from CI — they serve as a door to full reproducibility without adding day-to-day cost or risk.

---

## IaC artifact inventory

| Artifact | Location | Status |
|---|---|---|
| Bicep (subscription-scoped entry point) | `infrastructure/main.bicep` | Present, not wired to CI |
| Bicep modules (8) | `infrastructure/modules/` | Present |
| Dev parameters | `infrastructure/parameters/dev.parameters.json` | Present |
| Full-deploy workflow | `infrastructure/future/workflows/deploy-dev.yml` | Moved out of `.github/workflows/` — does not auto-trigger |
| Teardown workflow | `infrastructure/future/workflows/destroy-dev.yml` | Same — reference only |
| Databricks provisioner | `scripts/deploy_databricks.sh` | Idempotent; consumed by the unwired `deploy-dev.yml` |
| SQL DDL | `sql/deploy_schema.sql` | Idempotent — safe to run standalone on a fresh DB |
| Bacpac seed | `infrastructure/exported/DataCycleDB.bacpac` | One-shot data load for a fresh DB |
| ARM snapshots | `infrastructure/exported/adf-arm-snapshot/` | Frozen exports of current prod env for diffing |
| Bicep reverse-exports | `infrastructure/exported/main-rg.bicep`, `databricks-rg.bicep` | Frozen snapshots |
| Full runbook | `infrastructure/DEPLOY.md` | Step-by-step from-scratch rebuild procedure |

---

## Bicep modules

| Module | Resource |
|---|---|
| `data_factory.bicep` | Azure Data Factory |
| `databricks_workspace.bicep` | Databricks workspace |
| `key_vault.bicep` | Azure Key Vault |
| `monitoring.bicep` | Action Group + metric alert |
| `resource_groups.bicep` | Resource group definitions |
| `role_assignments.bicep` | RBAC assignments |
| `sql.bicep` | Azure SQL server + database |
| `storage.bicep` | ADLS Gen2 storage account |

---

## How to activate the IaC path

Should the project ever need to rebuild from scratch (new tenant, DR drill, parallel prod):

1. Move `infrastructure/future/workflows/*.yml` into `.github/workflows/`
2. Create a GitHub Environment `dev` with the secrets documented in [`infrastructure/DEPLOY.md`](https://github.com/sandersdHES/ADF_DataCycleProject/blob/main/infrastructure/DEPLOY.md)
3. Create a UAMI (or AAD app) + OIDC federated credential scoped to the `dev` environment (same pattern as the `prod` UAMI in [[CI-CD]])
4. Trigger `deploy-dev.yml` once — it provisions the full stack, runs `deploy_databricks.sh`, deploys ADF, and imports the bacpac
5. Complete the two post-deploy manual steps (ADF git integration + SHIR registration)
6. Verify, then tear down with `destroy-dev.yml`

Cost: well under $1 for a full deploy + verify + teardown cycle.

---

## Post-deploy manual steps (always required)

These two steps cannot be automated due to a circular dependency (ADF git integration) or physical access (SHIR):

1. **ADF git integration** — ADF Studio → Manage → Git configuration → point at the `main` branch, `adf/` root folder. Bicep cannot set `repoConfiguration` without creating a circular dependency with this repo.

2. **SHIR registration** — Copy the SHIR auth key from the `post-deploy-summary` step in the deploy workflow (printed to `$GITHUB_STEP_SUMMARY`). On Windows VM `10.130.25.152`, open **Microsoft Integration Runtime Configuration Manager** and register the node with this key.

---

## Known infrastructure limitations

- **ADF Git integration is manual.** See above.
- **Notebook paths are absolute.** `DatabricksNotebook` activities reference `/Repos/<user>/ADF_DataCycleProject/...`. `scripts/deploy_databricks.sh` creates the Repo under `/Repos/${DATABRICKS_USER}/` — the `DATABRICKS_USER` secret must match the paths in the pipeline JSON, or the paths must be updated in ADF Studio after first deploy.
- **`dim_date` / `dim_time` populators** are not included in the automated deploy — the DDL creates shells only. Populate separately.

See also [[Known Limitations and Roadmap]] for application-layer limitations.

---

*For the full step-by-step runbook, see [`infrastructure/DEPLOY.md`](https://github.com/sandersdHES/ADF_DataCycleProject/blob/main/infrastructure/DEPLOY.md).*
