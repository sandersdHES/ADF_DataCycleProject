# ADF_DataCycleProject — Monorepo

This repository consolidates all pipeline code for the Bellevue HES-SO data cycle project into a single monorepo.

## Repository Structure

```
ADF_DataCycleProject/
│
├── adf/                          # Azure Data Factory artifacts
│   ├── dataset/                  # ADF dataset definitions (26 files)
│   ├── factory/                  # ADF factory definition
│   ├── integrationRuntime/       # Self-hosted integration runtime configs
│   ├── linkedService/            # ADF linked service definitions (11 files)
│   ├── pipeline/                 # ADF pipeline definitions (9 files)
│   └── trigger/                  # ADF schedule triggers
│
├── databricks/                   # Databricks notebooks & config
│   ├── notebooks/                # PySpark ETL notebooks
│   │   ├── silver_transformation.py      # Bronze → Silver ETL
│   │   ├── silver_gold_dimensions.py     # Silver → Gold dimensions (MERGE)
│   │   ├── silver_gold_facts.py          # Silver → Gold fact tables (incremental)
│   │   ├── ml_export_to_knime.py         # Feature engineering → KNIME CSV export
│   │   ├── ml_load_predictions.py        # KNIME predictions → Gold DWH
│   │   └── sac_export_to_adls.py         # Gold views → SAP Analytics Cloud CSV
│   ├── cluster_configs/          # Databricks cluster configuration files
│   └── jobs/                     # Databricks job definitions
│
├── infrastructure/               # IaC templates (ARM / Bicep / Terraform)
├── sql/                          # Azure SQL DDL scripts (tables, views, procedures)
├── scripts/
│   └── export/                   # Utility export scripts
├── .github/
│   └── workflows/                # CI/CD GitHub Actions workflows
├── docs/                         # Project documentation
│
├── publish_config.json           # ADF Git integration config (root — required by ADF)
└── README.md
```

## Components

### Azure Data Factory (`adf/`)
All ADF factory artifacts (pipelines, datasets, linked services, triggers, integration runtimes) are stored under `adf/`. After merging, reconfigure ADF Studio Git integration to use `/adf` as the root folder.

**Pipelines:**
- `PL_Ingest_Bronze` — Main orchestrator: ingests all raw sources into Bronze layer, then triggers Silver/Gold transformation via Databricks
- `PL_Bronze_Bookings`, `PL_Bronze_Conso`, `PL_Bronze_Meteo`, `PL_Bronze_MeteoFuture`, `PL_Bronze_Solar` — Source-specific Bronze ingestion
- `PL_SAC_Export` — Exports Gold views to ADLS for SAP Analytics Cloud
- `PL_Upload_Pred_Gold` — Loads KNIME ML predictions into Gold DWH
- `Run_Knime` — Triggers KNIME workflow execution

### Databricks Notebooks (`databricks/notebooks/`)
PySpark notebooks executed by ADF via the Databricks linked service. Notebook paths reference this monorepo under `/Repos/dylan.sanderso@hes-so.ch/ADF_DataCycleProject/databricks/notebooks/`.

| Notebook | ADF Pipeline | Description |
|---|---|---|
| `silver_transformation.py` | `PL_Ingest_Bronze` | Bronze → Silver ETL (UTF-16, solar unpivot, GDPR masking) |
| `silver_gold_dimensions.py` | `PL_Ingest_Bronze` | Populates Gold dimension tables via MERGE |
| `silver_gold_facts.py` | `PL_Ingest_Bronze` | Incremental load of Gold fact tables via watermark |
| `ml_export_to_knime.py` | `PL_Ingest_Bronze` | Feature engineering for US#29 / US#30 ML models |
| `ml_load_predictions.py` | `PL_Upload_Pred_Gold` | Loads KNIME predictions into `fact_energy_prediction` |
| `sac_export_to_adls.py` | `PL_SAC_Export` | Exports Gold views to flat CSV for SAC upload |

## Post-Merge ADF Studio Steps

1. In ADF Studio → **Manage → Git configuration**, change the **Root folder** from `/` to `/adf`
2. Verify all pipelines, datasets and linked services are visible
3. Update the Databricks Repos path in your workspace to point to this monorepo

## Data Architecture

```
Bronze (ADLS)  →  Silver (ADLS Parquet)  →  Gold (Azure SQL DWH)  →  SAC / Power BI
     ↑                    ↑                         ↑
  ADF Copy            Databricks               Databricks
  Activities          PySpark ETL              JDBC append
```
