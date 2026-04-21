-- DataCycleDB — idempotent schema deployment.
--
-- Runs on every deploy. Safe after bacpac import (all CREATEs are guarded).
-- Schema is derived from databricks/notebooks/{silver_gold_dimensions,silver_gold_facts,ml_load_predictions,sac_export_to_adls}.py.
--
-- Conventions:
--   * surrogate *Key columns are IDENTITY PKs
--   * DateKey is INT (yyyymmdd); TimeKey is SMALLINT (minutes since midnight)
--   * dim_date / dim_time are assumed to exist (populated separately); only minimal shells are created if missing
--   * Computed columns use the hard-coded 0.15 CHF/kWh tariff the notebooks reference

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

----------------------------------------------------------------------
-- dim_date / dim_time (minimal shells — the real populator lives elsewhere)
----------------------------------------------------------------------

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'dim_date' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
  CREATE TABLE dbo.dim_date (
    DateKey     INT         NOT NULL PRIMARY KEY,
    FullDate    DATE        NOT NULL,
    [Year]      SMALLINT    NOT NULL,
    [Month]     TINYINT     NOT NULL,
    MonthName   NVARCHAR(20) NOT NULL,
    [Day]       TINYINT     NOT NULL,
    DayOfWeek   TINYINT     NOT NULL,
    IsWeekend   BIT         NOT NULL
  );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'dim_time' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
  CREATE TABLE dbo.dim_time (
    TimeKey     SMALLINT NOT NULL PRIMARY KEY,
    [Hour]      TINYINT  NOT NULL,
    [Minute]    TINYINT  NOT NULL,
    TimeOfDay   NVARCHAR(20) NOT NULL
  );
END
GO

----------------------------------------------------------------------
-- Dimensions
----------------------------------------------------------------------

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'dim_inverter' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
  CREATE TABLE dbo.dim_inverter (
    InverterKey     INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    InverterID      INT               NOT NULL UNIQUE,
    InverterName    NVARCHAR(255)     NOT NULL,
    RatedPower_kWp  DECIMAL(18,4)     NOT NULL,
    StringCount     INT               NOT NULL,
    RoofSection     NVARCHAR(255)     NULL,
    InstallDate     DATE              NULL,
    IsActive        BIT               NOT NULL
  );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'dim_inverter_status' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
  CREATE TABLE dbo.dim_inverter_status (
    StatusKey          TINYINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    StatusCode         INT           NOT NULL UNIQUE,
    StatusLabel        NVARCHAR(255) NOT NULL,
    StatusCategory     NVARCHAR(255) NOT NULL,
    IsFailure          BIT           NOT NULL,
    RequiresMaintenance BIT          NOT NULL
  );
END
GO

