# Bellevue Data Cycle — Wiki

A daily data pipeline that ingests building-energy, solar-production, meteorological, and room-booking data from on-premises sources at the HES-SO Bellevue campus into an **Azure Medallion Lakehouse**, transforms it with Databricks, produces ML-based consumption and solar forecasts via **KNIME Server**, and delivers analytics-ready data to **SAP Analytics Cloud** and **Power BI**.

---

## At a glance

| Dimension | Value |
|---|---|
| Pattern | Medallion lakehouse (Bronze → Silver → Gold) |
| Orchestration | Azure Data Factory — 9 pipelines, 2 daily triggers |
| Compute | Azure Databricks — 6 PySpark notebooks |
| Storage | ADLS Gen2 (`bronze`, `silver`, `mldata`, `sacexport`, `config`) |
| Serving | Azure SQL serverless Gen5 (`DevDB`) |
| ML | KNIME Server — GBT regressors for solar + consumption |
| On-prem link | Self-Hosted Integration Runtime on Windows VM `10.130.25.152` |
| Secrets | Azure Key Vault (`DataCycleGroup3Keys`) |
| CI/CD | GitHub Actions — OIDC / User-Assigned Managed Identity |

---

## Daily pipeline diagram

```
On-prem VM (SMB / SFTP)
  ├── Solar inverter logs (5-min, 5 inverters)
  ├── Room bookings (weekly TSV)
  ├── Energy consumption / temperature / humidity (15-min)
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

## Wiki pages

| Page | What you'll find |
|---|---|
| [[Onboarding]] | Step-by-step for new dashboard users and new developers |
| [[Architecture Overview]] | End-to-end data flow diagram, Medallion layers, trigger schedule |
| [[Data Sources]] | Source inventory, file formats, column tables, encoding quirks |
| [[ADF Pipelines]] | Pipeline catalog, orchestration tree, linked services |
| [[Databricks Notebooks]] | Per-notebook reference — inputs, Silver schemas, key logic, outputs |
| [[Data Warehouse Schema]] | Gold SQL schema, fact grains, computed columns, analytical views |
| [[Security and User Management]] | Roles, RLS, per-user provisioning (Teacher / Director / Technician) |
| [[ML Lifecycle]] | KNIME integration, model details, daily prediction cycle, workflow screenshots |
| [[CI-CD]] | GitHub Actions workflows, OIDC / UAMI setup |
| [[Secrets and Configuration]] | Key Vault inventory, ADLS config files |
| [[Operational Runbook]] | Day-to-day ops, alert triage, on-call reference |
| [[Infrastructure and IaC]] | Bicep modules, full-rebuild path |
| [[User Handbook — Solar Dashboard]] | End-user guide for the Solar Inverter Operations & Performance dashboard |
| [[User Handbook — Room Occupancy]] | End-user guide for the Room Occupancy & Utilization dashboard |
| [[User Handbook — SAC Dashboard]] | End-user guide for the SAP Analytics Cloud Solar Panel Overview dashboard |
| [[Data Privacy & GDPR]] | GDPR compliance, SHA-256 anonymization, legal basis |
| [[Known Limitations and Roadmap]] | Current gaps, housekeeping backlog, roadmap |

---

## Repository

Source code: [sandersdHES/ADF_DataCycleProject](https://github.com/sandersdHES/ADF_DataCycleProject)

Deep-dive reference: [Technical Guide](https://github.com/sandersdHES/ADF_DataCycleProject/blob/main/docs/TECHNICAL_GUIDE.md)
