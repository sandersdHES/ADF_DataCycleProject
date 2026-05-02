# Databricks Notebooks

[[Home]] > Databricks Notebooks

All notebooks live under `databricks/notebooks/` and are executed by ADF via the `AzureDatabricks` or `LS_Databricks_Silver` linked service. Notebook paths reference this repo under `/Repos/<user>/ADF_DataCycleProject/databricks/notebooks/`. All notebooks use the `keyvault-scope` Databricks secret scope. SQL writes use JDBC with batch size 20,000 and retry-with-backoff for the serverless DB pause/resume window (20–80 s, max 5 attempts).

---

## Overview

| Notebook | Called by | Layer | Description |
|---|---|---|---|
| `silver_transformation.py` | `PL_Ingest_Bronze` | Bronze → Silver | Cleans raw CSVs, deduplicates, writes Parquet |
| `silver_gold_dimensions.py` | `PL_Ingest_Bronze` | Silver → Gold | Populates 8 dimension tables via MERGE/INSERT |
| `silver_gold_facts.py` | `PL_Ingest_Bronze` | Silver → Gold | Incremental load of 7 fact tables via watermark |
| `ml_export_to_knime.py` | `PL_Ingest_Bronze` | Silver → ML | Feature engineering → CSV for KNIME |
| `ml_load_predictions.py` | `PL_Upload_Pred_Gold` | ML → Gold | Loads KNIME output into `fact_energy_prediction` |
| `sac_export_to_adls.py` | `PL_SAC_Export` | Gold → Export | Gold views → flat CSV for SAP Analytics Cloud |

---

## `silver_transformation.py` — Bronze → Silver

Reads raw CSVs from `bronze/` and writes cleaned, deduplicated **Parquet** to `silver/` (overwrite mode each run).

**Key transformations:**

| Topic | Detail |
|---|---|
| UTF-16 null-byte removal | `translate(col, " ", "")` applied to PV, conso, temp, humidity sources before any parsing |
| Dual date parsing | `regexp_extract` + `coalesce` handles both `dd.MM.yy` and `dd.MM.yyyy` |
| Solar unpivot | Input has 5 inverter columns per row (`pac_1..5`, `daysum_1..5` etc.). Notebook builds a 5-element array of structs and `explode()`s into one row per inverter |
| Counter-reset logic | Consumption and PV values are cumulative counters. When the counter decreases (reset or meter replacement), delta is set to `null` — downstream facts recompute via `lag()` |
| Synthetic Sierre weather | No station at the Sierre campus. Averages Sion + Visp forecasts; the sentinel value −99,999 is replaced with `null` before averaging |
| GDPR masking | SHA-256 hash on `Professeur` / `Nom de l'utilisateur` booking columns → `ProfessorMasked` / `UserMasked` |

### Silver table schemas

**`silver/solar_inverters/`** — one row per inverter per 5-minute log entry (source wide row unpivoted × 5)

| Column | Type | Description |
|---|---|---|
| `log_timestamp` | TIMESTAMP | Reconstructed from `date_raw` (date) + `time_raw` (HH:mm:ss) |
| `inverter_id` | INT | Inverter number 1–5 |
| `ac_power_w` | DOUBLE | AC output power across all phases (W) |
| `daysum` | DOUBLE | Cumulative Wh produced since midnight for this inverter |
| `status_code` | INT | 0 = standby/OK · 6 = running · 14 = error |
| `pdc1` / `pdc2` | DOUBLE | DC input power from generator strings 1 and 2 (W) |
| `udc1` / `udc2` | DOUBLE | DC voltage from generator strings 1 and 2 (V) |
| `is_failure` | BOOLEAN | `true` when `status_code == 14` |

**`silver/solar_aggregated/`** — one row per 15-minute PV meter reading

| Column | Type | Description |
|---|---|---|
| `timestamp` | TIMESTAMP | Reading time |
| `cumulative_reading` | DOUBLE | Cumulative kWh total — monotonically increasing |
| `delta_value` | DOUBLE | kWh since previous reading; `null` when a counter reset is detected |

**`silver/consumption/`** — same schema as `solar_aggregated`; measures building kWh consumed.

**`silver/temperature/`** — one row per 15-minute indoor temperature reading