-- Sentinel row used by silver_gold_facts.py when status lookup fails
IF NOT EXISTS (SELECT 1 FROM dbo.dim_inverter_status WHERE StatusCode = 99)
BEGIN
  SET IDENTITY_INSERT dbo.dim_inverter_status ON;
  INSERT INTO dbo.dim_inverter_status (StatusKey, StatusCode, StatusLabel, StatusCategory, IsFailure, RequiresMaintenance)
  VALUES (99, 99, N'Unknown', N'Unknown', 0, 0);
  SET IDENTITY_INSERT dbo.dim_inverter_status OFF;
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'dim_weather_site' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
  CREATE TABLE dbo.dim_weather_site (
    SiteKey         INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    SiteName        NVARCHAR(255) NOT NULL UNIQUE,
    SiteDescription NVARCHAR(255) NULL,
    IsSynthetic     BIT           NOT NULL,
    Latitude        FLOAT         NULL,
    Longitude       FLOAT         NULL,
    AltitudeM       INT           NULL,
    Country         NVARCHAR(10)  NOT NULL CONSTRAINT DF_dim_weather_site_Country DEFAULT (N'CH')
  );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'dim_measurement_type' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
  CREATE TABLE dbo.dim_measurement_type (
    MeasurementKey      INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    MeasurementCode     NVARCHAR(64)  NOT NULL UNIQUE,
    MeasurementName     NVARCHAR(255) NOT NULL,
    Category            NVARCHAR(64)  NOT NULL,
    Unit                NVARCHAR(32)  NOT NULL,
    Description         NVARCHAR(500) NULL,
    IsProductionDriver  BIT           NOT NULL
  );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'dim_division' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
  CREATE TABLE dbo.dim_division (
    DivisionKey   INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    DivisionCode  NVARCHAR(64)  NOT NULL,
    DivisionName  NVARCHAR(255) NOT NULL UNIQUE,
    SchoolName    NVARCHAR(255) NOT NULL,
    IsActive      BIT           NOT NULL
  );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'dim_room' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
  CREATE TABLE dbo.dim_room (
    RoomKey         INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    RoomCode        NVARCHAR(64)  NOT NULL UNIQUE,
    RoomFullName    NVARCHAR(255) NOT NULL,
    Campus          NVARCHAR(128) NOT NULL,
    Building        NVARCHAR(128) NOT NULL,
    Wing            NVARCHAR(64)  NULL,
    [Floor]         INT           NULL,
    RoomNumber      NVARCHAR(32)  NULL,
    RoomType        NVARCHAR(64)  NOT NULL,
    NominalCapacity INT           NULL,
    IsActive        BIT           NOT NULL
  );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'dim_prediction_model' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
  CREATE TABLE dbo.dim_prediction_model (
    ModelKey          TINYINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    ModelCode         NVARCHAR(64)  NOT NULL UNIQUE,
    ModelName         NVARCHAR(255) NOT NULL,
    ModelType         NVARCHAR(64)  NOT NULL,
    TargetVariable    NVARCHAR(64)  NOT NULL,
    Features          NVARCHAR(MAX) NOT NULL,
    TrainingStartDate DATE          NULL,
    TrainingEndDate   DATE          NULL,
    IsActive          BIT           NOT NULL,
    Notes             NVARCHAR(MAX) NULL
  );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'ref_electricity_tariff' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
  CREATE TABLE dbo.ref_electricity_tariff (
    TariffKey        INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    TariffName       NVARCHAR(128)  NOT NULL,
    PricePerKwh_CHF  DECIMAL(18,4)  NOT NULL,
    EffectiveFrom    DATE           NOT NULL,
    EffectiveTo      DATE           NULL,
    Notes            NVARCHAR(500)  NULL
  );
END
GO

