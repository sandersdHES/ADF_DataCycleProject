-- DataCycleDB — provision a contained database user and assign role.
--
-- Idempotent: safe to re-run. CREATE USER, ALTER ROLE, and the mapping
-- INSERT are each guarded.
--
-- Required sqlcmd variables (-v):
--   USER_NAME     login name, e.g. "teacher.jdupont"
--   USER_PASSWORD initial password (the user can change it later via ALTER USER)
--   USER_ROLE     one of: Teacher_Role | Director_Role | Technician_Role
--   DIVISION_KEY  integer; the dim_division.DivisionKey to scope this user to
--                 (use 0 for Technician_Role — the script skips the mapping insert)
--
-- Example:
--   sqlcmd -S sqlserver-bellevue-grp3.database.windows.net -d DevDB -U <admin> -P <pwd> \
--     -i sql/provision_user.sql \
--     -v USER_NAME="teacher.jdupont" \
--        USER_PASSWORD="<initial-password>" \
--        USER_ROLE="Teacher_Role" \
--        DIVISION_KEY="2"

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

----------------------------------------------------------------------
-- Validate role name up front
----------------------------------------------------------------------

IF N'$(USER_ROLE)' NOT IN (N'Teacher_Role', N'Director_Role', N'Technician_Role')
BEGIN
  RAISERROR(N'USER_ROLE must be Teacher_Role, Director_Role, or Technician_Role (got "%s").', 16, 1, N'$(USER_ROLE)');
  SET NOEXEC ON;
END
GO

----------------------------------------------------------------------
-- Create the contained user (no-op if it already exists)
----------------------------------------------------------------------

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'$(USER_NAME)' AND type = 'S')
BEGIN
  DECLARE @sql NVARCHAR(MAX) = N'CREATE USER [$(USER_NAME)] WITH PASSWORD = N''$(USER_PASSWORD)'', DEFAULT_SCHEMA = [dbo];';
  EXEC sp_executesql @sql;
END
GO

----------------------------------------------------------------------
-- Add user to the requested role (no-op if already a member)
----------------------------------------------------------------------

IF NOT EXISTS (
  SELECT 1
  FROM   sys.database_role_members rm
  JOIN   sys.database_principals   r ON r.principal_id = rm.role_principal_id
  JOIN   sys.database_principals   m ON m.principal_id = rm.member_principal_id
  WHERE  r.name = N'$(USER_ROLE)' AND m.name = N'$(USER_NAME)'
)
BEGIN
  DECLARE @sql NVARCHAR(MAX) = N'ALTER ROLE [$(USER_ROLE)] ADD MEMBER [$(USER_NAME)];';
  EXEC sp_executesql @sql;
END
GO

----------------------------------------------------------------------
-- Map the user to the requested DivisionKey for RLS
-- (skipped for Technician_Role — technicians bypass division filtering)
----------------------------------------------------------------------

IF N'$(USER_ROLE)' <> N'Technician_Role'
   AND NOT EXISTS (
     SELECT 1 FROM dbo.ref_user_division_access
     WHERE LoginName = N'$(USER_NAME)' AND DivisionKey = $(DIVISION_KEY)
   )
BEGIN
  INSERT INTO dbo.ref_user_division_access (LoginName, DivisionKey, [Role])
  VALUES (N'$(USER_NAME)', $(DIVISION_KEY),
          CASE WHEN N'$(USER_ROLE)' = N'Teacher_Role'  THEN N'Teacher'
               WHEN N'$(USER_ROLE)' = N'Director_Role' THEN N'Director'
          END);
END
GO

PRINT N'Provisioning complete: $(USER_NAME) → $(USER_ROLE) (DivisionKey=$(DIVISION_KEY))';
GO
