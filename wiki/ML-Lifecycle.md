# ML Lifecycle

[[Home]] > ML Lifecycle

The pipeline produces daily energy consumption and solar production forecasts via two **Gradient Boosted Tree (GBT) regressors** deployed on a KNIME Server. The full cycle spans both daily trigger windows.

---

## Overview

```
07:15  PL_Ingest_Bronze
         └── ml_export_to_knime.py
               writes ──▶ mldata/knime_input/
                           ├── solar_production_features.csv
                           └── consumption_features.csv

09:30  PL_Upload_Pred_Gold
         ├── Run_Knime (KNIME REST)
         │     ├── Data_Preparation   (unconditional)
         │     ├── Model_Selection    (Mondays only)
         │     ├── Solar predictor    ┐ parallel
         │     └── Consumption pred.  ┘
         │           writes ──▶ mldata/knime_output/
         │                       ├── production_predictions.csv
         │                       └── consumption_predictions.csv
         │
         └── ml_load_predictions.py
               reads ──▶ mldata/knime_output/
               writes ──▶ fact_energy_prediction (Gold SQL)
               calls ──▶ sp_backfill_prediction_actuals
```

---

## Models

| Model | Target | Algorithm | Training window |
|---|---|---|---|
| `PV_PROD_V1` | `production_delta_kwh` | GBT regressor (100 trees, lr=0.1, max_depth=5) | 2023-02-20 → 2023-04-19 |
| `CONS_V1` | `consumption_delta_kwh` | GBT regressor (100 trees, lr=0.1, max_depth=5) | 2023-02-20 → 2023-04-19 |

Training is done manually inside **KNIME Analytics Platform** — the models are deployed to the KNIME Server as REST endpoints and are not retrained automatically. `Model_Selection` re-evaluates which algorithm performs best each Monday, but does not extend the training window (see [[Known Limitations and Roadmap]]).

---

## KNIME workflow source files

