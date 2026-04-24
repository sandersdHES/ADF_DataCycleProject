# ADF_DataCycleProject — Technical Guide

A daily data cycle that ingests building-energy, solar-production, meteorological, and room-booking data from on-prem sources into an Azure Medallion Lakehouse, transforms it with Databricks, produces ML-based consumption and production forecasts via KNIME, and exports the resulting gold-layer analytics to **SAP Analytics Cloud (SAC)** for Power BI / SAC dashboards.

---

## 1. At a glance

| Dimension | Value |
|---|---|
| Pattern | Medallion lakehouse (Bronze → Silver → Gold) |
| Orchestration | Azure Data Factory (9 pipelines, 2 daily triggers) |
| Compute | Azure Databricks (6 notebooks, single interactive cluster) |
| Storage | ADLS Gen2 — containers `bronze`, `silver`, `mldata`, `sacexport`, `config` |
| Serving | Azure SQL (serverless Gen5) — `DevDB` → consumed by SAC / Power BI |
| ML | KNIME Server (REST deployments) — GBT regressors for solar + consumption |
| Integration | Self-Hosted Integration Runtime (SHIR) on on-prem Windows VM `10.130.25.152` |
| Alerts | Action Group + metric alert on `PL_Ingest_Bronze` failures |
| Secrets | Azure Key Vault via ADF `LS_AKV` and Databricks secret scope `keyvault-scope` |

---

## 2. Architecture

```
 On-prem Windows VM (10.130.25.152)
 ├── SMB shares: BellevueBooking, BellevueConso, Solarlogs
 └── SFTP: meteo + future forecasts
          │
          │  Self-Hosted IR
          ▼
 Azure Data Factory (group3-df)
   ├── PL_Ingest_Bronze (07:15 trigger)        → bronze/
   ├── Silver/Gold notebooks                    → silver/, SQL DevDB
   ├── ml_export_to_knime                       → mldata/knime_input/
   ├── PL_Upload_Pred_Gold (09:30 trigger) ──▶ KNIME Server (REST)
   │                                            │
   │                                            ▼
   │                                          mldata/knime_output/
   │                                            │
   │   ml_load_predictions ◀────────────────────┘
   │         └─▶ SQL: fact_energy_prediction + sp_backfill_prediction_actuals
   │
   └── PL_SAC_Export
           └─▶ sacexport/ → Azure File Share → SAC consumption
```

Every arrow runs under orchestration — there is no direct producer-to-consumer handoff outside ADF.

---

## 3. Repository layout

```
.
├── adf/                              # ADF source JSON (factory=group3-df)
│   ├── factory/group3-df.json
│   ├── credential/                   # 1 UAMI credential (gh-datacycle-oidc)
│   ├── linkedService/                # 10 linked services
│   ├── dataset/                      # 19 datasets
│   ├── pipeline/                     # 9 pipelines
│   ├── trigger/                      # 2 daily triggers
│   ├── integrationRuntime/           # 1 self-hosted IR
│   └── publish_config.json           # Legacy (adf_publish branch) — unused under new CI
│
├── databricks/notebooks/             # 6 notebooks imported via Databricks Repos
│
├── config/                           # Lives in ADLS /config/ at runtime
│   ├── ml_models_config.json
│   └── electricity_tariff_config.json
│
├── sql/
│   └── deploy_schema.sql             # Idempotent DDL (dims, facts, sp, views)
│
├── .github/workflows/                # Active CI
│   ├── validate.yml                  # PR gate — ADF source JSON consistency
│   └── deploy-adf.yml                # Push-to-main — export + deploy ARM
├── .github/dependabot.yml
│
├── infrastructure/                   # Future-proofing (unwired — see §11)
│   ├── main.bicep
│   ├── modules/                      # 8 Bicep modules
│   ├── parameters/dev.parameters.json
│   ├── exported/                     # Frozen snapshots of current prod env
│   ├── future/workflows/             # deploy-dev.yml, destroy-dev.yml
│   └── DEPLOY.md                     # Full-rebuild runbook
│
├── scripts/
│   └── deploy_databricks.sh          # Idempotent Databricks provisioning
│
└── TECHNICAL_GUIDE.md                # You are here
```

---

## 4. Data sources

