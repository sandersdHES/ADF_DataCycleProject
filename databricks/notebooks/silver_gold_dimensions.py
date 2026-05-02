# Databricks notebook source
# DBTITLE 1,Cell 1


# COMMAND ----------

# DBTITLE 1,Cell 2
# MAGIC %md
# MAGIC    
# MAGIC # 🥈→🥇 Step 1B — Data-Driven Dimensions
# MAGIC
# MAGIC This notebook populates and **maintains** all Gold dimensions whose content
# MAGIC depends on Silver data. It is **idempotent**: each execution performs a MERGE
# MAGIC (INSERT if new, UPDATE if changed, never DELETE or duplicate).
# MAGIC
# MAGIC | Dimension               | Silver Source              | ADF Trigger     |
# MAGIC |-------------------------|----------------------------|------------------|
# MAGIC | `dim_inverter`          | `silver/solar_inverters/`  | Daily           |
# MAGIC | `dim_inverter_status`   | `silver/solar_inverters/`  | Daily           |
# MAGIC | `dim_weather_site`      | `silver/weather_forecasts/`| Daily           |
# MAGIC | `dim_measurement_type`  | `silver/weather_forecasts/`| Daily           |
# MAGIC | `dim_room`              | `silver/bookings/`         | Weekly (Monday) |
# MAGIC | `dim_division`          | `silver/bookings/`         | Weekly (Monday) |
# MAGIC | `dim_prediction_model`  | JSON Config ADLS           | ML Deployment   |
# MAGIC | `ref_electricity_tariff`| JSON Config ADLS           | Tariff Change   |
# MAGIC
# MAGIC > **`dim_date` and `dim_time`** are calculated — maintained by `step1a_calculated_dimensions.sql`.

# COMMAND ----------

# DBTITLE 1,Cell 3
# MAGIC %md
# MAGIC    
# MAGIC ## 0 · Configuration & Connection

# COMMAND ----------

# DBTITLE 1,Cell 4
import logging

from pyspark.sql.functions import (
    col, lit, when, regexp_extract, upper, trim, max as spark_max
)
import re
import time

logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(logging.INFO)

# ── Azure Data Lake Storage ────────────────────────────────────────────
storage_account_name = "adlsbellevuegrp3"
storage_account_key  = dbutils.secrets.get(scope="keyvault-scope", key="adls-access-key")
spark.conf.set(
    f"fs.azure.account.key.{storage_account_name}.dfs.core.windows.net",
    storage_account_key,
)
silver_base = f"abfss://silver@{storage_account_name}.dfs.core.windows.net"
config_base = f"abfss://config@{storage_account_name}.dfs.core.windows.net"

# ── Azure SQL Database (Gold) ──────────────────────────────────────────
sql_server   = "sqlserver-bellevue-grp3"
sql_database = "DevDB"
sql_user     = "dylan.sanderso"
sql_password = dbutils.secrets.get(scope="keyvault-scope", key="Admin-SQL-Password")

jdbc_url = (
    f"jdbc:sqlserver://{sql_server}.database.windows.net:1433;"
    f"database={sql_database};encrypt=true;trustServerCertificate=false;"
    f"hostNameInCertificate=*.database.windows.net;loginTimeout=30"
)
jdbc_props = {"user": sql_user, "password": sql_password, "driver": "com.microsoft.sqlserver.jdbc.SQLServerDriver"}

def wake_up_sql(max_wait: int = 120):
    """
    Wakes up Azure SQL Serverless by attempting a simple connection in a loop.
    The database takes ~20-60s to start after a period of inactivity.
    """
    logger.info("Checking Azure SQL availability...")
    deadline = time.time() + max_wait
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            conn = spark._jvm.java.sql.DriverManager.getConnection(
                jdbc_url, sql_user, sql_password
            )
            conn.close()
            logger.info("Azure SQL available (attempt %d)", attempt)
            return
        except Exception as e:
            if "not currently available" in str(e):
                elapsed = int(time.time() - (deadline - max_wait))
                logger.info("Database waking up... (%ds elapsed, attempt %d)", elapsed, attempt)
                time.sleep(15)
            else:
                raise  # Other error (auth, network) → fail immediately

    raise TimeoutError(f"Azure SQL not available after {max_wait}s — check Azure portal.")

