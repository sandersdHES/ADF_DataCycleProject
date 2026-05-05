-- =============================================================================
-- Truncate the three Vetroz-derived fact tables so silver_gold_facts.py can
-- repopulate them from scratch after the gap-aware delta nulling change in
-- silver_transformation.py.
--
-- Why a full reload (not incremental):
--   - silver_transformation.py overwrites silver/, but silver_gold_facts.py
--     uses get_watermark() = MAX(DateKey) per fact table. With the watermark
--     pinned at the existing latest DateKey, the now-nulled deltas for the
--     post-missing-day rows (Feb 17, Mar 2, Apr 2, May 2) and any other
--     gap > 30 min would not overwrite the existing inflated rows in gold.
--   - Truncating the fact tables resets MAX(DateKey) to NULL → get_watermark
--     falls back to 0 → every silver row is reloaded.
--
-- fact_solar_inverter is NOT truncated: silver/solar_inverters/ uses 5-min
-- source telemetry, no gap-aware nulling applies there.
--
-- Run order
-- ---------
--   1. Re-run silver_transformation.py in Databricks first (silver/ is
--      overwritten with nulled deltas wherever gap > 30 min).
--   2. Run THIS script in SSMS / Azure Data Studio. Commits immediately.
--   3. Re-run silver_gold_facts.py in Databricks.
--   4. Refresh Power BI (Import-mode datasets need a manual refresh — the
--      hour-0 spike on the "Consumption Pattern by Time of Day" chart will
--      collapse from ~3,500 kWh to ~1,200 kWh once the post-missing-day
--      00:15 row carries a NULL delta).
-- =============================================================================

SET NOCOUNT ON;
SET XACT_ABORT ON;

-- ---------- BEFORE ----------------------------------------------------------
PRINT '--- BEFORE ---';
SELECT 'fact_energy_consumption' AS tbl, COUNT(*) AS rows_before, MAX(DateKey) AS max_dk FROM dbo.fact_energy_consumption
UNION ALL
SELECT 'fact_solar_production',          COUNT(*),                MAX(DateKey)          FROM dbo.fact_solar_production
UNION ALL
SELECT 'fact_environment',               COUNT(*),                MAX(DateKey)          FROM dbo.fact_environment;

-- The four post-missing-day 00:15 rows that should drop to NULL after reload:
SELECT DateKey, TimeKey, ROUND(DeltaEnergy_Kwh, 1) AS delta_before
FROM dbo.fact_energy_consumption
WHERE TimeKey = 15
  AND DateKey IN (20230217, 20230302, 20230402, 20230502)
ORDER BY DateKey;

-- ---------- TRUNCATE --------------------------------------------------------
TRUNCATE TABLE dbo.fact_energy_consumption;
TRUNCATE TABLE dbo.fact_solar_production;
TRUNCATE TABLE dbo.fact_environment;

PRINT 'Truncated 3 fact tables. Re-run silver_gold_facts.py to repopulate from silver.';

-- ---------- AFTER (run again after silver_gold_facts.py) -------------------
-- Expected: the four post-missing-day 00:15 rows now carry NULL DeltaEnergy_Kwh.
-- SELECT DateKey, TimeKey, DeltaEnergy_Kwh AS delta_after
-- FROM dbo.fact_energy_consumption
-- WHERE TimeKey = 15
--   AND DateKey IN (20230217, 20230302, 20230402, 20230502)
-- ORDER BY DateKey;
--
-- Expected: hour-0 average drops to ≈ TimeKey 30 / 45 average (~10.85 kWh).
-- SELECT TimeKey, ROUND(AVG(DeltaEnergy_Kwh), 2) AS avg_delta
-- FROM dbo.fact_energy_consumption
-- WHERE TimeKey IN (0, 15, 30, 45)
-- GROUP BY TimeKey ORDER BY TimeKey;
