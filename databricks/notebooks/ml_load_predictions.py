# Databricks notebook source


# COMMAND ----------

# DBTITLE 1,Cell 2
# MAGIC %md
# MAGIC # 🤖 ML Import — KNIME Predictions → Gold DWH
# MAGIC
# MAGIC This notebook reads KNIME CSV outputs from ADLS (`/mldata/knime_output/`) and
# MAGIC loads them into the Gold table **`fact_energy_prediction`** (Azure SQL).
# MAGIC
# MAGIC It also executes the stored procedure **`sp_backfill_prediction_actuals`** to populate
# MAGIC the `ActualProduction_Kwh` / `ActualConsumption_Kwh` columns for days already
# MAGIC available in `fact_solar_production` / `fact_energy_consumption`.
# MAGIC
# MAGIC | Step | Action                                    | US   |
# MAGIC |------|-------------------------------------------|------|
# MAGIC | 1    | Read `production_predictions.csv` (KNIME) | US#28|
# MAGIC | 2    | Read `consumption_predictions.csv` (KNIME)| US#28|
# MAGIC | 3    | Resolve FKs (DateKey, TimeKey, ModelKey)  | US#31|
# MAGIC | 4    | Write to `fact_energy_prediction`         | US#31|
# MAGIC | 5    | Backfill actuals via stored procedure     | US#31|
# MAGIC | 6    | Update `ml_models_config.json`            | US#31|

# COMMAND ----------

# DBTITLE 1,Cell 3
# MAGIC %md
# MAGIC ## 0 · Configuration & Connection

# COMMAND ----------

# DBTITLE 1,Cell 4
import logging

from pyspark.sql.functions import (
    col, lit, to_timestamp, date_format,
    year, month, hour, minute,
    coalesce, when
)
from pyspark.sql import DataFrame
import time, json

logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(logging.INFO)

# ── ADLS ──────────────────────────────────────────────────────────────────────
storage_account_name = "adlsbellevuegrp3"
storage_account_key  = dbutils.secrets.get(scope="keyvault-scope", key="adls-access-key")

spark.conf.set(
    f"fs.azure.account.key.{storage_account_name}.dfs.core.windows.net",
    storage_account_key,
)

ml_base     = f"abfss://mldata@{storage_account_name}.dfs.core.windows.net"
config_base = f"abfss://config@{storage_account_name}.dfs.core.windows.net"

# ── Azure SQL Gold ─────────────────────────────────────────────────────────────
sql_server   = "sqlserver-bellevue-grp3"
sql_database = "DevDB"
sql_user     = "dylan.sanderso"
sql_password = dbutils.secrets.get(scope="keyvault-scope", key="Admin-SQL-Password")

jdbc_url = (
    f"jdbc:sqlserver://{sql_server}.database.windows.net:1433;"
    f"database={sql_database};encrypt=true;trustServerCertificate=false;"
    f"hostNameInCertificate=*.database.windows.net;loginTimeout=30"
)
jdbc_props = {
    "user":     sql_user,
    "password": sql_password,
    "driver":   "com.microsoft.sqlserver.jdbc.SQLServerDriver",
}

# ── KNIME model metadata ───────────────────────────────────────────────────────
# Must match ModelCode values in dim_prediction_model
MODEL_CODE_US29 = "PV_PROD_V1"    # production model
MODEL_CODE_US30 = "CONS_V1"       # consumption model

# ── Helpers (same pattern as silver_gold_facts.py) ───────────────────────────
def _jdbc_retry(fn, max_attempts: int = 5, initial_wait: int = 20):
    wait = initial_wait
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as e:
            msg = str(e)
            if "not currently available" in msg or "connection" in msg.lower():
                if attempt == max_attempts:
                    raise
                logger.warning(
                    "Azure SQL waking up (attempt %d/%d) — retrying in %ds...",
                    attempt, max_attempts, wait,
                )
                time.sleep(wait)
                wait += initial_wait
            else:
                raise


def read_gold(table: str) -> DataFrame:
    return _jdbc_retry(
        lambda: spark.read.jdbc(url=jdbc_url, table=table, properties=jdbc_props)
    )


def write_gold(df: DataFrame, table: str, batch_size: int = 20_000):
    (df.write
       .mode("append")
       .option("batchsize", batch_size)
       .option("numPartitions", 4)
       .option("truncate", "false")
       .jdbc(url=jdbc_url, table=table, properties=jdbc_props))


