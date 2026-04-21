# infrastructure/exported/

**Frozen snapshots of the current production-like Azure environment.** These files are
reference artifacts — they are **not** deployed by the CI/CD pipeline. They exist to:

1. Serve as the source of truth for resource configuration when authoring the Bicep
   modules under `infrastructure/modules/`.
2. Provide a diffable baseline if the new environment ever needs to be compared against
   the original (e.g. to confirm we didn't lose a setting during parameterization).
3. Seed the new `DevDB` with real data on first deploy (via `DataCycleDB.bacpac`).

| File | Origin | Used by |
|------|--------|---------|
| `databricks-rg.bicep` | ARM-export of `databricks-rg-adb-bellevue-grp3-ehdvgodpwoynu`, converted via `az bicep decompile` | Model for `infrastructure/modules/databricks.bicep` networking |
| `main-rg.bicep` | ARM-export of the main project RG, converted via `az bicep decompile` | Model for `key_vault.bicep`, `storage.bicep`, `sql.bicep`, `monitoring.bicep` |
| `adf-arm-snapshot/` | `arm_template.zip` from ADF Studio Publish | Reference only — the deployed ARM is re-generated in CI via `Azure/data-factory-export-action` |
| `DataCycleDB.bacpac` | `sqlpackage /Action:Export` from `sqlserver-bellevue-grp3.DevDB` | Imported on first deploy by `deploy-dev.yml` when `dbo.sys.tables` is empty |

## Do not edit these files

If the production environment changes and you want the new baseline reflected, re-export
and replace the files wholesale — don't hand-edit them. The actual deploy modules live
under `infrastructure/modules/` and are parameterized; this folder stays verbatim so
diffs remain meaningful.