wake_up_sql()

def _jdbc_retry(fn, max_attempts: int = 5, initial_wait: int = 20):
    """
    Retry helper for Azure SQL Serverless — the database pauses after
    inactivity and takes ~20-60s to restart on first connection.
    Strategy: linear backoff (20s, 40s, 60s, 80s) on
    'not currently available' errors only. Other errors are re-raised immediately.
    """
    import time
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

def read_gold(table: str):
    """Reads a Gold table from Azure SQL."""
    return spark.read.jdbc(url=jdbc_url, table=table, properties=jdbc_props)

def exec_sql(statement: str):
    """Executes a T-SQL statement via JDBC (with retry on Serverless wake-up)."""
    def _run():
        conn = spark._jvm.java.sql.DriverManager.getConnection(jdbc_url, sql_user, sql_password)
        try:
            stmt = conn.createStatement()
            stmt.execute(statement)
        finally:
            conn.close()
    _jdbc_retry(_run)

logger.info("Configuration loaded.")
logger.info("   Silver : %s", silver_base)
logger.info("   Gold   : %s.database.windows.net / %s", sql_server, sql_database)

# COMMAND ----------

# DBTITLE 1,Cell 5
# MAGIC %md
# MAGIC    
# MAGIC ## 1 · `dim_inverter` — inverters from `solar_inverters`
# MAGIC
# MAGIC Source: `inverter_id` column (1-5) from Silver.
# MAGIC Logic: if a new ID appears → INSERT with default values (6 kWp, 2 strings).
# MAGIC A technician can then manually update `RoofSection` and `InstallDate`.

# COMMAND ----------

# DBTITLE 1,Cell 6
df_inv_silver = (
    spark.read.parquet(f"{silver_base}/solar_inverters/")
    .select(col("inverter_id").cast("int").alias("InverterID"))
    .distinct()
    .orderBy("InverterID")
)

df_inv_gold = read_gold("dim_inverter").select("InverterID")

# Only IDs absent from Gold
df_inv_new = df_inv_silver.join(df_inv_gold, on="InverterID", how="left_anti")

new_ids = [row["InverterID"] for row in df_inv_new.collect()]

if not new_ids:
    logger.info("dim_inverter: no new inverters detected.")
else:
    for inv_id in new_ids:
        exec_sql(f"""
            IF NOT EXISTS (SELECT 1 FROM dim_inverter WHERE InverterID = {inv_id})
            INSERT INTO dim_inverter
                (InverterID, InverterName, RatedPower_kWp, StringCount, RoofSection, InstallDate, IsActive)
            VALUES
                ({inv_id}, 'INV-{inv_id:02d}', 6.00, 2, NULL, NULL, 1)
        """)
    logger.info("dim_inverter: %d new inverter(s) inserted -> IDs %s", len(new_ids), new_ids)

# COMMAND ----------

# DBTITLE 1,Cell 7
# MAGIC %md
# MAGIC    
# MAGIC ## 2 · `dim_inverter_status` — status codes from `solar_inverters`
# MAGIC
# MAGIC Source: `status_code` column from Silver. Known codes are 0, 6, 14.
# MAGIC Any unknown code is automatically inserted with category 'Unknown'
# MAGIC to avoid FK violations in `fact_solar_inverter`.

# COMMAND ----------

# DBTITLE 1,Cell 8
# Status codes observed in Silver
df_status_silver = (
    spark.read.parquet(f"{silver_base}/solar_inverters/")
    .select(col("status_code").cast("int").alias("StatusCode"))
    .distinct()
    .filter(col("StatusCode").isNotNull())
)

df_status_gold = read_gold("dim_inverter_status").select("StatusCode")
df_status_new  = df_status_silver.join(df_status_gold, on="StatusCode", how="left_anti")

# Documented labels — any unknown code receives 'Unknown'
STATUS_LABELS = {
    0:  ("OK / Standby",  "OK",      0, 0),
    6:  ("Producing",     "Running", 0, 0),
    14: ("Error",         "Error",   1, 1),
}

