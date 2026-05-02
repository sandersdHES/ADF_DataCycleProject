# Databricks notebook source
# DBTITLE 1,Untitled


# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC # 🥈→🥇 Step 2 — Gold Fact Table Load
# MAGIC
# MAGIC This notebook reads Silver tables (Parquet on ADLS) and writes facts
# MAGIC into **Azure SQL BellevueEnergyDW** via JDBC.
# MAGIC
# MAGIC ### Load strategy: **incremental append by date**
# MAGIC
# MAGIC Each fact is identified by a **watermark** (max DateKey already loaded into Gold).
# MAGIC Only Silver rows after that watermark are inserted, avoiding duplicates
# MAGIC without truncate-and-reload.
# MAGIC
# MAGIC | Gold table                | Silver source              | Grain                  | Frequency |
# MAGIC |---------------------------|----------------------------|------------------------|-----------|
# MAGIC | `fact_solar_inverter`     | `solar_inverters/`         | 1-min × 5 inverters    | Daily     |
# MAGIC | `fact_solar_production`   | `solar_aggregated/`        | 15-min                 | Daily     |
# MAGIC | `fact_energy_consumption` | `consumption/`             | 15-min                 | Daily     |
# MAGIC | `fact_environment`        | `temperature/` + `humidity/`| 15-min (joined)       | Daily     |
# MAGIC | `fact_weather_forecast`   | `weather_forecasts/`       | 3h × measurement × horizon | Daily |
# MAGIC | `fact_room_booking`       | `bookings/`                | event / room           | Weekly    |
# MAGIC
# MAGIC > `fact_energy_prediction` is loaded by the ML pipeline (KNIME) — out of scope here.

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ## 0 · Configuration & helpers

# COMMAND ----------

# DBTITLE 1,Untitled
import logging

from pyspark.sql.functions import (
    col, lit, year, month, hour, minute,
    to_date, try_to_date, date_format, concat_ws,
    coalesce, when, trim, regexp_replace
)
from pyspark.sql import DataFrame
import datetime

logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(logging.INFO)

# ── ADLS Silver ────────────────────────────────────────────────────────────────
# BUG B FIXED: storage_account_name and sql_server were not declared.
storage_account_name = "adlsbellevuegrp3"
storage_account_key  = dbutils.secrets.get(scope="keyvault-scope", key="adls-access-key")
spark.conf.set(
    f"fs.azure.account.key.{storage_account_name}.dfs.core.windows.net",
    storage_account_key,
)
silver_base = f"abfss://silver@{storage_account_name}.dfs.core.windows.net"

# ── Azure SQL (Gold) ───────────────────────────────────────────────────────────
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

# ── Helpers ────────────────────────────────────────────────────────────────────
import time

def _jdbc_retry(fn, max_attempts: int = 5, initial_wait: int = 20):
    """
    Retry helper for Azure SQL Serverless — the database pauses after
    inactivity and takes ~20-60s to restart on the first connection.
    Strategy: linear backoff (20s, 40s, 60s, 80s) on
    'not currently available' errors only. Other errors are re-raised immediately.
    """
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
    """Read a Gold table from Azure SQL (with retry on Serverless wake-up)."""
    return _jdbc_retry(
        lambda: spark.read.jdbc(url=jdbc_url, table=table, properties=jdbc_props)
    )

def write_gold(df: DataFrame, table: str, batch_size: int = 20_000):
    """
    Append a DataFrame to Azure SQL.
    - batchsize    : rows per JDBC batch (memory/throughput trade-off)
    - numPartitions: write parallelism (tune to cluster size)
    """
    (df.write
       .mode("append")
       .option("batchsize", batch_size)
       .option("numPartitions", 8)
       .option("truncate", "false")
       .jdbc(url=jdbc_url, table=table, properties=jdbc_props))


def get_watermark(table: str, date_col: str = "DateKey") -> int:
    """
    Return the max DateKey already present in a Gold table.
    Returns 0 when the table is empty (first load).
    DateKey format: YYYYMMDD (int).
    """
    try:
        result = spark.read.jdbc(
            url=jdbc_url,
            table=f"(SELECT ISNULL(MAX({date_col}), 0) AS wm FROM {table}) t",
            properties=jdbc_props,
        ).collect()[0]["wm"]
        return int(result)
    except Exception:
        return 0


