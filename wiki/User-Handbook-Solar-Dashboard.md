# User Handbook — Solar Inverter Dashboard

[[Home]] > User Handbook — Solar Inverter Dashboard

End-user guide for the **Solar Inverter Operations & Performance Dashboard** (Power BI `.pbix`).  
File: `dashboards/Dashboard-Solar Production.pbix`  
Target audience: Technicians, Directors.

---

## Connecting Power BI with your own login

Each user has a personal SQL login (e.g. `technician.demo`, `director.demo`). The dashboard is the same for everyone — what you see is automatically filtered by your role.

1. Open `dashboards/Dashboard-Solar Production.pbix` in Power BI Desktop.
2. Go to **Home → Transform data → Data source settings**.
3. Select `sqlserver-bellevue-grp3.database.windows.net / DevDB` → **Edit Permissions → Edit…**
4. Switch the credential type to **Database** and enter your personal login + password.
5. Click **OK**, close, and **Refresh** the report.

> If visuals show "permission denied" or empty data, confirm with your administrator that your login is mapped to the correct division in `ref_user_division_access`.

### Demo accounts

| Username | Role | Key Vault secret |
|---|---|---|
| `teacher.demo` | `Teacher_Role` | `Teacher-Demo-Password` |
| `director.demo` | `Director_Role` | `Director-Demo-Password` |
| `technician.demo` | `Technician_Role` | `Technician-Demo-Password` |

Passwords are stored in Azure Key Vault `DataCycleGroup3Keys` — not in this document. Retrieve with `az keyvault secret show` or ask the administrator. Rotate after first use.

---

## 1. Data Controls & Navigation

The left-hand panel contains the primary tools for customising the view:

- **Time Frame Selector** — a slider and calendar tool to adjust the observation period (Daily, Weekly, or Monthly views).
- **Inverter Unit Selector** — individual buttons for units `INV-01` through `INV-05`. Toggle a single unit for a focused diagnostic, or select all to view total farm output.

---

## 2. Production & Environmental Correlation

The primary chart tracks **Energy Production (kWh)** alongside **Ambient Temperature** over the selected period.

> **Operational Insight:** Under normal conditions, these two lines should follow a similar trajectory. A significant divergence — high temperatures with low energy output, for example — is a primary indicator that a technical inspection is needed.

The temperature data comes from the building's internal sensor (`fact_environment`). The production data is the 15-minute aggregate from all five Sungrow inverters (`fact_solar_production`).

---

## 3. Historical Production Rankings (Top Days)

The **Top Days** section highlights the highest-producing intervals within the selected timeframe.

Each bar is segmented by colour, one segment per inverter. If one colour segment appears disproportionately thin compared to others on a given peak day, that unit was underperforming during that period.

---

## 4. Operational Log & Incident Tracking

The bottom table is a granular record of system activity drawn from `fact_solar_inverter`.

| Entry Type | Colour | Meaning |
|---|---|---|
| Normal operation | Green / Grey | System operating within expected parameters |
| Critical failure | **Red** | `status_code = 14` recorded — requires immediate attention |

Each red entry shows the exact **Timestamp** and the specific **Inverter Name** associated with the fault.

Status code reference:

| Code | Label | Meaning |
|---|---|---|
| 0 | OK / Standby | Inverter is powered and healthy but not producing |
| 6 | Running | Actively converting solar energy to AC power |
| 14 | Error | Fault condition — investigate immediately |
| 99 | Unknown | Undocumented manufacturer code (sentinel value used as fallback) |

---

## 5. Efficiency KPIs — Traffic Light System

The bottom-right section compares actual AC power output against each inverter's rated capacity (`RatedPower_kWp`).

The **Performance Ratio** formula: `SUM(AcPower_W) / (RatedPower_kWp × 1000 × COUNT(*))` across the selected period.

| Colour | Threshold | Status |
|---|---|---|
| 🟢 Green | > 85% | Optimal — operating at or above target efficiency |
| 🔴 Red | < 75% | Inspection needed — investigate root cause |

> **Note on low ratios:** The ratio includes all readings in the period, including nights and standby days. INV-01 and INV-02 may show low ratios (< 10%) not because they are inefficient when running, but because they spent significant time in standby or fault state.

---

## Quick Diagnostic Procedure

When investigating a suspected fault:

1. **Scan the Incident Log** for red entries.
2. **Use the Inverter Selector** to isolate the unit reporting the fault.
3. **Cross-reference its performance** against the Temperature Trend — determines whether the issue is weather-related or a hardware failure.

---

## Role-based data visibility

| Role | What you see |
|---|---|
| **Technician** | Full solar, weather, and prediction data. No room bookings. |
| **Teacher** | Energy and sustainability facts, room bookings for assigned divisions. |
| **Director** | Same as Teacher — room bookings filtered to assigned divisions. |

See [[Security and User Management]] for provisioning details.

---

*For the underlying data pipeline, see [[Databricks Notebooks]]. For the Gold schema, see [[Data Warehouse Schema]].*
