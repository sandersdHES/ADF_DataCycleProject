-- =============================================================================
-- Truncate the three Vetroz-derived fact tables so silver_gold_facts.py can
-- repopulate them from scratch after the xx:00 synthesis change in
-- silver_transformation.py.
--
-- Why a full reload (not incremental):
--   - silver_transformation.py overwrites silver/, but silver_gold_facts.py
--     uses get_watermark() = MAX(DateKey) per fact table. With the watermark
--     pinned at the existing latest DateKey, none of the new synthetic xx:00
--     rows for already-loaded dates would be picked up.
--   - Truncating the fact tables resets MAX(DateKey) to NULL → get_watermark
--     falls back to 0 → every silver row is reloaded.
--
-- fact_solar_inverter is NOT truncated: silver/solar_inverters/ already has
-- 5-min granularity, the xx:00 synthesis does not touch it.
--
-- Run order
-- ---------
--   1. Re-run silver_transformation.py in Databricks first (silver/ is
--      overwritten with the new 96-slot/day cadence).
--   2. Run THIS script (commits immediately — no transaction wrapper).
--   3. Re-run silver_gold_facts.py in Databricks.
--   4. Verify with the SELECT block at the bottom.
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

-- ---------- TRUNCATE --------------------------------------------------------
TRUNCATE TABLE dbo.fact_energy_consumption;
TRUNCATE TABLE dbo.fact_solar_production;
TRUNCATE TABLE dbo.fact_environment;

PRINT 'Truncated 3 fact tables. Re-run silver_gold_facts.py to repopulate from silver.';

-- ---------- AFTER (run again after silver_gold_facts.py) -------------------
-- Expected: each table has 96 distinct TimeKey values per healthy day.
-- SELECT TOP 5 DateKey, COUNT(DISTINCT TimeKey) AS slots
-- FROM dbo.fact_energy_consumption
-- WHERE DateKey >= 20230110
-- GROUP BY DateKey ORDER BY DateKey;
--
-- Expected: monthly totals unchanged (energy is conserved).
-- SELECT [Year], [Month], ROUND(SUM(DeltaEnergy_Kwh), 1) AS total_kwh
-- FROM dbo.fact_energy_consumption GROUP BY [Year], [Month] ORDER BY [Year], [Month];
--
-- Expected: TimeKey=0 average ≈ TimeKey=15 average (no more 2x stripe).
-- SELECT TimeKey, ROUND(AVG(DeltaEnergy_Kwh), 2) AS avg_delta
-- FROM dbo.fact_energy_consumption
-- WHERE TimeKey IN (0, 15, 30, 45)
-- GROUP BY TimeKey ORDER BY TimeKey;
