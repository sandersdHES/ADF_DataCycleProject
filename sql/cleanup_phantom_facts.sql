-- =============================================================================
-- One-shot cleanup for the phantom delta values in
--   dbo.fact_solar_production    (67% of rows had DeltaEnergy_Kwh = 0)
--   dbo.fact_energy_consumption  (6+ rows at 00:15 with deltas of 1k-22k kWh)
--
-- Both bugs were fixed in databricks/notebooks/silver_transformation.py
-- (Window.partitionBy + dropDuplicates by timestamp; cumulative-meter delta
-- recomputation for solar PV). The Gold loader silver_gold_facts.py is
-- incremental on `DateKey > MAX(DateKey)`, so existing corrupted rows are
-- never overwritten in place. This script wipes both fact tables; the next
-- run of silver_gold_facts will repopulate them from the corrected silver
-- layer, with no manual watermark bookkeeping needed.
--
-- Run order
-- ---------
--   1. Re-run databricks/notebooks/silver_transformation.py     (updates silver)
--   2. Run this script                                          (clears gold)
--   3. Re-run databricks/notebooks/silver_gold_facts.py         (reloads gold)
--   4. Re-deploy sql/deploy_schema.sql                          (refreshes views)
--
-- The script is wrapped in a transaction with ROLLBACK at the end so a dry
-- run prints the before/after counts without persisting. Switch ROLLBACK to
-- COMMIT to apply.
-- =============================================================================

SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRANSACTION;

-- ---------- BEFORE ----------------------------------------------------------
PRINT '--- BEFORE ---';
SELECT
    'fact_solar_production'                       AS table_name,
    COUNT(*)                                      AS row_count,
    SUM(CASE WHEN DeltaEnergy_Kwh = 0 THEN 1 END) AS zero_delta_rows,
    MAX(DateKey)                                  AS max_datekey
FROM dbo.fact_solar_production
UNION ALL
SELECT
    'fact_energy_consumption',
    COUNT(*),
    SUM(CASE WHEN DeltaEnergy_Kwh > 500 THEN 1 END), -- impossible for a 15-min slot
    MAX(DateKey)
FROM dbo.fact_energy_consumption;

-- ---------- DELETE ----------------------------------------------------------
-- DELETE (not TRUNCATE) so we don't trip over potential FK references and so
-- the operation is fully transactional.
DELETE FROM dbo.fact_solar_production;
PRINT CONCAT(N'fact_solar_production    : ', @@ROWCOUNT, N' rows deleted');

DELETE FROM dbo.fact_energy_consumption;
PRINT CONCAT(N'fact_energy_consumption  : ', @@ROWCOUNT, N' rows deleted');

-- Reseed the IDENTITY columns so the reload starts from 1 again. Safe even
-- if the table is now empty (DBCC CHECKIDENT with RESEED, 0 sets next = 1).
DBCC CHECKIDENT ('dbo.fact_solar_production',   RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('dbo.fact_energy_consumption', RESEED, 0) WITH NO_INFOMSGS;

-- ---------- AFTER -----------------------------------------------------------
PRINT '--- AFTER ---';
SELECT 'fact_solar_production'   AS table_name, COUNT(*) AS row_count FROM dbo.fact_solar_production
UNION ALL
SELECT 'fact_energy_consumption',                COUNT(*)             FROM dbo.fact_energy_consumption;

-- Flip ROLLBACK -> COMMIT to apply for real.
ROLLBACK TRANSACTION;
-- COMMIT TRANSACTION;
