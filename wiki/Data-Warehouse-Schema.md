# Data Warehouse Schema

[[Home]] > Data Warehouse Schema

The Gold layer lives in **Azure SQL serverless Gen5** (`sqlserver-bellevue-grp3.database.windows.net` / database `DevDB`). Two SQL files are deployed in order by CI on every push to `main`:

| File | Purpose |
|---|---|
| [`sql/deploy_schema.sql`](https://github.com/sandersdHES/ADF_DataCycleProject/blob/main/sql/deploy_schema.sql) | Tables, views, stored procedure — idempotent structural DDL |
| [`sql/deploy_security.sql`](https://github.com/sandersdHES/ADF_DataCycleProject/blob/main/sql/deploy_security.sql) | Roles, user, RLS, permissions — idempotent security DDL |

---

## Key design conventions

- **Integer surrogate keys for date and time.** `DateKey = yyyyMMdd` (INT); `TimeKey = hour × 60 + minute` (SMALLINT). Makes fact/dim joins cheap and partition-friendly.
- **Computed columns are SQL-persisted**, not computed in Spark. Notebooks omit them from INSERT column lists and let the engine calculate them on write.
- **No lineage columns.** Fact tables are append-only with no `LoadBatchId` or `IngestedAt`. Watermark re-runs are safe but audit trails rely only on DB timestamps.
- **All Gold column names are English.** The Silver layer mirrors the French source CSV (e.g. `Remarque`, `Périodicité`); the Databricks Silver→Gold notebook maps them to English at the Gold boundary (`Remark`, `Periodicity`, etc.).

---

## Schema map

```
dim_date ─────────────────┐
dim_time ─────────────────┤
dim_inverter ─────────────┼── fact_solar_inverter
dim_inverter_status ──────┘

dim_date ─────────────────┐
dim_time ──────────────── fact_solar_production
                          fact_energy_consumption
                          fact_environment

dim_weather_site ─────────┐
dim_measurement_type ─────┼── fact_weather_forecast
dim_date ─────────────────┘

dim_room ─────────────────┐
dim_division ─────────────┼── fact_room_booking  ← RLS filter applied
dim_date ─────────────────┘

dim_prediction_model ─────┐
dim_date ─────────────────┼── fact_energy_prediction
dim_time ─────────────────┘

ref_electricity_tariff     (SCD2 reference table)
ref_user_division_access   (RLS mapping — Directors / Teachers ↔ Divisions)
```

---

## Dimension tables

### `dim_date`
`DateKey INT (PK)` | `FullDate DATE` | `Year` | `Quarter` | `Month` | `MonthName` | `MonthShort` | `WeekOfYear` | `DayOfMonth` | `DayOfWeek` | `DayName` | `IsWeekend` | `IsSwissHoliday` | `HolidayName` | `Season` | `AcademicYear` | `AcademicSemester` | `IsAcademicDay`

Populated separately (not by these notebooks).

### `dim_time`
`TimeKey SMALLINT (PK)` | `TimeLabel NCHAR(5)` | `Hour` | `Minute` | `QuarterHourSlot` | `HalfHourSlot` | `HourSlot` | `TimePeriod` | `IsBusinessHour` | `IsLectureHour`

Populated separately.

### `dim_inverter`
`InverterKey INT IDENTITY (PK)` | `InverterID INT UNIQUE` | `InverterName` | `RatedPower_kWp` | `StringCount` | `RoofSection` | `InstallDate` | `IsActive`

Auto-populated from Solar Silver on each run.

### `dim_inverter_status`
`StatusKey TINYINT IDENTITY (PK)` | `StatusCode INT UNIQUE` | `StatusLabel` | `StatusCategory` | `IsFailure` | `RequiresMaintenance`

Seeded with sentinel `StatusCode = 99 (Unknown)` — used as fallback in `fact_solar_inverter`.

### `dim_weather_site` / `dim_measurement_type` / `dim_division` / `dim_room` / `dim_prediction_model`
All auto-populated from Silver on each run. See [[Databricks Notebooks]] for the MERGE/INSERT patterns.

### `ref_electricity_tariff` (SCD2)
`TariffKey INT IDENTITY (PK)` | `TariffName` | `PricePerKwh_CHF` | `EffectiveFrom DATE` | `EffectiveTo DATE` | `IsCurrent BIT`

On tariff change: old row `EffectiveTo = today-1`; new row inserted. See [[Known Limitations and Roadmap]] for the current triplicated-tariff issue.

### `ref_user_division_access` (RLS mapping)
`LoginName NVARCHAR(100)` | `DivisionKey TINYINT` | `Role NVARCHAR(20)` (`'Director'` or `'Teacher'`)

**Populated by `sql/provision_user.sql`** — one row per Director or Teacher login + each `DivisionKey` they may access. Used by `fn_division_security` to filter `fact_room_booking` rows. See [[Security and User Management]].

---

## Fact tables

| Table | Grain |
|---|---|
| `fact_solar_inverter` | `(DateKey, TimeKey, InverterKey)` |
| `fact_solar_production` | `(DateKey, TimeKey)` |
| `fact_energy_consumption` | `(DateKey, TimeKey)` |
| `fact_environment` | `(DateKey, TimeKey)` |
| `fact_weather_forecast` | `(DateKey, TimeKey, SiteKey, MeasurementKey, PredictionHorizon)` |
| `fact_room_booking` | Surrogate `BookingKey IDENTITY (PK)`; natural uniqueness on `(DateKey, StartTimeKey, RoomKey, ReservationNo)` |
| `fact_energy_prediction` | `(DateKey, TimeKey, ModelKey, PredictionRunDateKey)` |

**SQL-persisted computed columns (not in notebook INSERT lists):**
- `fact_solar_production.RetailValue_CHF = DeltaEnergy_Kwh × 0.15`
- `fact_energy_consumption.CostCHF = DeltaEnergy_Kwh × 0.15`
- `fact_room_booking.IsRecurring = CASE WHEN RecurrenceStart IS NOT NULL THEN 1 ELSE 0 END`

---

## Analytical views

### SAC export views
| View | Purpose |
|---|---|
| `vw_inverter_status_breakdown` | Daily inverter status distribution — `PctOfDayReadings` per status category |
| `vw_inverter_performance` | Actual AC power vs. rated capacity per inverter per day |
| `vw_prediction_accuracy` | MAPE of predicted vs. actual energy per model over time |

### Power BI dashboard views
| View | Dashboard target |
|---|---|
| `vw_daily_energy_balance` | Home tab — production vs. consumption time-series, net balance, self-sufficiency ratio, CHF costs |
| `vw_building_occupation` | Rooms tab — occupation % per room per academic day (denominator = 720 min teaching day) |
| `vw_kpi_dashboard_home` | Home tab — all five KPI cards in one query (consumption CHF, temperature, panel failure rate, occupation, humidity) |
| `vw_weather_vs_production` | Weather/Solar tab — irradiance forecast vs. actual PV output per 15-min slot |

---

## Stored procedure

`dbo.sp_backfill_prediction_actuals @TargetDate DATE`

Called by `ml_load_predictions.py` after each prediction load. Joins actuals from `fact_solar_production` and `fact_energy_consumption` back onto `fact_energy_prediction` rows, enabling `vw_prediction_accuracy` to track MAPE for past runs.

---

## Security model

Roles, RLS, and per-user provisioning are documented on a dedicated page: **[[Security and User Management]]**.

Quick summary:
- Three database roles: `Director_Role`, `Teacher_Role`, `Technician_Role`.
- Row-level security on `fact_room_booking` via `fn_division_security` + `ref_user_division_access`.
- New users are added with the idempotent `sql/provision_user.sql` script.

The base contained user `dev.admin.sql` (member of `Technician_Role`, password from Key Vault) is used by CI and admin tasks — see [[Secrets and Configuration]].

---

*For how data flows into this schema, see [[Databricks Notebooks]]. For the ML prediction table, see [[ML Lifecycle]]. For roles and user provisioning, see [[Security and User Management]].*