new_codes = [row["StatusCode"] for row in df_status_new.collect()]

if not new_codes:
    logger.info("dim_inverter_status: no new codes detected.")
else:
    for code in new_codes:
        label, category, is_failure, requires_maint = STATUS_LABELS.get(
            code, (f"Code {code}", "Unknown", 0, 0)
        )
        exec_sql(f"""
            IF NOT EXISTS (SELECT 1 FROM dim_inverter_status WHERE StatusCode = {code})
            INSERT INTO dim_inverter_status
                (StatusCode, StatusLabel, StatusCategory, IsFailure, RequiresMaintenance)
            VALUES
                ({code}, '{label}', '{category}', {is_failure}, {requires_maint})
        """)
    logger.info("dim_inverter_status: %d new code(s) inserted -> %s", len(new_codes), new_codes)

# Sentinel 99 (always present for missing FKs)
exec_sql("""
    IF NOT EXISTS (SELECT 1 FROM dim_inverter_status WHERE StatusCode = 99)
    INSERT INTO dim_inverter_status (StatusCode, StatusLabel, StatusCategory, IsFailure, RequiresMaintenance)
    VALUES (99, 'Unknown', 'Unknown', 0, 0)
""")

# COMMAND ----------

# DBTITLE 1,Cell 9
# MAGIC %md
# MAGIC    
# MAGIC ## 3 · `dim_weather_site` — sites from `weather_forecasts`
# MAGIC
# MAGIC Source: `Site` column from Silver (after filtering Sion + Visp → Sierre synthesis).
# MAGIC The "Sierre" site is synthetic: it is automatically inserted as soon as
# MAGIC Sion and Visp exist in Silver, even if it doesn't appear there as such.

# COMMAND ----------

# DBTITLE 1,Cell 10
# Known site coordinates — extend if new sites appear
SITE_META = {
    "Sion":    {"desc": "MeteoSwiss Station — Sion (VS). Southwest reference.",
                "is_synthetic": 0, "lat": 46.2167, "lon": 7.3500, "alt": 482},
    "Visp":    {"desc": "MeteoSwiss Station — Visp (VS). Northeast reference. "
                        "(Replaces 'Brig' absent from source dataset.)",
                "is_synthetic": 0, "lat": 46.2942, "lon": 7.8814, "alt": 658},
    "Sierre":  {"desc": "SYNTHETIC Bellevue Station — Sion + Visp interpolation. "
                        "Represents HES-SO campus conditions (~530 m).",
                "is_synthetic": 1, "lat": 46.2833, "lon": 7.5333, "alt": 530},
}

df_sites_silver = (
    spark.read.parquet(f"{silver_base}/weather_forecasts/")
    .select(trim(col("Site")).alias("SiteName"))
    .distinct()
)

df_sites_gold = read_gold("dim_weather_site").select("SiteName")
df_sites_new  = df_sites_silver.join(df_sites_gold, on="SiteName", how="left_anti")
new_sites     = [row["SiteName"] for row in df_sites_new.collect()]

# "Sierre" is synthetic → always ensure it's present
if "Sierre" not in [row["SiteName"] for row in df_sites_gold.collect()]:
    new_sites.append("Sierre")

if not new_sites:
    logger.info("dim_weather_site: no new sites detected.")
else:
    for site in new_sites:
        meta = SITE_META.get(site, {
            "desc": f"MeteoSwiss Site — {site}. Metadata to be completed.",
            "is_synthetic": 0, "lat": "NULL", "lon": "NULL", "alt": "NULL",
        })
        lat = f"{meta['lat']}" if meta['lat'] != "NULL" else "NULL"
        lon = f"{meta['lon']}" if meta['lon'] != "NULL" else "NULL"
        alt = f"{meta['alt']}" if meta['alt'] != "NULL" else "NULL"
        exec_sql(f"""
            IF NOT EXISTS (SELECT 1 FROM dim_weather_site WHERE SiteName = '{site}')
            INSERT INTO dim_weather_site
                (SiteName, SiteDescription, IsSynthetic, Latitude, Longitude, AltitudeM, Country)
            VALUES
                ('{site}', '{meta["desc"]}', {meta["is_synthetic"]}, {lat}, {lon}, {alt}, 'CH')
        """)
    logger.info("dim_weather_site: %d new site(s) inserted -> %s", len(new_sites), new_sites)

