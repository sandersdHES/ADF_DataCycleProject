# GitHub Wiki — Plan

This document maps the planned GitHub Wiki structure to source material in this repository.
Once created, Wiki pages live at `https://github.com/sandersdHES/ADF_DataCycleProject/wiki`.

---

## Page structure

```
Home
├── Architecture Overview
├── Data Sources
├── ADF Pipelines
│   ├── Pipeline Catalog
│   └── Linked Services
├── Databricks Notebooks
├── Data Warehouse Schema
├── Security & User Management
├── ML Lifecycle (KNIME Integration)
├── CI/CD
├── Secrets & Configuration
├── Operational Runbook
├── Infrastructure & IaC
├── User Handbook — Solar Inverter Dashboard
├── User Handbook — Room Occupancy Dashboard
├── Data Privacy & GDPR
└── Known Limitations & Roadmap
```

---

## Page-by-page breakdown

### Home
**Purpose:** Landing page — what the project is and where to go next.  
**Source:** `README.md`  
**Content:**
- 2-paragraph project summary (campus, data types, goal)
- High-level architecture ASCII diagram
- Quick-links table to all other Wiki pages
- Repository link

---

### Architecture Overview
**Purpose:** Full end-to-end data flow for a technical audience.  
**Source:** `docs/TECHNICAL_GUIDE.md` §2  
**Content:**
- Full architecture diagram (on-prem → ADF → ADLS → Databricks → SQL → SAC/Power BI)
- Medallion layer definitions (Bronze / Silver / Gold) with storage locations and formats
- Trigger schedule timeline (07:15 vs 09:30 cycle)
- Technology stack table (from README)

---

### Data Sources
**Purpose:** Reference for what data enters the pipeline, where it comes from, and encoding quirks.  
**Source:** `docs/TECHNICAL_GUIDE.md` §4  
**Content:**
- Source table (Solar, Bookings, Conso, Meteo, Future Forecasts)
- Transport per source (SMB vs SFTP)
- File format notes (UTF-8 vs UTF-16 LE, TSV separator, date formats)
- SHIR dependency note
- Sierre synthetic weather site explanation

---

### ADF Pipelines — Pipeline Catalog
**Purpose:** Reference for each pipeline's purpose, inputs, outputs, and dependencies.  
**Source:** `docs/TECHNICAL_GUIDE.md` §5; `adf/pipeline/*.json`  
**Content:**
- Orchestration tree diagram (`PL_Ingest_Bronze` → children)
- Per-pipeline table: name, trigger, description, downstream
- Bronze pipeline common shape (GetMetadata → Filter → ForEach Copy)
- `PL_Bronze_MeteoFuture` orphan note
- `Run_Knime` KNIME deployment IDs and cadence (Monday-only Model_Selection)

---

### ADF Pipelines — Linked Services
**Purpose:** Quick lookup of every integration endpoint.  
**Source:** `docs/TECHNICAL_GUIDE.md` §5.4; `adf/linkedService/*.json`  
**Content:**
- Linked service table (name, type, endpoint, credential method)
- Note: all credentials are AKV references or `encryptedCredential` blobs — none in git

---

### Databricks Notebooks
**Purpose:** Per-notebook reference — inputs, outputs, logic, and gotchas.  
**Source:** `docs/TECHNICAL_GUIDE.md` §6; `databricks/notebooks/*.py`  
**Content:**
- Overview table (notebook → ADF pipeline → description)
- One section per notebook:
  - `silver_transformation.py` — UTF-16 handling, solar unpivot, counter-reset, GDPR masking, weather synthesis
  - `silver_gold_dimensions.py` — MERGE pattern, SCD2 for `ref_electricity_tariff`, sentinel status code
  - `silver_gold_facts.py` — watermark pattern, grain per table, JDBC retry backoff
  - `ml_export_to_knime.py` — feature sets, 3-hour → 15-min interpolation, room occupation computation
  - `ml_load_predictions.py` — idempotency (DELETE-before-INSERT), `sp_backfill_prediction_actuals`
  - `sac_export_to_adls.py` — Gold views → single coalesced CSV → File Share

---