| Source | Host | Transport | Path / pattern | Notebook decoder |
|---|---|---|---|---|
| Solar inverter logs (raw) | On-prem VM | SMB | `\\10.130.25.152\Solarlogs\min*.csv` | UTF-8 |
| Solar aggregated (PV) | On-prem VM | SMB | `\\10.130.25.152\Solarlogs\*-PV.csv` | **UTF-16 LE** |
| Room bookings | On-prem VM | SMB | `\\10.130.25.152\BellevueBooking\*.csv` (TSV, `\t`) | UTF-8 |
| Consumption / temperature / humidity | On-prem VM | SMB | `\\10.130.25.152\BellevueConso\...` | **UTF-16 LE** |
| Historical weather | On-prem VM | SFTP | `/...*.csv` | UTF-8 |
| Future weather forecasts | On-prem VM | SFTP | `/.../future_forecasts/*.csv` | UTF-8 |

The UTF-16 BOM + null-byte handling happens in `silver_transformation.py` (`translate(col, "\u0000", "")` before any regex).

---

## 5. ADF — pipelines & triggers

### 5.1 Orchestration

```
TRG_Daily_0715 ─▶ PL_Ingest_Bronze                    (master orchestrator)
                      │
                      ├─▶ PL_Bronze_Solar             (ingest inverter + PV CSVs)
                      ├─▶ PL_Bronze_Bookings          (ingest room bookings)
                      ├─▶ PL_Bronze_Meteo             (ingest past weather, SFTP)
                      ├─▶ PL_Bronze_Conso             (ingest conso/temp/humidity)
                      │
                      ├─▶ Databricks: silver_transformation
                      ├─▶ Databricks: silver_gold_dimensions  ┐ (parallel)
                      ├─▶ Databricks: ml_export_to_knime      ┘
                      ├─▶ Databricks: silver_gold_facts
                      └─▶ PL_SAC_Export
                             ├─▶ Databricks: sac_export_to_adls
                             └─▶ Copy CSV → Azure File Share

TRG_Daily_0930 ─▶ PL_Upload_Pred_Gold
                      ├─▶ Run_Knime                   (KNIME REST calls)
                      │     ├─ Data_Preparation       (always)
                      │     ├─ Model_Selection        (Mondays only)
                      │     ├─ Consumption prediction (parallel)
                      │     └─ Solar prediction       (parallel)
                      └─▶ Databricks: ml_load_predictions
```

### 5.2 Bronze pipelines — common shape

All four `PL_Bronze_*` pipelines share an incremental-copy pattern:

1. `GetMetadata` on source (list files)
2. `GetMetadata` on destination (list already-ingested files)
3. `Filter` — keep only filenames not present in destination
4. `ForEach` (batch 50) `Copy` — binary copy to `bronze/<area>/`

`PL_Bronze_Conso` adds dynamic folder routing: filename prefix → `consumption/`, `temperature/`, `humidity/`, or `others/`.

`PL_Bronze_MeteoFuture` exists but is **not wired into `PL_Ingest_Bronze`** — it is a standalone pipeline. Future forecasts are still consumed by `silver_transformation.py` from whatever already sits in bronze.

### 5.3 Run_Knime — KNIME REST deployments

| Step | KNIME deployment ID | Cadence |
|---|---|---|
| `Data_Preparation` | `rest:e481f0fd-89ba-409a-aaa2-d8a648956949` | Every run |
| `Model_Selection` | `rest:509f9c76-1fd3-444d-80a6-4df7848b1621` | **Mondays only** (conditional via `TriggerTime.DayOfWeek`) |
| `Consumption predictor` | `rest:348633fa-f10f-4a27-99de-11e1707190cb` | Every run (parallel) |
| `Solar predictor` | `rest:eb96aa91-239b-4cf2-8c7e-a8a40516d4f3` | Every run (parallel) |

KNIME authenticates as user `N8XZA3zjIJVLk-P2XxLKBkLv1_aT-bX302wwgIGOmrY` using `knime` / `knimeappid` / `knimeappsecret` pulled from Key Vault.

### 5.4 Linked services