# COMMAND ----------

# DBTITLE 1,Cell 11
# MAGIC %md
# MAGIC    
# MAGIC ## 4 · `dim_measurement_type` — measurement types from `weather_forecasts`
# MAGIC
# MAGIC Source: `Measurement` and `Unit` columns from Silver.
# MAGIC Known codes: `PRED_GLOB_ctrl`, `PRED_T_2M_ctrl`, `PRED_RELHUM_2M_ctrl`, `PRED_TOT_PREC_ctrl`.
# MAGIC Any new code is automatically inserted (category 'Unknown' to be corrected manually).

# COMMAND ----------

# DBTITLE 1,Cell 12
MEASUREMENT_META = {
    "PRED_GLOB_ctrl":      ("Horizontal global irradiance", "Solar",         "Watt/m2", 1),
    "PRED_T_2M_ctrl":      ("Air temperature at 2 m",       "Temperature",   "°C",      0),
    "PRED_RELHUM_2M_ctrl": ("Relative humidity at 2 m",     "Humidity",      "Percent", 0),
    "PRED_TOT_PREC_ctrl":  ("Total precipitation",          "Precipitation", "Kg/m2",   0),
}

df_meas_silver = (
    spark.read.parquet(f"{silver_base}/weather_forecasts/")
    .select(
        trim(col("Measurement")).alias("MeasurementCode"),
        trim(col("Unit")).alias("Unit"),
    )
    .distinct()
)

df_meas_gold = read_gold("dim_measurement_type").select("MeasurementCode")
df_meas_new  = df_meas_silver.join(df_meas_gold, on="MeasurementCode", how="left_anti")
new_measurements = df_meas_new.collect()

if not new_measurements:
    logger.info("dim_measurement_type: no new measurement types detected.")
else:
    for row in new_measurements:
        code = row["MeasurementCode"].replace("'", "''")
        unit = row["Unit"].replace("'", "''")
        meta = MEASUREMENT_META.get(row["MeasurementCode"])
        if meta:
            name, category, unit_ref, is_driver = meta
        else:
            name, category, unit_ref, is_driver = code, "Unknown", unit, 0
        exec_sql(f"""
            IF NOT EXISTS (SELECT 1 FROM dim_measurement_type WHERE MeasurementCode = '{code}')
            INSERT INTO dim_measurement_type
                (MeasurementCode, MeasurementName, Category, Unit, Description, IsProductionDriver)
            VALUES
                ('{code}', '{name}', '{category}', '{unit_ref}',
                 'Automatically inserted — description to be completed.', {is_driver})
        """)
    logger.info("dim_measurement_type: %d new type(s) inserted.", len(new_measurements))

# COMMAND ----------

# DBTITLE 1,Cell 13
# MAGIC %md
# MAGIC    
# MAGIC ## 5 · `dim_division` — divisions from `bookings`
# MAGIC
# MAGIC Source: `Division` column from Silver (VS-BEL bookings only).
# MAGIC `IsActive = 1` for all divisions observed in VS-BEL bookings.
# MAGIC If a division changes name → new INSERT line, old one remains in database.

# COMMAND ----------

# DBTITLE 1,Cell 14
# Source values from bookings CSV — do not translate (used as join keys against the Division column).
DIVISION_META = {
    "Haute école de Gestion":
        ("HEG",     "HEG Valais-Wallis",          1),
    "Haute Ecole et Ecole Supérieure de Travail Social":
        ("HETS",    "HETS&Sa Valais",              1),
    "Haute école d'ingénierie":
        ("HEI",     "HEI Valais-Wallis",           1),
    "Haute Ecole de Santé - Agasse":
        ("HES-AGS", "HES-SO Santé Agasse",         1),
    "Haute Ecole de Santé - Leukerbad":
        ("HES-LEU", "HES-SO Santé Leukerbad",      1),
}

