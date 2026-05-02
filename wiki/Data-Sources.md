# Data Sources

[[Home]] > Data Sources

All sources are served by an on-premises Windows VM at `10.130.25.152` and reached via the **Self-Hosted Integration Runtime (SHIR)** registered as `Group3-VM-Runtime`.

---

## Source inventory

| Source | ADF Linked Service | Transport | File path pattern | Encoding | ADF Pipeline |
|---|---|---|---|---|---|
| Solar inverter logs (raw, 5-min) | `LS_Solarlogs_LocalServer` | SMB | `\\10.130.25.152\Solarlogs\min*.csv` | UTF-8 | `PL_Bronze_Solar` |
| Solar aggregated (PV, 15-min) | `LS_Solarlogs_LocalServer` | SMB | `\\10.130.25.152\Solarlogs\*-PV.csv` | **UTF-16 LE** | `PL_Bronze_Solar` |
| Room bookings | `LS_BellevueBooking_LocalServer` | SMB | `\\10.130.25.152\BellevueBooking\*.csv` | UTF-8, tab-separated | `PL_Bronze_Bookings` |
| Energy consumption | `LS_BellevueConso_LocalServer` | SMB | `\\10.130.25.152\BellevueConso\...-Consumption.csv` | **UTF-16 LE** | `PL_Bronze_Conso` |
| Indoor temperature | `LS_BellevueConso_LocalServer` | SMB | `\\10.130.25.152\BellevueConso\...-Temperature.csv` | **UTF-16 LE** | `PL_Bronze_Conso` |
| Indoor humidity | `LS_BellevueConso_LocalServer` | SMB | `\\10.130.25.152\BellevueConso\...-Humidity.csv` | **UTF-16 LE** | `PL_Bronze_Conso` |
| Historical weather (meteo) | `LS_SFTP_LocalServer` | SFTP | `/*.csv` | UTF-8 | `PL_Bronze_Meteo` |
| Future weather forecasts | `LS_SFTP_LocalServer` | SFTP | `/future_forecasts/*.csv` | UTF-8 | `PL_Bronze_MeteoFuture` ⚠️ |

> ⚠️ `PL_Bronze_MeteoFuture` is a standalone pipeline — it is **not** called by `PL_Ingest_Bronze`. See [[Known Limitations and Roadmap]].

---

## Bronze ingestion pattern

All four active Bronze pipelines share the same incremental-copy shape:

```
GetMetadata(source)  →  GetMetadata(destination)  →  Filter(new files only)  →  ForEach(batch 50) Copy
```

Files are binary-copied as-is to `bronze/<area>/`. No transformation at ingestion.

**`PL_Bronze_Conso` routing** — the copy destination is dynamic based on filename prefix:

| Prefix | Destination |
|---|---|
| `*-Consumption.csv` | `bronze/consumption/` |
| `*-Temperature.csv` | `bronze/temperature/` |
| `*-Humidity.csv` | `bronze/humidity/` |
| *(other)* | `bronze/others/` |

---

## Per-source detail

### Solar inverter logs (`min*.csv`)

One file per day named `minYYMMDD.csv`, semicolon-delimited, UTF-8. Each row covers a **5-minute sample across all five inverters simultaneously** in a single wide row with repeating column blocks — one block of 11 columns per inverter (55 data columns total after `Date` and `Time`).

`silver_transformation.py` unpivots this wide structure into **one row per inverter per timestamp** via `explode()` on a 5-element struct array.

| Column | Type | Description |
|---|---|---|
| `Date` | `DD.MM.YY` | Measurement date |
| `Time` | `HH:MM:SS` | Measurement time |
| `INV` | int | Inverter number (1–5); the header repeats this block five times |
| `Pac` | int (W) | AC output power across all phases (L1+L2+L3 combined) |
| `DaySum` | int (Wh) | Cumulative energy produced since midnight for this inverter |
| `Status` | int | Operating status: 0 = standby/OK · 6 = running · 14 = error |
| `Error` | int | Error code; 0 = no error |
| `Pdc1` / `Pdc2` | int (W) | DC input power from generator strings 1 and 2 |
| `Udc1` / `Udc2` | int (V) | DC voltage from generator strings 1 and 2 |
| `Temp` / `Uac` | int | Not used in the sensor export |

