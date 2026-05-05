-- =============================================================================
-- One-shot migration: dbo.fact_solar_inverter.DayEnergy_Kwh
--
-- Until silver_gold_facts.py was fixed, this column was being written with the
-- raw `daysum` value from the inverter CSVs, which is in watt-hours, not
-- kilowatt-hours. Existing rows are therefore 1000x too large. The notebook
-- now divides by 1000 at write time, so this script only has to correct rows
-- that were loaded before the fix.
--
-- Run order
-- ---------
--   1. Deploy the silver_gold_facts.py change so future loads write kWh.
--   2. Run this script ONCE to correct the rows already in the table.
--   3. Verify with the AFTER block (peak per-inverter daily energy should land
--      in the 0–60 kWh range, not 0–60,000).
--
-- The script uses a transaction with ROLLBACK by default so a dry run prints
-- the before/after extremes without persisting. Switch ROLLBACK to COMMIT to
-- apply.
--
-- It is NOT idempotent: running it twice would divide values by 1,000,000.
-- A guard checks `MAX(DayEnergy_Kwh) > 1000` (no single inverter realistically
-- produces more than 1,000 kWh in a day at 15-min granularity), so a second
-- accidental run will fail loudly instead of silently corrupting data.
-- =============================================================================

SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRANSACTION;

-- ---------- BEFORE ----------------------------------------------------------
PRINT '--- BEFORE ---';
SELECT
    COUNT(*)                  AS total_rows,
    MIN(DayEnergy_Kwh)        AS min_value,
    MAX(DayEnergy_Kwh)        AS max_value,
    AVG(DayEnergy_Kwh)        AS avg_value
FROM dbo.fact_solar_inverter
WHERE DayEnergy_Kwh IS NOT NULL;

-- ---------- GUARD -----------------------------------------------------------
-- If the table already looks like kWh (peak daily energy per inverter < 1000),
-- abort: the migration has likely already been applied.
DECLARE @max_value FLOAT = (SELECT MAX(DayEnergy_Kwh) FROM dbo.fact_solar_inverter);
IF @max_value IS NULL OR @max_value < 1000
BEGIN
    PRINT N'Aborting: MAX(DayEnergy_Kwh) is already below 1000 — values look like kWh, migration probably already applied.';
    ROLLBACK TRANSACTION;
    RETURN;
END

-- ---------- MIGRATE ---------------------------------------------------------
UPDATE dbo.fact_solar_inverter
SET    DayEnergy_Kwh = DayEnergy_Kwh / 1000.0
WHERE  DayEnergy_Kwh IS NOT NULL;
PRINT CONCAT(N'fact_solar_inverter: ', @@ROWCOUNT, N' rows scaled by 1/1000');

-- ---------- AFTER -----------------------------------------------------------
PRINT '--- AFTER ---';
SELECT
    COUNT(*)                  AS total_rows,
    MIN(DayEnergy_Kwh)        AS min_value,
    MAX(DayEnergy_Kwh)        AS max_value,
    AVG(DayEnergy_Kwh)        AS avg_value
FROM dbo.fact_solar_inverter
WHERE DayEnergy_Kwh IS NOT NULL;

-- Flip ROLLBACK -> COMMIT to apply for real.
ROLLBACK TRANSACTION;
-- COMMIT TRANSACTION;
