# Data Privacy & GDPR Compliance Statement

> Part of the [Solar Inverter Operations & Performance Dashboard](../README.md) project.  
> See also: [User Handbook](USER_HANDBOOK_DASHBOARD.md) · [Technical Guide](TECHNICAL_GUIDE.md) · [Wiki](https://github.com/sandersdHES/ADF_DataCycleProject/wiki)

---

## 1. Introduction and Scope

This document outlines the data protection policies and technical measures implemented within the framework of the Solar Inverter Performance Dashboard project. The processing of data in this project is conducted in strict accordance with Regulation (EU) 2016/679 of the European Parliament and of the Council (General Data Protection Regulation — GDPR).

The project is developed exclusively for academic and research purposes at HES-SO (Haute École Spécialisée de Suisse occidentale), aimed at demonstrating proficiency in data analytics, Business Intelligence (BI) architecture, and renewable energy monitoring.

---

## 2. Legal Basis for Processing

The processing of technical and operational data within this dashboard is grounded in the following GDPR articles:

- **Article 6(1)(e):** Processing is necessary for the performance of a task carried out in the public interest, specifically scientific research and academic education.
- **Article 89:** Specific safeguards and derogations regarding processing for archiving purposes in the public interest, scientific or historical research purposes, or statistical purposes, ensuring that the data is not used for taking decisions regarding specific data subjects.
- **Article 6(1)(a):** Explicit consent provided by the data source provider for the use of the dataset within the context of academic evaluation.

---

## 3. Principles of Data Processing

In the development of this dashboard, the following **Privacy by Design** principles have been applied:

| Principle | Implementation |
|---|---|
| **Data Minimization** | Only technical variables strictly necessary for energy efficiency calculations (e.g., kW, voltage, ambient temperature, timestamps) have been extracted and processed. |
| **Purpose Limitation** | The data is used solely for the monitoring of solar inverter performance in an academic context and is not repurposed for any other type of analysis. |
| **Accuracy and Integrity** | Data reflects real equipment logs and has been validated to prevent misinterpretation or the creation of false performance profiles. |

---

## 4. Anonymization and Pseudonymization Protocols

To protect the identity of data providers and asset owners, the following measures are in place:

- **PII Removal:** All Personally Identifying Information (PII), such as owner names, physical home addresses, phone numbers, and financial billing details, was completely removed prior to the data being imported into the Power BI environment.
- **Technical Identifiers:** Equipment is identified via abstract codes (e.g., `INV-01`, `INV-02`). This ensures that while performance can be monitored, it is impossible for unauthorized users to link production data to a specific geographic location or a natural person.

For the technical implementation of anonymization in the ETL pipeline, see [`databricks/notebooks/silver_transformation.py`](../databricks/notebooks/silver_transformation.py).

---

## 5. Data Security and Confidentiality

Technical and organizational measures have been implemented to protect the data against unauthorized access or accidental loss:

- **Secure Storage:** The dataset is hosted within the Microsoft Power BI Service cloud environment, which utilizes industry-standard encryption for data at rest and in transit.
- **Access Control:** Access to the dashboard is restricted via Multi-Factor Authentication (MFA) and is limited to the project developer and the academic evaluation board.
- **System Integrity:** The architecture of the dashboard prevents the modification of source data, ensuring that the original records remain intact and untampered with.

---

## 6. Data Subject Rights

In accordance with Chapter III of the GDPR, any party identifiable through these datasets (despite anonymization) maintains the following rights:

| Right | Description |
|---|---|
| **Right of Access** | The ability to see what specific data is being processed. |
| **Right to Rectification** | The correction of any technical errors found within the dataset. |
| **Right to Erasure** ("Right to be Forgotten") | The withdrawal of data from the project upon request, provided it does not compromise the integrity of the academic evaluation. |

---

## 7. Data Retention and Disposal Policy

Data used in this project will not be stored indefinitely:

- **Retention Period:** Data will be kept active only for the duration of the academic semester and the subsequent grading and appeal period.
- **Secure Disposal:** Upon completion of the academic requirements, all connections to data sources will be severed, and temporary datasets will be permanently deleted to prevent any unauthorized future use.

---

## 8. Declaration of Non-Commerciality

The project developer declares that:

- This project has no commercial purpose.
- No part of the processed data will be sold, leased, or shared with third parties for marketing or advertising purposes.
- The results of the analysis are intended solely for the advancement of technical knowledge in the field of renewable energy and data science.

---

## 9. Ethical Conclusion

By implementing these measures, the project demonstrates not only technical competence but also legal and ethical responsibility. Full compliance with the GDPR ensures a balance between digital innovation and the fundamental right to privacy.
