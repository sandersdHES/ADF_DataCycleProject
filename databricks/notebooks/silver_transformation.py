# Databricks notebook source


# COMMAND ----------

# DBTITLE 1,Cell 2
# MAGIC %md
# MAGIC    
# MAGIC # 🥈 Silver Layer — Sensor & Solar ETL
# MAGIC
# MAGIC Transforms raw data from **Bronze** to **Silver** by applying:
# MAGIC - UTF-16 LE decoding (BOM `\xFF\xFE`) for all sensors
# MAGIC - Robust timestamp parsing (formats `dd.MM.yy` and `dd.MM.yyyy`)
# MAGIC - Unpivot of 5 solar inverters by indexed columns
# MAGIC - Consumption reset counter correction
# MAGIC - True temporal delta calculation (Temperature & Humidity)
# MAGIC - GDPR anonymization of room bookings
# MAGIC
# MAGIC | Bronze Source          | Silver Table             | Expected Rows ||
# MAGIC |------------------------|--------------------------|---------------|
# MAGIC | `solar/min*.csv`       | `solar_inverters/`       | N × 5 inverters |
# MAGIC | `solar/*-PV.csv`       | `solar_aggregated/`      | N               |
# MAGIC | `forecasts/*.csv`      | `weather_forecasts/`     | N (Sierre only) |
# MAGIC | `bookings/*.csv`       | `bookings/`              | VS-BEL filtered |
# MAGIC | `consumption/*.csv`    | `consumption/`           | N               |
# MAGIC | `temperature/*.csv`    | `temperature/`           | N               |
# MAGIC | `humidity/*.csv`       | `humidity/`              | N               |

# COMMAND ----------

# DBTITLE 1,Cell 3
# MAGIC %md
# MAGIC    
# MAGIC ## 1 · Storage Configuration & Security

# COMMAND ----------

# DBTITLE 1,Cell 4
import logging

from pyspark.sql.functions import (
    col, sha2, to_timestamp, concat_ws, when, lit, mean,
    explode, array, struct, regexp_extract, regexp_replace,
    coalesce, lag, translate, date_format,
)
from pyspark.sql.window import Window

logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(logging.INFO)

storage_account_name = "adlsbellevuegrp3"
storage_account_key  = dbutils.secrets.get(scope="keyvault-scope", key="adls-access-key")

spark.conf.set(
    f"fs.azure.account.key.{storage_account_name}.dfs.core.windows.net",
    storage_account_key,
)

bronze_base = f"abfss://bronze@{storage_account_name}.dfs.core.windows.net"
silver_base = f"abfss://silver@{storage_account_name}.dfs.core.windows.net"

logger.info("Bronze: %s", bronze_base)
logger.info("Silver: %s", silver_base)

# COMMAND ----------

# DBTITLE 1,Cell 5
# MAGIC %md
# MAGIC    
# MAGIC ## 2A · Solar Hardware Logs `min*.csv` → `solar_inverters/`
# MAGIC
# MAGIC **Actual file structure (57 columns):**
# MAGIC
# MAGIC | idx | col      | idx | col      | idx | col      | idx | col      | idx | col      |
# MAGIC |-----|----------|-----|----------|-----|----------|-----|----------|-----|----------|
# MAGIC | 2   | inv_1    | 13  | inv_2    | 24  | inv_3    | 35  | inv_4    | 46  | inv_5    |
# MAGIC | 3   | **pac_1**| 14  | **pac_2**| 25  | **pac_3**| 36  | **pac_4**| 47  | **pac_5**|
# MAGIC | 4   | **daysum_1**|15| **daysum_2**|26| **daysum_3**|37| **daysum_4**|48| **daysum_5**|
# MAGIC | 5   | **status_1**| 16 | **status_2**| 27 | **status_3**| 38 | **status_4**| 49 | **status_5**|
# MAGIC | 7   | **pdc1_1**| 18 | **pdc1_2**| 29 | **pdc1_3**| 40 | **pdc1_4**| 51 | **pdc1_5**|
# MAGIC | 8   | **pdc2_1**| 19 | **pdc2_2**| 30 | **pdc2_3**| 41 | **pdc2_4**| 52 | **pdc2_5**|
# MAGIC | 9   | **udc1_1**| 20 | **udc1_2**| 31 | **udc1_3**| 42 | **udc1_4**| 53 | **udc1_5**|
# MAGIC | 10  | **udc2_1**| 21 | **udc2_2**| 32 | **udc2_3**| 43 | **udc2_4**| 54 | **udc2_5**|
# MAGIC
# MAGIC > ⚠️ Original column names (`Pac3`, `Status16`…) don't exist.
# MAGIC > Spark deduplicates identical headers non-deterministically depending on version.
# MAGIC > → Exhaustive renaming via `toDF()` immediately after reading.