df_div_silver = (
    spark.read.parquet(f"{silver_base}/bookings/")
    .select(trim(col("Division")).alias("DivisionName"))
    .filter(col("DivisionName").isNotNull() & (col("DivisionName") != ""))
    .distinct()
)

df_div_gold = read_gold("dim_division").select("DivisionName")
df_div_new  = df_div_silver.join(df_div_gold, on="DivisionName", how="left_anti")
new_divisions = df_div_new.collect()

if not new_divisions:
    logger.info("dim_division: no new divisions detected.")
else:
    for row in new_divisions:
        name_raw = row["DivisionName"]
        name_sql = name_raw.replace("'", "''")
        meta     = DIVISION_META.get(name_raw)
        if meta:
            code, school, is_active = meta
        else:
            # Generate short code from initials
            code     = "".join(w[0].upper() for w in name_raw.split() if w)[:10]
            school   = name_raw[:50]
            is_active = 1
        exec_sql(f"""
            IF NOT EXISTS (SELECT 1 FROM dim_division WHERE DivisionName = '{name_sql}')
            INSERT INTO dim_division (DivisionCode, DivisionName, SchoolName, IsActive)
            VALUES ('{code}', '{name_sql}', '{school.replace("'","''")}', {is_active})
        """)
    logger.info("dim_division: %d new division(s) inserted.", len(new_divisions))

# COMMAND ----------

# DBTITLE 1,Cell 15
# MAGIC %md
# MAGIC    
# MAGIC ## 6 · `dim_room` — rooms from `bookings`
# MAGIC
# MAGIC Source: `Nom` column from Silver (filtered `^VS-BEL` by Silver ETL).
# MAGIC Room code is parsed: `VS-BEL.{Wing}{Floor}{RoomNo}` or special pattern.
# MAGIC New room detected = automatic INSERT. No DELETE (historical consistency).

# COMMAND ----------

# DBTITLE 1,Cell 16
def parse_room_code(code: str) -> dict:
    """
    Parses a VS-BEL room code into its components.
    Examples:
      VS-BEL.N301        → wing=N, floor=3, room=01, type=Classroom
      VS-BEL.N401-Comodal→ wing=N, floor=4, room=01, type=Comodal
      VS-BEL.RS70-Aula   → wing=None, floor=None, room=None, type=Auditorium
      VS-BEL.Foyer       → type=Foyer
      VS-BEL.SUM         → type=Seminar
    """
    base = code.replace("VS-BEL.", "")
    result = {"wing": None, "floor": None, "room": None, "room_type": "Classroom"}

    if base == "Foyer":
        result["room_type"] = "Foyer"
    elif base == "SUM":
        result["room_type"] = "Seminar"
    elif "Aula" in base:
        result["room_type"] = "Auditorium"
    elif "Comodal" in base:
        m = re.match(r"([A-Z])(\d)(\d+)", base)
        if m:
            result.update({"wing": m.group(1), "floor": int(m.group(2)),
                           "room": m.group(3), "room_type": "Comodal"})
    else:
        m = re.match(r"([A-Z])(\d)(\d+)", base)
        if m:
            result.update({"wing": m.group(1), "floor": int(m.group(2)),
                           "room": m.group(3)})
    return result


df_rooms_silver = (
    spark.read.parquet(f"{silver_base}/bookings/")
    .select(trim(col("Nom")).alias("RoomCode"))
    .filter(col("RoomCode").rlike(r"^VS-BEL\."))
    .distinct()
)

df_rooms_gold = read_gold("dim_room").select("RoomCode")
df_rooms_new  = df_rooms_silver.join(df_rooms_gold, on="RoomCode", how="left_anti")
new_rooms     = df_rooms_new.collect()

if not new_rooms:
    logger.info("dim_room: no new rooms detected.")