| Name | Type | Endpoint |
|---|---|---|
| `AzureDatabricks` | Databricks | Existing cluster `0223-115927-nvtos4a4` |
| `LS_Databricks_Silver` | Databricks (job cluster) | PAT from AKV |
| `LS_ADLS_Bronze` | Azure Blob FS (Gen2) | `adlsbellevuegrp3.dfs.core.windows.net` — authenticates via UAMI `gh-datacycle-oidc` (ADF credential object) |
| `LS_DevDB_Gold` | Azure SQL | `sqlserver-bellevue-grp3.database.windows.net` / `DevDB` |
| `LS_AKV` | Key Vault | `DataCycleGroup3Keys` |
| `LS_AzureFileShare_SAC` | File Share | `sac-export-share` |
| `LS_BellevueBooking_LocalServer` | File System | SMB via SHIR |
| `LS_BellevueConso_LocalServer` | File System | SMB via SHIR |
| `LS_Solarlogs_LocalServer` | File System | SMB via SHIR |
| `LS_SFTP_LocalServer` | SFTP | SFTP via SHIR |

`LS_ADLS_Bronze` uses the `gh-datacycle-oidc` UAMI registered in `adf/credential/gh-datacycle-oidc.json` — OAuth2/RBAC, no account key. All other credentials are either ADF `encryptedCredential` blobs or Key Vault references — **none live in git**.

---

## 6. Databricks — notebooks

All notebooks use the `keyvault-scope` secret scope. Writes to SQL use JDBC with batch size 20 000 and retry-with-backoff for the serverless pause/resume window (20–80 s, max 5 attempts).

### 6.1 `silver_transformation.py` — Bronze → Silver

Reads raw CSVs from `bronze/` and writes cleaned, deduplicated **Parquet** to `silver/` (overwrite mode). Handles:

- UTF-16 null-byte removal for PV / conso / temp / humidity sources.
- Dual date parsing (`dd.MM.yy` and `dd.MM.yyyy`) via `regexp_extract` + `coalesce`.
- **Solar unpivot**: input has 5 inverter columns per row (`pac_1..5`, `daysum_1..5`, etc.); notebook builds a 5-element array of structs and `explode()`s into one row per inverter.
- **Counter-reset logic** (consumption): when cumulative decreases, set delta to `null` — downstream facts recompute via `lag()`.
- **Weather synthesis**: no station exists for the Sierre campus; notebook averages Sion + Visp forecasts to produce a synthetic `"Sierre"` site.
- **GDPR**: SHA-256 hash on `Professeur` / `Utilisateur` booking columns → `ProfessorMasked` / `UserMasked`.

**Output tables in `silver/`:** `solar_inverters`, `solar_aggregated`, `weather_forecasts`, `weather_future_forecasts`, `bookings`, `consumption`, `temperature`, `humidity`.

### 6.2 `silver_gold_dimensions.py` — Silver → Gold dims

Populates the eight dimension tables (`dim_inverter`, `dim_inverter_status`, `dim_weather_site`, `dim_measurement_type`, `dim_division`, `dim_room`, `dim_prediction_model`, `ref_electricity_tariff`).

Idempotency pattern: `LEFT ANTI JOIN` against existing dim rows → INSERT only new keys. For `dim_prediction_model` and `ref_electricity_tariff`, the notebook compares payloads and issues UPDATEs when metadata drifts (`ref_electricity_tariff` is SCD2 — old row `EffectiveTo = today - 1`, new row inserted with `EffectiveFrom`).

Seeds `dim_inverter_status` with sentinel `StatusCode = 99 (Unknown)` which `silver_gold_facts.py` coalesces to when a live status code is missing.

### 6.3 `silver_gold_facts.py` — Silver → Gold facts

Incremental load of the seven fact tables. **Watermark**: `SELECT MAX(DateKey) FROM <fact>` → filter silver to rows strictly newer → dedup within batch → JDBC append.

Grain of each fact table:

| Table | Grain (PK) |
|---|---|
| `fact_solar_inverter` | `(DateKey, TimeKey, InverterKey)` |
| `fact_solar_production` | `(DateKey, TimeKey)` |
| `fact_energy_consumption` | `(DateKey, TimeKey)` |
| `fact_environment` | `(DateKey, TimeKey)` |
| `fact_weather_forecast` | `(DateKey, TimeKey, SiteKey, MeasurementKey, PredictionHorizon)` |
| `fact_room_booking` | Surrogate `BookingKey`, natural uniqueness on `(DateKey, StartTimeKey, RoomKey, ReservationNo)` |
| `fact_energy_prediction` | `(DateKey, TimeKey, ModelKey, PredictionRunDateKey)` |

