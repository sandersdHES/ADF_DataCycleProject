-- DataCycleDB — security objects deployment.
--
-- Run after deploy_schema.sql. Idempotent — safe to re-run.
--
-- SECRETS: no passwords are stored here.
-- User creation requires the sqlcmd variable SQL_USER_PASSWORD to be set:
--   sqlcmd ... -v SQL_USER_PASSWORD="<Admin-SQL-Password from Key Vault>"
-- The IF NOT EXISTS guard makes this a no-op on any environment where the user
-- already exists (e.g. production), so the variable is consumed only on a fresh build.

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

----------------------------------------------------------------------
-- Custom roles
----------------------------------------------------------------------

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'Director_Role' AND type = 'R')
  CREATE ROLE [Director_Role];
GO

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'Technician_Role' AND type = 'R')
  CREATE ROLE [Technician_Role];
GO

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'Teacher_Role' AND type = 'R')
  CREATE ROLE [Teacher_Role];
GO

----------------------------------------------------------------------
-- RLS mapping table
-- Populated manually: one row per Director-level login + allowed DivisionKey.
-- db_owner and Technician_Role members bypass this table (see fn_division_security).
----------------------------------------------------------------------

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'ref_user_division_access' AND schema_id = SCHEMA_ID('dbo'))
  CREATE TABLE dbo.ref_user_division_access (
    LoginName   NVARCHAR(100) NOT NULL,
    DivisionKey TINYINT       NOT NULL,
    [Role]      NVARCHAR(20)  NOT NULL CONSTRAINT DF_ref_user_division_access_Role DEFAULT (N'Director'),
    CONSTRAINT PK_ref_user_division_access PRIMARY KEY (LoginName, DivisionKey)
  );
GO

----------------------------------------------------------------------
-- RLS predicate function
----------------------------------------------------------------------

CREATE OR ALTER FUNCTION dbo.fn_division_security(@DivisionKey AS TINYINT)
RETURNS TABLE
WITH SCHEMABINDING
AS RETURN
    SELECT 1 AS is_granted
    WHERE
        -- db_owner and Technicians see all rows
        IS_MEMBER('db_owner') = 1
        OR IS_MEMBER('Technician_Role') = 1
        -- Directors see only divisions they are mapped to in ref_user_division_access
        OR EXISTS (
            SELECT 1 FROM dbo.ref_user_division_access uda
            WHERE uda.LoginName = USER_NAME()
              AND uda.DivisionKey = @DivisionKey
        );
GO

----------------------------------------------------------------------
-- RLS security policy on fact_room_booking
----------------------------------------------------------------------

IF NOT EXISTS (SELECT 1 FROM sys.security_policies WHERE name = N'BookingDivisionFilter')
  CREATE SECURITY POLICY [BookingDivisionFilter]
    ADD FILTER PREDICATE [dbo].[fn_division_security]([DivisionKey])
    ON [dbo].[fact_room_booking]
  WITH (STATE = ON);
GO

----------------------------------------------------------------------
-- SQL contained database user
-- Password from Key Vault secret 'Admin-SQL-Password', passed via -v flag.
-- Guarded by IF NOT EXISTS — no-op when the user already exists.
----------------------------------------------------------------------

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'dev.admin.sql' AND type = 'S')
  CREATE USER [dev.admin.sql]
    WITH PASSWORD   = N'$(SQL_USER_PASSWORD)',
         DEFAULT_SCHEMA = [dbo];
GO

----------------------------------------------------------------------
-- Role membership
----------------------------------------------------------------------

IF NOT EXISTS (
  SELECT 1
  FROM   sys.database_role_members rm
  JOIN   sys.database_principals   r ON r.principal_id = rm.role_principal_id
  JOIN   sys.database_principals   m ON m.principal_id = rm.member_principal_id
  WHERE  r.name = N'Technician_Role' AND m.name = N'dev.admin.sql'
)
  ALTER ROLE [Technician_Role] ADD MEMBER [dev.admin.sql];
GO

----------------------------------------------------------------------
-- GRANT SELECT — Director_Role
-- Access: energy data, room bookings, management KPIs.
-- Row-level: fact_room_booking is filtered by fn_division_security.
-- (GRANTs are idempotent — re-running is safe)
----------------------------------------------------------------------