def ts_to_datekey(ts_col):
    """Convert a timestamp to DateKey YYYYMMDD (int)."""
    return date_format(ts_col, "yyyyMMdd").cast("int")


def ts_to_timekey(ts_col):
    """Convert a timestamp to TimeKey = minutes from midnight (smallint)."""
    return (hour(ts_col) * 60 + minute(ts_col)).cast("short")


def french_date_to_english(date_col):
    """
    Convert French date tokens to English for parsing.
    Example: '8 janv. 2023' -> '8 Jan 2023'.
    """
    result = date_col
    # Source values from bookings CSV — do not translate (regex matches actual French data).
    french_months = [
        ("janv\\.", "Jan"), ("févr\\.", "Feb"), ("mars", "Mar"),
        ("avr\\.", "Apr"), ("mai", "May"), ("juin", "Jun"),
        ("juil\\.", "Jul"), ("août", "Aug"), ("sept\\.", "Sep"),
        ("oct\\.", "Oct"), ("nov\\.", "Nov"), ("déc\\.", "Dec")
    ]
    for fr, en in french_months:
        result = regexp_replace(result, fr, en)
    return result


logger.info("Configuration loaded.")

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ## 1 · `fact_solar_inverter`
# MAGIC
# MAGIC **Source**: `silver/solar_inverters/`
# MAGIC **Grain**: 1 row per minute per inverter (5 inverters × ~1,440 min/day)
# MAGIC **FK lookups**:
# MAGIC - `InverterKey` ← `dim_inverter.InverterID`
# MAGIC - `StatusKey`   ← `dim_inverter_status.StatusCode` (sentinel 99 if unknown)
# MAGIC
# MAGIC **Silver columns** (all present thanks to BUG A fixed in silver_transformation.py):
# MAGIC `log_timestamp`, `inverter_id`, `ac_power_w`, `daysum`, `status_code`,
# MAGIC `pdc1`, `pdc2`, `udc1`, `udc2`, `is_failure`

# COMMAND ----------

# DBTITLE 1,Untitled
wm_inverter = get_watermark("fact_solar_inverter")
logger.info("Watermark fact_solar_inverter : DateKey > %d", wm_inverter)

# Lookup tables (broadcast — small dimensions)
df_dim_inv    = read_gold("dim_inverter").select(
    col("InverterKey"), col("InverterID")
).cache()

df_dim_status = read_gold("dim_inverter_status").select(
    col("StatusKey"), col("StatusCode")
).cache()

# Silver
df_inv_silver = (
    spark.read.parquet(f"{silver_base}/solar_inverters/")
    .filter(ts_to_datekey(col("log_timestamp")) > wm_inverter)
    .filter(col("log_timestamp").isNotNull())
)

if df_inv_silver.isEmpty():
    logger.info("No new Silver rows — fact_solar_inverter already up to date.")
else:
    df_fact_inv = (
        df_inv_silver
        # FK DateKey + TimeKey
        .withColumn("DateKey", ts_to_datekey(col("log_timestamp")))
        .withColumn("TimeKey", ts_to_timekey(col("log_timestamp")))
        # Lookup InverterKey
        .join(df_dim_inv, col("inverter_id") == col("InverterID"), how="left")
        # Lookup StatusKey (falls back to 99 when the code is unknown)
        .join(df_dim_status, col("status_code") == col("StatusCode"), how="left")
        .withColumn("StatusKey", coalesce(col("StatusKey"), lit(99).cast("byte")))
        # Measures — BUG C FIXED: read the real Silver columns
        # (BUG A in silver_transformation.py added these columns to the unpivot).
        .withColumn("AcPower_W",     col("ac_power_w").cast("double"))
        .withColumn("DayEnergy_Kwh", col("daysum").cast("double"))
        .withColumn("DcPower1_W",    col("pdc1").cast("double"))
        .withColumn("DcPower2_W",    col("pdc2").cast("double"))
        .withColumn("DcVoltage1_V",  col("udc1").cast("double"))
        .withColumn("DcVoltage2_V",  col("udc2").cast("double"))
        .withColumn("IsFailure",     col("is_failure").cast("boolean"))
        # Partition helpers
        .withColumn("Year",  year(col("log_timestamp")).cast("short"))
        .withColumn("Month", month(col("log_timestamp")).cast("byte"))
        .select(
            "DateKey", "TimeKey", "InverterKey", "StatusKey",
            "AcPower_W", "DayEnergy_Kwh",
            "DcPower1_W", "DcPower2_W", "DcVoltage1_V", "DcVoltage2_V",
            "IsFailure", "Year", "Month",
        )
        .filter(col("InverterKey").isNotNull())  # reject inverters with no matching dim row
        .dropDuplicates(["DateKey", "TimeKey", "InverterKey"])
    )

    n = df_fact_inv.count()
    write_gold(df_fact_inv, "fact_solar_inverter")
    logger.info("fact_solar_inverter : %s rows inserted (DateKey > %d).", f"{n:,}", wm_inverter)