else:
    for row in new_rooms:
        code = row["RoomCode"]
        p    = parse_room_code(code)
        wing  = f"'{p['wing']}'"   if p["wing"]  else "NULL"
        floor = str(p["floor"])    if p["floor"] else "NULL"
        room  = f"'{p['room']}'"   if p["room"]  else "NULL"
        code_sql = code.replace("'", "''")
        exec_sql(f"""
            IF NOT EXISTS (SELECT 1 FROM dim_room WHERE RoomCode = '{code_sql}')
            INSERT INTO dim_room
                (RoomCode, RoomFullName, Campus, Building, Wing, Floor,
                 RoomNumber, RoomType, NominalCapacity, IsActive)
            VALUES
                ('{code_sql}', '{code_sql}', 'Bellevue', 'VS-BEL',
                 {wing}, {floor}, {room}, '{p["room_type"]}', NULL, 1)
        """)
    logger.info("dim_room: %d new room(s) inserted.", len(new_rooms))

# COMMAND ----------

# DBTITLE 1,Cell 17
# MAGIC %md
# MAGIC    
# MAGIC ## 7 · `dim_prediction_model` — from JSON config file
# MAGIC
# MAGIC Source: `abfss://config@.../ml_models_config.json`
# MAGIC This file is versioned by the ML team and uploaded to ADLS before each deployment.
# MAGIC Expected format: list of models with ModelCode, ModelName, ModelType, etc.
# MAGIC Logic: INSERT if new ModelCode, UPDATE if ModelType or Features have changed.

# COMMAND ----------

# DBTITLE 1,Cell 18
import json

try:
    config_path = f"{config_base}/ml_models_config.json"
    raw = dbutils.fs.head(config_path, 65536)
    models = json.loads(raw)
    logger.info("ML config loaded: %d model(s).", len(models))
except Exception as e:
    # File missing → default values (first deployment)
    logger.warning("ML config not found (%s) — using default values.", e)
    models = [
        {
            "ModelCode": "PV_PROD_V1",
            "ModelName": "Solar Production Prediction v1",
            "ModelType": "To be defined",
            "TargetVariable": "Production_Kwh",
            "Features": "PRED_GLOB_ctrl, PRED_T_2M_ctrl, Hour, Month, IsWeekend",
            "TrainingStartDate": "2023-02-20",
            "TrainingEndDate":   "2023-05-05",
            "IsActive": 1,
            "Notes": "Model US#29 — predicts 15-min PV production (Sierre = Sion+Visp)."
        },
        {
            "ModelCode": "CONS_V1",
            "ModelName": "Building Consumption Prediction v1",
            "ModelType": "To be defined",
            "TargetVariable": "Consumption_Kwh",
            "Features": "PRED_T_2M_ctrl, PRED_RELHUM_2M_ctrl, RoomOccupation_Pct, Hour, IsAcademicDay",
            "TrainingStartDate": "2023-02-20",
            "TrainingEndDate":   "2023-05-05",
            "IsActive": 1,
            "Notes": "Model US#30 — predicts 15-min consumption (weather + occupancy)."
        },
    ]

df_models_gold = read_gold("dim_prediction_model").select("ModelCode", "ModelType", "Features")
existing = {row["ModelCode"]: row for row in df_models_gold.collect()}

for m in models:
    code = m["ModelCode"].replace("'", "''")
    name = m["ModelName"].replace("'", "''")
    mtype = m.get("ModelType", "To be defined").replace("'", "''")
    target = m.get("TargetVariable", "").replace("'", "''")
    features = m.get("Features", "").replace("'", "''")
    train_start = m.get("TrainingStartDate", "NULL")
    train_end = m.get("TrainingEndDate", "NULL")
    is_active = m.get("IsActive", 1)
    notes = m.get("Notes", "").replace("'", "''")

    if code not in [e for e in existing]:
        # New model → INSERT
        exec_sql(f"""
            INSERT INTO dim_prediction_model
                (ModelCode, ModelName, ModelType, TargetVariable, Features,
                 TrainingStartDate, TrainingEndDate, IsActive, Notes)
            VALUES
                ('{code}', '{name}', '{mtype}', '{target}', '{features}',
                 '{train_start}', '{train_end}', {is_active}, '{notes}')
        """)
        logger.info("dim_prediction_model: new model '%s' inserted.", code)
    else:
        # Check if ModelType or Features changed → UPDATE
        old = existing[code]
        if old["ModelType"] != mtype or old["Features"] != features:
            exec_sql(f"""
                UPDATE dim_prediction_model
                SET ModelType = '{mtype}', Features = '{features}', Notes = '{notes}'
                WHERE ModelCode = '{code}'
            """)
            logger.info("dim_prediction_model: model '%s' updated (type or features changed).", code)

