-- =============================================================================
-- Refresh fact_energy_consumption after fixing the four MM.DD.YYYY-named
-- consumption files in silver_transformation.py.
--
-- Until the fix, four bronze files used American date order in both their
-- filename and their Date_Raw column:
--    02.16.2023-Consumption.csv   (Feb 16)
--    03.01.2023-Consumption.csv   (Mar 1)
--    04.01.2023-Consumption.csv   (Apr 1)
--    05.01.2023-Consumption.csv   (May 1)
--
-- The dd.MM.yyyy parser either rejected them (Feb 16: month=16 invalid → all
-- rows dropped) or quietly relabeled their data as Jan 3 / Jan 4 / Jan 5,
-- where dropDuplicates(["timestamp"]) collided them with the real Jan files
-- and lost the misclassified rows.
--
-- After the silver fix, the four dates parse to their intended DateKey. To
-- pick them up in gold, wipe rows from DateKey >= 20230216 so the
-- watermark drops below Feb 16 and the next silver_gold_facts.py run
-- re-imports the corrected silver layer.
--
-- The Jan 3/4/5 rows already in gold should be intact (the misclassified
-- May/Apr/Mar rows did not survive dedup with cumulative_reading values
-- ~100k kWh higher than Jan). The verification block at the bottom checks
-- this; if any of those days look polluted, uncomment the optional DELETE.
--
-- Run order
-- ---------
--   1. Apply the silver_transformation.py change.
--   2. Re-run silver_transformation.py in Databricks.
--   3. Run this script with COMMIT.
--   4. Re-run silver_gold_facts.py.
--   5. Verify with the SELECT block at the bottom.
--
-- ROLLBACK is the default for a dry run; flip to COMMIT to apply.
-- =============================================================================

SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRANSACTION;

-- ---------- BEFORE ----------------------------------------------------------
PRINT '--- BEFORE ---';
SELECT DateKey,
       COUNT(*)                        AS row_count,
       MIN(CumulativeEnergy_Kwh)       AS min_cum,
       MAX(CumulativeEnergy_Kwh)       AS max_cum
FROM dbo.fact_energy_consumption
WHERE DateKey IN (20230103, 20230104, 20230105,
                  20230216, 20230301, 20230401, 20230501)
GROUP BY DateKey
ORDER BY DateKey;

-- ---------- DELETE ----------------------------------------------------------
DELETE FROM dbo.fact_energy_consumption
WHERE DateKey >= 20230216;
PRINT CONCAT(N'fact_energy_consumption: ', @@ROWCOUNT, N' rows deleted (DateKey >= 20230216)');

-- Optional: also clear Jan 3/4/5 if the verification step below shows their
-- cumulative_reading was contaminated by the previous misclassified data.
-- Uncomment only if the verification cum values look out of range.
-- DELETE FROM dbo.fact_energy_consumption WHERE DateKey IN (20230103, 20230104, 20230105);
-- PRINT CONCAT(N'fact_energy_consumption: ', @@ROWCOUNT, N' rows deleted (Jan 3/4/5)');

-- ---------- AFTER -----------------------------------------------------------
PRINT '--- AFTER ---';
SELECT MAX(DateKey) AS new_max_datekey, COUNT(*) AS remaining_rows
FROM dbo.fact_energy_consumption;

-- Flip ROLLBACK -> COMMIT to apply for real.
ROLLBACK TRANSACTION;
-- COMMIT TRANSACTION;
