# User Handbook: Solar Inverter Operations & Performance Dashboard

> Part of the [Solar Inverter Operations & Performance Dashboard](../README.md) project.  
> See also: [Data Privacy & GDPR Statement](DATA_PRIVACY_GDPR.md) · [Technical Guide](TECHNICAL_GUIDE.md) · [Wiki](https://github.com/sandersdHES/ADF_DataCycleProject/wiki)

---

This manual provides a detailed guide on how to navigate and interpret the solar production monitoring dashboard. The interface is optimized with a high-contrast **Dark Mode** to ensure clarity during continuous monitoring sessions.

---

## 1. Data Controls & Navigation

The left-hand panel contains the primary tools for data customization:

- **Time Frame Selector:** A slider and calendar tool used to adjust the observation period (Daily, Weekly, or Monthly views).
- **Inverter Unit Selector:** Individual buttons for units `INV-01` through `INV-05`. Toggle specific units to perform a detailed diagnostic on a single inverter, or select all to view the total farm output.

---

## 2. Production & Environmental Correlation

The primary chart at the top tracks **Energy Production (kWh)** alongside **Ambient Temperature**.

> **Operational Insight:** Under normal conditions, these lines should follow a similar trajectory. A significant divergence — such as high temperatures with low energy output — serves as a primary indicator that a technical inspection is required.

---

## 3. Historical Production Rankings (Top Days)

The **Top Days** section highlights the highest-performing intervals within the selected timeframe.

> **Analysis:** Each bar is segmented by color to represent individual inverters. If one color segment appears disproportionately thin compared to others, it indicates that the specific unit was underperforming during that peak period.

---

## 4. Operational Log & Incident Tracking

The table at the bottom serves as a granular record of system activity.

| Entry Type | Color | Meaning |
|---|---|---|
| Normal operation | Green / Grey | Standard rows — system operating within expected parameters |
| Critical failure | **Red** | Fault logged in the database — requires immediate attention |

Each red entry identifies the exact **Timestamp** and the specific **Inverter Name** associated with the fault.

---

## 5. Efficiency Key Performance Indicators (KPI)

The bottom-right section compares actual power output against the hardware's rated capacity.

### Traffic Light System

| Color | Threshold | Status |
|---|---|---|
| 🟢 Green | > 85% efficiency | Optimal |
| 🔴 Red | < 75% efficiency | Inspection Needed |

This visual helps maintenance teams prioritize tasks at a glance.

---

## Connecting Power BI with your own login

Each user has a personal SQL login (e.g. `teacher.jdupont`, `director.alopez`). The dashboards are the same for everyone — what you see is filtered automatically by your role and division.

1. Open the desired report (`.pbix`) or template (`.pbit`) from `dashboards/`.
2. In Power BI Desktop, go to **Home → Transform data → Data source settings**.
3. Select the `sqlserver-bellevue-grp3.database.windows.net / DevDB` source and click **Edit Permissions → Edit…**
4. Switch the credential type to **Database** and enter your personal login + password.
5. Click **OK**, close, and **Refresh** the report.

Notes:
- **Teachers** see room bookings only for divisions they are assigned to.
- **Directors** see room bookings only for divisions they are assigned to.
- **Technicians** see no room bookings (GDPR), but full solar/weather/prediction data.

If a visual shows "permission denied" or unexpectedly empty data, verify with your administrator that your login is mapped to the correct division (table `ref_user_division_access`).

### Demo accounts (one per role)

The following accounts exist for demonstrations. **Initial passwords are not stored in this document** — they live in Azure Key Vault `DataCycleGroup3Keys` (same vault as `Admin-SQL-Password`). Ask your administrator, or retrieve them yourself with `az keyvault secret show` if you have access. Rotate after first use.

| Username | Role | Division | Key Vault secret name |
|---|---|---|---|
| `teacher.demo` | `Teacher_Role` | 1 (default — adjust if needed) | `Teacher-Demo-Password` |
| `director.demo` | `Director_Role` | 1 (default — adjust if needed) | `Director-Demo-Password` |
| `technician.demo` | `Technician_Role` | n/a (bypasses RLS) | `Technician-Demo-Password` |

---

## Quick Diagnostic Procedure

Use this checklist when investigating a suspected fault:

1. **Scan the Incident Log** for red error entries.
2. **Use the Inverter Selector** to isolate the unit reporting the fault.
3. **Cross-reference its performance** against the Temperature Trend to determine whether the issue is weather-related or a hardware failure.

---

## Related Resources

- [Data Privacy & GDPR Statement](DATA_PRIVACY_GDPR.md) — data protection measures and anonymization protocols
- [Technical Guide](TECHNICAL_GUIDE.md) — ETL pipeline, data schema, and ML lifecycle
- [Architecture Overview](ARCHITECTURE.md) — end-to-end system architecture
- [Power BI Dashboards](../dashboards/) — `.pbix` / `.pbit` source files
- [Wiki](https://github.com/sandersdHES/ADF_DataCycleProject/wiki) — full browsable reference
