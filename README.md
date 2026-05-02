# Bellevue Data Cycle — ADF Monorepo

A daily data pipeline that ingests building-energy, solar-production, meteorological, and room-booking data from on-premises sources into an **Azure Medallion Lakehouse**, transforms it with Databricks PySpark notebooks, produces ML-based consumption and solar forecasts via a **KNIME Server**, and delivers analytics-ready data to **SAP Analytics Cloud** and **Power BI**.

> **Built for** the HES-SO Bellevue campus energy-monitoring project.

---

## What this pipeline does

```
On-prem VM (SMB / SFTP)
  ├── Solar inverter logs
  ├── Room bookings
  ├── Energy consumption / temperature / humidity
  └── Meteorological data & future forecasts
           │
           │  Self-Hosted Integration Runtime
           ▼
  Azure Data Factory  ──▶  ADLS Gen2 Bronze  ──▶  Databricks (Silver → Gold)
                                                          │
                                          ┌───────────────┼──────────────────┐
                                          ▼               ▼                  ▼
                                    Azure SQL DWH    KNIME Server    SAP Analytics Cloud
                                    (DevDB Gold)   (GBT forecasts)    + Power BI
```

Two daily triggers drive the cycle:
- **07:15** — `PL_Ingest_Bronze` ingests raw files, runs Silver/Gold ETL, exports to SAC
- **09:30** — `PL_Upload_Pred_Gold` calls KNIME REST endpoints and loads predictions into Gold

---

## Key technologies

| Layer | Technology |
|---|---|
| Orchestration | Azure Data Factory (`group3-df`) |
| Compute | Azure Databricks — 6 PySpark notebooks |
| Storage | ADLS Gen2 (`bronze`, `silver`, `mldata`, `sacexport`, `config`) |
| Serving | Azure SQL serverless Gen5 — `DevDB` |
| ML | KNIME Server — GBT regressors (solar + consumption) — workflow source in `knime/` |
| On-prem connectivity | Self-Hosted Integration Runtime on Windows VM |
| Secrets | Azure Key Vault (`DataCycleGroup3Keys`) |
| CI/CD | GitHub Actions — ADF validate + deploy (OIDC / UAMI) |

---

## Repository structure

```
ADF_DataCycleProject/
│
├── adf/                              # Azure Data Factory source JSON
│   ├── factory/group3-df.json        # Factory definition
│   ├── credential/                   # 1 UAMI credential (gh-datacycle-oidc)
│   ├── linkedService/                # 10 linked services (ADLS, SQL, KV, SHIR, Databricks…)
│   ├── dataset/                      # 19 datasets
│   ├── pipeline/                     # 9 pipelines
│   ├── trigger/                      # 2 daily triggers (07:15 / 09:30)
│   ├── integrationRuntime/           # 1 self-hosted IR
│   └── publish_config.json
│
├── databricks/
│   └── notebooks/                    # 6 PySpark ETL notebooks
│       ├── silver_transformation.py        # Bronze → Silver (UTF-16, unpivot, GDPR)
│       ├── silver_gold_dimensions.py       # Silver → Gold dimension MERGE
│       ├── silver_gold_facts.py            # Silver → Gold facts (incremental watermark)
│       ├── ml_export_to_knime.py           # Feature engineering → KNIME input CSVs
│       ├── ml_load_predictions.py          # KNIME output → fact_energy_prediction
│       └── sac_export_to_adls.py           # Gold views → SAC flat CSV
│
├── knime/                            # KNIME workflow source files (.knwf)
│   ├── Data_Preparation.knwf               # Loads feature CSVs, prepares data for inference
│   ├── Model_Selection.knwf                # Re-evaluates active model version (Mondays only)
│   ├── REST_Interface_Solar.knwf           # Solar production predictor — GBT (PV_PROD_V1)
│   └── REST_Interface_Cons.knwf            # Consumption predictor — GBT (CONS_V1)
│
├── config/                           # Runtime config files (also in ADLS /config/)
│   ├── ml_models_config.json
│   └── electricity_tariff_config.json
│
├── sql/
│   └── deploy_schema.sql             # Idempotent DDL — dims, facts, views, stored procs
│
├── dashboards/
│   └── PowerBy_RoomOccupacy.pbit     # Power BI template — room occupancy
│
├── infrastructure/                   # IaC (Bicep) — wired separately, see docs
│   ├── main.bicep
│   ├── modules/                      # 8 Bicep modules
│   ├── parameters/dev.parameters.json
│   ├── exported/                     # Frozen ARM + Bicep snapshots of current env
│   ├── future/workflows/             # deploy-dev.yml / destroy-dev.yml (unwired)
│   └── DEPLOY.md                     # Full-rebuild runbook
│
├── scripts/
│   └── deploy_databricks.sh          # Idempotent Databricks provisioning
│
├── docs/
│   ├── TECHNICAL_GUIDE.md            # Full architecture & operational reference
│   ├── USER_HANDBOOK_DASHBOARD.md    # End-user guide for the Solar Inverter dashboard
│   ├── USER_HANDBOOK_ROOM_OCCUPANCY.md # End-user guide for the Room Occupancy dashboard
│   ├── DATA_PRIVACY_GDPR.md          # GDPR compliance statement
│   └── TODO.md
│
└── .github/
    ├── workflows/
    │   ├── validate.yml              # PR gate — ADF JSON consistency check
    │   └── deploy-adf.yml            # Push-to-main — ARM export + ADF deploy
    └── dependabot.yml
```

---

## Documentation

- [Technical Guide](docs/TECHNICAL_GUIDE.md) — deep-dive on every component: pipelines, notebooks, SQL schema, ML lifecycle, CI/CD, secrets, IaC, and operational runbook.
- [User Handbook — Solar Inverter Dashboard](docs/USER_HANDBOOK_DASHBOARD.md) — how to navigate and interpret the Solar Inverter Operations & Performance Dashboard.
- [User Handbook — Room Occupancy Dashboard](docs/USER_HANDBOOK_ROOM_OCCUPANCY.md) — how to navigate and interpret the Room Occupancy & Utilization Dashboard.
- [Data Privacy & GDPR Statement](docs/DATA_PRIVACY_GDPR.md) — data protection policies, anonymization protocols, and legal basis for processing.
- [Infrastructure Deploy Runbook](infrastructure/DEPLOY.md) — full from-scratch rebuild procedure (Bicep + OIDC + bacpac + SHIR).
- [Wiki](https://github.com/sandersdHES/ADF_DataCycleProject/wiki) — browsable reference pages: architecture, data sources, pipeline catalog, notebook reference, DWH schema, ML lifecycle, CI/CD, operational runbook, and more.

---

## CI/CD at a glance

| Workflow | Trigger | What it does |
|---|---|---|
| `validate.yml` | Pull request touching `adf/**` | Validates ADF source JSON consistency |
| `deploy-adf.yml` | Push to `main` | Exports ARM from source JSON, deploys to `group3-df` |

Authentication uses a **User-Assigned Managed Identity** (`gh-datacycle-oidc`) via OIDC — no client secrets stored in GitHub. See the [Technical Guide §9](docs/TECHNICAL_GUIDE.md) for setup details.