### Data Warehouse Schema
**Purpose:** Reference for the Gold layer SQL schema consumed by SAC and Power BI.  
**Source:** `docs/TECHNICAL_GUIDE.md` §7; `sql/deploy_schema.sql`  
**Content:**
- ERD or table list grouped by type (dimensions, facts, reference, views)
- Grain (PK) per fact table
- DateKey / TimeKey integer surrogate explanation
- Computed columns (`RetailValue_CHF`, `CostCHF`, `IsRecurring`)
- Three analytical views (`vw_inverter_status_breakdown`, `vw_inverter_performance`, `vw_prediction_accuracy`)
- Tariff triplification note (SQL vs JSON vs SCD2)
- Naming convention: all columns are English (e.g. `fact_room_booking.Remark`); the French Silver layer is mapped to English at the Gold boundary

> Security objects (roles, RLS, user provisioning) live on the **Security & User Management** page.

---

### Security & User Management
**Purpose:** How multi-user access is implemented in Azure SQL without Active Directory, and how to add a new person.  
**Source:** `docs/TECHNICAL_GUIDE.md` §7.1, §7.2; `sql/deploy_security.sql`; `sql/provision_user.sql`  
**Content:**
- Why no AD: this is a lab environment; identity is modeled entirely with SQL **contained users** + database **roles** + **Row-Level Security**
- Role catalog (table):
  - `Director_Role` — energy + bookings + management KPIs (RLS by division)
  - `Teacher_Role` — reference data, energy/sustainability facts, bookings (RLS by division), dashboard views; excludes weather forecasts, prediction tables, and inverter detail views
  - `Technician_Role` — solar / weather / prediction; **no bookings** (GDPR); bypasses RLS
- RLS mechanism: `fn_division_security` checks `ref_user_division_access` against `USER_NAME()`; security policy `BookingDivisionFilter` filters `fact_room_booking`
- Provisioning a new user with `sql/provision_user.sql` — sqlcmd variables, idempotent re-runs, example invocation for each role
- Operational tasks: rotate password (`ALTER USER … WITH PASSWORD`), revoke access (`DROP USER` + delete `ref_user_division_access` row(s))
- How Power BI Desktop connects per user (Database authentication, edit Data source settings) — link to User Handbook page

---

### ML Lifecycle (KNIME Integration)
**Purpose:** Explain the daily ML prediction cycle end-to-end.  
**Source:** `docs/TECHNICAL_GUIDE.md` §8; `config/ml_models_config.json`; `knime/`  
**Content:**
- Flow diagram: `ml_export_to_knime` → KNIME Server → `ml_load_predictions`
- Two model descriptions (GBT solar, GBT consumption) with training period
- `knime/` workflow source file inventory — mapping each `.knwf` to its REST deployment ID
- KNIME deployment IDs and REST auth pattern
- Monday-only Model_Selection logic
- `sp_backfill_prediction_actuals` — how MAPE tracking works over time
- `ml_models_config.json` write-back behavior

---

### CI/CD
**Purpose:** How code gets from this repo to Azure Data Factory.  
**Source:** `docs/TECHNICAL_GUIDE.md` §9; `.github/workflows/`  
**Content:**
- Workflow summary table (validate.yml / deploy-adf.yml)
- `validate.yml` — what it checks and when it runs
- `deploy-adf.yml` — export → deploy steps, SAS staging, trigger stop/restart
- OIDC / UAMI setup: what `gh-datacycle-oidc` is, how federated credentials work
- GitHub Environment `prod` — required secrets and variables table
- Dependabot policy

---

### Secrets & Configuration
**Purpose:** Inventory of all credentials and runtime configuration, and where each lives.  
**Source:** `docs/TECHNICAL_GUIDE.md` §10; `config/`  
**Content:**
- Key Vault secrets table (secret name → consumer)
- ADLS config files (`ml_models_config.json`, `electricity_tariff_config.json`) — structure and consumers
- GitHub secrets table (OIDC values only — no app secrets in GitHub)
- Principle: all runtime credentials stay in Key Vault; nothing sensitive in git

---

### Operational Runbook
**Purpose:** Day-to-day operations reference for whoever is on-call.  
**Source:** `docs/TECHNICAL_GUIDE.md` §12  
**Content:**
- Event → action table (pipeline failure, SHIR offline, KNIME 5xx, SQL serverless pause, new inverter, new weather station, tariff change)
- ADF Monitor navigation tip
- Metric alert `ar-pl-ingest-bronze-failed` (fires within 1 hour)
- SHIR restart procedure (VM `10.130.25.152` → Integration Runtime Configuration Manager)

