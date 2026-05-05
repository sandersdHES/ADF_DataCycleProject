# Operational Runbook

[[Home]] > Operational Runbook

Quick reference for day-to-day operations and incident response.

---

## Daily pipeline schedule

| Time (UTC) | Pipeline | Expected duration |
|---|---|---|
| 07:15 | `PL_Ingest_Bronze` — ingest + ETL + SAC export | ~30–40 min |
| 09:30 | `PL_Upload_Pred_Gold` — KNIME predictions + Gold load | ~10–15 min |

---

## Alert

**Metric alert:** `ar-pl-ingest-bronze-failed`
- Fires within **1 hour** of a `PL_Ingest_Bronze` failure
- Routed to the Action Group configured in ADF monitoring
- Check: **ADF Studio → Monitor → Pipeline runs**

---

## Incident triage

### Pipeline failed overnight

1. Open **ADF Studio → Monitor → Pipeline runs**, filter by `PL_Ingest_Bronze`
2. Click the failed run → expand the failed activity to see the error message
3. Common causes:
   - SHIR offline (see below)
   - Source file encoding / format change
   - SQL serverless DB paused longer than retry window (see below)
   - KNIME REST timeout (09:30 pipeline only)

### SHIR (Self-Hosted Integration Runtime) offline

**Symptom:** Bronze ingestion activities fail with `Integration runtime is not running` or similar.

**Resolution:**
1. RDP to Windows VM `10.130.25.152`
2. Open **Microsoft Integration Runtime Configuration Manager**
3. Check the node status — restart the service if stopped
4. Verify the node shows **Connected** before re-running the pipeline

### KNIME REST call returning 5xx

**Symptom:** `Run_Knime` Web activity fails with HTTP 5xx.

**Resolution:**
1. Check KNIME Server logs for the relevant deployment ID
2. Verify `knimeappid` and `knimeappsecret` in Key Vault haven't been rotated
3. If KNIME Server is down, re-run `PL_Upload_Pred_Gold` once the server recovers — it is idempotent (deletes today's predictions before re-inserting)

### SQL serverless DB pause

Azure SQL serverless automatically pauses after inactivity. The first JDBC connection retries with **20–80 second backoff, max 5 attempts** (handled in all notebooks). This is not an error — the pipeline will self-heal. If all 5 retries fail, the serverless tier's auto-pause delay may need to be increased in Azure Portal.

### New inverter added

No action required. `silver_gold_dimensions.py` auto-inserts new `InverterID` values on the next run. `silver_gold_facts.py` picks them up via LEFT JOIN.

### New weather station added

`dim_weather_site` is not auto-populated for arbitrary new stations. Insert the new row manually:

```sql
INSERT INTO dbo.dim_weather_site (SiteName) VALUES ('<StationName>');
```

The Sierre synthetic site is guaranteed by `silver_gold_dimensions.py` on every run.

### Tariff change

Three sources must be updated together:

1. **SQL computed columns** in `sql/deploy_schema.sql` — update the `0.15` literal in `fact_solar_production` and `fact_energy_consumption` computed column definitions
2. **`config/electricity_tariff_config.json`** — update `tariff_chf_per_kwh`
3. **`ref_electricity_tariff` SCD2** — `silver_gold_dimensions.py` handles the SCD2 row rotation automatically when it reads the updated config file

Re-run `sql/deploy_schema.sql` after step 1 (it is idempotent). Upload the updated config file to the ADLS `config/` container before the next pipeline run.

### Re-running a specific pipeline

All pipelines are safe to re-run:
- **Bronze pipelines** — incremental; already-ingested files are skipped
- **Silver** (`silver_transformation.py`) — overwrites Silver Parquet (idempotent)
- **Gold dimensions** — LEFT ANTI JOIN insert-only (idempotent)
- **Gold facts** — watermark-based; re-run only ingests data newer than the current `MAX(DateKey)` in each fact table
- **`ml_load_predictions.py`** — DELETE + re-INSERT for today's `PredictionRunDateKey` (idempotent)

### Re-running xx:00 synthesis after a Silver fix

`silver_transformation.py` synthesises the xx:00 slot for every 30-min gap (96 rows/day). If Silver is corrupted or the synthesis logic is patched:

1. Re-run `silver_transformation.py` to regenerate all Silver Parquet files.
2. Manually TRUNCATE the affected Gold fact tables in SQL:
   ```sql
   TRUNCATE TABLE dbo.fact_energy_consumption;
   TRUNCATE TABLE dbo.fact_solar_production;
   TRUNCATE TABLE dbo.fact_environment;
   ```
3. Re-run `silver_gold_facts.py` (the watermark is now 0, so it reloads everything).

> ⚠️ TRUNCATE resets the watermark. All downstream views will show no data until the notebook completes.

### Re-running the inverter Pac backfill

`fact_solar_production` rows loaded from per-inverter `min*.csv` (2023-02-20 onwards) have `CumulativeEnergy_Kwh IS NULL`. To force a full reload of the backfill period:

1. Delete only the backfill rows:
   ```sql
   DELETE FROM dbo.fact_solar_production WHERE CumulativeEnergy_Kwh IS NULL;
   ```
2. Re-run `silver_gold_facts.py` — the LEFT ANTI JOIN in the two-pass load will re-insert the missing rows.

---

## Useful links

| Resource | Where |
|---|---|
| ADF Studio | Azure Portal → `group3-df` → Author |
| ADF Monitor | Azure Portal → `group3-df` → Monitor → Pipeline runs |
| Key Vault | Azure Portal → `DataCycleGroup3Keys` → Secrets |
| ADLS containers | Azure Portal → `adlsbellevuegrp3` → Containers |
| Azure SQL | Azure Portal → `sqlserver-bellevue-grp3` → `DevDB` → Query editor |
| Databricks workspace | Linked service `AzureDatabricks` endpoint |

---

*For full-rebuild procedures, see [[Infrastructure and IaC]]. For secrets and credential rotation, see [[Secrets and Configuration]].*