# COMMAND ----------

# DBTITLE 1,Cell 6
# Exhaustive renaming of 57 columns — no Spark deduplication ambiguity
SOLAR_HW_COLS = [
    "date_raw", "time_raw",
    "inv_1",  "pac_1",  "daysum_1",  "status_1",  "error_1",  "pdc1_1",  "pdc2_1",  "udc1_1",  "udc2_1",  "temp_1",  "uac_1",
    "inv_2",  "pac_2",  "daysum_2",  "status_2",  "error_2",  "pdc1_2",  "pdc2_2",  "udc1_2",  "udc2_2",  "temp_2",  "uac_2",
    "inv_3",  "pac_3",  "daysum_3",  "status_3",  "error_3",  "pdc1_3",  "pdc2_3",  "udc1_3",  "udc2_3",  "temp_3",  "uac_3",
    "inv_4",  "pac_4",  "daysum_4",  "status_4",  "error_4",  "pdc1_4",  "pdc2_4",  "udc1_4",  "udc2_4",  "temp_4",  "uac_4",
    "inv_5",  "pac_5",  "daysum_5",  "status_5",  "error_5",  "pdc1_5",  "pdc2_5",  "udc1_5",  "udc2_5",  "temp_5",  "uac_5",
]

df_solar_hw_raw = (
    spark.read.csv(
        f"{bronze_base}/solar/min*.csv",
        header=True,
        sep=";",
        inferSchema=True,   # ← parses date_raw as date and time_raw as timestamp
    )
    .toDF(*SOLAR_HW_COLS)
)

# inferSchema already parsed date_raw/time_raw, filter on non-null
df_solar_hw_clean = df_solar_hw_raw.filter(
    col("date_raw").isNotNull() &
    col("time_raw").isNotNull()
)

# Timestamp reconstruction: date_raw (date) + time_raw (timestamp → HH:mm:ss)
# Direct concat without date_format would produce "2023-02-20 2026-02-27 23:55:00"
df_solar_hw_prep = df_solar_hw_clean.withColumn(
    "log_timestamp",
    to_timestamp(
        concat_ws(" ", col("date_raw").cast("string"), date_format(col("time_raw"), "HH:mm:ss")),
        "yyyy-MM-dd HH:mm:ss",
    ),
)