def exec_sql(statement: str):
    def _run():
        conn = spark._jvm.java.sql.DriverManager.getConnection(
            jdbc_url, sql_user, sql_password
        )
        try:
            stmt = conn.createStatement()
            stmt.execute(statement)
        finally:
            conn.close()
    _jdbc_retry(_run)


def ts_to_datekey(ts_col):
    return date_format(ts_col, "yyyyMMdd").cast("int")


def ts_to_timekey(ts_col):
    return (hour(ts_col) * 60 + minute(ts_col)).cast("short")


logger.info("Configuration loaded.")
logger.info("   ML input/output : %s", ml_base)
logger.info("   Gold (Azure SQL): %s.database.windows.net / %s", sql_server, sql_database)

# COMMAND ----------

# DBTITLE 1,Cell 5
# MAGIC %md
# MAGIC ## 1 · Reading KNIME Predictions

# COMMAND ----------

# DBTITLE 1,Cell 6
# MAGIC %md
# MAGIC ### 1A · Production (US#29) — `production_predictions.csv`

# COMMAND ----------

# DBTITLE 1,Cell 7
df_prod_raw = (
    spark.read
    .option("header", "true")
    .option("inferSchema", "true")
    .csv(f"{ml_base}/knime_output/production_predictions.csv")
)

# Validate expected columns
expected_cols_prod = {"timestamp", "predicted_production_kwh"}
actual_cols_prod   = set(df_prod_raw.columns)
missing_prod       = expected_cols_prod - actual_cols_prod

if missing_prod:
    raise ValueError(
        f"production_predictions.csv — missing columns: {missing_prod}\n"
        f"   Columns found: {actual_cols_prod}\n"
        f"   Check the 'Column Rename' configuration in KNIME workflow US#29."
    )

df_prod_preds = (
    df_prod_raw
    .withColumn("ts", to_timestamp(col("timestamp"), "yyyy-MM-dd HH:mm:ss"))
    .withColumn("predicted_production_kwh",
        col("predicted_production_kwh").cast("double"))
    # Clamp negative predictions (physically impossible for solar production)
    .withColumn("predicted_production_kwh",
        when(col("predicted_production_kwh") < 0, lit(0.0))
        .otherwise(col("predicted_production_kwh")))
    .filter(col("ts").isNotNull())
    .dropDuplicates(["ts"])
    .orderBy("ts")
)

logger.info("production_predictions: %s rows", f"{df_prod_preds.count():,}")
df_prod_preds.show(3, truncate=False)

# COMMAND ----------

# DBTITLE 1,Cell 8
# MAGIC %md
# MAGIC ### 1B · Consumption (US#30) — `consumption_predictions.csv`

# COMMAND ----------

# DBTITLE 1,Cell 9
df_conso_raw = (
    spark.read
    .option("header", "true")
    .option("inferSchema", "true")
    .csv(f"{ml_base}/knime_output/consumption_predictions.csv")
)

expected_cols_conso = {"timestamp", "predicted_consumption_kwh"}
actual_cols_conso   = set(df_conso_raw.columns)
missing_conso       = expected_cols_conso - actual_cols_conso

if missing_conso:
    raise ValueError(
        f"consumption_predictions.csv — missing columns: {missing_conso}\n"
        f"   Columns found: {actual_cols_conso}\n"
        f"   Check the 'Column Rename' configuration in KNIME workflow US#30."
    )

df_conso_preds = (
    df_conso_raw
    .withColumn("ts", to_timestamp(col("timestamp"), "yyyy-MM-dd HH:mm:ss"))
    .withColumn("predicted_consumption_kwh",
        col("predicted_consumption_kwh").cast("double"))
    # Clamp negative predictions (consumption cannot be negative)
    .withColumn("predicted_consumption_kwh",
        when(col("predicted_consumption_kwh") < 0, lit(0.0))
        .otherwise(col("predicted_consumption_kwh")))
    .filter(col("ts").isNotNull())
    .dropDuplicates(["ts"])
    .orderBy("ts")
)

logger.info("consumption_predictions: %s rows", f"{df_conso_preds.count():,}")
df_conso_preds.show(3, truncate=False)

# COMMAND ----------