df_dim_inv.unpersist()
df_dim_status.unpersist()

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ## 2 · `fact_solar_production`
# MAGIC
# MAGIC **Source**: `silver/solar_aggregated/`
# MAGIC **Grain**: 1 row per 15-min slot (total building PV production)
# MAGIC **Columns**: `CumulativeEnergy_Kwh`, `DeltaEnergy_Kwh`
# MAGIC `RetailValue_CHF` is a SQL computed column (`DeltaEnergy_Kwh × 0.15`) — not inserted here.

# COMMAND ----------

# DBTITLE 1,Untitled
wm_prod = get_watermark("fact_solar_production")
logger.info("Watermark fact_solar_production : DateKey > %d", wm_prod)

df_prod_silver = (
    spark.read.parquet(f"{silver_base}/solar_aggregated/")
    .filter(ts_to_datekey(col("timestamp")) > wm_prod)
    .filter(col("timestamp").isNotNull())
)

if df_prod_silver.isEmpty():
    logger.info("No new Silver rows — fact_solar_production already up to date.")
else:
    df_fact_prod = (
        df_prod_silver
        .withColumn("DateKey", ts_to_datekey(col("timestamp")))
        .withColumn("TimeKey", ts_to_timekey(col("timestamp")))
        .withColumn("CumulativeEnergy_Kwh", col("cumulative_reading").cast("double"))
        .withColumn("DeltaEnergy_Kwh",      col("delta_value").cast("double"))
        .withColumn("Year",  year(col("timestamp")).cast("short"))
        .withColumn("Month", month(col("timestamp")).cast("byte"))
        # RetailValue_CHF is computed in SQL — do not include it here.
        .select("DateKey", "TimeKey", "CumulativeEnergy_Kwh", "DeltaEnergy_Kwh", "Year", "Month")
        .dropDuplicates(["DateKey", "TimeKey"])
    )

    n = df_fact_prod.count()
    write_gold(df_fact_prod, "fact_solar_production")
    logger.info("fact_solar_production : %s rows inserted (DateKey > %d).", f"{n:,}", wm_prod)

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ## 3 · `fact_energy_consumption`
# MAGIC
# MAGIC **Source**: `silver/consumption/`
# MAGIC **Grain**: 1 row per 15-min slot (building electrical consumption)
# MAGIC `CostCHF` is a SQL computed column — not inserted here.

# COMMAND ----------

# DBTITLE 1,Untitled
wm_conso = get_watermark("fact_energy_consumption")
logger.info("Watermark fact_energy_consumption : DateKey > %d", wm_conso)

df_conso_silver = (
    spark.read.parquet(f"{silver_base}/consumption/")
    .filter(ts_to_datekey(col("timestamp")) > wm_conso)
    .filter(col("timestamp").isNotNull())
)

if df_conso_silver.isEmpty():
    logger.info("No new Silver rows — fact_energy_consumption already up to date.")
else:
    df_fact_conso = (
        df_conso_silver
        .withColumn("DateKey", ts_to_datekey(col("timestamp")))
        .withColumn("TimeKey", ts_to_timekey(col("timestamp")))
        .withColumn("CumulativeEnergy_Kwh", col("cumulative_reading").cast("double"))
        .withColumn("DeltaEnergy_Kwh",      col("delta_value").cast("double"))
        .withColumn("Year",  year(col("timestamp")).cast("short"))
        .withColumn("Month", month(col("timestamp")).cast("byte"))
        # CostCHF is computed in SQL — do not include it here.
        .select("DateKey", "TimeKey", "CumulativeEnergy_Kwh", "DeltaEnergy_Kwh", "Year", "Month")
        .dropDuplicates(["DateKey", "TimeKey"])
    )

    n = df_fact_conso.count()
    write_gold(df_fact_conso, "fact_energy_consumption")
    logger.info("fact_energy_consumption : %s rows inserted (DateKey > %d).", f"{n:,}", wm_conso)

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ## 4 · `fact_environment`
# MAGIC
# MAGIC **Source**: `silver/temperature/` + `silver/humidity/`
# MAGIC **Grain**: 1 row per 15-min slot — OUTER join on `timestamp`
# MAGIC
# MAGIC Both sources share the same 15-min frequency but can have gaps.
# MAGIC A FULL OUTER JOIN ensures no measurement is lost when either sensor
# MAGIC is missing for a given slot.

