# Databricks notebook source
# MAGIC %md
# MAGIC # 📤 SAC Export — Gold Views → ADLS CSV
# MAGIC
# MAGIC Reads the pre-aggregated Gold layer views from Azure SQL, joins them,
# MAGIC and writes a single flat CSV to ADLS sacexport/ for SAP Analytics Cloud upload.
# MAGIC
# MAGIC | Output CSV                   | Source views                                           | US    |
# MAGIC |------------------------------|--------------------------------------------------------|-------|
# MAGIC | sac_inverter_combined.csv    | vw_inverter_status_breakdown + vw_inverter_performance | US#25 |

# COMMAND ----------

# MAGIC %md
# MAGIC ## 0 · Configuration

# COMMAND ----------

storage_account_name = "adlsbellevuegrp3"
storage_account_key  = dbutils.secrets.get(scope="keyvault-scope", key="adls-access-key")

spark.conf.set(
    f"fs.azure.account.key.{storage_account_name}.dfs.core.windows.net",
    storage_account_key,
)

sac_base = f"abfss://sacexport@{storage_account_name}.dfs.core.windows.net"

# Azure SQL — same credentials as silver_gold_facts.py
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

print(f"✅ ADLS SAC target : {sac_base}")
print(f"✅ Azure SQL       : {sql_server}.database.windows.net / {sql_database}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 · Read and JOIN Gold views via JDBC
# MAGIC
# MAGIC Strategy: aggregate vw_inverter_performance to day × inverter grain,
# MAGIC then LEFT JOIN onto vw_inverter_status_breakdown.
# MAGIC Result: one flat file at day × inverter × status category grain.
# MAGIC AvgPerformanceRatio repeats across status rows for the same day/inverter,
# MAGIC but since it is the same value, AVG() in SAC still gives the correct result.

# COMMAND ----------

df_combined = spark.read.jdbc(
    url   = jdbc_url,
    table = (
        "(SELECT "
        "    s.FullDate, s.Year, s.Month, s.MonthName, "
        "    s.InverterID, s.InverterName, "
        "    s.StatusCode, s.StatusLabel, s.StatusCategory, "
        "    s.IsFailure, s.ReadingCount, "
        "    CASE WHEN s.IsFailure = 1 THEN s.ReadingCount ELSE 0 END AS FailureReadingCount, "
        "    CAST(ROUND(s.PctOfDayReadings, 2) AS DECIMAL(6,2)) AS PctOfDayReadings, "
        "    CASE WHEN s.StatusCategory = 'OK' "
        "         THEN CAST(ROUND(p.AvgPerformanceRatio, 4) AS DECIMAL(8,4)) "
        "         ELSE NULL END AS AvgPerformanceRatio, "
        "    p.HadFailureToday "
        "FROM dbo.vw_inverter_status_breakdown s "
        "LEFT JOIN ( "
        "    SELECT InverterID, FullDate, "
        "           CAST(ROUND(AVG(PerformanceRatio), 4) AS DECIMAL(8,4)) AS AvgPerformanceRatio, "
        "           MAX(HadFailure) AS HadFailureToday "
        "    FROM dbo.vw_inverter_performance "
        "    GROUP BY InverterID, FullDate "
        ") p ON s.InverterID = p.InverterID AND s.FullDate = p.FullDate) AS t"
    ),
    properties = jdbc_props,
)
 
n_combined = df_combined.count()
print(f"✅ Combined (status + performance) : {n_combined:,} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 · Write combined CSV to temporary staging folder

# COMMAND ----------

tmp_combined   = f"{sac_base}/_tmp_sac_inverter_combined"
final_combined = f"{sac_base}/sac_inverter_combined.csv"

# Remove previous versions (idempotent re-run)
for path in [tmp_combined, final_combined]:
    try:
        dbutils.fs.rm(path, recurse=True)
        print(f"🗑️  Removed: {path}")
    except Exception:
        pass

# Write to temp folder first (Spark requires a directory target)
(
    df_combined
    .coalesce(1)
    .write
    .mode("overwrite")
    .option("header", "true")
    .option("sep", ",")
    .option("encoding", "UTF-8")
    .csv(tmp_combined)
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 · Rename to clean filename

# COMMAND ----------

def promote_csv(tmp_dir, final_path, label):
    """
    Move the single coalesce(1) part file out of its temp folder to a
    clean top-level filename, then delete the temp folder.
    Users see sac_inverter_combined.csv — not part-00000-xxxx.csv.
    """
    files    = dbutils.fs.ls(tmp_dir)
    part_csv = [f.path for f in files if f.name.endswith(".csv")]
    if not part_csv:
        raise FileNotFoundError(f"No CSV found in {tmp_dir}")
    dbutils.fs.mv(part_csv[0], final_path)
    dbutils.fs.rm(tmp_dir, recurse=True)
    print(f"✅ {label} → {final_path}")

promote_csv(tmp_combined, final_combined, f"sac_inverter_combined.csv ({n_combined:,} rows)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4 · Verification

# COMMAND ----------

print("=" * 70)
print("SAC EXPORT SUMMARY")
print("=" * 70)

info    = dbutils.fs.ls(final_combined)
size_kb = info[0].size // 1024
print(f"\n  sac_inverter_combined.csv  [US#25 — failures + performance]")
print(f"    Rows   : {n_combined:,}")
print(f"    Size   : ~{size_kb:,} KB")
print(f"    Path   : {final_combined}")
print("\n✅ Export complete — download sac_inverter_combined.csv from ADLS sacexport/ and upload to SAC.")
print("=" * 70)