----------------------------------------------------------------------
-- Fact tables
----------------------------------------------------------------------

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'fact_solar_inverter' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
  CREATE TABLE dbo.fact_solar_inverter (
    DateKey       INT      NOT NULL,
    TimeKey       SMALLINT NOT NULL,
    InverterKey   INT      NOT NULL,
    StatusKey     TINYINT  NOT NULL,
    AcPower_W     FLOAT    NULL,
    DayEnergy_Kwh FLOAT    NULL,
    DcPower1_W    FLOAT    NULL,
    DcPower2_W    FLOAT    NULL,
    DcVoltage1_V  FLOAT    NULL,
    DcVoltage2_V  FLOAT    NULL,
    IsFailure     BIT      NULL,
    [Year]        SMALLINT NOT NULL,
    [Month]       TINYINT  NOT NULL,
    CONSTRAINT PK_fact_solar_inverter PRIMARY KEY (DateKey, TimeKey, InverterKey),
    CONSTRAINT FK_fact_solar_inverter_date     FOREIGN KEY (DateKey)     REFERENCES dbo.dim_date(DateKey),
    CONSTRAINT FK_fact_solar_inverter_time     FOREIGN KEY (TimeKey)     REFERENCES dbo.dim_time(TimeKey),
    CONSTRAINT FK_fact_solar_inverter_inverter FOREIGN KEY (InverterKey) REFERENCES dbo.dim_inverter(InverterKey),
    CONSTRAINT FK_fact_solar_inverter_status   FOREIGN KEY (StatusKey)   REFERENCES dbo.dim_inverter_status(StatusKey)
  );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'fact_solar_production' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
  CREATE TABLE dbo.fact_solar_production (
    DateKey              INT      NOT NULL,
    TimeKey              SMALLINT NOT NULL,
    CumulativeEnergy_Kwh FLOAT    NULL,
    DeltaEnergy_Kwh      FLOAT    NULL,
    [Year]               SMALLINT NOT NULL,
    [Month]              TINYINT  NOT NULL,
    RetailValue_CHF AS CAST(DeltaEnergy_Kwh * 0.15 AS DECIMAL(18,4)) PERSISTED,
    CONSTRAINT PK_fact_solar_production PRIMARY KEY (DateKey, TimeKey),
    CONSTRAINT FK_fact_solar_production_date FOREIGN KEY (DateKey) REFERENCES dbo.dim_date(DateKey),
    CONSTRAINT FK_fact_solar_production_time FOREIGN KEY (TimeKey) REFERENCES dbo.dim_time(TimeKey)
  );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'fact_energy_consumption' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
  CREATE TABLE dbo.fact_energy_consumption (
    DateKey              INT      NOT NULL,
    TimeKey              SMALLINT NOT NULL,
    CumulativeEnergy_Kwh FLOAT    NULL,
    DeltaEnergy_Kwh      FLOAT    NULL,
    [Year]               SMALLINT NOT NULL,
    [Month]              TINYINT  NOT NULL,
    CostCHF AS CAST(DeltaEnergy_Kwh * 0.15 AS DECIMAL(18,4)) PERSISTED,
    CONSTRAINT PK_fact_energy_consumption PRIMARY KEY (DateKey, TimeKey),
    CONSTRAINT FK_fact_energy_consumption_date FOREIGN KEY (DateKey) REFERENCES dbo.dim_date(DateKey),
    CONSTRAINT FK_fact_energy_consumption_time FOREIGN KEY (TimeKey) REFERENCES dbo.dim_time(TimeKey)
  );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'fact_environment' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
  CREATE TABLE dbo.fact_environment (
    DateKey              INT      NOT NULL,
    TimeKey              SMALLINT NOT NULL,
    Temperature_C        FLOAT    NULL,
    TempVariation_C      FLOAT    NULL,
    Humidity_Pct         FLOAT    NULL,
    HumidityVariation_Pct FLOAT   NULL,
    [Year]               SMALLINT NOT NULL,
    [Month]              TINYINT  NOT NULL,
    CONSTRAINT PK_fact_environment PRIMARY KEY (DateKey, TimeKey),
    CONSTRAINT FK_fact_environment_date FOREIGN KEY (DateKey) REFERENCES dbo.dim_date(DateKey),
    CONSTRAINT FK_fact_environment_time FOREIGN KEY (TimeKey) REFERENCES dbo.dim_time(TimeKey)
  );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'fact_weather_forecast' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
  CREATE TABLE dbo.fact_weather_forecast (
    DateKey           INT      NOT NULL,
    TimeKey           SMALLINT NOT NULL,
    SiteKey           INT      NOT NULL,
    MeasurementKey    INT      NOT NULL,
    PredictionHorizon SMALLINT NOT NULL,
    ForecastValue     FLOAT    NULL,
    [Year]            SMALLINT NOT NULL,
    [Month]           TINYINT  NOT NULL,
    CONSTRAINT PK_fact_weather_forecast PRIMARY KEY (DateKey, TimeKey, SiteKey, MeasurementKey, PredictionHorizon),
    CONSTRAINT FK_fact_weather_forecast_date        FOREIGN KEY (DateKey)        REFERENCES dbo.dim_date(DateKey),
    CONSTRAINT FK_fact_weather_forecast_time        FOREIGN KEY (TimeKey)        REFERENCES dbo.dim_time(TimeKey),
    CONSTRAINT FK_fact_weather_forecast_site        FOREIGN KEY (SiteKey)        REFERENCES dbo.dim_weather_site(SiteKey),
    CONSTRAINT FK_fact_weather_forecast_measurement FOREIGN KEY (MeasurementKey) REFERENCES dbo.dim_measurement_type(MeasurementKey)
  );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'fact_room_booking' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
  CREATE TABLE dbo.fact_room_booking (
    BookingKey        BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    DateKey           INT           NOT NULL,
    StartTimeKey      SMALLINT      NOT NULL,
    EndTimeKey        SMALLINT      NOT NULL,
    DurationMinutes   SMALLINT      NOT NULL,
    RoomKey           INT           NOT NULL,
    DivisionKey       INT           NOT NULL,
    ReservationNo     INT           NULL,
    BookingType       NVARCHAR(64)  NULL,
    Codes             NVARCHAR(255) NULL,
    ProfessorMasked   NVARCHAR(128) NULL,
    UserMasked        NVARCHAR(128) NULL,
    ActivityType      NVARCHAR(64)  NULL,
    Class             NVARCHAR(64)  NULL,
    CostCenter        NVARCHAR(64)  NULL,
    Periodicity       NVARCHAR(64)  NULL,
    RecurrenceStart   DATE          NULL,
    RecurrenceEnd     DATE          NULL,
    Remarque          NVARCHAR(MAX) NULL,
    IsRecurring AS CAST(CASE WHEN RecurrenceStart IS NOT NULL OR RecurrenceEnd IS NOT NULL THEN 1 ELSE 0 END AS BIT) PERSISTED,
    CONSTRAINT FK_fact_room_booking_date  FOREIGN KEY (DateKey)      REFERENCES dbo.dim_date(DateKey),
    CONSTRAINT FK_fact_room_booking_start FOREIGN KEY (StartTimeKey) REFERENCES dbo.dim_time(TimeKey),
    CONSTRAINT FK_fact_room_booking_end   FOREIGN KEY (EndTimeKey)   REFERENCES dbo.dim_time(TimeKey),
    CONSTRAINT FK_fact_room_booking_room  FOREIGN KEY (RoomKey)      REFERENCES dbo.dim_room(RoomKey),
    CONSTRAINT FK_fact_room_booking_div   FOREIGN KEY (DivisionKey)  REFERENCES dbo.dim_division(DivisionKey)
  );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'fact_energy_prediction' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
  CREATE TABLE dbo.fact_energy_prediction (
    DateKey                  INT      NOT NULL,
    TimeKey                  SMALLINT NOT NULL,
    ModelKey                 TINYINT  NOT NULL,
    PredictionRunDateKey     INT      NOT NULL,
    PredictedProduction_Kwh  FLOAT    NULL,
    PredictedConsumption_Kwh FLOAT    NULL,
    ActualProduction_Kwh     FLOAT    NULL,
    ActualConsumption_Kwh    FLOAT    NULL,
    CONSTRAINT PK_fact_energy_prediction PRIMARY KEY (DateKey, TimeKey, ModelKey, PredictionRunDateKey),
    CONSTRAINT FK_fact_energy_prediction_date     FOREIGN KEY (DateKey)              REFERENCES dbo.dim_date(DateKey),
    CONSTRAINT FK_fact_energy_prediction_time     FOREIGN KEY (TimeKey)              REFERENCES dbo.dim_time(TimeKey),
    CONSTRAINT FK_fact_energy_prediction_model    FOREIGN KEY (ModelKey)             REFERENCES dbo.dim_prediction_model(ModelKey),
    CONSTRAINT FK_fact_energy_prediction_run_date FOREIGN KEY (PredictionRunDateKey) REFERENCES dbo.dim_date(DateKey)
  );