| Column | Type | Description |
|---|---|---|
| `timestamp` | TIMESTAMP | Reading time |
| `actual_temp` | DOUBLE | Indoor ambient temperature (°C) |
| `temp_delta` | DOUBLE | Change since the previous reading, re-derived via `lag()` — the source `Variation` column duplicates `Valeur Acquisition` and is not usable |

**`silver/humidity/`** — same schema as `temperature`; columns are `actual_humidity` (%) and `humidity_delta`.

**`silver/weather_forecasts/`** and **`silver/weather_future_forecasts/`** — one row per (time, measurement type); `Site` is always `"Sierre"` (synthetic)

| Column | Type | Description |
|---|---|---|
| `Time` | TIMESTAMP (UTC) | Forecast validity timestamp |
| `Value` | DOUBLE | Forecasted value; source sentinel −99,999 replaced with `null` before averaging |
| `Prediction` | INT | Forecast run counter for the day |
| `Site` | STRING | Always `"Sierre"` — mean of Sion and Visp readings |
| `Measurement` | STRING | `PRED_GLOB_ctrl` (irradiance) · `PRED_T_2M_ctrl` (temp) · `PRED_RELHUM_2M_ctrl` (humidity) · `PRED_TOT_PREC_ctrl` (precipitation) |
| `Unit` | STRING | Physical unit |

> ⚠️ **Known bug:** `silver/weather_future_forecasts/` currently contains the same historical Sierre data as `silver/weather_forecasts/`. The future forecast raw data is read from `bronze/future_forecasts/` but never processed — `df_sierre` (historical) is written instead. See [[Known Limitations and Roadmap]].

**`silver/bookings/`** — one row per booking entry; filtered to Bellevue rooms only (`Nom` starts with `VS-BEL`)

| Column | Type | Description |
|---|---|---|
| `Nom` / `Nom entier` | STRING | Room code and full display name |
| `Date` | STRING | Booking day in French locale (e.g. `8 janv. 2023`) — parsed to DATE in Gold |
| `Heure_Debut` / `Heure_Fin` | STRING | Session start / end time (HH:mm) — renamed from the duplicate `Date de début`/`Date de fin` column pair at index 3/4 |
| `Date_Recurrence_Debut` / `Date_Recurrence_Fin` | STRING | Recurrence window start/end dates — renamed from the duplicate pair at index 11/12 |
| `Rés.-no` | STRING | Reservation number |
| `Type de réservation` / `Codes` | STRING | Booking type and category codes |
| `Professeur_Masked` | STRING | SHA-256 of original `Professeur` field |
| `Utilisateur_Masked` | STRING | SHA-256 of original `Nom de l'utilisateur` field |
| `Périodicité` | STRING | Recurrence rule (e.g. `w` = weekly) |
| `Classe` / `Activité` | STRING | Attending class and activity type |
| `Division` | STRING | HES-SO school or service responsible for the booking |
| `Poste de dépenses` | STRING | Cost centre |
| `Remarque` / `Annotation` | STRING | Free-text notes |

---

## `silver_gold_dimensions.py` — Silver → Gold dimensions

Populates the 8 dimension tables. Uses a `LEFT ANTI JOIN` pattern to INSERT only new keys (idempotent). Updates metadata on `dim_prediction_model` and `ref_electricity_tariff` when payloads drift.

| Dimension table | Source | Notes |
|---|---|---|
| `dim_inverter` | Solar Silver | Auto-inserts new inverter IDs on each run |
| `dim_inverter_status` | Seeded | Seeds sentinel `StatusCode = 99 (Unknown)` for fallback in facts |
| `dim_weather_site` | Weather Silver | Synthetic `"Sierre"` site guaranteed on every run |
| `dim_measurement_type` | Static | Measurement type catalog |
| `dim_division` | Bookings Silver | Auto-inserts new divisions |
| `dim_room` | Bookings Silver | Auto-inserts new rooms |
| `dim_prediction_model` | `config/ml_models_config.json` | UPDATEs when KNIME metadata drifts |
| `ref_electricity_tariff` | `config/electricity_tariff_config.json` | **SCD2** — on tariff change: old row `EffectiveTo = today-1`, new row inserted with `EffectiveFrom = today` |

---

## `silver_gold_facts.py` — Silver → Gold facts (incremental)

