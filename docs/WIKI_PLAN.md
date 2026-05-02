# GitHub Wiki — Plan

The wiki lives at `https://github.com/sandersdHES/ADF_DataCycleProject.wiki.git`  
(a separate git repo — do **not** commit wiki pages into this main repo).  
This document is the authoritative blueprint: what every wiki page should contain, which source file to draw from, and which images to embed.

> **Section numbers below refer to `docs/TECHNICAL_GUIDE.md` as it stands today.**  
> A repository-layout section was removed and all sections were renumbered; the numbers here are current.

---

## Page tree

```
Home
├── Onboarding — New Developer / New User
├── Architecture Overview
├── Data Sources
├── ADF Pipelines
│   ├── Pipeline Catalog
│   └── Linked Services
├── Databricks Notebooks
│   └── Silver Table Schemas
├── Data Warehouse Schema
│   ├── Dimensions & Facts
│   └── Analytical Views
├── Security & User Management
├── ML Lifecycle (KNIME Integration)
├── CI/CD
├── Secrets & Configuration
├── Operational Runbook
├── Infrastructure & IaC
├── User Handbook — Solar Inverter Dashboard
├── User Handbook — Room Occupancy Dashboard
├── User Handbook — SAC Dashboard
├── Data Privacy & GDPR
└── Known Limitations & Roadmap
```

---

## Page-by-page breakdown

---

### Home (`Home.md`)

**Purpose:** Landing page — what the project is and where to go next.  
**Source:** `README.md`  
**Content:**
- 2-paragraph project summary: HES-SO Bellevue campus, data types (solar, energy, weather, bookings), goal (medallion lakehouse → dashboards + ML forecasts)
- High-level ASCII pipeline diagram (copy from `README.md`)
- Two daily triggers: 07:15 ingestion cycle / 09:30 ML prediction cycle
- Technology stack table (copy from `README.md` "Key technologies")
- Quick-links table to every other wiki page

---

### Onboarding — New Developer / New User (`Onboarding.md`)

**Purpose:** Step-by-step guide for anyone joining the project for the first time.  
**Source:** `docs/TECHNICAL_GUIDE.md` (multiple sections), `docs/TODO.md`, `sql/provision_user.sql`  
**Content:**