---

### Solar aggregated — PV (`*-PV.csv`)

One file per day named `DD.MM.YYYY-PV.csv`, semicolon-delimited, **UTF-16 LE with BOM**. Captures the whole-plant aggregate energy meter at **15-minute intervals**.

| Column | Type | Description |
|---|---|---|
| `Date` | `DD.MM.YYYY` | Measurement date |
| `Heure` | `HH:MM:SS` | Measurement time |
| `Unité affichage` | string | Unit — always `kWh` |
| `Valeur Acquisition` | decimal | **Cumulative** meter reading in kWh — monotonically increasing over time |
| `Variation` | decimal | kWh delta since the previous 15-minute reading |

Because the meter is **cumulative**, a counter reset (power outage or meter replacement) produces a negative `Variation`. `silver_transformation.py` detects the decrease and sets the delta to `null`; downstream facts re-derive it via `lag()`.

---

### Energy consumption (`*-Consumption.csv`)

One file per day, semicolon-delimited, **UTF-16 LE with BOM**. Identical structure to the PV file — measures building kWh consumed rather than produced.

| Column | Type | Description |
|---|---|---|
| `Date` | `DD.MM.YYYY` | Measurement date |
| `Heure` | `HH:MM:SS` | Measurement time |
| `Unité affichage` | string | Unit — always `kWh` |
| `Valeur Acquisition` | decimal | **Cumulative** kWh consumed by the building since meter installation |
| `Variation` | decimal | kWh delta since the previous 15-minute reading |

The same counter-reset null logic applies. Not every 15-minute slot is guaranteed to be present — gaps appear during weekends or sensor outages.

---

### Indoor temperature (`*-Temperature.csv`)

One file per day, semicolon-delimited, **UTF-16 LE with BOM**. Point-in-time readings, not cumulative.

| Column | Type | Description |
|---|---|---|
| `Date` | `DD.MM.YYYY` | Measurement date |
| `Heure` | `HH:MM:SS` | Measurement time |
| `Unité affichage` | string | Unit — always `C` (Celsius) |
| `Valeur Acquisition` | decimal | Indoor ambient temperature at the time of reading |
| `Variation` | decimal | Difference from the previous reading (not used downstream — `silver_transformation.py` re-derives the delta via `lag()`) |

---

### Indoor humidity (`*-Humidity.csv`)

One file per day, same structure as temperature.

| Column | Type | Description |
|---|---|---|
| `Date` | `DD.MM.YYYY` | Measurement date |
| `Heure` | `HH:MM:SS` | Measurement time |
| `Unité affichage` | string | Unit — always `%` |
| `Valeur Acquisition` | decimal | Relative indoor humidity at the time of reading |
| `Variation` | decimal | Difference from the previous reading (not used downstream) |

> Temperature and humidity do not always share the same timestamps. `silver_gold_facts.py` uses a **FULL OUTER JOIN** when loading `fact_environment` to preserve readings even when only one sensor reported for a given slot.

---

### Room bookings (`RoomAllocations_YYYYMMDD.csv`)

One file per week, **tab-separated** (`\t`), UTF-8. One row per booking entry — not a time-series.

Only bookings for Bellevue rooms (`Nom` starts with `VS-BEL`) are kept — other campus rooms are filtered out in Silver.

