# Databricks notebook source


# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC # 🤖 ML Export — Feature Engineering for KNIME
# MAGIC
# MAGIC This notebook reads **Silver** data (Parquet on ADLS) and produces two CSV files
# MAGIC in the **`mldata`** container (`abfss://mldata@.../knime_input/`) ready to be consumed by KNIME.
# MAGIC
# MAGIC | CSV File                                      | ML Target        | User Story |
# MAGIC |-----------------------------------------------|------------------|------------|
# MAGIC | `knime_input/solar_production_features.csv`   | PV Production    | US#29      |
# MAGIC | `knime_input/consumption_features.csv`        | Consumption      | US#30      |
# MAGIC
# MAGIC ### Silver Sources Used
# MAGIC | Silver Source         | Usage                                        |
# MAGIC |-----------------------|----------------------------------------------|
# MAGIC | `solar_aggregated/`   | US#29 Target: `production_delta_kwh`         |
# MAGIC | `weather_forecasts/`  | Weather features (irradiance, temp, humidity)|
# MAGIC | `consumption/`        | US#30 Target: `consumption_delta_kwh`        |
# MAGIC | `bookings/`           | US#30 Feature: room occupation rate          |
# MAGIC
# MAGIC ### Output Format Expected by KNIME
# MAGIC Both CSVs are written as **a single file** (coalesce 1) with header, `,` separator
# MAGIC and UTF-8 encoding. The `timestamp` field serves as the join key in KNIME.
# MAGIC
# MAGIC > **Expected KNIME Output** (for US#31 import):
# MAGIC > - `knime_output/production_predictions.csv`: columns `timestamp`, `predicted_production_kwh`
# MAGIC > - `knime_output/consumption_predictions.csv`: columns `timestamp`, `predicted_consumption_kwh`

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ## 0 · Configuration & ADLS Connection

# COMMAND ----------

# DBTITLE 1,Cell 4
import logging

from pyspark.sql.functions import (
    col, lit, year, month, hour, minute, dayofweek,
    when, coalesce, to_timestamp, date_format,
    regexp_replace, regexp_extract, translate,
    concat_ws, mean as spark_mean, count as spark_count,
    explode, sequence, expr
)
from pyspark.sql.window import Window
from pyspark.sql import DataFrame
import datetime

logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(logging.INFO)

storage_account_name = "adlsbellevuegrp3"
storage_account_key  = dbutils.secrets.get(scope="keyvault-scope", key="adls-access-key")

spark.conf.set(
    f"fs.azure.account.key.{storage_account_name}.dfs.core.windows.net",
    storage_account_key,
)

silver_base = f"abfss://silver@{storage_account_name}.dfs.core.windows.net"
ml_base     = f"abfss://mldata@{storage_account_name}.dfs.core.windows.net"

logger.info("Silver : %s", silver_base)
logger.info("ML     : %s", ml_base)

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ## 1 · Loading Silver Data

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ### 1A · Solar aggregated — US#29 target

# COMMAND ----------

# DBTITLE 1,Untitled
df_solar = (
    spark.read.parquet(f"{silver_base}/solar_aggregated/")
    .filter(col("timestamp").isNotNull())
    .filter(col("delta_value").isNotNull())
    # Exclude outliers (negative production is physically impossible)
    .filter(col("delta_value") >= 0)
    .select(
        col("timestamp"),
        col("delta_value").cast("double").alias("production_delta_kwh"),
    )
    .dropDuplicates(["timestamp"])
    .orderBy("timestamp")
)

logger.info("solar_aggregated   : %s rows", f"{df_solar.count():,}")
df_solar.show(3, truncate=False)

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ### 1B · Energy consumption — US#30 target

# COMMAND ----------

# DBTITLE 1,Untitled
df_conso = (
    spark.read.parquet(f"{silver_base}/consumption/")
    .filter(col("timestamp").isNotNull())
    .filter(col("delta_value").isNotNull())
    # Exclude meter resets (null set by silver_transformation.py)
    .filter(col("delta_value") >= 0)
    .select(
        col("timestamp"),
        col("delta_value").cast("double").alias("consumption_delta_kwh"),
    )
    .dropDuplicates(["timestamp"])
    .orderBy("timestamp")
)