#### For dashboard users (Teachers, Directors, Technicians)
1. Request a SQL login from a project admin (provide your name, role, and school division).
2. Download Power BI Desktop (free) — [powerbi.microsoft.com/desktop](https://powerbi.microsoft.com/desktop).
3. Open the `.pbix` / `.pbit` file for your dashboard from `dashboards/`.
4. Edit the data source connection: **Home → Transform data → Data source settings** → change server to `sqlserver-bellevue-grp3.database.windows.net`, database `DevDB`, authentication type **Database**, enter your SQL login.
5. Refresh — your role automatically filters what you can see (see Security & User Management page).
6. For the SAC dashboard, follow the daily refresh procedure on the SAC User Handbook page.

#### For new developers
1. **Clone the repo:** `git clone https://github.com/sandersdHES/ADF_DataCycleProject.git`
2. **Request Azure access** to:
   - Azure subscription (contact project owner for RBAC assignment)
   - Azure Databricks workspace (add your email as a workspace user)
   - Azure Key Vault (`DataCycleGroup3Keys`) — `Key Vault Secrets User` role minimum
   - Azure SQL `DevDB` — run `sql/provision_user.sql` with `Technician_Role`
3. **Import notebooks into Databricks Repos:**  
   Databricks → Repos → Add repo → paste the GitHub URL → notebooks land at `/Repos/<your-username>/ADF_DataCycleProject/databricks/notebooks/`.
   > ⚠️ ADF pipeline activities reference absolute Repo paths. To test pipeline runs, either re-point the `AzureDatabricks` activities to your path, or clone under the shared service account path.
4. **Set up local tools:**
   - Azure CLI (`az login`) for Key Vault and RBAC operations
   - `sqlcmd` for manual schema deployments (see Operational Runbook page)
   - KNIME Analytics Platform (if working on ML workflows) — import `.knwf` files from `knime/`
5. **Understand the daily cycle** — read the Architecture Overview and ADF Pipelines pages.
6. **Make a change:**
   - ADF changes: edit JSON under `adf/`, open a PR → `validate.yml` runs automatically → merge to `main` → `deploy-adf.yml` deploys to Azure.
   - Notebook changes: edit `.py` files under `databricks/notebooks/`, commit and push — Databricks Repos syncs on next run.
   - SQL changes: edit `sql/deploy_schema.sql` or `sql/deploy_security.sql`, then apply manually with `sqlcmd` (see Operational Runbook).
7. **Pending admin tasks** (from `docs/TODO.md`):
   - Subscription billing transfer to company account (Azure Portal → Subscription → Transfer billing ownership)
   - Delete `adf/publish_config.json` (legacy `adf_publish` branch no longer used)
   - Optionally wire `PL_Bronze_MeteoFuture` into `PL_Ingest_Bronze` for automatic future forecast ingestion

---

### Architecture Overview (`Architecture-Overview.md`)

**Purpose:** Full end-to-end data flow for a technical audience.  
**Source:** `docs/TECHNICAL_GUIDE.md` §1 + §2, `docs/ARCHITECTURE.md`  
**Content:**
- At-a-glance summary table (Pattern, Orchestration, Compute, Storage, Serving, ML, Integration, Alerts, Secrets) — copy from §1
- Link to or embed architecture diagrams from `docs/ARCHITECTURE.md` (Mermaid)
- Medallion layer definitions: Bronze (raw binary copy), Silver (cleaned Parquet), Gold (SQL star schema)
- Trigger schedule: 07:15 `PL_Ingest_Bronze` → 09:30 `PL_Upload_Pred_Gold`
- Storage container map: `bronze/`, `silver/`, `mldata/`, `sacexport/`, `config/`

---

### Data Sources (`Data-Sources.md`)

**Purpose:** Reference for every raw data source entering the pipeline.  
**Source:** `docs/TECHNICAL_GUIDE.md` §3 (subsections §3.1–§3.7)  
**Content:**

Summary table (copy from §3 intro):

| Source | Host | Transport | Path pattern | Encoding |
|---|---|---|---|---|
| Solar inverter logs | On-prem VM | SMB | `\Solarlogs\min*.csv` | UTF-8 |
| Solar aggregated (PV) | On-prem VM | SMB | `\Solarlogs\*-PV.csv` | UTF-16 LE |
| Room bookings | On-prem VM | SMB | `\BellevueBooking\*.csv` (TSV) | UTF-8 |
| Consumption / Temp / Humidity | On-prem VM | SMB | `\BellevueConso\...` | UTF-16 LE |
| Historical weather | On-prem VM | SFTP | `/*.csv` | UTF-8 |
| Future weather forecasts | On-prem VM | SFTP | `/future_forecasts/*.csv` | UTF-8 |

Then one subsection per source (§3.1–§3.7) with the full column tables, encoding quirks, counter-reset / GDPR / Sierre-synthesis notes — copy verbatim from the technical guide.

---

### ADF Pipelines — Pipeline Catalog (`ADF-Pipelines.md`)

**Purpose:** Reference for every pipeline's purpose and dependencies.  
**Source:** `docs/TECHNICAL_GUIDE.md` §4.1–§4.3  
**Content:**
- Orchestration ASCII tree (copy from §4.1)
- Bronze pipeline common shape: GetMetadata → Filter → ForEach Copy — §4.2
- `PL_Bronze_MeteoFuture` orphan note (must be triggered manually)
- `Run_Knime` table: deployment IDs, cadence (Monday-only `Model_Selection`), KNIME auth — §4.3

---

### ADF Pipelines — Linked Services (`ADF-Linked-Services.md`)

**Purpose:** Quick lookup of every integration endpoint.  
**Source:** `docs/TECHNICAL_GUIDE.md` §4.4  
**Content:**
- Linked service table (name, type, endpoint, credential method) — copy from §4.4
- Note: all credentials are AKV references or `encryptedCredential` blobs — none in git

---

### Databricks Notebooks (`Databricks-Notebooks.md`)

**Purpose:** Per-notebook reference — inputs, transformation logic, outputs, and known quirks.  
**Source:** `docs/TECHNICAL_GUIDE.md` §5.1–§5.6 (including all silver table schemas)  
**Content:**

Overview table:

| Notebook | Triggered by | Input | Output |
|---|---|---|---|
| `silver_transformation.py` | `PL_Ingest_Bronze` | `bronze/*` (CSVs) | `silver/*` (Parquet) |
| `silver_gold_dimensions.py` | `PL_Ingest_Bronze` | `silver/*` | SQL dimension tables |
| `silver_gold_facts.py` | `PL_Ingest_Bronze` | `silver/*` | SQL fact tables |
| `ml_export_to_knime.py` | `PL_Ingest_Bronze` | `silver/*` + SQL | `mldata/knime_input/*.csv` |
| `ml_load_predictions.py` | `PL_Upload_Pred_Gold` | `mldata/knime_output/*.csv` | `fact_energy_prediction` |
| `sac_export_to_adls.py` | `PL_SAC_Export` | SQL Gold views | `sacexport/sac_inverter_combined.csv` |

Then one section per notebook — copy from §5.1–§5.6, including:
- §5.1: UTF-16 handling, solar wide→long unpivot (55-column → 1 row/inverter), counter-reset null logic, GDPR SHA-256, Sierre synthesis, **and the full silver table schemas** (all 8 tables with column-level detail)
- §5.2: LEFT ANTI JOIN idempotency, SCD2 for `ref_electricity_tariff`, sentinel `StatusCode=99`
- §5.3: watermark pattern, grain per fact table, FULL OUTER JOIN for `fact_environment`
- §5.4: feature sets for solar and consumption, 3h→15min forward-fill, room occupation computation
- §5.5: DELETE-before-INSERT idempotency, `sp_backfill_prediction_actuals`
- §5.6: Gold views → single coalesced CSV → File Share

---

### Data Warehouse Schema (`Data-Warehouse-Schema.md`)

**Purpose:** Complete reference for the Gold SQL schema consumed by SAC and Power BI.  
**Source:** `docs/TECHNICAL_GUIDE.md` §6.1–§6.3, `sql/deploy_schema.sql`  
**Content:**

**Dimension tables** (key columns):

| Table | Key columns | Notes |
|---|---|---|
| `dim_date` | `DateKey INT` (yyyyMMdd) | `IsAcademicDay`, `IsWeekend`, `Season`, `AcademicYear` |
| `dim_time` | `TimeKey SMALLINT` (min since midnight) | `IsBusinessHour`, `IsLectureHour` |
| `dim_inverter` | `InverterKey`, `InverterID`, `RatedPower_kWp` | `StringCount`, `RoofSection` |
| `dim_inverter_status` | `StatusCode` | Sentinel row: `StatusCode=99 (Unknown)` |
| `dim_weather_site` | `SiteName` | `IsSynthetic=1` for Sierre |
| `dim_measurement_type` | `MeasurementCode` | `IsProductionDriver` flag |
| `dim_division` | `DivisionName`, `SchoolName` | HES-SO schools |
| `dim_room` | `RoomCode`, `Building`, `Floor`, `Wing` | `NominalCapacity` |
| `dim_prediction_model` | `ModelCode` (`PV_PROD_V1`, `CONS_V1`) | `Features`, `TrainingStartDate/EndDate` |
| `ref_electricity_tariff` | `PricePerKwh_CHF`, `EffectiveFrom` | SCD2 — `EffectiveTo=NULL` for current row |

**Fact tables** (grain / computed columns):

| Table | Grain (PK) | Computed columns |
|---|---|---|
| `fact_solar_inverter` | `(DateKey, TimeKey, InverterKey)` | — |
| `fact_solar_production` | `(DateKey, TimeKey)` | `RetailValue_CHF = DeltaEnergy_Kwh × 0.15` |
| `fact_energy_consumption` | `(DateKey, TimeKey)` | `CostCHF = DeltaEnergy_Kwh × 0.15` |
| `fact_environment` | `(DateKey, TimeKey)` | — |
| `fact_weather_forecast` | `(DateKey, TimeKey, SiteKey, MeasurementKey, PredictionHorizon)` | — |
| `fact_room_booking` | Surrogate `BookingKey` | `IsRecurring = RecurrenceStart IS NOT NULL` |
| `fact_energy_prediction` | `(DateKey, TimeKey, ModelKey, PredictionRunDateKey)` | Actuals backfilled by `sp_backfill_prediction_actuals` |

**Analytical views** — copy the full §6.3 per-view sections, including column tables and formulas for all seven views:
- `vw_inverter_status_breakdown`: `PctOfDayReadings` window formula
- `vw_inverter_performance`: `PerformanceRatio = SUM(AcPower_W) / (RatedPower_kWp × 1000 × COUNT(*))`
- `vw_daily_energy_balance`: `SelfSufficiencyRatio`, `NetConsumption_Kwh`
- `vw_building_occupation`: `OccupationPct = TotalBookedMinutes / 720 × 100`
- `vw_kpi_dashboard_home`: five KPI card columns
- `vw_weather_vs_production`: `PredictionHorizon = 0` only; Irradiance + ForecastTemp from weather facts
- `vw_prediction_accuracy`: MAPE = `SUM(|Predicted − Actual|) / SUM(Actual)`

**Tariff note:** `0.15 CHF/kWh` is hard-coded in SQL computed columns AND in `config/electricity_tariff_config.json` AND in `ref_electricity_tariff`. All three must be updated on a tariff change.

---

### Security & User Management (`Security-and-User-Management.md`)

**Purpose:** How multi-user access works and how to provision a new person.  
**Source:** `docs/TECHNICAL_GUIDE.md` §6.1, §6.2  
**Content:**
- No Active Directory: identity modelled with SQL contained users + database roles + Row-Level Security
- Role catalog (copy from §6.1): `Director_Role`, `Teacher_Role`, `Technician_Role` — access scopes and GDPR restriction on Technician
- RLS mechanism: `fn_division_security` + `ref_user_division_access` + `BookingDivisionFilter` security policy
- Provisioning a new user: `sqlcmd` invocation with `USER_NAME`, `USER_PASSWORD`, `USER_ROLE`, `DIVISION_KEY` — copy full example from §6.2
- Operational tasks: rotate password (`ALTER USER … WITH PASSWORD`), revoke (`DROP USER` + delete row from `ref_user_division_access`)
- How Power BI Desktop connects: data source settings → Database authentication → SQL login

---

### ML Lifecycle — KNIME Integration (`ML-Lifecycle.md`)

**Purpose:** End-to-end explanation of the daily ML prediction cycle.  
**Source:** `docs/TECHNICAL_GUIDE.md` §7 (§7.1–§7.3), `config/ml_models_config.json`, `knime/`  

**Images to embed** (copy from `docs/assets/knime/` into the wiki repo):

| Image file | Caption | Section |
|---|---|---|
| `data_preparation_workflow.png` | Data_Preparation workflow (runs every cycle) | §7.1 |
| `model_selection_overview.png` | Model_Selection top-level — 4 algorithms × 2 datasets (Mondays only) | §7.2 |
| `model_selection_rf_detail.png` | Model_Selection — RF learner metanode detail | §7.2 |
| `model_selection_output.png` | Model_Selection — concatenate scores and persist best model | §7.2 |
| `rest_interface_workflow.png` | REST_Interface_Solar / Cons — predictor endpoint | §7.3 |

> ⚠️ The 5 KNIME screenshots still need to be saved as actual image files to `docs/assets/knime/` (folder exists; files are placeholders). Save them from the KNIME Analytics Platform screenshots and commit to the main repo, then copy to the wiki repo.

**Content:**
- Daily cycle numbered steps (copy §7 intro): `ml_export_to_knime` → KNIME Server → `ml_load_predictions`
- §7.1 `Data_Preparation.knwf`: two-path flow (solar + consumption), Rule Engine for domain constraints + image
- §7.2 `Model_Selection.knwf`: 4 algorithms × 2 targets, cross-validation metanodes, RMSE-based winner, model persistence + 3 images
- §7.3 `REST_Interface_Solar/Cons.knwf`: KNIME REST endpoint, ADLS auth, RF Predictor, Container Output JSON + image
- KNIME REST deployment IDs table (copy from §4.3)
- `sp_backfill_prediction_actuals` — how MAPE tracking builds up over time
- Training data window: 2023-02-20 → 2023-04-19 (fixed; see Known Limitations)

---

### CI/CD (`CICD.md`)

**Purpose:** How code changes reach Azure Data Factory.  
**Source:** `docs/TECHNICAL_GUIDE.md` §8 (§8.1–§8.3)  
**Content:**
- Workflow summary table (`validate.yml` / `deploy-adf.yml`)
- `validate.yml`: ADF JSON consistency check on PRs touching `adf/**`
- `deploy-adf.yml`: export ARM → stop triggers → deploy → restart triggers; no `adf_publish` branch needed
- OIDC / UAMI: what `gh-datacycle-oidc` is, federated credential pinned to `environment:prod`
- GitHub Environment `prod` required secrets and variables table (copy from §8.2)
- Dependabot: weekly GitHub Actions version updates

---

### Secrets & Configuration (`Secrets-and-Configuration.md`)

**Purpose:** Inventory of all credentials and runtime config.  
**Source:** `docs/TECHNICAL_GUIDE.md` §9  
**Content:**
- Key Vault secrets table (secret name → consumer) — copy from §9
- ADLS config files: `ml_models_config.json` (model metadata, written back by `ml_load_predictions.py`) and `electricity_tariff_config.json` (`{ "tariff_chf_per_kwh": 0.15 }`)
- GitHub secrets table: OIDC identity values only — no application secrets in GitHub
- Principle: all runtime credentials in Key Vault; nothing sensitive in git

---

### Operational Runbook (`Operational-Runbook.md`)

**Purpose:** Day-to-day operations reference.  
**Source:** `docs/TECHNICAL_GUIDE.md` §11  
**Content:** Copy the full expanded runbook table from §11, which covers:
- Pipeline failure (ADF Monitor + metric alert `ar-pl-ingest-bronze-failed`)
- SHIR offline (VM `10.130.25.152` → IR Configuration Manager)
- KNIME REST 5xx (Server logs + KV secret check)
- KNIME Model_Selection failure (Monday — re-trigger manually; last-known-good model continues)
- SQL serverless auto-retry (no manual action needed)
- Future weather data stale (`PL_Bronze_MeteoFuture` must be triggered manually)
- Silver data gaps due to sensor outage (FULL OUTER JOIN handles it; no action)
- New inverter (auto-inserted by `silver_gold_dimensions.py`)
- New weather station (manual `dim_weather_site` insert)
- SQL schema change (manual `sqlcmd` with `deploy_schema.sql` then `deploy_security.sql`)
- New user provisioning (run `sql/provision_user.sql` — link to Security page)
- Tariff change (three places must stay in sync)

---

### Infrastructure & IaC (`Infrastructure-and-IaC.md`)

**Purpose:** Explain the Bicep IaC path and how to use it if a rebuild is needed.  
**Source:** `docs/TECHNICAL_GUIDE.md` §10, `infrastructure/DEPLOY.md`  
**Content:**
- Current state: manually-provisioned environment; billing transfer pending
- IaC artifact inventory table (copy from §10)
- How to apply SQL DDL manually today: `sqlcmd` commands for `deploy_schema.sql` then `deploy_security.sql` (copy from §10)
- How to activate the SQL CI deploy workflow: two-step UAMI RBAC + move yml file (copy from §10)
- How to rebuild the full environment from scratch: four steps; link to `infrastructure/DEPLOY.md`
- ADF Git config caveat: must be set manually in ADF Studio after any rebuild

---

### User Handbook — Solar Inverter Dashboard (`User-Handbook-Solar-Dashboard.md`)

**Purpose:** End-user guide for the Solar Inverter Operations & Performance Dashboard (Power BI).  
**Source:** `docs/USER_HANDBOOK_DASHBOARD.md` — copy in full  
**Content:**
- Time Frame Selector and Inverter Unit Selector controls
- Production & Environmental Correlation chart
- Historical Production Rankings (Top Days)
- Operational Log & Incident Tracking — status codes and red alert entries
- Efficiency KPI Traffic Light system (thresholds and meaning)
- Quick Diagnostic Procedure (3-step checklist)
- **Connecting Power BI with your own login** — step-by-step for changing data source credentials; link to Security & User Management page

---

### User Handbook — Room Occupancy Dashboard (`User-Handbook-Room-Occupancy.md`)

**Purpose:** End-user guide for the Room Occupancy & Utilization Dashboard (Power BI).  
**Source:** `docs/USER_HANDBOOK_ROOM_OCCUPANCY.md` — copy in full  

**Images to embed** (copy from `docs/assets/room-occupancy/` into the wiki repo):

| Image file | Caption |
|---|---|
| `dashboard-overview.png` | Full dashboard overview |
| `filters-panel.png` | Top Filters panel (WeekOfYear, SchoolName, DayName) |
| `kpi-cards.png` | KPI summary cards |
| `room-occupancy-by-hour.png` | Room Occupancy by Hour heatmap |
| `occupancy-by-day.png` | Occupancy by Day of the Week bar chart |
| `occupancy-over-time.png` | Occupancy Over Time by Division line chart |
| `occupancy-by-week.png` | Occupancy by Week of the Year area chart |
| `top-rooms-by-occupancy.png` | Top Rooms by Occupancy leaderboard |

---

### User Handbook — SAC Dashboard (`User-Handbook-SAC-Dashboard.md`)

**Purpose:** End-user guide for the SAP Analytics Cloud Solar Panel Overview dashboard.  
**Source:** `docs/USER_HANDBOOK_SAC_DASHBOARD.md` — copy in full  
**Content:**
- Dashboard purpose and target audiences (technicians vs. directors)
- Access instructions (SAC login, Stories navigation)
- Filter reference (Date Range, Inverter Name, Status Category)
- Four KPI cards (Failings, Failure Rate, Performance Ratio, Days with Failures)
- Four chart descriptions
- Technician daily check routine and fault investigation procedure
- **Data refresh workflow:** automated schedule + 3-step manual import via Azure Storage Explorer → SAC model
- Glossary of technical terms

---

### Data Privacy & GDPR (`Data-Privacy-GDPR.md`)

**Purpose:** Legal and ethical framework for data processing.  
**Source:** `docs/DATA_PRIVACY_GDPR.md` — copy in full  
**Content:** Legal basis (GDPR Articles 6(1)(e), 89, 6(1)(a)), Privacy by Design, anonymization protocols (SHA-256 on `Professeur` and `Nom de l'utilisateur`), data security measures, data subject rights, retention and disposal policy, declaration of non-commerciality.

---

### Known Limitations & Roadmap (`Known-Limitations.md`)

**Purpose:** Honest inventory of current gaps and planned improvements.  
**Source:** `docs/TECHNICAL_GUIDE.md` §12, `docs/TODO.md`  
**Content:**

Copy the full §12 list (updated), including:
- ADF git config is manual
- Notebook paths are absolute
- `PL_Bronze_MeteoFuture` orphaned
- **`weather_future_forecasts` silver bug** — `df_sierre` (historical) written instead of processed future forecasts
- Booking column rename is positional — silent failure if CSV column order changes
- Tariff triplicated — SQL computed columns, JSON config, SCD2 table
- No lineage in Gold (no `LoadBatchId` / `IngestedAt`)
- Fixed ML training window 2023-02-20 → 2023-04-19
- `publish_config.json` is legacy

**Roadmap / suggested next steps** (from `docs/TODO.md`):
- [ ] Transfer Azure subscription billing ownership
- [ ] Delete `adf/publish_config.json`
- [ ] Wire `PL_Bronze_MeteoFuture` into `PL_Ingest_Bronze`
- [ ] Fix `weather_future_forecasts` silver: apply Sierre-synthesis logic to `df_futureweather_raw`
- [ ] Consolidate tariff to a single source of truth
- [ ] Add `LoadBatchId` to fact tables for audit lineage
- [ ] Extend KNIME training window beyond the 2023-Q1 period

---

## Images summary

All images referenced in wiki pages are stored in the main repo under `docs/assets/`. Copy them into the wiki repo when creating pages.

| Wiki page | Image path in main repo | Status |
|---|---|---|
| ML Lifecycle | `docs/assets/knime/data_preparation_workflow.png` | ⚠️ Folder exists — file must be saved from KNIME screenshot |
| ML Lifecycle | `docs/assets/knime/model_selection_overview.png` | ⚠️ Folder exists — file must be saved from KNIME screenshot |
| ML Lifecycle | `docs/assets/knime/model_selection_rf_detail.png` | ⚠️ Folder exists — file must be saved from KNIME screenshot |
| ML Lifecycle | `docs/assets/knime/model_selection_output.png` | ⚠️ Folder exists — file must be saved from KNIME screenshot |
| ML Lifecycle | `docs/assets/knime/rest_interface_workflow.png` | ⚠️ Folder exists — file must be saved from KNIME screenshot |
| Room Occupancy | `docs/assets/room-occupancy/dashboard-overview.png` | ✅ Present |
| Room Occupancy | `docs/assets/room-occupancy/filters-panel.png` | ✅ Present |
| Room Occupancy | `docs/assets/room-occupancy/kpi-cards.png` | ✅ Present |
| Room Occupancy | `docs/assets/room-occupancy/room-occupancy-by-hour.png` | ✅ Present |
| Room Occupancy | `docs/assets/room-occupancy/occupancy-by-day.png` | ✅ Present |
| Room Occupancy | `docs/assets/room-occupancy/occupancy-by-week.png` | ✅ Present |
| Room Occupancy | `docs/assets/room-occupancy/occupancy-over-time.png` | ✅ Present |
| Room Occupancy | `docs/assets/room-occupancy/top-rooms-by-occupancy.png` | ✅ Present |

To embed images in GitHub Wiki, upload them to the wiki repo (e.g. into `images/knime/`) and reference as:
```markdown
![Caption](images/knime/data_preparation_workflow.png)
```

---

## Wiki creation instructions

1. Enable the Wiki in GitHub repository Settings if not already on.
2. Clone the wiki repo: `git clone https://github.com/sandersdHES/ADF_DataCycleProject.wiki.git`
3. Create one `.md` file per page. The filename becomes the URL slug (spaces → hyphens).
4. `Home.md` is the wiki landing page.
5. Create `_Sidebar.md` for persistent left-hand navigation (see below).
6. Copy images from `docs/assets/` into the wiki repo (e.g. `images/knime/`, `images/room-occupancy/`).
7. Push — changes appear immediately at `https://github.com/sandersdHES/ADF_DataCycleProject/wiki`.

Each page should open with a one-sentence summary and a breadcrumb link back to Home.

---

## Suggested `_Sidebar.md`

```markdown
**[Home](Home)**

**Getting started**
- [Onboarding](Onboarding)

**Architecture & Data**
- [Architecture Overview](Architecture-Overview)
- [Data Sources](Data-Sources)

**Pipeline reference**
- [ADF — Pipeline Catalog](ADF-Pipelines)
- [ADF — Linked Services](ADF-Linked-Services)
- [Databricks Notebooks](Databricks-Notebooks)

**Gold layer**
- [Data Warehouse Schema](Data-Warehouse-Schema)
- [Security & User Management](Security-and-User-Management)

**ML & Forecasting**
- [ML Lifecycle (KNIME)](ML-Lifecycle)

**Operations**
- [CI/CD](CICD)
- [Secrets & Configuration](Secrets-and-Configuration)
- [Operational Runbook](Operational-Runbook)
- [Infrastructure & IaC](Infrastructure-and-IaC)

**User guides**
- [Solar Inverter Dashboard](User-Handbook-Solar-Dashboard)
- [Room Occupancy Dashboard](User-Handbook-Room-Occupancy)
- [SAC Dashboard](User-Handbook-SAC-Dashboard)

**Compliance & Status**
- [Data Privacy & GDPR](Data-Privacy-GDPR)
- [Known Limitations & Roadmap](Known-Limitations)
```
