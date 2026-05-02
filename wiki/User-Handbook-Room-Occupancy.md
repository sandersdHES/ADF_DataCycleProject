# User Handbook — Room Occupancy Dashboard

[[Home]] > User Handbook — Room Occupancy Dashboard

End-user guide for the **Room Occupancy & Utilization** Power BI dashboard. Walks through every visual, what it shows, and how to interact with it.

> Canonical source: [`docs/USER_HANDBOOK_ROOM_OCCUPANCY.md`](https://github.com/sandersdHES/ADF_DataCycleProject/blob/main/docs/USER_HANDBOOK_ROOM_OCCUPANCY.md). The repo version has the same content with locally hosted screenshots.

![Room Occupancy & Utilization — full dashboard overview](https://raw.githubusercontent.com/sandersdHES/ADF_DataCycleProject/main/docs/assets/room-occupancy/dashboard-overview.png)

---

## 1. Top Filters

![Top Filters panel](https://raw.githubusercontent.com/sandersdHES/ADF_DataCycleProject/main/docs/assets/room-occupancy/filters-panel.png)

> **Technical Setup:** Three drop-down menus mapped to the `WeekOfYear`, `SchoolName`, and `DayName` fields.

| Filter | What it does |
|---|---|
| **WeekOfYear** | Restrict the view to a single week of the academic calendar. |
| **SchoolName** | Show only rooms belonging to a specific school. |
| **DayName** | Focus on a specific day of the week. |

> **Tip:** Hover over the top-right corner of any filter to reveal a small eraser icon. Click it to clear your selection.

---

## 2. KPI Cards — The Big Numbers

![KPI summary cards](https://raw.githubusercontent.com/sandersdHES/ADF_DataCycleProject/main/docs/assets/room-occupancy/kpi-cards.png)

> **Technical Setup:** Three independent Card visuals using the `Occupation Rate Pct`, `Peak Day Occupation`, and `Total Bookings` measures.

| Card | What it shows |
|---|---|
| **Occupation Rate Pct** | Average % of time rooms are in use under the current filters. |
| **Peak Day Occupation** | The day of the week with the highest demand. |
| **Total Bookings** | Number of reservations in the filtered period. |

---

## 3. Room Occupancy by Hour (Heatmap)

![Room Occupancy heatmap by hour](https://raw.githubusercontent.com/sandersdHES/ADF_DataCycleProject/main/docs/assets/room-occupancy/room-occupancy-by-hour.png)

> **Technical Setup:** Matrix visual — rows = `RoomCode`, columns = hour 0–23. Conditional background formatting on the value.

Darker red = busier room at that hour. Lighter / white = available slot. Use it to scout free rooms or plan meetings.

---

## 4. Occupancy by Day of the Week

![Occupancy Rate by Day of the Week bar chart](https://raw.githubusercontent.com/sandersdHES/ADF_DataCycleProject/main/docs/assets/room-occupancy/occupancy-by-day.png)

> **Technical Setup:** Column chart — `DayName` X-axis, average `Occupation Rate Pct` Y-axis.

- Reveals the weekly rhythm — busiest day vs. quietest day.
- Click a bar to **cross-filter the whole dashboard** to that day. Click again to reset.

---

## 5. Occupancy Over Time by Division

![Occupancy Over Time by Division line chart](https://raw.githubusercontent.com/sandersdHES/ADF_DataCycleProject/main/docs/assets/room-occupancy/occupancy-over-time.png)

> **Technical Setup:** Line chart — `FullDate` X-axis, `Occupation Rate Pct` Y-axis, `Division Code` legend, plus a trendline.

- Each colour = a school / division.
- Spikes = exceptional demand (sometimes >100% when rooms double-book).
- Dashed black trendline shows whether usage is rising or falling overall.

---

## 6. Occupancy by Week of the Year

![Occupancy Rate by Week of Year area chart](https://raw.githubusercontent.com/sandersdHES/ADF_DataCycleProject/main/docs/assets/room-occupancy/occupancy-by-week.png)

> **Technical Setup:** Area chart — `WeekOfYear` X-axis, `Occupation Rate Pct` Y-axis, `IsAcademicDay` legend.

- Mountains = busiest semester weeks (midterms, project deadlines).
- Valleys = breaks and holidays.
- The `IsAcademicDay` legend separates term-time and out-of-term traffic.

---

## 7. Top Rooms by Occupancy

![Top Rooms by Occupancy leaderboard bar chart](https://raw.githubusercontent.com/sandersdHES/ADF_DataCycleProject/main/docs/assets/room-occupancy/top-rooms-by-occupancy.png)

> **Technical Setup:** Clustered bar chart — `RoomCode` Y-axis, `Occupation Rate Pct` X-axis, sorted descending.

Ranks the most heavily booked rooms. Click any bar to filter the entire dashboard to that room — useful for spotting bottleneck rooms.

---

## Quick Reference — Interactive Tips

| Visual | Click action |
|---|---|
| Day bar chart | Filters entire dashboard to the selected day |
| Top Rooms bar chart | Filters entire dashboard to the selected room |
| Time series chart | Hover to reveal exact date, division & percentage |
| Any filter | Hover top-right corner → eraser icon → clears filter |

---

## Access & multi-user notes

What you see depends on which SQL login the report is connected with — Row-Level Security narrows `fact_room_booking` to the divisions you are mapped to. See **[[Security and User Management]]** for the role catalog and how to switch the Power BI connection to your own login.

---

*Related: [[User Handbook — Solar Inverter Dashboard|Solar Inverter Dashboard guide]] (canonical: [`docs/USER_HANDBOOK_DASHBOARD.md`](https://github.com/sandersdHES/ADF_DataCycleProject/blob/main/docs/USER_HANDBOOK_DASHBOARD.md))* · *[[Data Warehouse Schema]]* · *[[Security and User Management]]*