# Unpivot: 1 row per (timestamp, inverter) via array of structs
# FIXED BUG: daysum, pdc1, pdc2, udc1, udc2 added to each struct
# — necessary for fact_solar_inverter (DayEnergy_Kwh, DcPower1/2_W, DcVoltage1/2_V)
inverter_data = array(
    struct(lit(1).alias("id"),
           col("pac_1").cast("double").alias("pac"),
           col("daysum_1").cast("double").alias("daysum"),
           col("status_1").cast("int").alias("status"),
           col("pdc1_1").cast("double").alias("pdc1"),
           col("pdc2_1").cast("double").alias("pdc2"),
           col("udc1_1").cast("double").alias("udc1"),
           col("udc2_1").cast("double").alias("udc2")),
    struct(lit(2).alias("id"),
           col("pac_2").cast("double").alias("pac"),
           col("daysum_2").cast("double").alias("daysum"),
           col("status_2").cast("int").alias("status"),
           col("pdc1_2").cast("double").alias("pdc1"),
           col("pdc2_2").cast("double").alias("pdc2"),
           col("udc1_2").cast("double").alias("udc1"),
           col("udc2_2").cast("double").alias("udc2")),
    struct(lit(3).alias("id"),
           col("pac_3").cast("double").alias("pac"),
           col("daysum_3").cast("double").alias("daysum"),
           col("status_3").cast("int").alias("status"),
           col("pdc1_3").cast("double").alias("pdc1"),
           col("pdc2_3").cast("double").alias("pdc2"),
           col("udc1_3").cast("double").alias("udc1"),
           col("udc2_3").cast("double").alias("udc2")),
    struct(lit(4).alias("id"),
           col("pac_4").cast("double").alias("pac"),
           col("daysum_4").cast("double").alias("daysum"),
           col("status_4").cast("int").alias("status"),
           col("pdc1_4").cast("double").alias("pdc1"),
           col("pdc2_4").cast("double").alias("pdc2"),
           col("udc1_4").cast("double").alias("udc1"),
           col("udc2_4").cast("double").alias("udc2")),
    struct(lit(5).alias("id"),
           col("pac_5").cast("double").alias("pac"),
           col("daysum_5").cast("double").alias("daysum"),
           col("status_5").cast("int").alias("status"),
           col("pdc1_5").cast("double").alias("pdc1"),
           col("pdc2_5").cast("double").alias("pdc2"),
           col("udc1_5").cast("double").alias("udc1"),
           col("udc2_5").cast("double").alias("udc2")),
)

df_solar_inverters = (
    df_solar_hw_prep
    .withColumn("inv", explode(inverter_data))
    .select(
        col("log_timestamp"),
        col("inv.id").alias("inverter_id"),
        col("inv.pac").alias("ac_power_w"),
        col("inv.daysum").alias("daysum"),
        col("inv.status").alias("status_code"),
        col("inv.pdc1").alias("pdc1"),
        col("inv.pdc2").alias("pdc2"),
        col("inv.udc1").alias("udc1"),
        col("inv.udc2").alias("udc2"),
        when(col("inv.status") == 14, True).otherwise(False).alias("is_failure"),
    )
    .dropna(subset=["log_timestamp"])
    .dropDuplicates()
)

df_solar_inverters.write.mode("overwrite").parquet(f"{silver_base}/solar_inverters/")
logger.info("solar_inverters   -> %s rows", f"{df_solar_inverters.count():,}")

# COMMAND ----------

# DBTITLE 1,Cell 7
# MAGIC %md
# MAGIC    
# MAGIC ## 2B · Solar Aggregated Production `*-PV.csv` → `solar_aggregated/`
# MAGIC
# MAGIC > ⚠️ **UTF-16 LE encoding** (BOM `\xFF\xFE`).  
# MAGIC > Spark reading as UTF-8 produces null spaces between each character (`0 1 . 0 1 . 2 0 2 3`),
# MAGIC > causing all regex filters to fail → 0 rows output.  
# MAGIC > **Fix**: `translate()` removes null bytes `\u0000` and residual quotes
# MAGIC > before any comparison.

# COMMAND ----------

# DBTITLE 1,Cell 8
def _read_utf16_sensor(path: str, val_col: str, var_col: str):
    """
    Reads a UTF-16 LE CSV with 5 columns, cleans null bytes and quotes,
    and renames columns explicitly.
    Returns a DataFrame with: Date_Raw, Heure_Raw, Unit_Raw, <val_col>, <var_col>
    """
    df = spark.read.csv(path, header=True, sep=";", quote='"', inferSchema=True)
    c = df.columns  # original names (potentially corrupted by UTF-16)
    return df.select(
        translate(col(c[0]), '\u0000"', "").alias("Date_Raw"),
        translate(col(c[1]), '\u0000"', "").alias("Heure_Raw"),
        translate(col(c[2]), '\u0000"', "").alias("Unit_Raw"),
        translate(col(c[3]), '\u0000"', "").alias(val_col),
        translate(col(c[4]), '\u0000"', "").alias(var_col),
    )


