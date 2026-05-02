# Onboarding

[[Home]] > Onboarding

Step-by-step guide for anyone joining the project for the first time — whether as a dashboard user or a developer.

---

## For dashboard users (Teachers, Directors, Technicians)

1. **Request a SQL login** from a project admin — provide your name, role (`Teacher_Role`, `Director_Role`, or `Technician_Role`), and school division key.
2. **Download Power BI Desktop** (free) — [powerbi.microsoft.com/desktop](https://powerbi.microsoft.com/desktop).
3. **Open the correct report file** from [`dashboards/`](https://github.com/sandersdHES/ADF_DataCycleProject/tree/main/dashboards):
   - `Dashboard-Solar Production.pbix` — solar inverter operations (Technicians)
   - `Energy & Financial Overview.pbit` — energy balance, costs, KPIs (Directors, Teachers)
   - `PowerBy_RoomOccupacy.pbit` — room bookings and occupancy (Directors, Teachers)
4. **Enter your credentials** — Home → Transform data → Data source settings → select `sqlserver-bellevue-grp3.database.windows.net / DevDB` → Edit Permissions → switch credential type to **Database** → enter your SQL login and password.
5. **Refresh** — your role automatically filters what you can see (see [[Security and User Management]]).
6. For the **SAC dashboard** (solar fault analysis), follow the daily refresh procedure in [[User Handbook — SAC Dashboard]].

> **What you can see depends on your role:**
> - **Technicians** see solar, weather, and prediction data — no room bookings (GDPR).
> - **Teachers / Directors** see energy data and room bookings for the divisions they are mapped to.

---

## For new developers

### 1. Clone the repo

```bash
git clone https://github.com/sandersdHES/ADF_DataCycleProject.git
cd ADF_DataCycleProject
```

### 2. Request Azure access

Contact the project owner for:

| Resource | Minimum role |
|---|---|
| Azure subscription | Reader (or scoped Contributor on the resource group) |
| Azure Databricks workspace | Workspace user — add your email in the admin console |
| Azure Key Vault `DataCycleGroup3Keys` | `Key Vault Secrets User` |
| Azure SQL `DevDB` | Run `sql/provision_user.sql` with `Technician_Role` (see below) |

### 3. Import notebooks into Databricks Repos

Databricks → **Repos → Add repo** → paste `https://github.com/sandersdHES/ADF_DataCycleProject.git`.

Notebooks land at `/Repos/<your-username>/ADF_DataCycleProject/databricks/notebooks/`.

> ⚠️ ADF pipeline activities reference **absolute Repo paths**. To run pipelines end-to-end, either re-point the `AzureDatabricks` activities in ADF Studio to your path, or clone under the same shared service-account path already configured.

### 4. Set up local tools

| Tool | Purpose |
|---|---|
| Azure CLI (`az login`) | Key Vault secret reads, RBAC operations |
| `sqlcmd` | Manual schema deploys, user provisioning |
| KNIME Analytics Platform | Open and edit `.knwf` workflows in `knime/` |

### 5. Provision your own SQL login

```bash
sqlcmd -S sqlserver-bellevue-grp3.database.windows.net -d DevDB \
       -U dev.admin.sql -P <admin-password> \
       -i sql/provision_user.sql \
       -v USER_NAME="yourname.dev" \
          USER_PASSWORD="<initial-password>" \
          USER_ROLE="Technician_Role" \
          DIVISION_KEY="0"
```

See [[Security and User Management]] for the full provisioning reference.

### 6. Understand the daily cycle

Read [[Architecture Overview]] and [[ADF Pipelines]] to understand what runs when and why. The short version:

- **07:15** — `PL_Ingest_Bronze` copies raw files from on-prem, runs Silver/Gold ETL, exports to SAC.
- **09:30** — `PL_Upload_Pred_Gold` calls KNIME REST endpoints and loads ML predictions into Gold.

### 7. Make a change

| Change type | How |
|---|---|
| **ADF pipeline** | Edit JSON under `adf/`, open a PR → `validate.yml` runs → merge to `main` → `deploy-adf.yml` deploys automatically |
| **Databricks notebook** | Edit `.py` files under `databricks/notebooks/`, commit and push — Databricks Repos syncs on next run |
| **SQL schema** | Edit `sql/deploy_schema.sql` or `sql/deploy_security.sql`, apply manually with `sqlcmd` (see [[Infrastructure and IaC]]) |

---

## Pending tasks (from `docs/TODO.md`)

- [ ] Transfer Azure subscription billing ownership to the company account
- [ ] Delete `adf/publish_config.json` — the `adf_publish` branch is no longer used
- [ ] Wire `PL_Bronze_MeteoFuture` into `PL_Ingest_Bronze` so future forecasts flow automatically (currently orphaned)

---

*For a deeper dive into architecture and pipelines, see [[Architecture Overview]] and [[ADF Pipelines]].*