Key engineering tricks:

- `DateKey = yyyyMMdd::int`, `TimeKey = hour*60 + minute::smallint`.
- `fact_environment` uses a **FULL OUTER JOIN** between temperature and humidity silver tables — keeps a reading even if only one sensor reported.
- Bookings parse French dates via a custom helper (`french_date_to_english`) before `try_to_date`.
- Computed columns (`RetailValue_CHF`, `CostCHF`, `IsRecurring`) are **SQL-side** — the notebook does not include them in the INSERT column list.

### 6.4 `ml_export_to_knime.py` — feature engineering

Produces two CSV feature sets for the KNIME workflow, targeting two ML stories:

| Output | Target | Features |
|---|---|---|
| `mldata/knime_input/solar_production_features.csv` | `production_delta_kwh` | irradiance, temp, temporal features (hour/minute/month/dow/is_weekend/quarter_hour) |
| `mldata/knime_input/consumption_features.csv` | `consumption_delta_kwh` | temp, humidity, precipitation, **room_occupation_pct**, temporal features, `is_academic_day` |

Interpolation trick: weather forecasts come at 3-hour granularity; notebook forward-fills via `Window.rowsBetween(unbounded, 0)` onto a 15-minute grid to match consumption/production samples.

**Room occupation** is computed by exploding each booking into 15-minute slots and counting distinct rooms per slot / total rooms.

### 6.5 `ml_load_predictions.py` — KNIME → Gold

Reads `mldata/knime_output/{production_predictions,consumption_predictions}.csv`, resolves `ModelKey` via `dim_prediction_model.ModelCode` (`PV_PROD_V1`, `CONS_V1`), clamps negative predictions to 0, and INSERTs into `fact_energy_prediction`.

**Idempotency**: `DELETE FROM fact_energy_prediction WHERE PredictionRunDateKey = <today>` before INSERT — full replace per run date.

After load, it calls `EXEC dbo.sp_backfill_prediction_actuals @TargetDate = 'YYYY-MM-DD'` once per distinct `DateKey` in the batch to join actuals from `fact_solar_production` and `fact_energy_consumption`.

Also writes back an updated `config/ml_models_config.json` to ADLS if KNIME metadata (features, notes) changed.

### 6.6 `sac_export_to_adls.py` — Gold → SAC

Reads two gold views (`vw_inverter_status_breakdown`, `vw_inverter_performance`) via JDBC, LEFT JOINs them at `(FullDate, InverterID)` grain, and writes `sacexport/sac_inverter_combined.csv` (single coalesced file).

Downstream, `PL_SAC_Export` binary-copies the CSV to the `sac-export-share` Azure File Share, which SAC polls.

---

## 7. Data warehouse — SQL schema

Two SQL files in [`sql/`](sql/) are deployed in order on every push to `main` (see §9.3):

| File | Purpose |
|---|---|
| [`sql/deploy_schema.sql`](sql/deploy_schema.sql) | Tables, views, stored procedure — idempotent structural DDL |
| [`sql/deploy_security.sql`](sql/deploy_security.sql) | Roles, user, RLS, permissions — idempotent security DDL |

Three notable design points in the structural schema:

- **Date & time keys are INT / SMALLINT surrogates**, not DATETIME. This makes `fact_*` joins cheap and partition-friendly. `dim_date` / `dim_time` are populated out-of-band (see `step1a_calculated_dimensions.sql` reference in notebooks).
- **Computed columns are persisted server-side**, not computed in Spark:
  - `fact_solar_production.RetailValue_CHF AS DeltaEnergy_Kwh * 0.15 PERSISTED`
  - `fact_energy_consumption.CostCHF AS DeltaEnergy_Kwh * 0.15 PERSISTED`
  - `fact_room_booking.IsRecurring AS CASE WHEN RecurrenceStart/End IS NOT NULL THEN 1 ELSE 0 END PERSISTED`