# COMMAND ----------

# DBTITLE 1,Untitled
wm_env = get_watermark("fact_environment")
logger.info("Watermark fact_environment : DateKey > %d", wm_env)

df_temp = (
    spark.read.parquet(f"{silver_base}/temperature/")
    .filter(col("timestamp").isNotNull())
    .filter(ts_to_datekey(col("timestamp")) > wm_env)
    .select(
        col("timestamp").alias("ts_temp"),
        col("actual_temp").cast("double").alias("Temperature_C"),
        col("temp_delta").cast("double").alias("TempVariation_C"),
    )
)

df_humi = (
    spark.read.parquet(f"{silver_base}/humidity/")
    .filter(col("timestamp").isNotNull())
    .filter(ts_to_datekey(col("timestamp")) > wm_env)
    .select(
        col("timestamp").alias("ts_humi"),
        col("actual_humidity").cast("double").alias("Humidity_Pct"),
        col("humidity_delta").cast("double").alias("HumidityVariation_Pct"),
    )
)

if df_temp.isEmpty() and df_humi.isEmpty():
    logger.info("No new Silver rows — fact_environment already up to date.")
else:
    # Full outer join on timestamp so nothing is lost.
    df_env_joined = df_temp.join(df_humi,
        df_temp["ts_temp"] == df_humi["ts_humi"], how="outer"
    )

    df_fact_env = (
        df_env_joined
        .withColumn("ts", coalesce(col("ts_temp"), col("ts_humi")))
        .withColumn("DateKey", ts_to_datekey(col("ts")))
        .withColumn("TimeKey", ts_to_timekey(col("ts")))
        .withColumn("Year",    year(col("ts")).cast("short"))
        .withColumn("Month",   month(col("ts")).cast("byte"))
        .select(
            "DateKey", "TimeKey",
            "Temperature_C", "TempVariation_C",
            "Humidity_Pct",  "HumidityVariation_Pct",
            "Year", "Month",
        )
        .dropDuplicates(["DateKey", "TimeKey"])
    )

    n = df_fact_env.count()
    write_gold(df_fact_env, "fact_environment")
    logger.info("fact_environment : %s rows inserted (DateKey > %d).", f"{n:,}", wm_env)

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ## 5 · `fact_weather_forecast`
# MAGIC
# MAGIC **Source**: `silver/weather_forecasts/`
# MAGIC **Grain**: 1 row per (datetime × measurement × forecast horizon)
# MAGIC **FK lookups**:
# MAGIC - `SiteKey`        ← `dim_weather_site.SiteName`   (Sierre only in Silver)
# MAGIC - `MeasurementKey` ← `dim_measurement_type.MeasurementCode`
# MAGIC
# MAGIC The Silver `Prediction` column is a string integer `'00'`–`'45'`
# MAGIC representing the forecast horizon in 3h steps → cast to SMALLINT.
# MAGIC
# MAGIC **Note**: dates outside the `dim_date` range (e.g. DateKey 20221231) cause
# MAGIC a JDBC FK violation and are rejected. No ad-hoc filter is needed:
# MAGIC Silver only contains dates from the dataset (2023-02 → 2023-05).

# COMMAND ----------

# DBTITLE 1,Untitled
wm_weather = get_watermark("fact_weather_forecast")
logger.info("Watermark fact_weather_forecast : DateKey > %d", wm_weather)

df_dim_site = read_gold("dim_weather_site").select(
    col("SiteKey"), col("SiteName")
).cache()

df_dim_meas = read_gold("dim_measurement_type").select(
    col("MeasurementKey"), col("MeasurementCode")
).cache()

