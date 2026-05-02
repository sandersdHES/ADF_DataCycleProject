# User Handbook: Bellevue Solar Building — SAP Analytics Cloud Dashboard

> Part of the [Solar Inverter Operations & Performance Dashboard](../README.md) project.  
> See also: [Solar Inverter Dashboard Guide](USER_HANDBOOK_DASHBOARD.md) · [Room Occupancy Dashboard Guide](USER_HANDBOOK_ROOM_OCCUPANCY.md) · [Data Privacy & GDPR Statement](DATA_PRIVACY_GDPR.md) · [Technical Guide](TECHNICAL_GUIDE.md) · [Wiki](https://github.com/sandersdHES/ADF_DataCycleProject/wiki)

**SAP Analytics Cloud · Monitoring Dashboard · Version 1.0**

---

## 1. Purpose of this Dashboard

The **Bellevue – Solar Panel Overview** dashboard provides real-time visibility into the operational health and energy performance of the five solar inverters installed at the Bellevue building. It is designed for two audiences:

- **Technicians** — Daily monitoring, fault diagnosis, and maintenance planning.
- **Directors** — High-level performance review and reporting.

The dashboard draws from sensor readings captured every 5 minutes (288 readings per inverter per day) and is refreshed automatically each morning by ~07:30 after the data pipeline completes.

---

## 2. Accessing the Dashboard

The dashboard is hosted on **SAP Analytics Cloud (SAC)**. To access it:

1. Open your browser and go to your organisation's SAC URL.
2. Log in with your **HES-SO credentials** (same username and password as your other institutional tools).
3. In the left navigation panel, click **Stories**.
4. Open the story named **Bellevue – Solar Panel Overview**.

> The dashboard is **read-only** for Viewer accounts. You can interact with filters and drill into charts but cannot modify the underlying data or story layout.

---

## 3. Using the Filters

Three filters at the top of the page control what is shown across all charts simultaneously. Any change you make is applied immediately to every visual on the page.

| Filter | Default value | What it does |
|---|---|---|
| **Date Range** (`FullDate`) | Feb 2023 – Apr 2023 | Restricts all charts to the selected date window. Use this to zoom into a specific incident period or compare months. |
| **Inverter Name** | All (INV-01 to INV-05) | Shows data for one or more specific inverters. Select a single inverter to focus maintenance analysis on it. |
| **Status Category** | All | Filters by operational status: `OK` (standby), `Running` (producing), `Error` (fault), `Unknown` (undefined codes). Select `Error` to focus exclusively on fault events. |

> **Tip:** To reset all filters to their defaults, refresh the page in your browser.

---

## 4. Key Performance Indicators (Top Row)

The four KPI cards at the top of the page give an instant summary of the selected period. They update automatically when you change any filter.

| KPI Card | Example value | What it means |
|---|---|---|
| **Number of Failings** | 2,897 | Total number of 5-minute sensor readings recorded in an `Error` state across all inverters and all days in the selected period. A high number indicates repeated or sustained faults. |
| **Overall Failure Rate** | 3.60 % | Percentage of all sensor readings that were in a fault state. Calculated as: `Error readings ÷ total readings × 100`. A rate above **5%** warrants investigation. |
| **Average Performance Ratio** | 37.95 % | Average daily efficiency of the inverters across the period, including days with zero production (nights, standby). A higher value means the inverters converted a greater share of available solar energy into electricity. Colour indicator: 🟢 ≥ 85% · 🟠 75–84% · 🔴 < 75%. |
| **Days with Failures** | 80 | Number of distinct calendar days on which at least one inverter recorded a fault. Use this alongside the line chart to understand whether faults are concentrated in a short window or spread across the period. |

---

## 5. Chart Descriptions

### 5.1 Errors Over the Days (Line Chart)

This chart plots the **daily count of fault readings** across the entire fleet for each day in the selected period. Each point represents the total number of 5-minute slots during which at least one inverter was in an `Error` state.

- **A spike** indicates a day with sustained or repeated faults — worth cross-referencing with the inverter breakdown chart.
- **A sudden drop to near-zero** (as seen around 14 March 2023) typically means a fault cleared or was resolved.
- Use the **Date Range** filter to zoom into a specific incident window for finer analysis.

---

### 5.2 Number of Errors per Inverter (Horizontal Bar Chart)

Shows the **cumulative fault reading count** for each inverter over the selected period. Bars are sorted from highest to lowest to immediately surface the most problematic unit.

| Inverter | Error readings | Interpretation |
|---|---|---|
| INV-01 | 1,486 | High — primary maintenance priority |
| INV-03 | 1,386 | High — secondary maintenance priority |
| INV-04 | 12 | Low — occasional transient faults |
| INV-05 | 12 | Low — occasional transient faults |
| INV-02 | 1 | Negligible — near-zero fault history |

---

### 5.3 Overall Inverter Status (100% Stacked Bar)

Each bar represents one inverter and shows how its daily reading time was distributed across the four status categories as a percentage of the total. This gives a **health profile at a glance**.

| Status | Colour | Meaning |
|---|---|---|
| **OK** | Orange | Standby — inverter is powered and healthy but not producing (typical at night or on low-irradiation days). |
| **Running** | Green | Inverter is actively converting solar energy to AC power. |
| **Error** | Blue | A fault was recorded. A large blue segment demands immediate attention. |
| **Unknown** | Pink | Undocumented manufacturer status codes. A small slice is normal; a growing slice should be flagged. |

> INV-01 shows a visible Error segment (~9.2%), confirming it as the highest-priority unit for inspection. INV-02 is almost entirely in OK/standby, suggesting limited production activity during the period.

---

### 5.4 Average Performance Ratio per Inverter (Horizontal Bar)

Displays the **average efficiency** of each inverter across the selected period. The performance ratio measures how much of the theoretically available solar energy was actually converted to electricity — a ratio of 100% would mean perfect conversion with no losses.

| Bar colour | Threshold | Status |
|---|---|---|
| 🟢 Green | ≥ 85% | Operating at or above target efficiency |
| 🟠 Orange | 75–84% | Slightly below target — monitor closely |
| 🔴 Red | < 75% | Underperforming — investigation recommended |

> **Note:** The ratio includes all days in the period, including days with no production (ratio = 0). INV-01 (5.92%) and INV-02 (1.94%) appear very low because they spent most of the period in standby or fault state with minimal productive hours — not because they are inefficient when running.

---

## 6. Practical Guidance for Technicians

### 6.1 Daily Check Routine

1. Open the dashboard and confirm the **Date Range** filter covers the current day or last 7 days.
2. Check the **Number of Failings** and **Overall Failure Rate** KPI cards — any significant increase since yesterday?
3. Scan the **Errors over the days** line chart for yesterday's data point — is it higher than the baseline?
4. If a spike is visible, check the **Number of errors per Inverter** bar chart to identify which unit is responsible.
5. Use the **Inverter Name** filter to isolate that inverter and review its status distribution and performance ratio.

---

### 6.2 Investigating a Specific Fault Event

1. Set the **Date Range** filter to the period of interest (e.g., the day of the spike).
2. Set the **Status Category** filter to `Error` to isolate fault readings only.
3. Review which inverters show non-zero error counts in the bar chart.
4. Note the percentage of the day affected (shown in the status distribution chart).
5. Cross-reference with the **performance ratio** — a low ratio on an error day confirms energy was lost during the fault.
6. Record the inverter ID, date, and error percentage for the maintenance log.

---

### 6.3 Priority Maintenance Flags

Based on the current data (Feb–Apr 2023), the following units require attention:

| Inverter | Issue | Priority |
|---|---|---|
| **INV-01** | 1,486 fault readings · 9.2% of daily time in Error state | 🔴 Highest — physical inspection required |
| **INV-03** | 1,386 fault readings | 🟠 High — schedule inspection after INV-01 |
| **INV-01** (performance) | Performance ratio of 5.92% across the period — very low | 🔴 Verify whether extended downtime was planned or unplanned |

---

## 7. Updating the Dashboard Data

The dashboard data is updated **once per day**. The pipeline runs automatically each morning, but the final step — importing the new file into the SAC model — must be performed manually by a member of the data analyst team. The process takes approximately 5 minutes.

The CSV file delivered by the pipeline is already fully prepared: all calculations (performance ratio, failure counts) are pre-computed at source. No data transformation is needed in SAC — the file is imported directly into the model.

### 7.1 Automated Refresh Schedule

| Time | What happens |
|---|---|
| ~07:15 | Automated data pipeline starts — raw sensor files are collected and processed. |
| ~07:30 | Gold layer data is updated and `sac_inverter_combined.csv` is deposited in the ADLS `sacexport` container. |
| ~07:35+ | Data analyst downloads the CSV via Azure Storage Explorer and imports it into the SAC model (Steps 1–3 below). |

---

### 7.2 Step 1 — Install Microsoft Azure Storage Explorer *(first time only)*

Azure Storage Explorer is a free desktop application from Microsoft that lets you browse and download files from the secure cloud storage container. You only need to install it once.

1. **Download** — Go to [https://azure.microsoft.com/en-us/products/storage/storage-explorer/](https://azure.microsoft.com/en-us/products/storage/storage-explorer/) and click **Download now**.
2. **Install** — Run the installer and follow the on-screen instructions (Windows, Mac, and Linux are all supported).
3. **Sign in** — Open Azure Storage Explorer. Click the plug icon (**Connect to Azure resources**) in the top-left toolbar.
4. **Select account type** — Choose **Subscription**, then click **Next**.
5. **Authenticate** — A browser window will open. Sign in with your HES-SO credentials (same as your institutional email login).
6. **Find the container** — In the left panel, expand **Storage Accounts → adlsbellevuegrp3 → Blob Containers → sacexport**. This is the only container you will have access to.

> **Note:** If you cannot see the `sacexport` container or receive an authorisation error, contact your data engineer to confirm your account has been added to the `GRP_Bellevue_SAC_Analysts` access group.

---

### 7.3 Step 2 — Download the CSV from Azure Storage Explorer

Each time the dashboard needs to be refreshed, download the latest CSV file:

1. **Open Storage Explorer** — Navigate to `sacexport` in the left panel (as set up in Step 1).
2. **Locate the file** — In the main panel, find the file named `sac_inverter_combined.csv`. Check the **Last Modified** date to confirm it was updated today (after 07:30).
3. **Download** — Right-click the file and select **Download**, or select it and click the **Download** button in the toolbar.
4. **Save locally** — Choose a location on your computer (e.g., your Downloads folder). **Do not rename the file** — keep it as `sac_inverter_combined.csv`.

---

### 7.4 Step 3 — Import the CSV into the SAC Model

The CSV is imported directly into the SAC model using the model's built-in import job. There is no intermediate dataset or data preparation step — the file is ready to use as-is.

1. **Open SAC** — Log in to SAP Analytics Cloud with your HES-SO credentials.
2. **Navigate to the model** — In the left navigation panel, click **Files**. Locate and open the model named **Bellevue_InverterFailure_Model** in the Modeler.
3. **Open Data Management** — Click **Data Management** in the top toolbar. The Data Integration tab will open, showing Draft Sources and Import Jobs.
4. **Import new data** — In the Draft Sources section, click the import icon (**↓ arrow**, top right of the section). Select **Upload a file** and browse to the `sac_inverter_combined.csv` file you downloaded in Step 2.
5. **Map columns** — SAC will display a column mapping screen. Verify that all columns are correctly mapped to their model counterparts (this should be automatic after the first time). Click **Import**.
6. **Run the import** — Once the import completes, click **Finalize** or **Publish** to push the draft data into the live model. *(The exact button label may vary by SAC version.)*
7. **Verify** — Open the Story (**Stories → Bellevue – Solar Panel Overview**) and confirm the date range in the line chart now includes the most recent days.

> **Summary — full refresh in 3 steps:**
> 1. Open Azure Storage Explorer → download `sac_inverter_combined.csv`
> 2. Open SAC model → Data Management → import the file
> 3. Open the Story to confirm the data is current

> **If the data appears outdated** after following these steps (e.g., the most recent date in the line chart is more than 2 days old), contact your data engineer to verify the automated pipeline ran successfully.

---

## 8. Glossary

| Term | Definition |
|---|---|
| **Inverter** | A device that converts the DC electricity produced by solar panels into AC electricity for building use or grid export. |
| **Performance Ratio** | A dimensionless efficiency index (0–100%) comparing actual energy output to the theoretical maximum given available sunlight. |
| **Reading / Sensor Reading** | One data point captured every 5 minutes by the monitoring system. There are 288 readings per inverter per day. |
| **Status Category** | A classification of the inverter's operational state: `OK` (standby), `Running` (producing), `Error` (fault), or `Unknown` (undocumented code). |
| **Failure Rate** | The percentage of sensor readings recorded in an Error state relative to all readings in the selected period. |
| **Error State** | An inverter status indicating a fault condition that is preventing normal operation. Corresponds to Status Code 14 in the raw data. |
| **Unknown State** | A manufacturer-defined status code that has not been officially documented. Appears rarely (<0.1% of readings) and typically represents brief transitional states. |
| **Gold Layer** | The pre-processed, analytics-ready data in the platform, aggregated from raw 5-minute readings into daily summaries per inverter. |

---

*Bellevue Solar Building · Group 3 · HES-SO Valais · Dashboard v1.0 · April 2026*