def _parse_timestamp(df):
    """Extracts and parses timestamp from Date_Raw / Heure_Raw columns."""
    return (
        df
        .withColumn("_d", regexp_extract(col("Date_Raw"),  r"(\d{2}\.\d{2}\.\d{2,4})", 1))
        .withColumn("_t", regexp_extract(col("Heure_Raw"), r"(\d{2}:\d{2}(?::\d{2})?)", 1))
        .withColumn(
            "timestamp",
            coalesce(
                to_timestamp(concat_ws(" ", col("_d"), col("_t")), "dd.MM.yyyy HH:mm:ss"),
                to_timestamp(concat_ws(" ", col("_d"), col("_t")), "dd.MM.yyyy HH:mm"),
            ),
        )
        .drop("_d", "_t", "Date_Raw", "Heure_Raw", "Unit_Raw")
    )


df_solar_agg_filtered = (
    _read_utf16_sensor(f"{bronze_base}/solar/*-PV.csv", "cumulative_reading", "delta_value")
    .filter(
        col("Date_Raw").rlike(r"\d{2}\.\d{2}\.\d{2,4}") &
        col("Heure_Raw").rlike(r"\d{2}:\d{2}")
    )
)

df_solar_agg = (
    _parse_timestamp(df_solar_agg_filtered)
    .withColumn("cumulative_reading", regexp_extract(col("cumulative_reading"), r"(-?\d+\.?\d*)", 1).cast("double"))
    .withColumn("delta_value",        regexp_extract(col("delta_value"),        r"(-?\d+\.?\d*)", 1).cast("double"))
    .dropna(subset=["timestamp"])
    .dropDuplicates()
)

df_solar_agg.write.mode("overwrite").parquet(f"{silver_base}/solar_aggregated/")
logger.info("solar_aggregated  -> %s rows", f"{df_solar_agg.count():,}")

# COMMAND ----------

# DBTITLE 1,Cell 9
# MAGIC %md
# MAGIC    
# MAGIC ## 3 · Weather Forecasts `forecasts/*.csv` → `weather_forecasts/`
# MAGIC
# MAGIC **"Sierre"** synthesis = interpolated average between **Sion** and **Visp** stations.  
# MAGIC Sentinel value `99999.0` is replaced by `null` before aggregation.

# COMMAND ----------

# DBTITLE 1,Cell 10
df_weather_raw = spark.read.csv(f"{bronze_base}/forecasts/*.csv", header=True, inferSchema=True)

df_sierre = (
    df_weather_raw
    .filter(col("Site").isin("Sion", "Visp"))
    .withColumn("Value", when(col("Value") == 99999.0, lit(None)).otherwise(col("Value")))
    .groupBy("Time", "Measurement", "Prediction", "Unit")
    .agg(mean("Value").alias("Value"))
    .withColumn("Site", lit("Sierre"))
    .dropna(subset=["Time"])
)

df_sierre.write.mode("overwrite").parquet(f"{silver_base}/weather_forecasts/")
logger.info("weather_forecasts -> %s rows", f"{df_sierre.count():,}")

df_futureweather_raw = spark.read.csv(f"{bronze_base}/future_forecasts/*.csv", header=True, inferSchema=True)

df_sierre.write.mode("overwrite").parquet(f"{silver_base}/weather_future_forecasts/")
logger.info("future_weather_forecasts -> %s rows", f"{df_sierre.count():,}")



# COMMAND ----------

# DBTITLE 1,Cell 11
# MAGIC %md
# MAGIC    
# MAGIC ## 4 · Room Bookings `bookings/*.csv` → `bookings/`
# MAGIC
# MAGIC - Filter **Bellevue** perimeter (`Nom` starts with `VS-BEL`)
# MAGIC - **GDPR**: `Professeur` and `Utilisateur` replaced by their SHA-256 hash

# COMMAND ----------