df_weather_silver = (
    spark.read.parquet(f"{silver_base}/weather_forecasts/")
    .filter(col("Time").isNotNull())
    .filter(ts_to_datekey(col("Time").cast("timestamp")) > wm_weather)
)

if df_weather_silver.isEmpty():
    logger.info("No new Silver rows — fact_weather_forecast already up to date.")
else:
    df_fact_weather = (
        df_weather_silver
        .withColumn("ts",       col("Time").cast("timestamp"))
        .withColumn("DateKey",  ts_to_datekey(col("ts")))
        .withColumn("TimeKey",  ts_to_timekey(col("ts")))
        # Lookup FK Site
        .join(df_dim_site,
              trim(col("Site")) == col("SiteName"), how="left")
        # Lookup FK Measurement
        .join(df_dim_meas,
              trim(col("Measurement")) == col("MeasurementCode"), how="left")
        .withColumn("PredictionHorizon", col("Prediction").cast("short"))
        .withColumn("ForecastValue",     col("Value").cast("double"))
        .withColumn("Year",  year(col("ts")).cast("short"))
        .withColumn("Month", month(col("ts")).cast("byte"))
        .select(
            "DateKey", "TimeKey", "SiteKey", "MeasurementKey",
            "PredictionHorizon", "ForecastValue", "Year", "Month",
        )
        # Reject rows without a valid FK (unknown site or measurement).
        .filter(col("SiteKey").isNotNull() & col("MeasurementKey").isNotNull())
        .dropDuplicates(["DateKey", "TimeKey", "SiteKey", "MeasurementKey", "PredictionHorizon"])
    )

    n = df_fact_weather.count()
    write_gold(df_fact_weather, "fact_weather_forecast")
    logger.info("fact_weather_forecast : %s rows inserted (DateKey > %d).", f"{n:,}", wm_weather)

df_dim_site.unpersist()
df_dim_meas.unpersist()

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ## 6 · `fact_room_booking`
# MAGIC
# MAGIC **Source**: `silver/bookings/`
# MAGIC **Grain**: 1 row per booking (occurrence in a room)
# MAGIC **FK lookups**:
# MAGIC - `RoomKey`     ← `dim_room.RoomCode`
# MAGIC - `DivisionKey` ← `dim_division.DivisionName`
# MAGIC
# MAGIC **Notes**:
# MAGIC - `DateKey` = date of the occurrence (Silver `Date` column)
# MAGIC - `StartTimeKey` / `EndTimeKey` = `HH:MM` → minutes from midnight (Silver `Heure_Debut` / `Heure_Fin` columns)
# MAGIC - `DurationMinutes` = EndTimeKey − StartTimeKey
# MAGIC - `IsRecurring` : TRUE when `Date_Recurrence_Debut` or `Date_Recurrence_Fin` is non-NULL
# MAGIC - BUG D FIXED: the CSV had two duplicate "Date de début" and "Date de fin" columns.
# MAGIC   They were renamed in Silver → `Heure_Debut`, `Heure_Fin`, `Date_Recurrence_Debut`, `Date_Recurrence_Fin`.
# MAGIC - BUG E FIXED: "29 févr. 2023" (non-existent date) → `try_to_date` returns NULL,
# MAGIC   filtered out by `filter(col("DateKey").isNotNull())`. No ad-hoc filter needed.

# COMMAND ----------

# DBTITLE 1,Cell 16
wm_booking = get_watermark("fact_room_booking")
logger.info("Watermark fact_room_booking : DateKey > %d", wm_booking)

df_dim_room = read_gold("dim_room").select(
    col("RoomKey"), col("RoomCode")
).cache()

df_dim_div = read_gold("dim_division").select(
    col("DivisionKey"), col("DivisionName")
).cache()

df_booking_silver = (
    spark.read.parquet(f"{silver_base}/bookings/")
    .filter(col("Date").isNotNull())
)

# Compute DateKey from the Date column (French text format).
df_booking_silver = (
    df_booking_silver
    .withColumn("date_en", french_date_to_english(col("Date")))
    .withColumn("ts_date", try_to_date(col("date_en"), "d MMM yyyy"))
    .withColumn("DateKey", date_format(col("ts_date"), "yyyyMMdd").cast("int"))
    .filter(col("DateKey").isNotNull())  # Drop invalid dates (NULL)
    .filter(col("DateKey") > wm_booking)
)