# DBTITLE 1,Cell 10
# MAGIC %md
# MAGIC ## 2 · Resolving Foreign Keys
# MAGIC
# MAGIC `fact_energy_prediction` requires:
# MAGIC - `DateKey`              → from `dim_date` (YYYYMMDD int)
# MAGIC - `TimeKey`              → minutes since midnight (SMALLINT)
# MAGIC - `ModelKey`             → from `dim_prediction_model` (via ModelCode)
# MAGIC - `PredictionRunDateKey` → pipeline execution date (= today)

# COMMAND ----------

# DBTITLE 1,Cell 11
import datetime

# Pipeline execution date (today)
run_date_key = int(datetime.date.today().strftime("%Y%m%d"))
logger.info("   PredictionRunDateKey: %d", run_date_key)

# Retrieve ModelKey from dim_prediction_model
df_models = read_gold("dim_prediction_model").select("ModelKey", "ModelCode").cache()
models_map = {row["ModelCode"]: row["ModelKey"] for row in df_models.collect()}

model_key_us29 = models_map.get(MODEL_CODE_US29)
model_key_us30 = models_map.get(MODEL_CODE_US30)

if model_key_us29 is None:
    raise ValueError(
        f"ModelCode '{MODEL_CODE_US29}' not found in dim_prediction_model.\n"
        f"   Available models: {list(models_map.keys())}\n"
        f"   Run silver_gold_dimensions.py to initialize the dimension."
    )
if model_key_us30 is None:
    raise ValueError(
        f"ModelCode '{MODEL_CODE_US30}' not found in dim_prediction_model.\n"
        f"   Available models: {list(models_map.keys())}\n"
        f"   Run silver_gold_dimensions.py to initialize the dimension."
    )

logger.info("ModelKey US#29 (production)  : %s  [%s]", model_key_us29, MODEL_CODE_US29)
logger.info("ModelKey US#30 (consumption) : %s  [%s]", model_key_us30, MODEL_CODE_US30)
df_models.unpersist()

# COMMAND ----------

# DBTITLE 1,Cell 12
# MAGIC %md
# MAGIC ## 3 · Building `fact_energy_prediction` Rows
# MAGIC
# MAGIC Strategy: **Full replace by PredictionRunDateKey**.
# MAGIC If this pipeline is re-executed on the same day, the old predictions from that day
# MAGIC are first deleted and then reinserted (idempotency).
# MAGIC
# MAGIC Both models (US#29 and US#30) share the same table but have separate rows:
# MAGIC NULL column for the non-relevant model.

# COMMAND ----------

# DBTITLE 1,Cell 13
# Delete predictions already inserted for today's run (idempotency)
exec_sql(f"""
    DELETE FROM fact_energy_prediction
    WHERE PredictionRunDateKey = {run_date_key}
""")
logger.info("Existing predictions for RunDateKey=%d deleted.", run_date_key)

# COMMAND ----------

# DBTITLE 1,Cell 14
# MAGIC %md
# MAGIC ### 3A · Production rows (US#29 model)

# COMMAND ----------

# DBTITLE 1,Cell 15
df_fact_prod = (
    df_prod_preds
    .withColumn("DateKey",             ts_to_datekey(col("ts")))
    .withColumn("TimeKey",             ts_to_timekey(col("ts")))
    .withColumn("ModelKey",            lit(model_key_us29).cast("byte"))
    .withColumn("PredictionRunDateKey", lit(run_date_key).cast("int"))
    .withColumn("PredictedProduction_Kwh",
        col("predicted_production_kwh").cast("double"))
    .withColumn("PredictedConsumption_Kwh", lit(None).cast("double"))  # NULL — not this model
    .withColumn("ActualProduction_Kwh",     lit(None).cast("double"))  # backfilled later
    .withColumn("ActualConsumption_Kwh",    lit(None).cast("double"))  # backfilled later
    .select(
        "DateKey", "TimeKey", "ModelKey", "PredictionRunDateKey",
        "PredictedProduction_Kwh", "PredictedConsumption_Kwh",
        "ActualProduction_Kwh",    "ActualConsumption_Kwh",
    )
    .dropDuplicates(["DateKey", "TimeKey", "ModelKey"])
)

n_prod = df_fact_prod.count()
write_gold(df_fact_prod, "fact_energy_prediction")
logger.info("fact_energy_prediction (production)  : %s rows inserted.", f"{n_prod:,}")

# COMMAND ----------