Loads 7 fact tables incrementally. **Watermark pattern:** `SELECT MAX(DateKey) FROM <fact>` → filter Silver to rows strictly newer → dedup within batch → JDBC append.

| Fact table | Grain | Special logic |
|---|---|---|
| `fact_solar_inverter` | `(DateKey, TimeKey, InverterKey)` | Status coalesced to sentinel `StatusKey = 99` when lookup fails |
| `fact_solar_production` | `(DateKey, TimeKey)` | `RetailValue_CHF = DeltaEnergy_Kwh × 0.15` is a SQL-side computed column |
| `fact_energy_consumption` | `(DateKey, TimeKey)` | `CostCHF = DeltaEnergy_Kwh × 0.15` is a SQL-side computed column |
| `fact_environment` | `(DateKey, TimeKey)` | **FULL OUTER JOIN** between temp and humidity Silver tables — preserves readings when only one sensor reported |
| `fact_weather_forecast` | `(DateKey, TimeKey, SiteKey, MeasurementKey, PredictionHorizon)` | 3-hour data loaded as-is; interpolation to 15-min happens in KNIME |
| `fact_room_booking` | Surrogate `BookingKey`; natural on `(DateKey, StartTimeKey, RoomKey, ReservationNo)` | French dates parsed via `french_date_to_english`; `IsRecurring` SQL-computed |
| `fact_energy_prediction` | `(DateKey, TimeKey, ModelKey, PredictionRunDateKey)` | Loaded by `ml_load_predictions.py`, not this notebook |

**Key engineering notes:**
- `DateKey = yyyyMMdd` (INT); `TimeKey = hour×60 + minute` (SMALLINT)
- Computed columns (`RetailValue_CHF`, `CostCHF`, `IsRecurring`) are SQL-persisted — notebooks omit them from the INSERT column list

---

## `ml_export_to_knime.py` — Feature engineering

Produces two CSV feature sets and writes them to `mldata/knime_input/`.

| Output file | ML target | Key features |
|---|---|---|
| `solar_production_features.csv` | `production_delta_kwh` | Irradiance, temperature, temporal features (hour, minute, month, day-of-week, is_weekend, quarter-hour) |
| `consumption_features.csv` | `consumption_delta_kwh` | Temperature, humidity, precipitation, **room_occupation_pct**, temporal features, `is_academic_day` |

**Room occupation computation:** Each booking is exploded into 15-minute slots; `room_occupation_pct = distinct_rooms_occupied / total_rooms` per slot.

**Weather interpolation:** `Window.rowsBetween(unboundedPreceding, 0)` forward-fills 3-hour forecasts onto a 15-minute grid.

---

## `ml_load_predictions.py` — KNIME → Gold

Reads `mldata/knime_output/{production_predictions,consumption_predictions}.csv` and loads them into `fact_energy_prediction`.

1. Resolve `ModelKey` via `dim_prediction_model.ModelCode` (`PV_PROD_V1`, `CONS_V1`)
2. Clamp negative predictions to 0 (physical constraint)
3. `DELETE FROM fact_energy_prediction WHERE PredictionRunDateKey = <today>` (idempotency)
4. JDBC INSERT the batch
5. Call `EXEC dbo.sp_backfill_prediction_actuals @TargetDate = 'YYYY-MM-DD'` once per distinct `DateKey` — joins actuals onto prior predictions, enabling MAPE tracking in `vw_prediction_accuracy`
6. Write back `config/ml_models_config.json` if KNIME metadata changed

---

## `sac_export_to_adls.py` — Gold → SAC

Reads two Gold views via JDBC, LEFT JOINs them at `(FullDate, InverterID)` grain, and writes `sacexport/sac_inverter_combined.csv` (single coalesced file).

| Gold view | Content |
|---|---|
| `vw_inverter_status_breakdown` | Daily inverter status distribution, `PctOfDayReadings` |
| `vw_inverter_performance` | Actual AC power vs. rated capacity, `HadFailure` flag |

`PL_SAC_Export` then binary-copies this CSV to the `sac-export-share` Azure File Share, which SAC polls.

---

*For the SQL schema these notebooks write to, see [[Data Warehouse Schema]]. For the KNIME prediction cycle, see [[ML Lifecycle]].*