---

### Infrastructure & IaC
**Purpose:** Explain the Bicep IaC path and how to use it if a rebuild is ever needed.  
**Source:** `docs/TECHNICAL_GUIDE.md` §11; `infrastructure/DEPLOY.md`  
**Content:**
- Current state: manually-provisioned environment, IaC present but intentionally unwired
- Artifact inventory table (main.bicep, modules, future workflows, deploy_databricks.sh, bacpac)
- How to activate the full IaC path (4 steps)
- Link to [`infrastructure/DEPLOY.md`](../infrastructure/DEPLOY.md) for the full runbook
- ADF Git configuration caveat (must be set manually in ADF Studio)

---

### User Handbook — Solar Inverter Dashboard
**Purpose:** End-user guide for navigating and interpreting the Solar Inverter Operations & Performance Dashboard.  
**Source:** `docs/USER_HANDBOOK_DASHBOARD.md`  
**Content:**
- Data Controls & Navigation (Time Frame Selector, Inverter Unit Selector)
- Production & Environmental Correlation chart explanation
- Historical Production Rankings (Top Days)
- Operational Log & Incident Tracking — status codes and red alert entries
- Efficiency KPI Traffic Light system (thresholds and meaning)
- Quick Diagnostic Procedure (3-step checklist)
- **Connecting Power BI with your own login** — step-by-step for changing the data source credentials in Power BI Desktop, plus what each role (Teacher / Director / Technician) sees; cross-link to the Security & User Management page

---

### User Handbook — Room Occupancy Dashboard
**Purpose:** End-user guide for navigating and interpreting the Room Occupancy & Utilization Dashboard.  
**Source:** `docs/USER_HANDBOOK_ROOM_OCCUPANCY.md`  
**Assets:** `docs/assets/room-occupancy/` (8 dashboard screenshots)  
**Content:**
- Top Filters panel (WeekOfYear, SchoolName, DayName drop-downs)
- KPI summary cards (Occupation Rate Pct, Peak Day Occupation, Total Bookings)
- Room Occupancy by Hour heatmap matrix (colour-coded by red intensity)
- Occupancy by Day of the Week bar chart (interactive cross-filtering)
- Occupancy Over Time by Division line chart with trendline
- Occupancy by Week of the Year area chart (IsAcademicDay legend)
- Top Rooms by Occupancy leaderboard (interactive room filter)
- Quick Reference table of interactive tips

---

### Data Privacy & GDPR
**Purpose:** Legal and ethical framework for data processing in this project.  
**Source:** `docs/DATA_PRIVACY_GDPR.md`  
**Content:**
- Legal basis for processing (GDPR Articles 6(1)(e), 89, 6(1)(a))
- Privacy by Design principles (minimization, purpose limitation, accuracy)
- Anonymization and pseudonymization protocols (PII removal, abstract identifiers)
- Data security measures (secure storage, MFA access control, system integrity)
- Data subject rights (access, rectification, erasure)
- Data retention and disposal policy
- Declaration of non-commerciality

---

### Known Limitations & Roadmap
**Purpose:** Honest inventory of current gaps and planned improvements.  
**Source:** `docs/TECHNICAL_GUIDE.md` §13; `docs/TODO.md`  
**Content:**
- Known limitations table from §13 (ADF git config, absolute notebook paths, orphaned MeteoFuture pipeline, tariff triplification, no lineage in Gold, legacy publish_config.json)
- Items from `TODO.md`
- Suggested next steps (consolidate tariff source of truth, add `LoadBatchId` to facts, wire `PL_Bronze_MeteoFuture` into orchestrator)

---

## Creation instructions

GitHub Wikis do not support automated push from the main repo's CI (they are a separate git repository at `<repo>.wiki.git`). Steps to create:

1. Enable the Wiki on the GitHub repository settings page.
2. Clone the wiki repo: `git clone https://github.com/sandersdHES/ADF_DataCycleProject.wiki.git`
3. Create one `.md` file per page above. The filename becomes the URL slug (e.g. `Architecture-Overview.md`).
4. The file named `Home.md` is the Wiki landing page.
5. Add a `_Sidebar.md` for persistent navigation (mirrors the page tree above).
6. Push — changes appear immediately at the Wiki URL.

Each page should open with a one-sentence summary and a breadcrumb line linking back to Home.
