# Known Limitations and Roadmap

[[Home]] > Known Limitations and Roadmap

---

## Current limitations

### ADF Git integration is manual

`repoConfiguration` cannot be set in Bicep without creating a circular dependency with this repo. After every fresh deploy, ADF Studio → Manage → Git configuration must be pointed at `main` / `adf/` manually.

**Impact:** One manual step per environment rebuild. Low risk in day-to-day operations.

---

### Notebook paths are absolute

`DatabricksNotebook` activities reference `/Repos/<specific-user>/ADF_DataCycleProject/databricks/notebooks/...`. A new developer's Databricks Repos path does not work without either:
- Re-pointing all activities in ADF Studio, or
- Cloning the repo under the same path as the original user (i.e. a shared service account)

**Workaround:** Use a shared Databricks service account whose Repos path matches what's in the pipeline JSON.

---

### `PL_Bronze_MeteoFuture` is orphaned

`PL_Bronze_MeteoFuture` is a standalone pipeline not called by `PL_Ingest_Bronze`. Future weather forecasts consumed by `silver_transformation.py` rely on whatever already sits in `bronze/meteo_future/` — they are not refreshed daily.

**Fix:** Wire `PL_Bronze_MeteoFuture` into `PL_Ingest_Bronze` as a parallel Bronze step (alongside the other four `PL_Bronze_*` pipelines).

---

### `weather_future_forecasts` Silver table contains historical data (not future forecasts)

In `silver_transformation.py`, `df_futureweather_raw` is read from `bronze/future_forecasts/` but **never processed**. `df_sierre` (the historical Sierre average) is written to `silver/weather_future_forecasts/` instead. The two Silver tables currently contain identical data.

**Impact:** Downstream ML features that should draw on forward-looking weather forecasts receive the same historical data as `silver/weather_forecasts/`. The future forecast data stored in Bronze is not being used.

**Fix:** Apply the same Sierre-synthesis logic to `df_futureweather_raw` before writing to `silver/weather_future_forecasts/`. Also wire `PL_Bronze_MeteoFuture` into the daily cycle (see below).

---

### Booking column rename is positional

`silver_transformation.py` renames the duplicate `Date de début` / `Date de fin` header pairs based on the numeric suffix Spark auto-appends (e.g. `Date de début3`, `Date de début11`). If the source CSV column order ever changes, the rename silently produces wrong column names with no pipeline error.

**Impact:** Room bookings could be loaded with swapped start/end dates or incorrect recurrence windows — undetectable until a downstream consumer notices stale-looking data.

**Fix:** Parse by explicit positional index or add a header validation step that errors out if expected column names are absent.

---

### Tariff is triplicated

The electricity tariff of `0.15 CHF/kWh` lives in three places:
1. SQL computed columns in `sql/deploy_schema.sql` (`RetailValue_CHF`, `CostCHF`)
2. `config/electricity_tariff_config.json`
3. `ref_electricity_tariff` SCD2 table in Gold SQL

These must all be updated together on a tariff change. There is no single source of truth.

**Fix (when needed):** Replace the SQL computed columns with view-based pricing joins that read from `ref_electricity_tariff`. Until then, update all three manually.

---

### No lineage in Gold

Fact tables are append-only with no `LoadBatchId` or `IngestedAt` column. Watermark-based re-runs are safe, but audit trails rely only on database timestamps, which the engine doesn't preserve for JDBC-appended rows.

**Fix (if needed):** Add a `LoadBatchId UNIQUEIDENTIFIER DEFAULT NEWID()` and `IngestedAt DATETIME2 DEFAULT SYSUTCDATETIME()` to each fact table. Notebooks would need to include them in INSERT column lists or let SQL default them.

---

### `publish_config.json` is legacy

`adf/publish_config.json` was used by the old `adf_publish` branch workflow. The current CI uses `Azure/data-factory-export-action` to build ARM from source JSON directly — no `adf_publish` branch is needed.

**Fix:** Delete `adf/publish_config.json` in a follow-up PR.

---

### `dim_date` / `dim_time` not populated by CI

The DDL creates shells for both tables but does not populate them. Fact table joins on date/time keys will fail until these are populated separately.

**Fix:** Add a `step1a_calculated_dimensions.sql` execution step to the deploy workflow, or implement population in a Databricks notebook.

---

## Housekeeping backlog (from `docs/TODO.md`)

- [ ] Delete `adf/publish_config.json`
- [ ] Fix `weather_future_forecasts` Silver: process `df_futureweather_raw` instead of writing `df_sierre`
- [ ] Fix booking column rename to be index-based rather than suffix-based
- [ ] Decide on tariff consolidation (SQL computed columns vs. `ref_electricity_tariff` vs. JSON config)
- [ ] Wire `PL_Bronze_MeteoFuture` into `PL_Ingest_Bronze`
- [ ] Transfer Azure subscription billing ownership to the company account
- [ ] Verify triggers `TRG_Daily_0715` and `TRG_Daily_0930` are `Started` after next deploy
- [ ] Extend KNIME training window beyond the 2023-Q1 period

---

## Roadmap ideas

- **Fix future-forecast Silver bug** — correct `df_futureweather_raw` processing; wire `PL_Bronze_MeteoFuture` daily
- **Consolidate tariff source of truth** — use `ref_electricity_tariff` as the single source; replace SQL computed columns with view-based pricing joins
- **Add `LoadBatchId` to facts** — improve audit trail and re-run observability
- **Populate `dim_date` / `dim_time` in CI** — remove the manual post-deploy step
- **Parameterise notebook paths** — replace absolute `/Repos/<user>/...` paths with an ADF pipeline parameter or global parameter; `deploy_databricks.sh` already passes `DATABRICKS_USER` which could feed this
- **Expand ML training window** — both GBT models are trained on a fixed 2023-Q1 window; accuracy degrades as seasonal patterns shift
- **Activate the full IaC path** — move `infrastructure/future/workflows/` into `.github/workflows/` for a fully reproducible environment

---

*For the full-rebuild procedure, see [[Infrastructure and IaC]] and [`infrastructure/DEPLOY.md`](https://github.com/sandersdHES/ADF_DataCycleProject/blob/main/infrastructure/DEPLOY.md).*