if df_booking_silver.isEmpty():
    logger.info("No new Silver rows — fact_room_booking already up to date.")
else:
    def time_str_to_minutes(time_col):
        """Convert 'HH:mm' to minutes from midnight (TimeKey)."""
        return (
            col(time_col).substr(1, 2).cast("int") * 60
            + col(time_col).substr(4, 2).cast("int")
        ).cast("short")

    df_fact_booking = (
        df_booking_silver
        # Lookup FK Room
        .join(df_dim_room,
              trim(col("Nom")) == col("RoomCode"), how="left")
        # Lookup FK Division (NULL → rejected by filter below)
        .join(df_dim_div,
              trim(col("Division")) == col("DivisionName"), how="left")
        # BUG D FIXED: real column names after Silver rename.
        # idx 3 (booking start time) → Heure_Debut             format HH:mm
        # idx 4 (booking end time)   → Heure_Fin               format HH:mm
        # idx 11 (recurrence start)  → Date_Recurrence_Debut   format 'd MMM yyyy'
        # idx 12 (recurrence end)    → Date_Recurrence_Fin     format 'd MMM yyyy'
        .withColumn("StartTimeKey", time_str_to_minutes("Heure_Debut"))
        .withColumn("EndTimeKey",   time_str_to_minutes("Heure_Fin"))
        .withColumn("DurationMinutes",
            (col("EndTimeKey").cast("int") - col("StartTimeKey").cast("int")).cast("short"))
        # Recurrence dates
        .withColumn("date_en_recur_start", french_date_to_english(coalesce(col("Date_Recurrence_Debut"), lit(""))))
        .withColumn("RecurrenceStart", try_to_date(col("date_en_recur_start"), "d MMM yyyy"))
        .withColumn("date_en_recur_end", french_date_to_english(coalesce(col("Date_Recurrence_Fin"), lit(""))))
        .withColumn("RecurrenceEnd", try_to_date(col("date_en_recur_end"), "d MMM yyyy"))
        # NOTE: IsRecurring is a SQL computed column — do NOT include it in the
        # INSERT; SQL Server fills it automatically.
        # Measures & metadata. Source values from bookings CSV
        # (`Rés.-no`, `Type de réservation`, `Activité`, `Classe`,
        # `Poste de dépenses`, `Périodicité`, `Remarque`,
        # `Professeur_Masked`, `Utilisateur_Masked`) — do not translate.
        .withColumn("ReservationNo",
            when(col("`Rés.-no`").cast("int") == 0, lit(None))
            .otherwise(col("`Rés.-no`").cast("int")))
        .withColumn("BookingType",   col("`Type de réservation`").cast("string"))
        .withColumn("Codes",         col("Codes").cast("string"))
        .withColumn("ProfessorMasked", col("Professeur_Masked").cast("string"))
        .withColumn("UserMasked",    col("Utilisateur_Masked").cast("string"))
        .withColumn("ActivityType",  col("`Activité`").cast("string"))
        .withColumn("Class",         col("Classe").cast("string"))
        .withColumn("CostCenter",    col("`Poste de dépenses`").cast("string"))
        .withColumn("Periodicity",   col("`Périodicité`").cast("string"))
        .withColumn("Remark",        col("Remarque").cast("string"))
        .select(
            "DateKey", "StartTimeKey", "EndTimeKey", "DurationMinutes",
            "RoomKey", "DivisionKey", "ReservationNo",
            "BookingType", "Codes", "ProfessorMasked", "UserMasked",
            "ActivityType", "Class", "CostCenter", "Periodicity",
            "RecurrenceStart", "RecurrenceEnd", "Remark",
            # IsRecurring is omitted — SQL computed column.
        )
        # Reject rows without a valid FK (unknown room or division).
        .filter(col("RoomKey").isNotNull() & col("DivisionKey").isNotNull())
        .dropDuplicates(["DateKey", "StartTimeKey", "RoomKey", "ReservationNo"])
    )

    n = df_fact_booking.count()
    write_gold(df_fact_booking, "fact_room_booking")
    logger.info("fact_room_booking : %s rows inserted (DateKey > %d).", f"{n:,}", wm_booking)

df_dim_room.unpersist()
df_dim_div.unpersist()

# COMMAND ----------

logger.info("=" * 80)
logger.info("Fact table load complete.")
logger.info("=" * 80)
