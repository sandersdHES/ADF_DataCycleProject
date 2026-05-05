-- =============================================================================
-- Refresh the inverter-derived backfill of dbo.fact_solar_production.
--
-- Backfilled rows are recognisable because their CumulativeEnergy_Kwh is NULL:
-- only the *-PV.csv source (Jan 1 - Feb 19 2023) populates that column. Rows
-- where it is NULL come from silver_gold_facts.py step 2b (Pac integration on
-- the per-inverter min*.csv data) and can safely be wiped and regenerated.
--
-- Use this when:
--   * The Pac-integration logic changes and you want the backfill recomputed
--   * A new inverter's data starts flowing and old rows under-counted it
--   * You added inverter rows after the previous backfill ran
--
-- Run order
-- ---------
--   1. Run this script with COMMIT to clear backfilled rows.
--   2. Re-run silver_gold_facts.py in Databricks. Step 2 (watermark-based,
--      from *-PV.csv) skips everything that's still there; step 2b refills
--      the deleted slots from the inverter Pac data.
--   3. Verify with the monthly query in vw_daily_energy_balance.
--
-- ROLLBACK is the default for a dry run; flip to COMMIT to apply.
-- =============================================================================

SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRANSACTION;

-- ---------- BEFORE ----------------------------------------------------------
PRINT '--- BEFORE ---';
SELECT
    SUM(CASE WHEN CumulativeEnergy_Kwh IS NULL     THEN 1 ELSE 0 END) AS backfilled_rows,
    SUM(CASE WHEN CumulativeEnergy_Kwh IS NOT NULL THEN 1 ELSE 0 END) AS pv_csv_rows,
    COUNT(*)                                                          AS total_rows,
    MIN(DateKey)                                                      AS min_datekey,
    MAX(DateKey)                                                      AS max_datekey
FROM dbo.fact_solar_production;

-- Show per-month impact so you can sanity-check before committing.
SELECT
    [Year], [Month],
    COUNT(*)                                                AS rows_to_delete,
    ROUND(SUM(DeltaEnergy_Kwh), 1)                          AS kwh_to_delete
FROM dbo.fact_solar_production
WHERE CumulativeEnergy_Kwh IS NULL
GROUP BY [Year], [Month]
ORDER BY [Year], [Month];

-- ---------- DELETE ----------------------------------------------------------
DELETE FROM dbo.fact_solar_production
WHERE CumulativeEnergy_Kwh IS NULL;
PRINT CONCAT(N'fact_solar_production: ', @@ROWCOUNT, N' backfilled rows deleted');

-- ---------- AFTER -----------------------------------------------------------
PRINT '--- AFTER ---';
SELECT
    SUM(CASE WHEN CumulativeEnergy_Kwh IS NULL     THEN 1 ELSE 0 END) AS backfilled_rows,
    SUM(CASE WHEN CumulativeEnergy_Kwh IS NOT NULL THEN 1 ELSE 0 END) AS pv_csv_rows,
    COUNT(*)                                                          AS total_rows,
    MIN(DateKey)                                                      AS min_datekey,
    MAX(DateKey)                                                      AS max_datekey
FROM dbo.fact_solar_production;

-- Flip ROLLBACK -> COMMIT to apply for real.
ROLLBACK TRANSACTION;
-- COMMIT TRANSACTION;
