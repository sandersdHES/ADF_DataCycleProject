# Databricks notebook source
# DBTITLE 1,Untitled


# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC # 🥈→🥇 Étape 2 — Chargement des tables de faits (Gold)
# MAGIC
# MAGIC Ce notebook lit les tables Silver (Parquet sur ADLS) et écrit les faits
# MAGIC dans **Azure SQL BellevueEnergyDW** via JDBC.
# MAGIC
# MAGIC ### Stratégie de chargement : **Append incrémental par date**
# MAGIC
# MAGIC Chaque fait est identifié par une **watermark** (date max déjà chargée en Gold).
# MAGIC Seules les lignes Silver postérieures à cette watermark sont insérées.
# MAGIC Cela évite les doublons sans avoir à vider et recharger toutes les tables.
# MAGIC
# MAGIC | Table Gold                | Source Silver              | Grain              | Fréquence   |
# MAGIC |---------------------------|----------------------------|--------------------|-------------|
# MAGIC | `fact_solar_inverter`     | `solar_inverters/`         | 1-min × 5 onduleurs| Quotidien   |
# MAGIC | `fact_solar_production`   | `solar_aggregated/`        | 15-min             | Quotidien   |
# MAGIC | `fact_energy_consumption` | `consumption/`             | 15-min             | Quotidien   |
# MAGIC | `fact_environment`        | `temperature/` + `humidity/`| 15-min (jointure) | Quotidien   |
# MAGIC | `fact_weather_forecast`   | `weather_forecasts/`       | 3h × mesure × horiz| Quotidien   |
# MAGIC | `fact_room_booking`       | `bookings/`                | événement/salle    | Hebdomadaire|
# MAGIC
# MAGIC > `fact_energy_prediction` est alimentée par le pipeline ML (KNIME) — hors scope ici.

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ## 0 · Configuration & helpers

# COMMAND ----------

# DBTITLE 1,Untitled
from pyspark.sql.functions import (
    col, lit, year, month, hour, minute,
    to_date, try_to_date, date_format, concat_ws,
    coalesce, when, trim, regexp_replace
)
from pyspark.sql import DataFrame
import datetime

# ── ADLS Silver ────────────────────────────────────────────────────────────────
# BUG B CORRIGÉ : storage_account_name et sql_server n'étaient pas déclarés
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
    Retry helper pour Azure SQL Serverless — la base se met en pause après
    inactivité et met ~20-60 s à redémarrer à la première connexion.
    Stratégie : backoff linéaire (20s, 40s, 60s, 80s) sur les erreurs
    'not currently available' uniquement. Les autres erreurs sont relancées immédiatement.
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
                print(f"⚠️  Azure SQL en cours de réveil (tentative {attempt}/{max_attempts}) "
                      f"— nouvelle tentative dans {wait}s...")
                time.sleep(wait)
                wait += initial_wait
            else:
                raise

def read_gold(table: str) -> DataFrame:
    """Lit une table Gold depuis Azure SQL (avec retry au réveil Serverless)."""
    return _jdbc_retry(
        lambda: spark.read.jdbc(url=jdbc_url, table=table, properties=jdbc_props)
    )

def write_gold(df: DataFrame, table: str, batch_size: int = 20_000):
    """
    Écrit un DataFrame en APPEND dans Azure SQL.
    - batchsize   : nombre de lignes par batch JDBC (compromis mémoire/débit)
    - numPartitions: parallélisme d'écriture (adapter selon le cluster)
    """
    (df.write
       .mode("append")
       .option("batchsize", batch_size)
       .option("numPartitions", 8)
       .option("truncate", "false")
       .jdbc(url=jdbc_url, table=table, properties=jdbc_props))