- **Seven analytical views** feed Power BI / SAC:
  - `vw_inverter_status_breakdown` — daily inverter status distribution, `PctOfDayReadings`.
  - `vw_inverter_performance` — actual AC power / rated capacity.
  - `vw_prediction_accuracy` — MAPE of predicted vs. actual energy.
  - `vw_daily_energy_balance` — daily production vs. consumption, net balance, self-sufficiency ratio, CHF costs.
  - `vw_building_occupation` — room occupation % per room per academic day (denominator = 720 min teaching day).
  - `vw_kpi_dashboard_home` — all five Home-tab KPI cards in a single query (consumption CHF, temperature, panel failure rate, occupation, humidity).
  - `vw_weather_vs_production` — irradiance forecast vs. actual PV output per 15-min slot (for the solar technical dashboard).

The tariff of `0.15 CHF/kWh` is hard-coded in the computed columns **and** in `config/electricity_tariff_config.json`. `ref_electricity_tariff` exists with SCD2 structure for when pricing needs to become time-varying; the computed columns would then need to be replaced with view-based pricing joins.

### 7.1 Security model (`sql/deploy_security.sql`)

| Object | Type | Purpose |
|---|---|---|
| `Director_Role` | DB role | Broad read access: energy, room bookings, management KPIs |
| `Technician_Role` | DB role | Technical read access: solar, prediction, weather data. **No access to room bookings** (GDPR) |
| `dev.admin.sql` | SQL contained user | Member of `Technician_Role`. Password from Key Vault `Admin-SQL-Password` — never in git |
| `ref_user_division_access` | Table | Maps Director-level login names to allowed `DivisionKey` values for RLS |
| `fn_division_security` | Inline TVF | RLS predicate: `db_owner` + `Technician_Role` see all rows; Directors see only their mapped divisions |
| `BookingDivisionFilter` | Security policy | Applies `fn_division_security` as a FILTER predicate on `fact_room_booking` |

The RLS policy means a Director connecting as their login can only read `fact_room_booking` rows for divisions they are listed in `ref_user_division_access`. `db_owner` and `Technician_Role` bypass this filter.

Populating `ref_user_division_access` is a manual step — insert one row per Director login + `DivisionKey` they should access.

---

## 8. ML lifecycle (KNIME integration)

1. **Training** is manual and lives inside KNIME Analytics Platform — the two GBT regressors (100 trees, `lr=0.1`, `max_depth=5`) are currently trained on 2023-02-20 → 2023-04-19 data.
2. Daily at **09:30**, `PL_Upload_Pred_Gold` fires:
   - `Data_Preparation` deployment runs unconditionally.
   - On Mondays only, `Model_Selection` re-evaluates the active model (via `@pipeline().TriggerTime.DayOfWeek`).
   - Consumption + solar predictors run in parallel.
3. KNIME writes CSVs to `mldata/knime_output/`.
4. `ml_load_predictions.py` ingests them and updates `fact_energy_prediction`.
5. `sp_backfill_prediction_actuals` joins yesterday's actuals onto earlier predictions, enabling `vw_prediction_accuracy` to track MAPE over time.

---

## 9. CI/CD

Two active workflows:

### 9.1 [`validate.yml`](.github/workflows/validate.yml) — PR gate

Runs `Azure/data-factory-validate-action@v1.1.4` against `adf/` on any PR touching `adf/**`. Catches broken references between pipelines / datasets / linked services before merge.

### 9.2 [`deploy-adf.yml`](.github/workflows/deploy-adf.yml) — push to main

1. `Azure/data-factory-export-action@v1.2.1` builds `ARMTemplateForFactory.json` from the source JSON in `adf/` — **no `adf_publish` branch required**.
2. `Azure/data-factory-deploy-action@v1.2.0` stops triggers, deploys the linked-template master with SAS staging, and restarts triggers.

SQL schema changes (`sql/deploy_schema.sql`, `sql/deploy_security.sql`) are **not** deployed automatically today — see §11 for the ready-to-activate `deploy-sql.yml` workflow.

#### Authentication — User-Assigned Managed Identity (UAMI)

The workflow authenticates to Azure via **OIDC with a User-Assigned Managed Identity** rather than a classic App Registration. A UAMI is a plain Azure resource (not an Azure AD tenant object), so it can be created by any subscription Owner without IT/admin involvement.

