# Security & User Management

[[Home]] > Security & User Management

How multi-user access works in `DevDB` without Active Directory, and how to add a new person.

This is a lab environment — there is no AD/Entra integration. Identity is modeled entirely with **SQL contained users** + **database roles** + **Row-Level Security (RLS)**. Each person logs into Power BI with their own SQL credentials; the database filters what they can see.

Source files:
| File | Purpose |
|---|---|
| [`sql/deploy_security.sql`](https://github.com/sandersdHES/ADF_DataCycleProject/blob/main/sql/deploy_security.sql) | Roles, RLS predicate function, security policy, base contained user |
| [`sql/provision_user.sql`](https://github.com/sandersdHES/ADF_DataCycleProject/blob/main/sql/provision_user.sql) | Idempotent script for adding a new user (creates user, assigns role, maps division) |

---

## Role catalog

| Role | Sees | Excludes | RLS |
|---|---|---|---|
| `Director_Role` | All dims, all facts, all energy / booking / KPI views | — | Filtered by division on `fact_room_booking` |
| `Teacher_Role` | Reference data, energy/sustainability facts (`fact_solar_production`, `fact_energy_consumption`, `fact_environment`), `fact_room_booking`, dashboard views (`vw_daily_energy_balance`, `vw_building_occupation`, `vw_kpi_dashboard_home`) | Weather forecasts, prediction tables/views, inverter detail views, electricity tariff | Filtered by division on `fact_room_booking` |
| `Technician_Role` | Solar / weather / prediction dims, facts, views | `fact_room_booking`, room/division dims, building/KPI views (GDPR) | Bypasses RLS |

`db_owner` membership bypasses both GRANTs and RLS.

---

## Row-Level Security on `fact_room_booking`

The security policy `BookingDivisionFilter` applies `fn_division_security([DivisionKey])` as a FILTER predicate on every SELECT from `fact_room_booking`.

```sql
-- fn_division_security returns 1 (visible) when…
IS_MEMBER('db_owner') = 1
OR IS_MEMBER('Technician_Role') = 1
OR EXISTS (
    SELECT 1 FROM dbo.ref_user_division_access uda
    WHERE uda.LoginName  = USER_NAME()
      AND uda.DivisionKey = @DivisionKey
);
```

| Caller | Rows visible |
|---|---|
| `db_owner` | All |
| `Technician_Role` member | All — but `Technician_Role` has no `GRANT SELECT` on `fact_room_booking`, so the table is effectively inaccessible to technicians (GDPR) |
| `Director_Role` member | Only `DivisionKey` values listed in `ref_user_division_access` for their login |
| `Teacher_Role` member | Only `DivisionKey` values listed in `ref_user_division_access` for their login |

Directors and Teachers use the **same** RLS path. The `Role` column on `ref_user_division_access` (`'Director'` / `'Teacher'`) is informational — it is not consulted by `fn_division_security`.

---

## Provisioning a new user

`sql/provision_user.sql` is idempotent. It creates the contained user, adds them to the requested role, and (for Teachers/Directors) inserts the division mapping. Re-running with the same inputs is a no-op.

### Required `sqlcmd` variables

| Variable | Description |
|---|---|
| `USER_NAME` | Login name (e.g. `teacher.jdupont`) |
| `USER_PASSWORD` | Initial password — the user can rotate it later |
| `USER_ROLE` | One of `Teacher_Role`, `Director_Role`, `Technician_Role` |
| `DIVISION_KEY` | Integer `dim_division.DivisionKey`. Pass `0` for `Technician_Role` (the script skips the mapping insert) |

### Example — provision a teacher for division 2

```sh
sqlcmd -S sqlserver-bellevue-grp3.database.windows.net -d DevDB \
       -U <admin> -P <pwd> \
       -i sql/provision_user.sql \
       -v USER_NAME="teacher.jdupont" \
          USER_PASSWORD="<initial-password>" \
          USER_ROLE="Teacher_Role" \
          DIVISION_KEY="2"
```

### Provision a director for multiple divisions

Run the script once per `DivisionKey`. Each run with the same `USER_NAME` re-uses the existing user and only adds the new mapping row.

### Provision a technician

```sh
sqlcmd ... -i sql/provision_user.sql \
   -v USER_NAME="tech.aroche" USER_PASSWORD="<...>" \
      USER_ROLE="Technician_Role" DIVISION_KEY="0"
```

The `DIVISION_KEY="0"` is required syntactically but ignored — technicians bypass RLS.

---

## Day-to-day operations

| Task | Command |
|---|---|
| Rotate password | `ALTER USER [teacher.jdupont] WITH PASSWORD = N'<new>';` |
| Revoke access | `DROP USER [teacher.jdupont];` then `DELETE FROM dbo.ref_user_division_access WHERE LoginName = N'teacher.jdupont';` |
| List role members | `EXEC sp_helprolemember 'Teacher_Role';` |
| Inspect a user's mappings | `SELECT * FROM dbo.ref_user_division_access WHERE LoginName = N'teacher.jdupont';` |
| Audit who can see which division | `SELECT [Role], LoginName, DivisionKey FROM dbo.ref_user_division_access ORDER BY DivisionKey, [Role];` |

---

## Connecting Power BI Desktop as a non-shared user

The `.pbix` / `.pbit` files in [`dashboards/`](https://github.com/sandersdHES/ADF_DataCycleProject/tree/main/dashboards) point at the same `DevDB` for everyone. Each user enters their **own** SQL credentials, and the database narrows the result set automatically:

1. Open the report in Power BI Desktop.
2. **Home → Transform data → Data source settings**.
3. Select `sqlserver-bellevue-grp3.database.windows.net / DevDB` → **Edit Permissions → Edit…**.
4. Set credential type to **Database**, enter your personal login + password.
5. **Refresh** the report.

Empty visuals or "permission denied" errors usually mean the login is missing from `ref_user_division_access`, or the role does not have `GRANT SELECT` on the underlying table.

---

## Demo accounts (one per role)

The following accounts exist for demonstrations and testing. **Passwords are not stored on this page** — they live in Key Vault `DataCycleGroup3Keys`, alongside `Admin-SQL-Password`. Retrieve them with `az keyvault secret show` or ask the administrator.

| Username | Role | Division | Key Vault secret |
|---|---|---|---|
| `teacher.demo` | `Teacher_Role` | 1 | `Teacher-Demo-Password` |
| `director.demo` | `Director_Role` | 1 | `Director-Demo-Password` |
| `technician.demo` | `Technician_Role` | — (bypasses RLS) | `Technician-Demo-Password` |

These are initial passwords. Rotate after first use:

```sql
ALTER USER [teacher.demo] WITH PASSWORD = N'<new>';
```

---

## Base contained user (CI / admin access)

`dev.admin.sql` is a member of `Technician_Role`. Password lives in Azure Key Vault as secret `Admin-SQL-Password` — never in git. See [[Secrets and Configuration]] for the full Key Vault inventory.

This account is used by:
- The CI deploy job to run `deploy_schema.sql` and `deploy_security.sql`.
- Admin-side runs of `provision_user.sql` to onboard new users.
- (Historically) by Power BI Desktop as a single shared login. New deployments should switch each user to their own contained account using this page.

---

*For the Gold schema this security model protects, see [[Data Warehouse Schema]]. For Key Vault and credential inventory, see [[Secrets and Configuration]].*
