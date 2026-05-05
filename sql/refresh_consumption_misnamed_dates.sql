-- =============================================================================
-- Restore fact_energy_consumption to a clean state after a corrupted
-- silver/gold reload.
--
-- Context: a bad silver_transformation.py run mislabeled Jan 3/4/5 data as
-- Mar/Apr/May 1, inflating monthly consumption 3–20×. Silver has since been
-- reverted and re-run cleanly. This script resets the gold watermark so
-- silver_gold_facts.py can re-import the correct data.
--
-- Run order
-- ---------
--   1. Confirm silver_transformation.py on branch claude/fix-solar-data-St3Z0
--      has already been re-run in Databricks (silver/consumption/ overwritten).
--   2. Run THIS script (commits immediately — no dry-run wrapper).
--   3. Re-run silver_gold_facts.py in Databricks.
--   4. Verify monthly totals with the SELECT at the bottom.
-- =============================================================================

SET NOCOUNT ON;
SET XACT_ABORT ON;

-- ---------- BEFORE ----------------------------------------------------------
PRINT '--- BEFORE ---';
SELECT [Year], [Month],
       COUNT(DISTINCT DateKey)           AS days,
       ROUND(SUM(DeltaEnergy_Kwh), 1)   AS total_kwh
FROM dbo.fact_energy_consumption
GROUP BY [Year], [Month]
ORDER BY [Year], [Month];

-- ---------- DELETE ----------------------------------------------------------
DELETE FROM dbo.fact_energy_consumption
WHERE DateKey >= 20230216;
PRINT CONCAT(N'fact_energy_consumption: deleted ', @@ROWCOUNT, N' rows (DateKey >= 20230216). '
           + N'Re-run silver_gold_facts.py to reload.');

-- ---------- WATERMARK CHECK -------------------------------------------------
SELECT MAX(DateKey) AS new_max_datekey,
       COUNT(*)     AS remaining_rows
FROM dbo.fact_energy_consumption;
-- Expected: new_max_datekey = 20230215

-- ---------- AFTER (run again after silver_gold_facts.py) -------------------
-- SELECT [Year], [Month],
--        COUNT(DISTINCT DateKey)           AS days,
--        ROUND(SUM(DeltaEnergy_Kwh), 1)   AS total_kwh
-- FROM dbo.fact_energy_consumption
-- GROUP BY [Year], [Month]
-- ORDER BY [Year], [Month];
-- Expected: Jan=43340, Feb=38342, Mar=45009, Apr=39974, May=8243