GRANT SELECT ON [dbo].[dim_date]                TO [Director_Role];
GRANT SELECT ON [dbo].[dim_time]                TO [Director_Role];
GRANT SELECT ON [dbo].[dim_inverter]            TO [Director_Role];
GRANT SELECT ON [dbo].[dim_inverter_status]     TO [Director_Role];
GRANT SELECT ON [dbo].[dim_room]                TO [Director_Role];
GRANT SELECT ON [dbo].[dim_division]            TO [Director_Role];
GRANT SELECT ON [dbo].[dim_weather_site]        TO [Director_Role];
GRANT SELECT ON [dbo].[dim_measurement_type]    TO [Director_Role];
GRANT SELECT ON [dbo].[dim_prediction_model]    TO [Director_Role];
GRANT SELECT ON [dbo].[ref_electricity_tariff]  TO [Director_Role];
GRANT SELECT ON [dbo].[fact_solar_inverter]     TO [Director_Role];
GRANT SELECT ON [dbo].[fact_solar_production]   TO [Director_Role];
GRANT SELECT ON [dbo].[fact_energy_consumption] TO [Director_Role];
GRANT SELECT ON [dbo].[fact_environment]        TO [Director_Role];
GRANT SELECT ON [dbo].[fact_weather_forecast]   TO [Director_Role];
GRANT SELECT ON [dbo].[fact_room_booking]       TO [Director_Role];
GRANT SELECT ON [dbo].[vw_daily_energy_balance] TO [Director_Role];
GRANT SELECT ON [dbo].[vw_building_occupation]  TO [Director_Role];
GRANT SELECT ON [dbo].[vw_kpi_dashboard_home]   TO [Director_Role];
GO

----------------------------------------------------------------------
-- GRANT SELECT — Technician_Role
-- Access: solar, weather, prediction data. No room bookings (GDPR).
----------------------------------------------------------------------

GRANT SELECT ON [dbo].[dim_date]                     TO [Technician_Role];
GRANT SELECT ON [dbo].[dim_time]                     TO [Technician_Role];
GRANT SELECT ON [dbo].[dim_inverter]                 TO [Technician_Role];
GRANT SELECT ON [dbo].[dim_inverter_status]          TO [Technician_Role];
GRANT SELECT ON [dbo].[dim_measurement_type]         TO [Technician_Role];
GRANT SELECT ON [dbo].[dim_prediction_model]         TO [Technician_Role];
GRANT SELECT ON [dbo].[dim_weather_site]             TO [Technician_Role];
GRANT SELECT ON [dbo].[fact_solar_inverter]          TO [Technician_Role];
GRANT SELECT ON [dbo].[fact_solar_production]        TO [Technician_Role];
GRANT SELECT ON [dbo].[fact_energy_prediction]       TO [Technician_Role];
GRANT SELECT ON [dbo].[fact_environment]             TO [Technician_Role];
GRANT SELECT ON [dbo].[fact_weather_forecast]        TO [Technician_Role];
GRANT SELECT ON [dbo].[vw_inverter_status_breakdown] TO [Technician_Role];
GRANT SELECT ON [dbo].[vw_inverter_performance]      TO [Technician_Role];
GRANT SELECT ON [dbo].[vw_prediction_accuracy]       TO [Technician_Role];
GRANT SELECT ON [dbo].[vw_weather_vs_production]     TO [Technician_Role];
GO

----------------------------------------------------------------------
-- GRANT SELECT — Teacher_Role
-- Access: reference data, energy/sustainability facts, room bookings,
-- and the high-level dashboard views.
-- Row-level: fact_room_booking is filtered by fn_division_security
-- (teachers must be mapped to one or more DivisionKeys in
-- ref_user_division_access — same mechanism used for directors).
-- Excludes: weather forecasts, prediction tables/views, inverter detail
-- views, electricity tariff. Keeps the role narrower than Director.
----------------------------------------------------------------------

GRANT SELECT ON [dbo].[dim_date]                TO [Teacher_Role];
GRANT SELECT ON [dbo].[dim_time]                TO [Teacher_Role];
GRANT SELECT ON [dbo].[dim_room]                TO [Teacher_Role];
GRANT SELECT ON [dbo].[dim_division]            TO [Teacher_Role];
GRANT SELECT ON [dbo].[dim_inverter]            TO [Teacher_Role];
GRANT SELECT ON [dbo].[dim_inverter_status]     TO [Teacher_Role];
GRANT SELECT ON [dbo].[fact_solar_production]   TO [Teacher_Role];
GRANT SELECT ON [dbo].[fact_energy_consumption] TO [Teacher_Role];
GRANT SELECT ON [dbo].[fact_environment]        TO [Teacher_Role];
GRANT SELECT ON [dbo].[fact_room_booking]       TO [Teacher_Role];
GRANT SELECT ON [dbo].[vw_daily_energy_balance] TO [Teacher_Role];
GRANT SELECT ON [dbo].[vw_building_occupation]  TO [Teacher_Role];
GRANT SELECT ON [dbo].[vw_kpi_dashboard_home]   TO [Teacher_Role];
GO