END
GO

----------------------------------------------------------------------
-- Stored procedure: backfill actuals into fact_energy_prediction
----------------------------------------------------------------------

CREATE OR ALTER PROCEDURE dbo.sp_backfill_prediction_actuals
  @TargetDate DATE
AS
BEGIN
  SET NOCOUNT ON;

  DECLARE @TargetDateKey INT = CONVERT(INT, CONVERT(CHAR(8), @TargetDate, 112));

  UPDATE p
    SET p.ActualProduction_Kwh = sp.DeltaEnergy_Kwh
  FROM dbo.fact_energy_prediction p
  INNER JOIN dbo.fact_solar_production sp
    ON sp.DateKey = p.DateKey
   AND sp.TimeKey = p.TimeKey
  WHERE p.DateKey = @TargetDateKey;

  UPDATE p
    SET p.ActualConsumption_Kwh = ec.DeltaEnergy_Kwh
  FROM dbo.fact_energy_prediction p
  INNER JOIN dbo.fact_energy_consumption ec
    ON ec.DateKey = p.DateKey
   AND ec.TimeKey = p.TimeKey
  WHERE p.DateKey = @TargetDateKey;
END
GO

----------------------------------------------------------------------
-- Views consumed by SAC export (sac_export_to_adls.py)
----------------------------------------------------------------------

