# ADF DataCycle Project – Corrected Agile Backlog

_Generated on 2026-04-24 from Agile_ProjectPlan_Group3.xlsx with corrections applied._

## Anomaly Corrections Applied

- US03–US13: Due dates corrected from 27/02/2026 (Sprint 1 end) to their actual sprint end dates
- US27: Status corrected To do → In Progress (partial RLS implementation confirmed in notes)
- US38: Status corrected Done → In Progress (4/7 tasks still pending: ML docs, dashboard docs, final review)
- US26: Moved Sprint 5 → Sprint 6 (not started with 3 days left in Sprint 5)
- US27: Moved Sprint 5 → Sprint 6 (incomplete with 3 days left in Sprint 5)
- US34: Scope-undefined warning added to notes
- US13: Note added that historization/end-to-end test tasks were deferred

## Sprint Summary

| Sprint | Period | Goal | SP | US | Status |
|---|---|---|---|---|---|
| Sprint 1 | 17/02/2026 → 02/03/2026 | Project kick-off: architecture defined and environment ready | 8 SP | 2 US | Done |
| Sprint 2 | 03/03/2026 → 16/03/2026 | Raw data ingestion pipelines for all core data sources operational | 24 SP | 6 US | Done |
| Sprint 3 | 17/03/2026 → 30/03/2026 | Remaining ingestion pipelines, security foundations and monitoring in place | 37 SP | 6 US | Done |
| Sprint 4 | 31/03/2026 → 13/04/2026 | Silver (clean) layer and OLAP database built and populated | 34 SP | 6 US | Done |
| Sprint 5 | 14/04/2026 → 27/04/2026 | All BI dashboards (PowerBI & SAC) delivered with security controls | 42 SP | 6 US | In Progress |
| Sprint 6 | 28/04/2026 → 08/05/2026 | ML models, predictions, documentation, deployment and final presentation | 83 SP | 13 US | Planned |

## Full Backlog

| US # | Theme | Sprint | SP | MoSCoW | Status | Summary |
|---|---|---|---|---|---|---|
| US01 | Architecture | 1 | 5 | Must | Done | Design the end-to-end high level architecture required for the project |
| US02 | Preparation | 1 | 3 | Must | Done | Explore the available data, verify the access, connectivity and instal |
| US03 | Data Integration | 2 | 3 | Must | Done | Build the adequate raw data storage area |
| US04 | Data Integration | 2 | 5 | Must | Done | Develop the data flow to ingest the solar panel data into the raw data |
| US05 | Data Integration | 2 | 5 | Must | Done | Develop the data flow to ingest the general power data into the raw da |
| US06 | Data Integration | 2 | 3 | Must | Done | Develop the data flow to ingest the temperature/weather data into the  |
| US07 | Data Integration | 2 | 3 | Must | Done | Develop the data flow to ingest the humidity/weather data into the raw |
| US08 | Data Integration | 3 | 5 | Must | Done | Develop the data flow to ingest the rooms reservation data into the ra |
| US09 | Data Integration | 3 | 5 | Must | Done | Develop the data flow to ingest the weather forecast data into the raw |
| US10 | Security | 2 | 5 | Could | Done | Implement a secure way to store and manage the keys, pwd and certifica |
| US11 | Security | 3 | 8 | Should | Done | Implement the integration and storage security (encryption, transport) |
| US12 | Data Integration | 3 | 8 | Must | Done | Implement error handling, monitoring and alerts for all data flows |
| US13 | Data Integration | 3 | 8 | Must | Done | Implement the scheduling in all data flows to retrieve the latest data |
| US14 | BI | 3 | 3 | Should | Done | Prepare mockups of the dashboards and reports |
| US15 | Data Integration | 4 | 3 | Must | Done | Build the adequate clean (silver) data storage area |
| US16 | Data Integration | 4 | 8 | Must | Done | Identify the possible data quality issues, and develop the flow to loa |
| US17 | BI | 4 | 5 | Should | Done | Modelize the OLAP database to store the aggregated (gold) data |
| US18 | BI | 4 | 8 | Must | Done | Build the OLAP database |
| US19 | Data Integration | 4 | 5 | Must | Done | Develop the data flow to load data from the silver storage into the OL |
| US20 | Security | 4 | 5 | Could | Done | Implement data masking (anonymisation) for personal data |
| US21 | BI | 5 | 8 | Must | In Progress | Build the solar panel production report/dashboard in PowerBI |
| US22 | BI | 5 | 8 | Must | In Progress | Build the energy report/dashboard in PowerBI |
| US23 | BI | 5 | 5 | Should | Done | Build the rooms report/dashboard in PowerBI |
| US24 | Data Integration | 5 | 8 | Must | Done | Develop the data flow to export data and load into SAP SAC |
| US25 | BI | 5 | 8 | Must | In Progress | Build the solar panel failure report/dashboard in SAC |
| US26 | Security | 6 | 5 | Should | To do | Implement user access right management |
| US27 | Security | 6 | 5 | Could | In Progress | Implement row level security |
| US28 | Data Integration | 5 | 5 | Must | Done | Build a data flow to export/import the data to Knime |
| US29 | Data Science | 6 | 13 | Must | Done | Build a model to predict the energy production for the solar panels (c |
| US30 | Data Science | 6 | 13 | Must | Done | Build a model to predict the energy consumption (considering weather f |
| US31 | Data Integration | 6 | 5 | Should | Done | Load back the results of the prediction into the data warehouse |
| US32 | BI | 6 | 5 | Should | In Progress | Update the report/dashboard in PowerBI to visualize the prediction res |
| US33 | BI | 6 | 3 | Could | To do | Implement internationalization of the reports, dashboards and stories |
| US34 | Architecture | 6 | 5 | Could | To do | Verify the scalability of the solution and provide a forecast of requi |
| US35 | Data Privacy | 6 | 5 | Should | To do | Provide a written assessment of how the solution is compliant with GDP |
| US36 | Deployment | 6 | 8 | Must | In Progress | Configure a package/transport to deploy to the customer environment |
| US37 | Documentation | 6 | 5 | Must | In Progress | Generate user guide to facilitate the use of the dashboard and underst |
| US38 | Documentation | 6 | 8 | Must | In Progress | Generate technical documentation to ensure another IT specialist can u |
| US39 | Presentation | 6 | 3 | Must | To do | Prepare the presentation |