The identity `gh-datacycle-oidc` lives in the same resource group as `group3-df` and carries:
- A **Contributor** role assignment on the resource group (enough to deploy ADF ARM).
- A **federated credential** pinned to `repo:sandersdHES/ADF_DataCycleProject:environment:prod` — only GitHub Actions jobs running under the `prod` environment can request a token for it.

`azure/login@v2` accepts UAMI and App Registration identically — the workflow needs no changes if the identity type changes in the future.

#### GitHub Environment `prod` — required values

**Secrets:**

| Secret | Value |
|---|---|
| `AZURE_CLIENT_ID` | Client ID (UUID) of the `gh-datacycle-oidc` UAMI |
| `AZURE_TENANT_ID` | Azure AD tenant ID of the subscription |
| `AZURE_SUBSCRIPTION_ID` | Target subscription ID |

**Variables** (plain text, not secrets):

| Variable | Value |
|---|---|
| `AZURE_RESOURCE_GROUP` | RG containing `group3-df` |
| `AZURE_ADF_NAME` | `group3-df` |

### 9.3 Dependabot

Weekly updates for the GitHub Actions ecosystem (`.github/dependabot.yml`). Keeps `Azure/data-factory-*-action` pinned versions fresh.

---

## 10. Secrets & configuration

**Azure Key Vault (`DataCycleGroup3Keys`)** — read by both ADF (`LS_AKV`) and Databricks (scope `keyvault-scope`):

| Secret | Consumer |
|---|---|
| `Databricks-Access-Token` | ADF `LS_Databricks_Silver` |
| `adls-access-key` | All notebooks (OAuth-less JDBC to SQL still needs this for ADLS reads) |
| `Admin-SQL-Password` | All gold-writing notebooks, `LS_DevDB_Gold` |
| `Admin-VM-Password`, `Student-VM-Password` | ADF `LS_*_LocalServer`, `LS_SFTP_LocalServer` |
| `knime`, `knimeappid`, `knimeappsecret` | `Run_Knime` Web activities |
| `sacpassword` | `LS_AzureFileShare_SAC` |

**ADLS configuration files** (`config/` container):

- `ml_models_config.json` — model metadata. Read + written by `ml_load_predictions.py` when KNIME reports new features.
- `electricity_tariff_config.json` — `{ "tariff_chf_per_kwh": 0.15 }`. Read by documentation tooling; the SQL computed columns currently use a hard-coded literal.

**GitHub Secrets** (see §9) are only OIDC identity and factory-targeting values — no application secrets. All runtime credentials stay in Key Vault.

---

## 11. Future-proofing — unwired reproducibility

This project currently runs on a manually-provisioned Azure environment. To keep a door open to rebuilding from scratch (new tenant, DR drill, spinning up a parallel prod), the repo carries a **fully-fledged Infrastructure-as-Code path that is intentionally unwired**:

| Artifact | Location | Status |
|---|---|---|
| Bicep (subscription-scoped) | [`infrastructure/main.bicep`](infrastructure/main.bicep) + [`infrastructure/modules/`](infrastructure/modules) | Present, not wired to CI |
| Full-deploy workflow | [`infrastructure/future/workflows/deploy-dev.yml`](infrastructure/future/workflows/deploy-dev.yml) | Moved out of `.github/workflows/` so it does not auto-trigger |
| Teardown workflow | [`infrastructure/future/workflows/destroy-dev.yml`](infrastructure/future/workflows/destroy-dev.yml) | Same — reference only |
| Databricks provisioner | [`scripts/deploy_databricks.sh`](scripts/deploy_databricks.sh) | Consumed by the unwired `deploy-dev.yml` |
| SQL structural DDL | [`sql/deploy_schema.sql`](sql/deploy_schema.sql) | Idempotent — tables, views, stored procedure |
| SQL security DDL | [`sql/deploy_security.sql`](sql/deploy_security.sql) | Idempotent — roles, RLS, user, grants. Run after deploy_schema.sql |
| SQL deploy workflow | [`infrastructure/future/workflows/deploy-sql.yml`](infrastructure/future/workflows/deploy-sql.yml) | Ready to activate — requires Key Vault Secrets User role on the UAMI (see below) |
| Bacpac seed | `infrastructure/exported/DataCycleDB.bacpac` | One-shot data load for a fresh DB |
| Frozen exports | [`infrastructure/exported/`](infrastructure/exported/) | ARM + Bicep snapshots of the current environment for diffing |
| Runbook | [`infrastructure/DEPLOY.md`](infrastructure/DEPLOY.md) | Full rebuild procedure |

