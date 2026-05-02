# Data Privacy & GDPR

[[Home]] > Data Privacy & GDPR

Data protection policies and technical measures for the Bellevue Data Cycle project at HES-SO.  
Source: [`docs/DATA_PRIVACY_GDPR.md`](https://github.com/sandersdHES/ADF_DataCycleProject/blob/main/docs/DATA_PRIVACY_GDPR.md)

---

## Legal Basis for Processing

Processing is grounded in the following GDPR articles:

| Article | Basis |
|---|---|
| **Art. 6(1)(e)** | Processing necessary for a task in the public interest — scientific research and academic education |
| **Art. 89** | Safeguards for processing for archiving, scientific/historical research, or statistical purposes — data not used to make decisions about individual data subjects |
| **Art. 6(1)(a)** | Explicit consent from the data source provider for use within academic evaluation |

---

## Privacy by Design

| Principle | Implementation |
|---|---|
| **Data Minimisation** | Only technical variables strictly necessary for energy calculations (kW, voltage, temperature, timestamps) are extracted and processed |
| **Purpose Limitation** | Data is used solely for solar inverter performance monitoring in an academic context — not repurposed for any other analysis |
| **Accuracy and Integrity** | Data reflects real equipment logs and has been validated to prevent misinterpretation or fabrication of performance profiles |

---

## Personal Data in the Pipeline

Room booking CSVs contain two personally identifiable fields:

| Raw field | Where it appears | Treatment |
|---|---|---|
| `Professeur` | `BellevueBooking/*.csv` | **SHA-256 hashed** by `silver_transformation.py` → stored as `ProfessorMasked` in Silver. Raw value never reaches Gold. |
| `Nom de l'utilisateur` | `BellevueBooking/*.csv` | **SHA-256 hashed** → stored as `UserMasked` in Silver. |

The hashed values are one-way — they cannot be reversed to recover the original names. This satisfies the pseudonymisation requirement while still allowing per-session correlation where needed (e.g. detecting booking patterns without identifying individuals).

**Row-Level Security** further restricts who can read booking data:
- `Technician_Role` has **no access** to `fact_room_booking` (GDPR).
- `Teacher_Role` and `Director_Role` see only bookings for their own assigned divisions.

See [[Security and User Management]] for the RLS implementation details.

---

## Data Security Measures

| Measure | Detail |
|---|---|
| **Encryption at rest** | Azure Data Lake Storage Gen2 and Azure SQL both use Microsoft-managed keys for encryption at rest |
| **Encryption in transit** | All connections use TLS — JDBC to SQL, HTTPS to Key Vault, SMB/SFTP via SHIR |
| **Access control** | Power BI access uses individual SQL contained users (no shared credentials). Azure resources protected by RBAC and Key Vault. |
| **Secrets management** | All credentials are stored in Azure Key Vault `DataCycleGroup3Keys` — never in git or config files |
| **Read-only dashboards** | SQL roles grant only `SELECT` permissions — dashboard users cannot modify source data |

---

## Data Subject Rights

In accordance with GDPR Chapter III:

| Right | Description |
|---|---|
| **Right of Access** | Any identified party may request to see what specific data is processed about them |
| **Right to Rectification** | Technical errors in the dataset can be corrected on request |
| **Right to Erasure** | Data can be withdrawn on request, provided it does not compromise the integrity of the academic evaluation |

Contact the project owner to exercise any of these rights.

---

## Data Retention and Disposal

- **Retention period:** Data is kept active for the duration of the academic semester and the subsequent grading and appeal period.
- **Secure disposal:** Upon completion of academic requirements, all connections to data sources are severed and temporary datasets are permanently deleted.

---

## Declaration of Non-Commerciality

This project:
- Has no commercial purpose.
- Does not sell, lease, or share processed data with third parties for marketing or advertising.
- Produces results solely for advancing technical knowledge in renewable energy and data science.

---

*For the technical implementation of SHA-256 masking, see the `silver_transformation.py` section in [[Databricks Notebooks]].*