# DBTITLE 1,Cell 12
df_bookings_raw = spark.read.option("quote", "").csv(
    f"{bronze_base}/bookings/*.csv", header=True, sep="\t", inferSchema=True
)

# Clean residual quotes in column names
df_bookings_raw = df_bookings_raw.toDF(*[c.replace('"', '') for c in df_bookings_raw.columns])

# FIXED BUG E: CSV contains 2 "Date de début" columns (idx 3=start time, idx 11=recurrence start)
# and 2 "Date de fin" columns (idx 4=end time, idx 12=recurrence end).
# Spark silently deduplicates by adding a numeric suffix based on position:
#   idx  3 → "Date de début3"   (booking start time, format HH:mm)
#   idx  4 → "Date de fin4"     (booking end time,   format HH:mm)
#   idx 11 → "Date de début11"  (recurrence start,   format 'd MMM yyyy')
#   idx 12 → "Date de fin12"    (recurrence end,     format 'd MMM yyyy')
# We rename explicitly to avoid ambiguity in Silver Parquet
# and in Gold notebooks reading these columns.
df_bookings_raw = (
    df_bookings_raw
    .withColumnRenamed("Date de début3",  "Heure_Debut")
    .withColumnRenamed("Date de fin4",    "Heure_Fin")
    .withColumnRenamed("Date de début11", "Date_Recurrence_Debut")
    .withColumnRenamed("Date de fin12",   "Date_Recurrence_Fin")
)

df_bookings = (
    df_bookings_raw
    .withColumn("Nom", regexp_replace(col("Nom").cast("string"), '"', ""))
    .filter(col("Nom").rlike("^VS-BEL"))
    .withColumn("Professeur_Masked",  sha2(col("Professeur"), 256))
    .withColumn("Utilisateur_Masked", sha2(col("Nom de l'utilisateur"), 256))
    .drop("Professeur", "Nom de l'utilisateur")
    .dropna(subset=["Nom"])
    .dropDuplicates()
)

# Note: invalid dates "29 févr. 2023" (2023 is not a leap year) are
# naturally eliminated by try_to_date() in Gold (returns NULL → filtered).
# No ad-hoc filter needed here.

df_bookings.write.mode("overwrite").parquet(f"{silver_base}/bookings/")
logger.info("bookings          -> %s rows", f"{df_bookings.count():,}")

# COMMAND ----------

# DBTITLE 1,Cell 13
# MAGIC %md
# MAGIC    
# MAGIC ## 5 · Sensor Data → `consumption/` · `temperature/` · `humidity/`
# MAGIC
# MAGIC All three sources share the same 5-column CSV structure and UTF-16 LE encoding.
# MAGIC
# MAGIC | Parameter              | Consumption          | Temperature       | Humidity          |
# MAGIC |------------------------|----------------------|-------------------|-------------------|
# MAGIC | `is_cumulative_meter`  | ✅ True              | ❌ False          | ❌ False          |
# MAGIC | `compute_real_delta`   | ❌ False             | ✅ True           | ✅ True           |
# MAGIC | val_col                | `cumulative_reading` | `actual_temp`     | `actual_humidity` |
# MAGIC | var_col                | `delta_value`        | `temp_delta`      | `humidity_delta`  |
# MAGIC
# MAGIC ### Applied Corrections
# MAGIC
# MAGIC **Bug 4 — Counter Reset Logic (Consumption)**  
# MAGIC The original substituted `cumulative_reading` as delta when value was negative.
# MAGIC This is incorrect: the true delta is `(MAX_COUNTER - prev) + new`. Without knowing `MAX_COUNTER`,
# MAGIC we set `null` to signal the event and let downstream layers decide.
# MAGIC Delta is properly recalculated via `lag()` on time window.
# MAGIC
# MAGIC **Bug 5 — False "Variation" Column (Temperature & Humidity)**  
# MAGIC The source exports the absolute value in both columns (`Variation == Acquisition`).
# MAGIC We replace the useless column with a true delta calculated via `lag()`.

# COMMAND ----------