CREATE OR ALTER VIEW dbo.vw_inverter_status_breakdown
AS
SELECT
  d.FullDate,
  d.[Year],
  d.[Month],
  d.MonthName,
  i.InverterID,
  i.InverterName,
  s.StatusCode,
  s.StatusLabel,
  s.StatusCategory,
  s.IsFailure,
  COUNT_BIG(*)                                                  AS ReadingCount,
  CAST(100.0 * COUNT_BIG(*) / NULLIF(
    SUM(COUNT_BIG(*)) OVER (PARTITION BY d.FullDate, i.InverterID), 0)
    AS DECIMAL(6,2))                                            AS PctOfDayReadings
FROM dbo.fact_solar_inverter f
JOIN dbo.dim_date            d ON d.DateKey    = f.DateKey
JOIN dbo.dim_inverter        i ON i.InverterKey = f.InverterKey
JOIN dbo.dim_inverter_status s ON s.StatusKey   = f.StatusKey
GROUP BY d.FullDate, d.[Year], d.[Month], d.MonthName,
         i.InverterID, i.InverterName,
         s.StatusCode, s.StatusLabel, s.StatusCategory, s.IsFailure;
GO

CREATE OR ALTER VIEW dbo.vw_inverter_performance
AS
SELECT
  i.InverterID,
  d.FullDate,
  CAST(SUM(CASE WHEN f.AcPower_W IS NOT NULL THEN f.AcPower_W ELSE 0 END)
       / NULLIF(i.RatedPower_kWp * 1000.0 * COUNT_BIG(*), 0)
       AS DECIMAL(10,6))                                        AS PerformanceRatio,
  MAX(CAST(f.IsFailure AS INT))                                 AS HadFailure
FROM dbo.fact_solar_inverter f
JOIN dbo.dim_date     d ON d.DateKey     = f.DateKey
JOIN dbo.dim_inverter i ON i.InverterKey = f.InverterKey
GROUP BY i.InverterID, i.RatedPower_kWp, d.FullDate;
GO

CREATE OR ALTER VIEW dbo.vw_prediction_accuracy
AS
SELECT
  d.FullDate,
  m.ModelCode,
  m.ModelName,
  p.PredictionRunDateKey,
  SUM(p.PredictedProduction_Kwh)                                          AS PredictedProduction_Kwh,
  SUM(p.ActualProduction_Kwh)                                             AS ActualProduction_Kwh,
  SUM(p.PredictedConsumption_Kwh)                                         AS PredictedConsumption_Kwh,
  SUM(p.ActualConsumption_Kwh)                                            AS ActualConsumption_Kwh,
  CAST(SUM(ABS(p.PredictedProduction_Kwh - p.ActualProduction_Kwh))
       / NULLIF(SUM(p.ActualProduction_Kwh), 0) AS DECIMAL(10,6))         AS ProductionMape,
  CAST(SUM(ABS(p.PredictedConsumption_Kwh - p.ActualConsumption_Kwh))
       / NULLIF(SUM(p.ActualConsumption_Kwh), 0) AS DECIMAL(10,6))        AS ConsumptionMape
FROM dbo.fact_energy_prediction p
JOIN dbo.dim_date             d ON d.DateKey  = p.DateKey
JOIN dbo.dim_prediction_model m ON m.ModelKey = p.ModelKey
GROUP BY d.FullDate, m.ModelCode, m.ModelName, p.PredictionRunDateKey;
GO