# COMMAND ----------

# DBTITLE 1,Cell 19
# MAGIC %md
# MAGIC    
# MAGIC ## 8 · `ref_electricity_tariff` — from JSON config file
# MAGIC
# MAGIC Source: `abfss://config@.../electricity_tariff_config.json`
# MAGIC Simplified SCD Type 2 logic: if a new tariff is detected, we close the active one
# MAGIC (`EffectiveTo = yesterday`) and insert the new one. History is preserved.

# COMMAND ----------

# DBTITLE 1,Cell 20
try:
    tariff_path = f"{config_base}/electricity_tariff_config.json"
    raw_tariff  = dbutils.fs.head(tariff_path, 4096)
    tariff_cfg  = json.loads(raw_tariff)
    logger.info("Tariff config loaded.")
except Exception:
    tariff_cfg = {
        "TariffName":      "Standard HES-SO Valais",
        "PricePerKwh_CHF": 0.1500,
        "EffectiveFrom":   "2023-01-01",
        "Notes":           "Initial tariff 0.15 CHF/kWh — from Bellevue dashboard."
    }
    logger.warning("Tariff config not found — using default tariff (0.15 CHF/kWh).")

# Get active tariff (EffectiveTo IS NULL)
df_tariff_gold = read_gold("ref_electricity_tariff").filter(col("EffectiveTo").isNull())
active = df_tariff_gold.collect()

if not active:
    # First INSERT
    exec_sql(f"""
        INSERT INTO ref_electricity_tariff
            (TariffName, PricePerKwh_CHF, EffectiveFrom, EffectiveTo, Notes)
        VALUES
            ('{tariff_cfg["TariffName"]}', {tariff_cfg["PricePerKwh_CHF"]},
             '{tariff_cfg["EffectiveFrom"]}', NULL,
             '{tariff_cfg.get("Notes","").replace("'","''")}')""")
    logger.info("ref_electricity_tariff: initial tariff inserted (%s CHF/kWh).", tariff_cfg['PricePerKwh_CHF'])
elif float(active[0]["PricePerKwh_CHF"]) != float(tariff_cfg["PricePerKwh_CHF"]):
    # Tariff change → SCD2: close old, insert new
    exec_sql(f"""
        UPDATE ref_electricity_tariff
        SET EffectiveTo = DATEADD(DAY, -1, '{tariff_cfg["EffectiveFrom"]}')
        WHERE EffectiveTo IS NULL
    """)
    exec_sql(f"""
        INSERT INTO ref_electricity_tariff
            (TariffName, PricePerKwh_CHF, EffectiveFrom, EffectiveTo, Notes)
        VALUES
            ('{tariff_cfg["TariffName"]}', {tariff_cfg["PricePerKwh_CHF"]},
             '{tariff_cfg["EffectiveFrom"]}', NULL,
             '{tariff_cfg.get("Notes","").replace("'","''")}')""")
    logger.info("ref_electricity_tariff: new tariff %s CHF/kWh active.", tariff_cfg['PricePerKwh_CHF'])
else:
    logger.info("ref_electricity_tariff: tariff unchanged (%s CHF/kWh).", active[0]['PricePerKwh_CHF'])

# COMMAND ----------

# DBTITLE 1,Cell 21
# MAGIC %md
# MAGIC    
# MAGIC ## 9 · Final Verification

# COMMAND ----------

# DBTITLE 1,Cell 22
dims = [
    "dim_inverter", "dim_inverter_status", "dim_weather_site",
    "dim_measurement_type", "dim_division", "dim_room",
    "dim_prediction_model", "ref_electricity_tariff",
]

logger.info("=" * 55)
logger.info("%-30s %8s  %14s", "Table", "Rows", "Last Update")
logger.info("=" * 55)
for dim in dims:
    df = read_gold(dim)
    n  = df.count()
    logger.info("  %-28s %8d", dim, n)
logger.info("=" * 55)
logger.info("Step 1B completed — all Gold dimensions are up to date.")