logger.info("consumption        : %s rows", f"{df_conso.count():,}")
df_conso.show(3, truncate=False)

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ### 1C · Weather forecasts — common weather features for both models
# MAGIC
# MAGIC We use the **shortest available prediction horizon** per measurement.
# MAGIC Horizon 0 (analysis) provides valid data for temperature and humidity,
# MAGIC but returns sentinel values (`-99999.0`) for irradiance and precipitation
# MAGIC → for those, we fall back to horizon 1 (first forecast step).
# MAGIC
# MAGIC Data is in **3-hour** granularity → interpolated to **15 minutes** by forward-fill.
# MAGIC
# MAGIC | Measurement Code     | Exported Feature       | Valid Horizon | Model      |
# MAGIC |----------------------|------------------------|---------------|------------|
# MAGIC | `PRED_GLOB_ctrl`     | `irradiance_wm2`       | 1+            | US#29      |
# MAGIC | `PRED_T_2M_ctrl`     | `temp_c`               | 0             | US#29 + 30 |
# MAGIC | `PRED_RELHUM_2M_ctrl`| `humidity_pct`         | 0             | US#30      |
# MAGIC | `PRED_TOT_PREC_ctrl` | `precipitation_kgm2`   | 1+            | US#30      |

# COMMAND ----------

# DBTITLE 1,Untitled
df_weather_raw = (
    spark.read.parquet(f"{silver_base}/weather_forecasts/")
    .filter(col("Time").isNotNull())
    .filter(col("Site") == "Sierre")
    # Remove meteorological sentinel value (-99999.0 = no data for this horizon)
    .filter(col("Value").cast("double") != -99999.0)
    .select(
        col("Time").cast("timestamp").alias("timestamp_3h"),
        col("Measurement"),
        col("Prediction").cast("int").alias("prediction_horizon"),
        col("Value").cast("double").alias("value"),
    )
)

# For each timestamp × measurement, keep the shortest prediction horizon
# (closest to analysis). Horizon 0 has valid data for temp/humidity;
# irradiance and precipitation only start from horizon 1.
df_weather_best = (
    df_weather_raw
    .withColumn(
        "_rn",
        expr("ROW_NUMBER() OVER (PARTITION BY timestamp_3h, Measurement ORDER BY prediction_horizon)"),
    )
    .filter(col("_rn") == 1)
    .drop("_rn", "prediction_horizon")
)

# Pivot: one column per measurement type
df_weather_pivot = (
    df_weather_best
    .groupBy("timestamp_3h")
    .pivot("Measurement", [
        "PRED_GLOB_ctrl",
        "PRED_T_2M_ctrl",
        "PRED_RELHUM_2M_ctrl",
        "PRED_TOT_PREC_ctrl",
    ])
    .agg(spark_mean("value"))
    .withColumnRenamed("PRED_GLOB_ctrl",       "irradiance_wm2")
    .withColumnRenamed("PRED_T_2M_ctrl",       "temp_c")
    .withColumnRenamed("PRED_RELHUM_2M_ctrl",  "humidity_pct")
    .withColumnRenamed("PRED_TOT_PREC_ctrl",   "precipitation_kgm2")
    .orderBy("timestamp_3h")
)

logger.info("weather (3h pivot) : %s rows", f"{df_weather_pivot.count():,}")
df_weather_pivot.show(3, truncate=False)

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ### 1D · Weather interpolation 3h → 15 min (forward-fill)
# MAGIC
# MAGIC Weather data is available every 3 hours. To join it with production/consumption
# MAGIC data at 15-min intervals, we generate a 15-min grid across the entire time range,
# MAGIC then apply **forward-fill** (last observation carried forward).

# COMMAND ----------

# DBTITLE 1,Untitled
# 15-minute grid covering entire data range
ts_min = df_weather_pivot.agg({"timestamp_3h": "min"}).collect()[0][0]
ts_max = df_weather_pivot.agg({"timestamp_3h": "max"}).collect()[0][0]

