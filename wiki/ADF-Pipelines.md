# ADF Pipelines

[[Home]] > ADF Pipelines

---

## Pipeline catalog

| Pipeline | Trigger | Description |
|---|---|---|
| `PL_Ingest_Bronze` | `TRG_Daily_0715` | Master orchestrator — runs all Bronze ingestion then the Silver/Gold ETL chain |
| `PL_Bronze_Solar` | Called by `PL_Ingest_Bronze` | Incremental copy of solar inverter + PV CSVs to `bronze/solar/` |
| `PL_Bronze_Bookings` | Called by `PL_Ingest_Bronze` | Incremental copy of room booking CSVs to `bronze/bookings/` |
| `PL_Bronze_Meteo` | Called by `PL_Ingest_Bronze` | Incremental copy of weather CSVs from SFTP to `bronze/meteo/` |
| `PL_Bronze_Conso` | Called by `PL_Ingest_Bronze` | Incremental copy of conso/temp/humidity CSVs with dynamic subfolder routing |
| `PL_SAC_Export` | Called by `PL_Ingest_Bronze` | Exports Gold views to ADLS then copies to Azure File Share for SAC |
| `Run_Knime` | Called by `PL_Upload_Pred_Gold` | Calls KNIME Server REST deployments in sequence/parallel |
| `PL_Upload_Pred_Gold` | `TRG_Daily_0930` | Triggers KNIME predictions and loads results into `fact_energy_prediction` |
| `PL_Bronze_MeteoFuture` | *(none — orphaned)* | Standalone ingestion for future weather forecasts — not wired into the daily cycle |

---

## Orchestration tree

```
TRG_Daily_0715 ──▶ PL_Ingest_Bronze
                       │
                       ├──▶ PL_Bronze_Solar
                       ├──▶ PL_Bronze_Bookings
                       ├──▶ PL_Bronze_Meteo
                       ├──▶ PL_Bronze_Conso
                       │        (all four complete before proceeding)
                       │
                       ├──▶ Databricks: silver_transformation
                       │
                       ├──▶ Databricks: silver_gold_dimensions  ┐ parallel
                       ├──▶ Databricks: ml_export_to_knime      ┘
                       │
                       ├──▶ Databricks: silver_gold_facts
                       │
                       └──▶ PL_SAC_Export
                                ├──▶ Databricks: sac_export_to_adls
                                └──▶ Copy: sacexport/ → Azure File Share

TRG_Daily_0930 ──▶ PL_Upload_Pred_Gold
                       ├──▶ Run_Knime
                       │       ├── Data_Preparation       (every run)
                       │       ├── Model_Selection        (Mondays only)
                       │       ├── Consumption predictor  ┐ parallel
                       │       └── Solar predictor        ┘
                       └──▶ Databricks: ml_load_predictions
```

---

## Bronze pipeline common shape

All four `PL_Bronze_*` pipelines share an identical incremental-copy pattern:

1. `GetMetadata` — list files in the source directory
2. `GetMetadata` — list files already in the destination Bronze container
3. `Filter` — keep only filenames absent from the destination
4. `ForEach` (batch size 50) → `Copy` — binary copy to `bronze/<area>/`

This pattern ensures files are never re-ingested, even if the pipeline is re-run.

**`PL_Bronze_Conso` addition:** a dynamic expression routes each file to a different Bronze subfolder based on its filename prefix (`consumption/`, `temperature/`, `humidity/`, or `others/`).

---

## Run_Knime — KNIME REST deployments

`Run_Knime` calls the KNIME Server via four HTTP Web activities. The `.knwf` source workflow for each deployment is version-controlled in [`knime/`](https://github.com/sandersdHES/ADF_DataCycleProject/tree/main/knime):

| Step | KNIME Deployment ID | Cadence | Source workflow |
|---|---|---|---|
| `Data_Preparation` | `rest:e481f0fd-89ba-409a-aaa2-d8a648956949` | Every run | `knime/Data_Preparation.knwf` |
| `Model_Selection` | `rest:509f9c76-1fd3-444d-80a6-4df7848b1621` | **Mondays only** — conditional on `@pipeline().TriggerTime.DayOfWeek` | `knime/Model_Selection.knwf` |
| `Consumption predictor` | `rest:348633fa-f10f-4a27-99de-11e1707190cb` | Every run (parallel with Solar) | `knime/REST_Interface_Cons.knwf` |
| `Solar predictor` | `rest:eb96aa91-239b-4cf2-8c7e-a8a40516d4f3` | Every run (parallel with Consumption) | `knime/REST_Interface_Solar.knwf` |

Authentication uses `knime` user + `knimeappid` / `knimeappsecret` pulled from Azure Key Vault.

---

## Linked services

| Name | Type | Endpoint / Target |
|---|---|---|
| `AzureDatabricks` | Databricks (interactive cluster) | Cluster `0223-115927-nvtos4a4` |
| `LS_Databricks_Silver` | Databricks (job cluster) | PAT from Key Vault |
| `LS_ADLS_Bronze` | Azure Data Lake Storage Gen2 | `adlsbellevuegrp3.dfs.core.windows.net` — UAMI `gh-datacycle-oidc` (OAuth2) |
| `LS_DevDB_Gold` | Azure SQL | `sqlserver-bellevue-grp3.database.windows.net` / `DevDB` |
| `LS_AKV` | Azure Key Vault | `DataCycleGroup3Keys` |
| `LS_AzureFileShare_SAC` | Azure File Share | `sac-export-share` |
| `LS_BellevueBooking_LocalServer` | File System (SHIR) | SMB share `BellevueBooking` |
| `LS_BellevueConso_LocalServer` | File System (SHIR) | SMB share `BellevueConso` |
| `LS_Solarlogs_LocalServer` | File System (SHIR) | SMB share `Solarlogs` |
| `LS_SFTP_LocalServer` | SFTP (SHIR) | SFTP server on `10.130.25.152` |

`LS_ADLS_Bronze` authenticates via the `gh-datacycle-oidc` UAMI registered as an ADF credential object (`adf/credential/gh-datacycle-oidc.json`) — OAuth2/RBAC, no account key. All other credentials are stored as ADF `encryptedCredential` blobs or Key Vault references — nothing sensitive is in git.

---

## Triggers

| Trigger | Time (UTC) | Targets |
|---|---|---|
| `TRG_Daily_0715` | 07:15 | `PL_Ingest_Bronze` |
| `TRG_Daily_0930` | 09:30 | `PL_Upload_Pred_Gold` |

---

*For the notebook logic executed within these pipelines, see [[Databricks Notebooks]].*