# DBTITLE 1,Cell 16
# MAGIC %md
# MAGIC ### 3B · Consumption rows (US#30 model)

# COMMAND ----------

# DBTITLE 1,Cell 17
df_fact_conso = (
    df_conso_preds
    .withColumn("DateKey",             ts_to_datekey(col("ts")))
    .withColumn("TimeKey",             ts_to_timekey(col("ts")))
    .withColumn("ModelKey",            lit(model_key_us30).cast("byte"))
    .withColumn("PredictionRunDateKey", lit(run_date_key).cast("int"))
    .withColumn("PredictedProduction_Kwh",  lit(None).cast("double"))  # NULL — not this model
    .withColumn("PredictedConsumption_Kwh",
        col("predicted_consumption_kwh").cast("double"))
    .withColumn("ActualProduction_Kwh",  lit(None).cast("double"))  # backfilled later
    .withColumn("ActualConsumption_Kwh", lit(None).cast("double"))  # backfilled later
    .select(
        "DateKey", "TimeKey", "ModelKey", "PredictionRunDateKey",
        "PredictedProduction_Kwh", "PredictedConsumption_Kwh",
        "ActualProduction_Kwh",    "ActualConsumption_Kwh",
    )
    .dropDuplicates(["DateKey", "TimeKey", "ModelKey"])
)

n_conso = df_fact_conso.count()
write_gold(df_fact_conso, "fact_energy_prediction")
logger.info("fact_energy_prediction (consumption): %s rows inserted.", f"{n_conso:,}")

# COMMAND ----------

# DBTITLE 1,Cell 18
# MAGIC %md
# MAGIC ## 4 · Backfilling Actuals
# MAGIC
# MAGIC For each day where `fact_solar_production` / `fact_energy_consumption` have already
# MAGIC been loaded, the stored procedure `sp_backfill_prediction_actuals` fills the
# MAGIC `ActualProduction_Kwh` and `ActualConsumption_Kwh` columns in `fact_energy_prediction`.
# MAGIC
# MAGIC The procedure is called for all days covered by the KNIME predictions.

# COMMAND ----------

# DBTITLE 1,Cell 19
# Collect distinct dates from the inserted predictions
dates_prod  = [row["DateKey"] for row in df_fact_prod.select("DateKey").distinct().collect()]
dates_conso = [row["DateKey"] for row in df_fact_conso.select("DateKey").distinct().collect()]
all_dates   = sorted(set(dates_prod) | set(dates_conso))

logger.info("   Dates to backfill: %d days", len(all_dates))

backfill_ok = 0
for dk in all_dates:
    # Convert YYYYMMDD int → DATE string
    date_str = f"{str(dk)[:4]}-{str(dk)[4:6]}-{str(dk)[6:8]}"
    try:
        exec_sql(f"EXEC dbo.sp_backfill_prediction_actuals @TargetDate = '{date_str}'")
        backfill_ok += 1
    except Exception as e:
        # Non-fatal: actuals for the day may not be available yet
        logger.warning("   Backfill skipped for %s: %s", date_str, e)

logger.info("Backfill completed: %d/%d days processed.", backfill_ok, len(all_dates))

# COMMAND ----------

# DBTITLE 1,Cell 20
# MAGIC %md
# MAGIC ## 5 · Updating `ml_models_config.json`
# MAGIC
# MAGIC Updates `ModelType` in the ADLS config file to reflect the
# MAGIC algorithms actually used. `silver_gold_dimensions.py` will propagate
# MAGIC these values to `dim_prediction_model` during its next execution.

# COMMAND ----------

# DBTITLE 1,Cell 21
config_path = f"{ml_base}/ml_models_config.json"

# Read existing config (or use default values if absent)
try:
    raw = dbutils.fs.head(config_path, 65536)
    models_cfg = json.loads(raw)
    logger.info("Existing ML config loaded (%d models).", len(models_cfg))
except Exception:
    models_cfg = []
    logger.warning("ML config not found — creating new config.")