The `.knwf` workflow files for all four REST deployments are version-controlled in [`knime/`](https://github.com/sandersdHES/ADF_DataCycleProject/tree/main/knime). This makes the KNIME Server fully reproducible from the repo: deploy each workflow via KNIME Analytics Platform and re-register it as a REST endpoint using the deployment IDs below.

| Source file | REST deployment | Purpose |
|---|---|---|
| `knime/Data_Preparation.knwf` | `Data_Preparation` | Loads feature CSVs, prepares data for inference |
| `knime/Model_Selection.knwf` | `Model_Selection` | Re-evaluates which model version is active (Mondays) |
| `knime/REST_Interface_Solar.knwf` | `Solar predictor` | Runs `PV_PROD_V1` GBT inference |
| `knime/REST_Interface_Cons.knwf` | `Consumption predictor` | Runs `CONS_V1` GBT inference |

---

## KNIME REST deployments

| Step | Deployment ID | Source workflow | Cadence |
|---|---|---|---|
| `Data_Preparation` | `rest:e481f0fd-89ba-409a-aaa2-d8a648956949` | `Data_Preparation.knwf` | Every run |
| `Model_Selection` | `rest:509f9c76-1fd3-444d-80a6-4df7848b1621` | `Model_Selection.knwf` | **Mondays only** |
| `Consumption predictor` | `rest:348633fa-f10f-4a27-99de-11e1707190cb` | `REST_Interface_Cons.knwf` | Every run (parallel) |
| `Solar predictor` | `rest:eb96aa91-239b-4cf2-8c7e-a8a40516d4f3` | `REST_Interface_Solar.knwf` | Every run (parallel) |

`Model_Selection` is gated by `@pipeline().TriggerTime.DayOfWeek == 1` (Monday) in ADF. The Consumption and Solar predictors run **in parallel** after `Data_Preparation` completes.

**Authentication:** KNIME user `N8XZA3zjIJVLk-P2XxLKBkLv1_aT-bX302wwgIGOmrY` using `knime` / `knimeappid` / `knimeappsecret` pulled from Key Vault.

---

## Workflow details

### `Data_Preparation.knwf` — runs every cycle

Reads the two feature CSVs from ADLS Gen2, applies missing-value handling, row filtering, lag-column creation, and writes cleaned files back to ADLS for the predictor workflows.

![Data_Preparation KNIME workflow](https://raw.githubusercontent.com/sandersdHES/ADF_DataCycleProject/main/docs/assets/knime/data_preparation_workflow.png)

- **Top path (solar):** CSV Reader → Missing Value → Row Filter → Rule Engine → Lag Column → CSV Writer
- **Bottom path (consumption):** CSV Reader → Missing Value → Row Filter → Lag Column → CSV Writer

The **Rule Engine** step (solar path only) applies domain constraints before the lag is computed — e.g. zeroing out production readings outside daylight hours.

---

### `Model_Selection.knwf` — runs Mondays only

Re-trains and benchmarks **four candidate algorithms** (Gradient Boosted Trees, Linear Regression, Random Forest, Simple Regression Tree) against both the solar and consumption datasets, then picks and persists the best-scoring model for each target.

![Model_Selection top-level workflow](https://raw.githubusercontent.com/sandersdHES/ADF_DataCycleProject/main/docs/assets/knime/model_selection_overview.png)

Two CSV Readers (one per dataset) feed eight parallel learner components — four algorithms × two targets. Each algorithm block is a wrapped metanode sub-workflow:

![Random Forest learner metanode detail](https://raw.githubusercontent.com/sandersdHES/ADF_DataCycleProject/main/docs/assets/knime/model_selection_rf_detail.png)

Inside each metanode: **X-Partitioner** splits for cross-validation → **Learner** trains the model → **Predictor** scores the held-out fold → **X-Aggregator** collects results → **Numeric Scorer** computes RMSE/R² → **Table Transposer + Constant Value Column Appender** attach metadata → **Model Writer** persists the model.

After all eight metanodes finish, their metric rows are concatenated:

![Model_Selection output — best model selection](https://raw.githubusercontent.com/sandersdHES/ADF_DataCycleProject/main/docs/assets/knime/model_selection_output.png)

**Row Filter** keeps only the top-scoring row per target → **Table Row to Variable** extracts the winning model path → **Model Reader** loads the winner → **Model Writer** overwrites the active model slot used by the predictor workflows.

---

### `REST_Interface_Solar.knwf` and `REST_Interface_Cons.knwf` — run every cycle in parallel

Each workflow is a KNIME REST endpoint: receives no input parameters, reads everything from ADLS, and returns the prediction table as JSON via `Container Output`.

![REST Interface predictor workflow](https://raw.githubusercontent.com/sandersdHES/ADF_DataCycleProject/main/docs/assets/knime/rest_interface_workflow.png)

| Step | Purpose |
|---|---|
| **Microsoft Authenticator + ADLS Gen2 Connector** | Authenticate to Azure, open a file-system connection |
| **CSV Reader** | Load the prepared feature CSV from `mldata/knime_input/` |
| **Model Reader** | Load the active model written by `Model_Selection` (or the initial GBT from project setup) |
| **Missing Value** | Impute any remaining gaps before inference |
| **Random Forest Predictor (Regression)** | Score each 15-minute row |
| **Column Filter + Column Renamer** | Keep only timestamp + prediction columns and standardise names |
| **CSV Writer** | Write predictions to `mldata/knime_output/` for `ml_load_predictions.py` |
| **Table to JSON + Container Output (JSON)** | Return the prediction table as the REST response body |

---

## Feature sets

### Solar production features (`solar_production_features.csv`)

| Feature | Source | Notes |
|---|---|---|
| Irradiance (`PRED_GLOB_ctrl`) | `fact_weather_forecast` — synthetic Sierre site | Primary production driver |
| Temperature | `fact_environment` | Affects panel efficiency |
| Hour, Minute | Temporal | Position within day |
| Month | Temporal | Seasonal context |
| DayOfWeek, IsWeekend | Temporal | |
| QuarterHour (0–3 within hour) | Temporal | Sub-hour pattern |

### Consumption features (`consumption_features.csv`)

| Feature | Source | Notes |
|---|---|---|
| Temperature | `fact_environment` | Heating/cooling load |
| Humidity | `fact_environment` | |
| Precipitation (`PRED_TOT_PREC_ctrl`) | `fact_weather_forecast` | |
| `room_occupation_pct` | Computed from `fact_room_booking` | Occupancy drives consumption |
| `is_academic_day` | `dim_date` | Academic days have higher baseline consumption |
| Hour, Minute, Month, DayOfWeek, IsWeekend, QuarterHour | Temporal | |

**Weather interpolation:** Forecast data arrives at 3-hour granularity. `ml_export_to_knime.py` forward-fills via `Window.rowsBetween(unboundedPreceding, 0)` onto a 15-minute grid to align with production/consumption samples.

**Room occupation:** Each booking is exploded into 15-minute slots. `room_occupation_pct = distinct_rooms_occupied / total_rooms` per slot.

---

## Gold load & accuracy tracking

After KNIME writes prediction CSVs, `ml_load_predictions.py`:

1. **Resolves model keys** from `dim_prediction_model` using `ModelCode` (`PV_PROD_V1`, `CONS_V1`)
2. **Clamps negatives** — `MAX(predicted, 0)` (physical constraint: no negative production)
3. **Deletes today's run** — `DELETE FROM fact_energy_prediction WHERE PredictionRunDateKey = <today>` (idempotency)
4. **Inserts** the cleaned batch via JDBC
5. **Calls `sp_backfill_prediction_actuals`** once per distinct `DateKey` — this stored procedure joins actuals from `fact_solar_production` and `fact_energy_consumption` onto earlier prediction rows, populating `ActualValue`
6. **Updates `ml_models_config.json`** in ADLS if KNIME metadata (features, notes) changed

**MAPE tracking:** `vw_prediction_accuracy` joins `PredictedValue` vs `ActualValue` across all past `PredictionRunDateKey` values. Formula: `SUM(|Predicted − Actual|) / SUM(Actual)` — 0 = perfect, 1 = 100% average error.

---

## Configuration

`config/ml_models_config.json` (also in ADLS `config/` container) stores model metadata read by `silver_gold_dimensions.py` to seed `dim_prediction_model`. It is written back by `ml_load_predictions.py` whenever KNIME reports new feature lists or notes.

---

*For the notebook implementation details, see [[Databricks Notebooks]]. For the Gold schema for predictions, see [[Data Warehouse Schema]].*
