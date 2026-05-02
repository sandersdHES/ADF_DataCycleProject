# Architecture Overview

[[Home]] > Architecture Overview

---

## End-to-end data flow

```
 On-prem Windows VM (10.130.25.152)
 ├── SMB shares: BellevueBooking, BellevueConso, Solarlogs
 └── SFTP: meteo + future forecasts
          │
          │  Self-Hosted Integration Runtime (Group3-VM-Runtime)
          ▼
 Azure Data Factory (group3-df)
   │
   ├── 07:15 → PL_Ingest_Bronze              ← master orchestrator
   │     ├── PL_Bronze_Solar                   copy inverter + PV CSVs → bronze/solar/
   │     ├── PL_Bronze_Bookings                copy booking CSVs      → bronze/bookings/
   │     ├── PL_Bronze_Meteo                   copy weather CSVs      → bronze/meteo/
   │     ├── PL_Bronze_Conso                   copy conso/temp/hum    → bronze/consumption|temperature|humidity/
   │     ├── Databricks: silver_transformation         bronze/ → silver/ (Parquet)
   │     ├── Databricks: silver_gold_dimensions  ┐
   │     ├── Databricks: ml_export_to_knime      ┘ (parallel)
   │     ├── Databricks: silver_gold_facts
   │     └── PL_SAC_Export
   │           ├── Databricks: sac_export_to_adls    Gold views → sacexport/
   │           └── Copy CSV → Azure File Share (sac-export-share)
   │
   └── 09:30 → PL_Upload_Pred_Gold
         ├── Run_Knime
         │     ├── Data_Preparation        (every run)
         │     ├── Model_Selection         (Mondays only)
         │     ├── Consumption predictor   (parallel)
         │     └── Solar predictor         (parallel)
         └── Databricks: ml_load_predictions    KNIME output → fact_energy_prediction
```

---

## Medallion layers

| Layer | Storage | Format | Owner |
|---|---|---|---|
| **Bronze** | ADLS Gen2 `bronze/` container | Raw binary / CSV (unchanged from source) | ADF Copy activities |
| **Silver** | ADLS Gen2 `silver/` container | Parquet (cleaned, deduplicated) | `silver_transformation.py` |
| **Gold** | Azure SQL `DevDB` (serverless Gen5) | Relational DWH — star schema | `silver_gold_dimensions.py`, `silver_gold_facts.py` |
| **ML data** | ADLS Gen2 `mldata/` container | CSV (features in, predictions out) | `ml_export_to_knime.py` / KNIME |
| **SAC export** | ADLS Gen2 `sacexport/` + Azure File Share | Flat CSV | `sac_export_to_adls.py` |

---

## Trigger schedule

```
00:00 ─────────────────────────────────────────────────────── 24:00
                │                         │
              07:15                      09:30
         PL_Ingest_Bronze          PL_Upload_Pred_Gold
         (~30–40 min)               (~10–15 min)
         Ingest + ETL              KNIME predictions
         + SAC export              + Gold load
```

The gap between 07:15 and 09:30 gives `ml_export_to_knime.py` time to write its feature CSVs to `mldata/knime_input/` before the KNIME REST calls begin.

---

## Technology stack

| Layer | Technology | Notes |
|---|---|---|
| Orchestration | Azure Data Factory (`group3-df`) | 9 pipelines, 10 linked services, 2 triggers |
| Compute | Azure Databricks | 6 PySpark notebooks via Databricks Repos |
| Raw storage | ADLS Gen2 (`adlsbellevuegrp3`) | 5 containers |
| Serving layer | Azure SQL serverless Gen5 (`DevDB`) | Star schema, JDBC writes from Databricks |
| ML inference | KNIME Server (REST deployments) | GBT regressors, 4 deployments |
| On-prem bridge | Self-Hosted Integration Runtime | Windows VM, SMB + SFTP |
| Secrets | Azure Key Vault (`DataCycleGroup3Keys`) | Accessed by ADF + Databricks secret scope |
| Analytics | SAP Analytics Cloud + Power BI | Consume Gold views and File Share CSV |
| CI/CD | GitHub Actions | OIDC / UAMI, no stored secrets |

---

*For the full pipeline-by-pipeline breakdown, see [[ADF Pipelines]]. For notebook logic, see [[Databricks Notebooks]].*