# Metadata for the KNIME models actually used
KNIME_MODELS_META = {
    MODEL_CODE_US29: {
        "ModelCode":        MODEL_CODE_US29,
        "ModelName":        "Solar Production Prediction v1 (KNIME Random Forest)",
        "ModelType":        "GradientBoostedTrees",
        "TargetVariable":   "Production_Kwh",
        "Features":         "irradiance_wm2, temp_c, hour, minute, month, day_of_week, is_weekend, quarter_hour",
        "TrainingStartDate": "2023-02-20",
        "TrainingEndDate":   "2023-04-19",   # ~80% of the dataset
        "IsActive":          1,
        "Notes":             (
            "US#29 — Gradient Boosted Trees Regressor (100 trees, lr=0.1, max_depth=5) "
            "Trained in KNIME Analytics Platform. "
            "Input: solar_production_features.csv from ADLS /ml/knime_input/. "
            "Output: production_predictions.csv to ADLS /ml/knime_output/."
        ),
    },
    MODEL_CODE_US30: {
        "ModelCode":        MODEL_CODE_US30,
        "ModelName":        "Building Consumption Prediction v1 (KNIME Gradient Boosted Trees)",
        "ModelType":        "GradientBoostedTrees",
        "TargetVariable":   "Consumption_Kwh",
        "Features":         "temp_c, humidity_pct, precipitation_kgm2, room_occupation_pct, hour, minute, month, day_of_week, is_weekend, is_academic_day, quarter_hour",
        "TrainingStartDate": "2023-02-20",
        "TrainingEndDate":   "2023-04-19",
        "IsActive":          1,
        "Notes":             (
            "US#30 — Gradient Boosted Trees Regressor (100 trees, lr=0.1, max_depth=5). "
            "Trained in KNIME Analytics Platform. "
            "Input: consumption_features.csv from ADLS /ml/knime_input/. "
            "Output: consumption_predictions.csv to ADLS /ml/knime_output/."
        ),
    },
}

# Merge: update existing entries or add new ones
existing_codes = {m["ModelCode"]: i for i, m in enumerate(models_cfg)}
for code, meta in KNIME_MODELS_META.items():
    if code in existing_codes:
        models_cfg[existing_codes[code]].update(meta)
        logger.info("Config updated: '%s'", code)
    else:
        models_cfg.append(meta)
        logger.info("Config added  : '%s'", code)

# Write updated config to ADLS
updated_json = json.dumps(models_cfg, indent=2, ensure_ascii=False)
dbutils.fs.put(config_path, updated_json, overwrite=True)
logger.info("ml_models_config.json written -> %s", config_path)

# COMMAND ----------

# DBTITLE 1,Cell 22
# MAGIC %md
# MAGIC ## 6 · Final Verification

# COMMAND ----------

# DBTITLE 1,Cell 23
logger.info("=" * 70)
logger.info("SUMMARY — ml_load_predictions.py (US#28 + US#31)")
logger.info("=" * 70)

# Count by model in fact_energy_prediction
df_check = spark.read.jdbc(
    url=jdbc_url,
    table=(
        "(SELECT m.ModelCode, m.ModelType, COUNT(*) AS Rows, "
        " MIN(d.FullDate) AS DateMin, MAX(d.FullDate) AS DateMax "
        " FROM fact_energy_prediction fp "
        " JOIN dim_prediction_model m ON m.ModelKey = fp.ModelKey "
        " JOIN dim_date d ON d.DateKey = fp.DateKey "
        f" WHERE fp.PredictionRunDateKey = {run_date_key} "
        " GROUP BY m.ModelCode, m.ModelType) t"
    ),
    properties=jdbc_props,
)

df_check.show(truncate=False)

# Count rows with backfilled actuals
df_actuals = spark.read.jdbc(
    url=jdbc_url,
    table=(
        "(SELECT "
        " SUM(CASE WHEN ActualProduction_Kwh  IS NOT NULL THEN 1 ELSE 0 END) AS ProdActuals, "
        " SUM(CASE WHEN ActualConsumption_Kwh IS NOT NULL THEN 1 ELSE 0 END) AS ConsoActuals, "
        " COUNT(*) AS Total "
        f" FROM fact_energy_prediction WHERE PredictionRunDateKey = {run_date_key}) t"
    ),
    properties=jdbc_props,
)

row = df_actuals.collect()[0]
logger.info("   Total rows inserted     : %s", f"{row['Total']:,}")
logger.info("   Production actuals      : %s", f"{row['ProdActuals']:,}")
logger.info("   Consumption actuals     : %s", f"{row['ConsoActuals']:,}")
logger.info("Complete ML pipeline — fact_energy_prediction up to date.")
logger.info("   -> vw_prediction_accuracy is now populated for Power BI.")
logger.info("=" * 70)
