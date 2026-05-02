# User Handbook — SAC Dashboard

[[Home]] > User Handbook — SAC Dashboard

End-user guide for the **Bellevue – Solar Panel Overview** dashboard in **SAP Analytics Cloud (SAC)**.  
Target audience: Technicians (daily monitoring), Directors (performance review).

---

## 1. Purpose

The dashboard provides real-time visibility into the operational health and energy performance of the five solar inverters at the Bellevue building. It draws from sensor readings captured every 5 minutes (288 readings per inverter per day) and is refreshed automatically each morning by ~07:30 after the data pipeline completes.

The data arrives through the pipeline as `sacexport/sac_inverter_combined.csv`, which pre-computes performance ratios, failure counts, and status distributions — no additional transformation is needed in SAC.

---

## 2. Accessing the Dashboard

1. Open your browser and go to your organisation's SAC URL.
2. Log in with your **HES-SO credentials**.
3. In the left navigation panel, click **Stories**.
4. Open the story named **Bellevue – Solar Panel Overview**.

> The dashboard is **read-only** for Viewer accounts. You can interact with filters and drill into charts but cannot modify the underlying data or story layout.

---

## 3. Filters

Three filters at the top control all charts simultaneously.

| Filter | Default | What it does |
|---|---|---|
| **Date Range** (`FullDate`) | Feb 2023 – Apr 2023 | Restricts all charts to the selected date window |
| **Inverter Name** | All (INV-01 to INV-05) | Shows data for one or more specific inverters |
| **Status Category** | All | Filters by operational status: `OK`, `Running`, `Error`, `Unknown` |

> **Tip:** To reset all filters, refresh the page in your browser.

---

## 4. KPI Cards (Top Row)

The four cards give an instant summary of the selected period.

| KPI Card | Example | What it means |
|---|---|---|
| **Number of Failings** | 2,897 | Total 5-minute readings recorded in `Error` state across all inverters in the period. High = repeated or sustained faults. |
| **Overall Failure Rate** | 3.60% | `Error readings ÷ total readings × 100`. Rates above **5%** warrant investigation. |
| **Average Performance Ratio** | 37.95% | Daily inverter efficiency including days with zero production (nights, standby). Higher = more solar energy converted. Colour: 🟢 ≥ 85% · 🟠 75–84% · 🔴 < 75%. |
| **Days with Failures** | 80 | Calendar days on which at least one inverter recorded a fault. |

---

## 5. Charts

### 5.1 Errors Over the Days (Line Chart)

Daily count of fault readings across the whole fleet. Each point = total 5-minute fault slots for that day.

- **A spike** → sustained or repeated faults on that day — cross-reference with the inverter breakdown.
- **A sudden drop to near-zero** → fault cleared or resolved.
- Use **Date Range** to zoom into a specific incident window.

---

### 5.2 Number of Errors per Inverter (Horizontal Bar Chart)

Cumulative fault reading count per inverter over the selected period, sorted highest to lowest.

| Inverter | Fault readings (Feb–Apr 2023) | Interpretation |
|---|---|---|
| INV-01 | 1,486 | High — primary maintenance priority |
| INV-03 | 1,386 | High — secondary maintenance priority |
| INV-04 | 12 | Low — occasional transient faults |
| INV-05 | 12 | Low — occasional transient faults |
| INV-02 | 1 | Negligible — near-zero fault history |

---

### 5.3 Overall Inverter Status (100% Stacked Bar)

Each bar is one inverter. Shows how daily reading time was split across the four status categories — a **health profile at a glance**.

| Status | Colour | Meaning |
|---|---|---|
| **OK** | Orange | Standby — healthy but not producing (typical at night or on overcast days) |
| **Running** | Green | Actively converting solar energy to AC power |
| **Error** | Blue | A fault was recorded — a large segment demands immediate attention |
| **Unknown** | Pink | Undocumented manufacturer status codes — a small slice is normal |

> INV-01 shows a visible Error segment (~9.2%), confirming it as the highest-priority unit.

---

### 5.4 Average Performance Ratio per Inverter (Horizontal Bar)

Average daily efficiency per inverter, including all days (even zero-production days).

| Colour | Threshold | Status |
|---|---|---|
| 🟢 Green | ≥ 85% | Operating at or above target |
| 🟠 Orange | 75–84% | Slightly below target — monitor closely |
| 🔴 Red | < 75% | Underperforming — investigation recommended |