# Generate each 15-min slot between ts_min and ts_max
df_grid_15min = (
    spark.range(0, int((ts_max - ts_min).total_seconds() // 900) + 1)
    .select(
        expr(f"timestamp '{ts_min}' + (id * interval 15 minutes)").alias("timestamp")
    )
)

# Left join grid → weather 3h (only full slots have direct values)
df_weather_joined = (
    df_grid_15min
    .join(
        df_weather_pivot.withColumnRenamed("timestamp_3h", "timestamp"),
        on="timestamp",
        how="left",
    )
)

# Forward-fill: for each weather column, propagate last known value
w_ff = Window.orderBy("timestamp").rowsBetween(Window.unboundedPreceding, 0)

df_weather_15min = (
    df_weather_joined
    .withColumn("irradiance_wm2",     coalesce(col("irradiance_wm2"),    lit(None)))
    .withColumn("irradiance_wm2",     spark_mean("irradiance_wm2").over(w_ff))
    .withColumn("temp_c",             coalesce(col("temp_c"),            lit(None)))
    .withColumn("temp_c",             spark_mean("temp_c").over(w_ff))
    .withColumn("humidity_pct",       coalesce(col("humidity_pct"),      lit(None)))
    .withColumn("humidity_pct",       spark_mean("humidity_pct").over(w_ff))
    .withColumn("precipitation_kgm2", coalesce(col("precipitation_kgm2"), lit(None)))
    .withColumn("precipitation_kgm2", spark_mean("precipitation_kgm2").over(w_ff))
    .filter(col("irradiance_wm2").isNotNull())  # Remove slots before first weather measurement
)

logger.info("weather (15min ff) : %s rows", f"{df_weather_15min.count():,}")
df_weather_15min.show(3, truncate=False)

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ### 1E · Room occupation — US#30 feature
# MAGIC
# MAGIC For each 15-min slot, calculate the **occupation rate** of VS-BEL rooms:
# MAGIC `room_occupation_pct = occupied_rooms / total_unique_rooms`
# MAGIC
# MAGIC Approach:
# MAGIC 1. Reconstruct start/end timestamps for each booking
# MAGIC 2. Generate all 15-min slots covered by each booking
# MAGIC 3. `COUNT DISTINCT(room)` per slot → divide by total known rooms

# COMMAND ----------

# DBTITLE 1,Untitled
df_bookings_raw = (
    spark.read.parquet(f"{silver_base}/bookings/")
    .filter(col("Nom").isNotNull())
    .filter(col("Date").isNotNull())
    .filter(col("Heure_Debut").isNotNull())
    .filter(col("Heure_Fin").isNotNull())
    .select("Date", "Heure_Debut", "Heure_Fin", "Nom")
)

# Convert French dates → start and end timestamps.
# Source values from bookings CSV — do not translate (regex matches actual French data).
french_months_map = [
    ("janv\\.", "Jan"), ("févr\\.", "Feb"), ("mars", "Mar"),
    ("avr\\.",  "Apr"), ("mai",     "May"), ("juin", "Jun"),
    ("juil\\.", "Jul"), ("août",    "Aug"), ("sept\\.", "Sep"),
    ("oct\\.",  "Oct"), ("nov\\.",  "Nov"), ("déc\\.", "Dec"),
]

def french_to_english(c):
    result = c
    for fr, en in french_months_map:
        result = regexp_replace(result, fr, en)
    return result


df_bookings = (
    df_bookings_raw
    .withColumn("date_en",  french_to_english(col("Date")))
    .withColumn("date_parsed",
        expr("try_to_timestamp(concat(date_en, ' ', Heure_Debut), 'd MMM yyyy HH:mm')")
    )
    .withColumn("end_parsed",
        expr("try_to_timestamp(concat(date_en, ' ', Heure_Fin),   'd MMM yyyy HH:mm')")
    )
    .filter(col("date_parsed").isNotNull() & col("end_parsed").isNotNull())
    .filter(col("end_parsed") > col("date_parsed"))   # Positive duration
    .select("date_parsed", "end_parsed", col("Nom").alias("room_code"))
)

# Total distinct known rooms (denominator for occupation rate)
total_rooms = df_bookings.select("room_code").distinct().count()
logger.info("Total distinct rooms: %d", total_rooms)

# Generate all 15-min slots covered by each booking
# Each slot = timestamp rounded down to the nearest 15-min where the room is occupied
df_booking_slots = (
    df_bookings
    .withColumn(
        "slot",
        explode(
            sequence(
                # Round down to 15-min
                expr("timestamp_seconds(floor(unix_timestamp(date_parsed) / 900) * 900)"),
                # Exclusive end → stop at slot before
                expr("timestamp_seconds(floor(unix_timestamp(end_parsed)   / 900) * 900)"),
                expr("interval 15 minutes"),
            )
        )
    )
    .select("slot", "room_code")
)

# Occupation rate per 15-min slot
df_occupation = (
    df_booking_slots
    .groupBy("slot")
    .agg(
        expr("count(DISTINCT room_code)").alias("rooms_occupied")
    )
    .withColumn(
        "room_occupation_pct",
        (col("rooms_occupied") / lit(total_rooms)).cast("double"),
    )
    .select(
        col("slot").alias("timestamp"),
        col("room_occupation_pct"),
    )
)

logger.info("room occupation    : %s slots", f"{df_occupation.count():,}")
df_occupation.show(3, truncate=False)

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ## 2 · Temporal Feature Engineering (helper)

# COMMAND ----------

# DBTITLE 1,Untitled
def add_time_features(df: DataFrame, ts_col: str = "timestamp") -> DataFrame:
    """
    Add common temporal features for both models.
    - hour          : 0–23
    - minute        : 0, 15, 30, 45
    - month         : 1–12
    - day_of_week   : 1=Sunday … 7=Saturday (Spark convention)
    - is_weekend    : 1 if Saturday or Sunday
    - is_academic_day : 1 if Monday–Friday (academic period Feb–May 2023)
    - quarter_hour  : daily slot index 0–95 (identifies the 15-min slot in the day)
    """
    return (
        df
        .withColumn("hour",           hour(col(ts_col)).cast("int"))
        .withColumn("minute",         minute(col(ts_col)).cast("int"))
        .withColumn("month",          month(col(ts_col)).cast("int"))
        .withColumn("day_of_week",    dayofweek(col(ts_col)).cast("int"))   # 1=Sun, 7=Sat
        .withColumn("is_weekend",
            when(dayofweek(col(ts_col)).isin(1, 7), 1).otherwise(0).cast("int"))
        .withColumn("is_academic_day",
            # Monday–Friday during dataset period (Feb–May 2023)
            when(
                (dayofweek(col(ts_col)).isin(1, 7) == False),
                1
            ).otherwise(0).cast("int"))
        .withColumn("quarter_hour",
            (col("hour") * 4 + col("minute") / 15).cast("int"))
    )

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ## 3 · Building US#29 Dataset — Solar Production
# MAGIC
# MAGIC Join:
# MAGIC `solar_aggregated` ⟕ `weather_15min`
# MAGIC
# MAGIC Features: `irradiance_wm2`, `temp_c`, `hour`, `minute`, `month`,
# MAGIC           `day_of_week`, `is_weekend`, `quarter_hour`
# MAGIC Target:   `production_delta_kwh`

# COMMAND ----------

# DBTITLE 1,Untitled
df_us29 = (
    df_solar
    # Inner join: only keep slots where both sources have data
    .join(df_weather_15min, on="timestamp", how="inner")
    .transform(lambda df: add_time_features(df, "timestamp"))
    .withColumn("timestamp_str", date_format(col("timestamp"), "yyyy-MM-dd HH:mm:ss"))
    .select(
        # Temporal identifier
        col("timestamp_str").alias("timestamp"),
        # Weather features
        col("irradiance_wm2"),
        col("temp_c"),
        # Temporal features
        col("hour"),
        col("minute"),
        col("month"),
        col("day_of_week"),
        col("is_weekend"),
        col("quarter_hour"),
        # Target variable
        col("production_delta_kwh"),
    )
    .dropna(subset=["production_delta_kwh", "irradiance_wm2", "temp_c"])
    .orderBy("timestamp")
)

n_us29 = df_us29.count()
logger.info("US#29 dataset : %s rows", f"{n_us29:,}")
logger.info(
    "   Period       : %s -> %s",
    df_us29.agg({'timestamp': 'min'}).collect()[0][0],
    df_us29.agg({'timestamp': 'max'}).collect()[0][0],
)
df_us29.show(5, truncate=False)

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ## 4 · Building US#30 Dataset — Energy Consumption
# MAGIC
# MAGIC Join:
# MAGIC `consumption` ⟕ `weather_15min` ⟕ `room_occupation`
# MAGIC
# MAGIC Features: `temp_c`, `humidity_pct`, `precipitation_kgm2`, `room_occupation_pct`,
# MAGIC           `hour`, `minute`, `month`, `day_of_week`, `is_weekend`, `is_academic_day`, `quarter_hour`
# MAGIC Target:   `consumption_delta_kwh`

# COMMAND ----------

# DBTITLE 1,Untitled
df_us30 = (
    df_conso
    # Inner join weather
    .join(df_weather_15min, on="timestamp", how="inner")
    # Left join occupation (0 if no booking found)
    .join(df_occupation, on="timestamp", how="left")
    .withColumn("room_occupation_pct",
        coalesce(col("room_occupation_pct"), lit(0.0)))
    .transform(lambda df: add_time_features(df, "timestamp"))
    .withColumn("timestamp_str", date_format(col("timestamp"), "yyyy-MM-dd HH:mm:ss"))
    .select(
        # Temporal identifier
        col("timestamp_str").alias("timestamp"),
        # Weather features
        col("temp_c"),
        col("humidity_pct"),
        col("precipitation_kgm2"),
        # Occupation feature
        col("room_occupation_pct"),
        # Temporal features
        col("hour"),
        col("minute"),
        col("month"),
        col("day_of_week"),
        col("is_weekend"),
        col("is_academic_day"),
        col("quarter_hour"),
        # Target variable
        col("consumption_delta_kwh"),
    )
    .dropna(subset=["consumption_delta_kwh", "temp_c", "humidity_pct"])
    .orderBy("timestamp")
)

n_us30 = df_us30.count()
logger.info("US#30 dataset : %s rows", f"{n_us30:,}")
logger.info(
    "   Period       : %s -> %s",
    df_us30.agg({'timestamp': 'min'}).collect()[0][0],
    df_us30.agg({'timestamp': 'max'}).collect()[0][0],
)
df_us30.show(5, truncate=False)

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ## 5 · CSV Export to ADLS `/mldata/knime_input/`
# MAGIC
# MAGIC Each dataset is written as **a single CSV file** (coalesce 1) with:
# MAGIC - Header included
# MAGIC - Separator `,`
# MAGIC - UTF-8 encoding
# MAGIC - Quotes only when necessary
# MAGIC
# MAGIC > ⚠️ `coalesce(1)` forces writing to a single file — acceptable here since ML
# MAGIC > datasets are small (<1M rows). Do not use on Big Data volumes.

# COMMAND ----------

# DBTITLE 1,Untitled
output_us29 = f"{ml_base}/knime_input/solar_production_features"
output_us30 = f"{ml_base}/knime_input/consumption_features"

# Delete old version before writing (idempotence)
try:
    dbutils.fs.rm(output_us29, recurse=True)
    logger.info("Old version deleted: %s", output_us29)
except Exception:
    pass

try:
    dbutils.fs.rm(output_us30, recurse=True)
    logger.info("Old version deleted: %s", output_us30)
except Exception:
    pass

# Export US#29 — Solar Production
(
    df_us29
    .coalesce(1)
    .write
    .mode("overwrite")
    .option("header", "true")
    .option("sep", ",")
    .option("encoding", "UTF-8")
    .csv(output_us29)
)
logger.info("Exported -> %s  (%s rows)", output_us29, f"{n_us29:,}")

# Export US#30 — Consumption
(
    df_us30
    .coalesce(1)
    .write
    .mode("overwrite")
    .option("header", "true")
    .option("sep", ",")
    .option("encoding", "UTF-8")
    .csv(output_us30)
)
logger.info("Exported -> %s  (%s rows)", output_us30, f"{n_us30:,}")

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ## 6 · Final Verification

# COMMAND ----------

# DBTITLE 1,Untitled
logger.info("=" * 70)
logger.info("EXPORT SUMMARY — ml_export_to_knime.py")
logger.info("=" * 70)

for path, label, n in [
    (output_us29, "solar_production_features.csv  [US#29]", n_us29),
    (output_us30, "consumption_features.csv        [US#30]", n_us30),
]:
    files = dbutils.fs.ls(path)
    csv_files = [f for f in files if f.name.endswith(".csv")]
    size_kb = csv_files[0].size // 1024 if csv_files else 0
    logger.info("  %s", label)
    logger.info("    Rows    : %s", f"{n:,}")
    logger.info("    Size    : ~%s KB", f"{size_kb:,}")
    logger.info("    Path    : %s/", path)

logger.info("US#29 Schema (KNIME features):")
df_us29.printSchema()

logger.info("US#30 Schema (KNIME features):")
df_us30.printSchema()

logger.info("=" * 70)
logger.info("Expected KNIME OUTPUT format (for ml_load_predictions.py — US#31):")
logger.info("  knime_output/production_predictions.csv")
logger.info("    -> columns: timestamp (yyyy-MM-dd HH:mm:ss), predicted_production_kwh")
logger.info("  knime_output/consumption_predictions.csv")
logger.info("    -> columns: timestamp (yyyy-MM-dd HH:mm:ss), predicted_consumption_kwh")
logger.info("=" * 70)
logger.info("Export complete — KNIME can start.")