def get_watermark(table: str, date_col: str = "DateKey") -> int:
    """
    Retourne le DateKey maximum déjà présent dans une table Gold.
    Retourne 0 si la table est vide (premier chargement).
    Format DateKey : YYYYMMDD (int).
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
    """Convertit un timestamp en DateKey YYYYMMDD (int)."""
    return date_format(ts_col, "yyyyMMdd").cast("int")


def ts_to_timekey(ts_col):
    """Convertit un timestamp en TimeKey = minutes depuis minuit (smallint)."""
    return (hour(ts_col) * 60 + minute(ts_col)).cast("short")


def french_date_to_english(date_col):
    """
    Convertit les dates françaises en anglais pour parsing.
    Ex: '8 janv. 2023' → '8 Jan 2023'
    """
    result = date_col
    french_months = [
        ("janv\\.", "Jan"), ("févr\\.", "Feb"), ("mars", "Mar"),
        ("avr\\.", "Apr"), ("mai", "May"), ("juin", "Jun"),
        ("juil\\.", "Jul"), ("août", "Aug"), ("sept\\.", "Sep"),
        ("oct\\.", "Oct"), ("nov\\.", "Nov"), ("déc\\.", "Dec")
    ]
    for fr, en in french_months:
        result = regexp_replace(result, fr, en)
    return result


print("✅ Configuration chargée.")

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ## 1 · `fact_solar_inverter`
# MAGIC
# MAGIC **Source** : `silver/solar_inverters/`  
# MAGIC **Grain** : 1 ligne par minute par onduleur (5 onduleurs × ~1 440 min/jour)  
# MAGIC **Lookups FK** :
# MAGIC - `InverterKey` ← `dim_inverter.InverterID`
# MAGIC - `StatusKey`   ← `dim_inverter_status.StatusCode` (sentinelle 99 si inconnu)
# MAGIC
# MAGIC **Colonnes Silver** (toutes présentes grâce au BUG A corrigé dans silver_transformation.py) :
# MAGIC `log_timestamp`, `inverter_id`, `ac_power_w`, `daysum`, `status_code`,
# MAGIC `pdc1`, `pdc2`, `udc1`, `udc2`, `is_failure`

# COMMAND ----------

# DBTITLE 1,Untitled
wm_inverter = get_watermark("fact_solar_inverter")
print(f"Watermark fact_solar_inverter : DateKey > {wm_inverter}")

# Lookup tables (broadcast — petites dimensions)
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
    print("ℹ️  Aucune nouvelle ligne Silver — fact_solar_inverter déjà à jour.")
else:
    df_fact_inv = (
        df_inv_silver
        # FK DateKey + TimeKey
        .withColumn("DateKey", ts_to_datekey(col("log_timestamp")))
        .withColumn("TimeKey", ts_to_timekey(col("log_timestamp")))
        # Lookup InverterKey
        .join(df_dim_inv, col("inverter_id") == col("InverterID"), how="left")
        # Lookup StatusKey (utilise 99 si le code est inconnu)
        .join(df_dim_status, col("status_code") == col("StatusCode"), how="left")
        .withColumn("StatusKey", coalesce(col("StatusKey"), lit(99).cast("byte")))
        # Mesures — BUG C CORRIGÉ : lecture des vraies colonnes Silver
        # (le BUG A dans silver_transformation.py a ajouté ces colonnes dans l'unpivot)
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
        .filter(col("InverterKey").isNotNull())  # rejette les onduleurs sans correspondance dim
        .dropDuplicates(["DateKey", "TimeKey", "InverterKey"])
    )

    n = df_fact_inv.count()
    write_gold(df_fact_inv, "fact_solar_inverter")
    print(f"✅ fact_solar_inverter : {n:,} lignes insérées (DateKey > {wm_inverter}).")

df_dim_inv.unpersist()
df_dim_status.unpersist()

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ## 2 · `fact_solar_production`
# MAGIC
# MAGIC **Source** : `silver/solar_aggregated/`  
# MAGIC **Grain** : 1 ligne par slot 15-min (production PV totale du bâtiment)  
# MAGIC **Colonnes** : `CumulativeEnergy_Kwh`, `DeltaEnergy_Kwh`  
# MAGIC `RetailValue_CHF` est une colonne calculée SQL (`DeltaEnergy_Kwh × 0.15`) — non à insérer.

# COMMAND ----------

# DBTITLE 1,Untitled
wm_prod = get_watermark("fact_solar_production")
print(f"Watermark fact_solar_production : DateKey > {wm_prod}")

df_prod_silver = (
    spark.read.parquet(f"{silver_base}/solar_aggregated/")
    .filter(ts_to_datekey(col("timestamp")) > wm_prod)
    .filter(col("timestamp").isNotNull())
)

if df_prod_silver.isEmpty():
    print("ℹ️  Aucune nouvelle ligne Silver — fact_solar_production déjà à jour.")
else:
    df_fact_prod = (
        df_prod_silver
        .withColumn("DateKey", ts_to_datekey(col("timestamp")))
        .withColumn("TimeKey", ts_to_timekey(col("timestamp")))
        .withColumn("CumulativeEnergy_Kwh", col("cumulative_reading").cast("double"))
        .withColumn("DeltaEnergy_Kwh",      col("delta_value").cast("double"))
        .withColumn("Year",  year(col("timestamp")).cast("short"))
        .withColumn("Month", month(col("timestamp")).cast("byte"))
        # RetailValue_CHF est calculée par SQL → ne pas l'inclure
        .select("DateKey", "TimeKey", "CumulativeEnergy_Kwh", "DeltaEnergy_Kwh", "Year", "Month")
        .dropDuplicates(["DateKey", "TimeKey"])
    )

    n = df_fact_prod.count()
    write_gold(df_fact_prod, "fact_solar_production")
    print(f"✅ fact_solar_production : {n:,} lignes insérées (DateKey > {wm_prod}).")

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ## 3 · `fact_energy_consumption`
# MAGIC
# MAGIC **Source** : `silver/consumption/`  
# MAGIC **Grain** : 1 ligne par slot 15-min (consommation électrique du bâtiment)  
# MAGIC `CostCHF` est une colonne calculée SQL — non à insérer.

# COMMAND ----------

# DBTITLE 1,Untitled
wm_conso = get_watermark("fact_energy_consumption")
print(f"Watermark fact_energy_consumption : DateKey > {wm_conso}")

df_conso_silver = (
    spark.read.parquet(f"{silver_base}/consumption/")
    .filter(ts_to_datekey(col("timestamp")) > wm_conso)
    .filter(col("timestamp").isNotNull())
)

if df_conso_silver.isEmpty():
    print("ℹ️  Aucune nouvelle ligne Silver — fact_energy_consumption déjà à jour.")
else:
    df_fact_conso = (
        df_conso_silver
        .withColumn("DateKey", ts_to_datekey(col("timestamp")))
        .withColumn("TimeKey", ts_to_timekey(col("timestamp")))
        .withColumn("CumulativeEnergy_Kwh", col("cumulative_reading").cast("double"))
        .withColumn("DeltaEnergy_Kwh",      col("delta_value").cast("double"))
        .withColumn("Year",  year(col("timestamp")).cast("short"))
        .withColumn("Month", month(col("timestamp")).cast("byte"))
        # CostCHF est calculée par SQL → ne pas l'inclure
        .select("DateKey", "TimeKey", "CumulativeEnergy_Kwh", "DeltaEnergy_Kwh", "Year", "Month")
        .dropDuplicates(["DateKey", "TimeKey"])
    )

    n = df_fact_conso.count()
    write_gold(df_fact_conso, "fact_energy_consumption")
    print(f"✅ fact_energy_consumption : {n:,} lignes insérées (DateKey > {wm_conso}).")

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ## 4 · `fact_environment`
# MAGIC
# MAGIC **Source** : `silver/temperature/` + `silver/humidity/`  
# MAGIC **Grain** : 1 ligne par slot 15-min — jointure OUTER sur `timestamp`  
# MAGIC
# MAGIC Les deux sources ont la même fréquence 15-min mais peuvent avoir des trous.
# MAGIC Un FULL OUTER JOIN garantit qu'aucune mesure n'est perdue si l'un des
# MAGIC deux capteurs est défaillant sur un slot donné.

# COMMAND ----------

# DBTITLE 1,Untitled
wm_env = get_watermark("fact_environment")
print(f"Watermark fact_environment : DateKey > {wm_env}")

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
    print("ℹ️  Aucune nouvelle ligne Silver — fact_environment déjà à jour.")
else:
    # Full outer join sur timestamp pour ne rien perdre
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
    print(f"✅ fact_environment : {n:,} lignes insérées (DateKey > {wm_env}).")

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ## 5 · `fact_weather_forecast`
# MAGIC
# MAGIC **Source** : `silver/weather_forecasts/`  
# MAGIC **Grain** : 1 ligne par (datetime × measurement × horizon de prévision)  
# MAGIC **Lookups FK** :
# MAGIC - `SiteKey`        ← `dim_weather_site.SiteName`   (Sierre uniquement en Silver)
# MAGIC - `MeasurementKey` ← `dim_measurement_type.MeasurementCode`
# MAGIC
# MAGIC La colonne `Prediction` du Silver est un entier string `'00'`→`'45'`
# MAGIC représentant l'horizon en pas de 3h → castée en SMALLINT.
# MAGIC
# MAGIC **Note** : Les dates hors plage de `dim_date` (ex: DateKey 20221231) produisent
# MAGIC une violation de FK JDBC et sont rejetées. Aucun filtre ad-hoc nécessaire :
# MAGIC le Silver ne contient que des dates du jeu de données (2023-02 → 2023-05).

# COMMAND ----------

# DBTITLE 1,Untitled
wm_weather = get_watermark("fact_weather_forecast")
print(f"Watermark fact_weather_forecast : DateKey > {wm_weather}")

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
    print("ℹ️  Aucune nouvelle ligne Silver — fact_weather_forecast déjà à jour.")
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
        # Rejette les lignes sans FK valide (site ou mesure inconnus)
        .filter(col("SiteKey").isNotNull() & col("MeasurementKey").isNotNull())
        .dropDuplicates(["DateKey", "TimeKey", "SiteKey", "MeasurementKey", "PredictionHorizon"])
    )

    n = df_fact_weather.count()
    write_gold(df_fact_weather, "fact_weather_forecast")
    print(f"✅ fact_weather_forecast : {n:,} lignes insérées (DateKey > {wm_weather}).")

df_dim_site.unpersist()
df_dim_meas.unpersist()

# COMMAND ----------

# DBTITLE 1,Untitled
# MAGIC %md
# MAGIC ## 6 · `fact_room_booking`
# MAGIC
# MAGIC **Source** : `silver/bookings/`  
# MAGIC **Grain** : 1 ligne par réservation (occurrence dans une salle)  
# MAGIC **Lookups FK** :
# MAGIC - `RoomKey`     ← `dim_room.RoomCode`
# MAGIC - `DivisionKey` ← `dim_division.DivisionName`
# MAGIC
# MAGIC **Particularités** :
# MAGIC - `DateKey` = date de l'occurrence (colonne `Date` du Silver)
# MAGIC - `StartTimeKey` / `EndTimeKey` = `HH:MM` → minutes depuis minuit (colonnes `Heure_Debut` / `Heure_Fin`)
# MAGIC - `DurationMinutes` = EndTimeKey − StartTimeKey
# MAGIC - `IsRecurring` : TRUE si `Date_Recurrence_Debut` ou `Date_Recurrence_Fin` non NULL
# MAGIC - BUG D CORRIGÉ : le CSV avait 2 colonnes dupliquées "Date de début" et "Date de fin".
# MAGIC   Renommées dans Silver → `Heure_Debut`, `Heure_Fin`, `Date_Recurrence_Debut`, `Date_Recurrence_Fin`.
# MAGIC - BUG E CORRIGÉ : "29 févr. 2023" (date inexistante) → `try_to_date` retourne NULL,
# MAGIC   filtrée par `filter(col("DateKey").isNotNull())`. Pas de filtre ad-hoc nécessaire.

# COMMAND ----------

# DBTITLE 1,Cell 16
wm_booking = get_watermark("fact_room_booking")
print(f"Watermark fact_room_booking : DateKey > {wm_booking}")

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

# Calcul du DateKey depuis la colonne Date (format texte français)
df_booking_silver = (
    df_booking_silver
    .withColumn("date_en", french_date_to_english(col("Date")))
    .withColumn("ts_date", try_to_date(col("date_en"), "d MMM yyyy"))
    .withColumn("DateKey", date_format(col("ts_date"), "yyyyMMdd").cast("int"))
    .filter(col("DateKey").isNotNull())  # Exclut les dates invalides (NULL)
    .filter(col("DateKey") > wm_booking)
)

if df_booking_silver.isEmpty():
    print("ℹ️  Aucune nouvelle ligne Silver — fact_room_booking déjà à jour.")
else:
    def time_str_to_minutes(time_col):
        """Convertit 'HH:mm' en minutes depuis minuit pour TimeKey."""
        return (
            col(time_col).substr(1, 2).cast("int") * 60
            + col(time_col).substr(4, 2).cast("int")
        ).cast("short")

    df_fact_booking = (
        df_booking_silver
        # Lookup FK Room
        .join(df_dim_room,
              trim(col("Nom")) == col("RoomCode"), how="left")
        # Lookup FK Division (NULL → rejeté par filter plus bas)
        .join(df_dim_div,
              trim(col("Division")) == col("DivisionName"), how="left")
        # BUG D CORRIGÉ : noms réels des colonnes après renommage Silver
        # idx 3 (heure début réservation) → Heure_Debut     format HH:mm
        # idx 4 (heure fin réservation)   → Heure_Fin       format HH:mm
        # idx 11 (début récurrence)       → Date_Recurrence_Debut  format 'd MMM yyyy'
        # idx 12 (fin récurrence)         → Date_Recurrence_Fin    format 'd MMM yyyy'
        .withColumn("StartTimeKey", time_str_to_minutes("Heure_Debut"))
        .withColumn("EndTimeKey",   time_str_to_minutes("Heure_Fin"))
        .withColumn("DurationMinutes",
            (col("EndTimeKey").cast("int") - col("StartTimeKey").cast("int")).cast("short"))
        # Recurrence dates
        .withColumn("date_en_recur_start", french_date_to_english(coalesce(col("Date_Recurrence_Debut"), lit(""))))
        .withColumn("RecurrenceStart", try_to_date(col("date_en_recur_start"), "d MMM yyyy"))
        .withColumn("date_en_recur_end", french_date_to_english(coalesce(col("Date_Recurrence_Fin"), lit(""))))
        .withColumn("RecurrenceEnd", try_to_date(col("date_en_recur_end"), "d MMM yyyy"))
        # NOTE: IsRecurring est une colonne calculée SQL (computed column)
        # → Ne PAS l'inclure dans l'INSERT, SQL Server la calcule automatiquement
        # Mesures & métadonnées
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
            # IsRecurring retiré — colonne calculée SQL
        )
        # Rejette les lignes sans FK valide (salle ou division inconnues)
        .filter(col("RoomKey").isNotNull() & col("DivisionKey").isNotNull())
        .dropDuplicates(["DateKey", "StartTimeKey", "RoomKey", "ReservationNo"])
    )

    n = df_fact_booking.count()
    write_gold(df_fact_booking, "fact_room_booking")
    print(f"✅ fact_room_booking : {n:,} lignes insérées (DateKey > {wm_booking}).")

df_dim_room.unpersist()
df_dim_div.unpersist()

# COMMAND ----------

print("\n" + "="*80)
print("✅ Chargement des tables de faits terminé.")
print("="*80)