**How to activate the SQL deploy workflow** (two-step, no rebuild needed):

1. Grant `Key Vault Secrets User` role to the `gh-datacycle-oidc` UAMI on the Key Vault:
   ```bash
   az role assignment create \
     --assignee-object-id <UAMI_PRINCIPAL_ID> \
     --assignee-principal-type ServicePrincipal \
     --role "Key Vault Secrets User" \
     --scope "/subscriptions/<SUB>/resourceGroups/<RG>/providers/Microsoft.KeyVault/vaults/DataCycleGroup3Keys"
   ```
2. Move `infrastructure/future/workflows/deploy-sql.yml` to `.github/workflows/deploy-sql.yml`.

> **Why it is not active today:** the `gh-datacycle-oidc` UAMI currently has only `Contributor` on the resource group. Key Vault uses a separate RBAC plane — `Contributor` does not grant secret reads. The workflow fails with `ForbiddenByRbac` without the explicit `Key Vault Secrets User` assignment.

**How to activate the full environment rebuild** (should the POC ever need to become reproducible):

1. Move `infrastructure/future/workflows/deploy-dev.yml` and `destroy-dev.yml` into `.github/workflows/`.
2. Create a GitHub Environment `dev` with the secret set documented in `DEPLOY.md`.
3. Create a UAMI (or AAD app) + OIDC federated credential scoped to the new environment (see §9.2).
4. Run `deploy-dev.yml` once to build a parallel environment; verify; tear down with `destroy-dev.yml`.

Until then these files are just "scaffolding in the attic" — they pay no cost, break nothing, and will be green on `validate.yml` because nothing references them.

---

## 12. Operational runbook — quick reference

| Event | Where to look |
|---|---|
| Pipeline failed overnight | ADF Studio → Monitor → `PL_Ingest_Bronze`. Metric alert `ar-pl-ingest-bronze-failed` fires within 1 h |
| SHIR offline | Windows VM `10.130.25.152` — check the Integration Runtime Configuration Manager |
| KNIME REST call 5xx | KNIME Server logs; verify `knimeappid` / `knimeappsecret` in KV haven't rotated |
| SQL serverless pause | First JDBC call retries with 20–80 s backoff (handled in notebooks) |
| New inverter added | `silver_gold_dimensions.py` auto-inserts on next run; `silver_gold_facts.py` picks it up via LEFT JOIN |
| New weather station | Add to `dim_weather_site` manually — notebook only guarantees the Sierre synthetic site exists |
| Tariff change | Update literal in `sql/deploy_schema.sql` computed columns AND `config/electricity_tariff_config.json` AND add SCD2 row to `ref_electricity_tariff` |

---

## 13. Known limitations

- **ADF git integration is manual.** `repoConfiguration` cannot be set via Bicep without a circular dep, so it's configured once in ADF Studio → Manage → Git.
- **Notebook paths are absolute.** `AzureDatabricks` activities reference `/Repos/<specific-user>/ADF_DataCycleProject/...` — a new developer's Repos path does not work without either re-pointing activities or cloning under the shared user.
- **`PL_Bronze_MeteoFuture` is orphaned** — standalone pipeline, not called by `PL_Ingest_Bronze`. If future forecasts are needed in silver, the upstream trigger has to be added manually.
- **Tariff is triplicated** — SQL computed columns, JSON config, `ref_electricity_tariff` SCD2 table. Consolidate before trusting any single source.
- **No lineage in Gold.** Fact tables are append-only; there is no `LoadBatchId` / `IngestedAt`. Watermark-based re-runs are safe but audit trails rely on DB timestamps the engine doesn't preserve.
- **`publish_config.json` is legacy** — we no longer use the `adf_publish` branch because `Azure/data-factory-export-action` builds ARM from source JSON. Safe to delete.

---

*For the full-rebuild procedure (Bicep + OIDC + bacpac + SHIR registration), see [`infrastructure/DEPLOY.md`](infrastructure/DEPLOY.md).*