> INV-01 (5.92%) and INV-02 (1.94%) appear very low because they spent most of the period in standby or fault state — not because they are inefficient when running.

---

## 6. Daily Check Routine (Technicians)

1. Open the dashboard. Confirm the **Date Range** filter covers today or the last 7 days.
2. Check **Number of Failings** and **Failure Rate** — any significant increase since yesterday?
3. Scan the **Errors over the days** line chart for yesterday's point — higher than the baseline?
4. If a spike is visible, check the **Errors per Inverter** bar chart to identify the unit.
5. Use **Inverter Name** filter to isolate that inverter and review its status distribution and performance ratio.

---

## 7. Investigating a Fault Event

1. Set **Date Range** to the period of interest.
2. Set **Status Category** to `Error` — isolates fault readings only.
3. Check which inverters show non-zero error counts.
4. Note the percentage of the day affected (status distribution chart).
5. Cross-reference with the **performance ratio** — a low ratio on an error day confirms energy was lost.
6. Record inverter ID, date, and error percentage in the maintenance log.

---

## 8. Priority Maintenance Flags (Feb–Apr 2023 baseline)

| Inverter | Issue | Priority |
|---|---|---|
| **INV-01** | 1,486 fault readings · 9.2% of daily time in Error | 🔴 Highest — physical inspection required |
| **INV-03** | 1,386 fault readings | 🟠 High — schedule after INV-01 |

---

## 9. Updating the Dashboard Data

The pipeline runs automatically each morning. The final import step must be done manually by a data analyst (~5 minutes).

### Automated schedule

| Time | What happens |
|---|---|
| ~07:15 | Pipeline starts — raw sensor files collected and processed |
| ~07:30 | Gold data updated; `sac_inverter_combined.csv` deposited in ADLS `sacexport` |
| ~07:35+ | Data analyst downloads CSV via Azure Storage Explorer and imports into SAC model |

### Step 1 — Download the CSV from Azure Storage Explorer *(install once)*

1. Download Azure Storage Explorer from [azure.microsoft.com/products/storage/storage-explorer](https://azure.microsoft.com/products/storage/storage-explorer).
2. Sign in with your HES-SO credentials.
3. Navigate to **Storage Accounts → adlsbellevuegrp3 → Blob Containers → sacexport**.
4. Locate `sac_inverter_combined.csv`, confirm the **Last Modified** date is today (after 07:30).
5. Right-click → **Download** → save as `sac_inverter_combined.csv`.

> If you cannot see the `sacexport` container, contact your data engineer to confirm your account is in `GRP_Bellevue_SAC_Analysts`.

### Step 2 — Import into the SAC model

1. Log in to SAC with HES-SO credentials.
2. Click **Files** → open the model **Bellevue_InverterFailure_Model** in the Modeler.
3. Click **Data Management** → **Draft Sources** → import icon (↓ arrow) → **Upload a file** → select the downloaded CSV.
4. Verify column mapping is correct, then click **Import**.
5. Click **Finalize / Publish** to push draft data into the live model.
6. Open **Stories → Bellevue – Solar Panel Overview** and confirm the date range includes the most recent days.

> **If data appears outdated** (most recent date > 2 days old): contact your data engineer to verify the pipeline ran successfully.

---

## 10. Glossary

| Term | Definition |
|---|---|
| **Inverter** | A device that converts DC electricity from solar panels into AC electricity for building use. |
| **Performance Ratio** | Efficiency index (0–100%) comparing actual output to theoretical maximum given available sunlight. |
| **Sensor Reading** | One data point captured every 5 minutes — 288 readings per inverter per day. |
| **Status Category** | Operational state: `OK` (standby), `Running` (producing), `Error` (fault), `Unknown` (undocumented code). |
| **Failure Rate** | Percentage of readings in Error state relative to all readings in the period. |
| **Error State** | Fault condition — corresponds to `status_code = 14` in the raw inverter data. |
| **Gold Layer** | Analytics-ready data in Azure SQL, pre-aggregated from raw 5-minute readings into daily summaries per inverter. |

---

*For the pipeline that produces this data, see [[Databricks Notebooks]] and [[ADF Pipelines]].*