# DBTITLE 1,Cell 14
def process_vetroz_sensor(
    bronze_folder: str,
    silver_folder: str,
    val_col: str,
    var_col: str,
    is_cumulative_meter: bool = False,
    compute_real_delta: bool = False,
):
    """
    Reads, cleans and writes a Vetroz sensor in UTF-16 LE format to Silver.

    Parameters
    ----------
    bronze_folder      : subfolder in Bronze container
    silver_folder      : subfolder in Silver container
    val_col            : name of main value column (4th CSV col)
    var_col            : name of variation / delta column  (5th CSV col)
    is_cumulative_meter: True → cumulative counter (energy) with reset handling
    compute_real_delta : True → recalculate delta via lag() (temperature, humidity)
    """
    df_filtered = (
        _read_utf16_sensor(f"{bronze_base}/{bronze_folder}/*.csv", val_col, var_col)
        .filter(
            col("Date_Raw").rlike(r"\d{2}\.\d{2}\.\d{2,4}") &
            col("Heure_Raw").rlike(r"\d{2}:\d{2}")
        )
    )
    
    df = (
        _parse_timestamp(df_filtered)
        .withColumn(val_col, regexp_extract(col(val_col), r"(-?\d+\.?\d*)", 1).cast("double"))
        .withColumn(var_col, regexp_extract(col(var_col), r"(-?\d+\.?\d*)", 1).cast("double"))
        .dropna(subset=["timestamp"])
        .dropDuplicates()
    )

    # ── Cumulative counter: recalculate delta and handle overflow ──────────
    if is_cumulative_meter:
        w = Window.orderBy("timestamp")
        df = (
            df
            .withColumn("_prev", lag(val_col, 1).over(w))
            .withColumn(
                var_col,
                when(col("_prev").isNotNull(),
                    when(col(val_col) < col("_prev"), lit(None))   # reset detected → null
                    .otherwise(col(val_col) - col("_prev"))        # normal delta
                )
            )
            .drop("_prev")
        )

    # ── Instantaneous sensor: var_col == val_col in source → true delta ────────
    if compute_real_delta:
        w = Window.orderBy("timestamp")
        df = df.withColumn(var_col, col(val_col) - lag(col(val_col), 1).over(w))

    df.write.mode("overwrite").parquet(f"{silver_base}/{silver_folder}/")
    logger.info("%-20s -> %s rows", silver_folder, f"{df.count():,}")

# COMMAND ----------

process_vetroz_sensor(
    "consumption", "consumption",
    val_col="cumulative_reading",
    var_col="delta_value",
    is_cumulative_meter=True,
)

process_vetroz_sensor(
    "temperature", "temperature",
    val_col="actual_temp",
    var_col="temp_delta",
    compute_real_delta=True,
)

process_vetroz_sensor(
    "humidity", "humidity",
    val_col="actual_humidity",
    var_col="humidity_delta",
    compute_real_delta=True,
)

# COMMAND ----------

# DBTITLE 1,Cell 16
# MAGIC %md
# MAGIC    
# MAGIC ## ✅ Silver Transformation Complete
# MAGIC
# MAGIC All Silver tables are available under `abfss://silver@adlsbellevuegrp3…`
# MAGIC
# MAGIC ```
# MAGIC silver/
# MAGIC ├── solar_inverters/      ← 5 inverters × N timestamps (10 columns: log_timestamp, inverter_id, ac_power_w, daysum, status_code, pdc1, pdc2, udc1, udc2, is_failure)
# MAGIC ├── solar_aggregated/     ← cumulative PV production + delta
# MAGIC ├── weather_forecasts/    ← Sierre interpolated (Sion + Visp)
# MAGIC ├── bookings/             ← VS-BEL reservations, GDPR masked (duplicate columns renamed: Heure_Debut, Heure_Fin, Date_Recurrence_Debut, Date_Recurrence_Fin)
# MAGIC ├── consumption/          ← cumulative energy + corrected delta
# MAGIC ├── temperature/          ← temperature + true temporal delta
# MAGIC └── humidity/             ← humidity   + true temporal delta
# MAGIC ```