| Column | Type | Description |
|---|---|---|
| `Nom` / `Nom entier` | string | Room code and full display name (e.g. `VS-BEL.N301`) |
| `Date` | French date string | Day of the individual booking session (e.g. `8 janv. 2023`) — converted to standard date in Gold via a `french_date_to_english` helper |
| `Date de début` / `Date de fin` (1st pair, index 3/4) | time | Session start and end time |
| `Rés.-no` | string | Unique reservation number |
| `Type de réservation` / `Codes` | string | Booking type and category codes |
| `Nom de l'utilisateur` | string | Login of the person who made the booking — **GDPR: SHA-256 hashed** → `UserMasked` |
| `Date de début` / `Date de fin` (2nd pair, index 11/12) | date | Start and end dates of the recurrence window |
| `Périodicité` | string | Recurrence rule (e.g. `w` = weekly) |
| `Classe` | string | Attending class or service |
| `Activité` | string | Nature of the activity (e.g. `Cours`) |
| `Professeur` | string | Person conducting the activity — **GDPR: SHA-256 hashed** → `ProfessorMasked` |
| `Division` | string | HES-SO school or service responsible for the booking |
| `Poste de dépenses` | string | Cost centre |
| `Remarque` / `Annotation` | string | Free-text notes |

> **Column rename caveat (known limitation):** `silver_transformation.py` renames the duplicate `Date de début` / `Date de fin` pairs based on their positional suffix assigned by Spark (e.g. `Date de début3`, `Date de début11`). If the CSV column order ever changes, the rename silently produces wrong column names.

---

### Weather forecasts (`Pred_YYYY-MM-DD.csv`)

One file per forecast run, comma-delimited, UTF-8. **Long/tall format** — one row per (time, site, measurement type) combination.

Historical files (past actuals) and future forecasts share the same schema and differ only in SFTP source folder.

| Column | Type | Description |
|---|---|---|
| `Time` | ISO 8601 datetime with TZ offset | Forecast validity timestamp (UTC) |
| `Value` | decimal | Forecasted value; the sentinel value `−99,999` signals missing or invalid data (replaced with `null` in Silver) |
| `Prediction` | int | Forecast run counter for the day (multiple runs are issued per day) |
| `Site` | string | Target weather station name (e.g. `Sion`, `Visp`) |
| `Measurement` | string | Measurement type code (see below) |
| `Unit` | string | Physical unit for the value |

Measurement type codes:

| Code | Measurement | Unit |
|---|---|---|
| `PRED_GLOB_ctrl` | Global solar irradiance | W/m² |
| `PRED_T_2M_ctrl` | Air temperature 2 m above ground | °C |
| `PRED_RELHUM_2M_ctrl` | Relative humidity 2 m above ground | % |
| `PRED_TOT_PREC_ctrl` | Total precipitation | mm |

Forecasts arrive at **3-hour granularity**. `ml_export_to_knime.py` forward-fills them onto a 15-minute grid to align with consumption and production samples.

---

## Encoding notes

### UTF-16 LE with BOM

Solar PV, consumption, temperature, and humidity files use **UTF-16 Little Endian with BOM**. Standard Spark CSV readers fail on these. `silver_transformation.py` handles them by stripping the BOM and removing null bytes: `translate(col, " ", "")`.

### Date formats

Two date formats coexist:
- `dd.MM.yy` (2-digit year) — inverter logs
- `dd.MM.yyyy` (4-digit year) — PV, consumption, temp, humidity

`silver_transformation.py` uses `regexp_extract` + `coalesce` to handle both in a single pass.

---

## Synthetic Sierre weather site

There is no physical weather station at the Sierre campus. `silver_transformation.py` synthesises a `"Sierre"` site by averaging readings from the **Sion** and **Visp** stations, which bracket Sierre geographically. The sentinel value `−99,999` is replaced with `null` before averaging so that a single missing station does not contaminate the synthetic reading.

---

## GDPR masking

Room booking files contain lecturer and user login names. `silver_transformation.py` applies **SHA-256** hashing to `Professeur` and `Nom de l'utilisateur`, storing the results as `ProfessorMasked` / `UserMasked` in the Silver layer. Raw names never reach Gold. See [[Data Privacy & GDPR]] for the full compliance statement.

---

*For how each source is transformed into Silver and Gold tables, see [[Databricks Notebooks]].*
