"""Topic 4 — Architecture.

Two slides:
  4a — components diagram (sources → SHIR → ADF → Bronze/Silver/Gold → ML/SAC/PBI)
  4b — technology stack & cross-cutting concerns
"""
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

import _pptx_helpers as h


def _layer_box(slide, *, left, top, width, height, label, fill, accent):
    h.rounded_card(slide, left=left, top=top, width=width, height=height,
                   fill=fill, line=accent)
    h.add_text(slide, label, left=left, top=top, width=width, height=Inches(0.45),
               size=14, bold=True, color=accent,
               align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


def architecture_components(prs):
    s = h.blank(prs)
    h.header_band(s, "4.  Architecture",
                  "Medallion lakehouse on Azure  ·  on-prem sources → analytics-ready data")

    # ---------- ON-PREM SOURCES (left column) ----------
    src_left = Inches(0.30)
    src_top = Inches(1.40)
    src_w = Inches(2.40)

    h.add_text(s, "ON-PREMISES",
               left=src_left, top=src_top - Inches(0.30),
               width=src_w, height=Inches(0.30),
               size=11, bold=True, color=h.BLUE, align=PP_ALIGN.CENTER)

    sources = [
        ("SMB · Bookings",       "Room reservations (TSV)"),
        ("SMB · Conso",          "Energy / temp / humidity (UTF-16)"),
        ("SMB · Solarlogs",      "Sungrow inverter CSVs"),
        ("SFTP · Weather",       "Past + 3 h forecast"),
    ]
    box_h = Inches(0.85)
    gap = Inches(0.12)
    for i, (title, sub) in enumerate(sources):
        y = src_top + (box_h + gap) * i
        h.rounded_card(s, left=src_left, top=y, width=src_w, height=box_h,
                       fill=h.LIGHT_BLUE, line=h.BLUE)
        h.add_text(s, title, left=src_left + Inches(0.10), top=y + Inches(0.08),
                   width=src_w - Inches(0.20), height=Inches(0.32),
                   size=12, bold=True, color=h.NAVY)
        h.add_text(s, sub, left=src_left + Inches(0.10), top=y + Inches(0.40),
                   width=src_w - Inches(0.20), height=Inches(0.40),
                   size=10, color=h.GREY)

    # SHIR gateway
    shir_top = src_top + (box_h + gap) * 4 + Inches(0.10)
    h.rounded_card(s, left=src_left, top=shir_top, width=src_w, height=Inches(0.55),
                   fill=h.GOLD_FILL, line=h.ORANGE)
    h.add_text(s, "Self-Hosted IR (Win VM)",
               left=src_left, top=shir_top, width=src_w, height=Inches(0.55),
               size=11, bold=True, color=h.ORANGE,
               align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    # arrow → ADF
    h.arrow(s, left=src_left + src_w + Inches(0.05),
            top=src_top + Inches(2.0), width=Inches(0.55),
            color=h.GREY)

    # ---------- ADF orchestration ----------
    adf_left = src_left + src_w + Inches(0.65)
    adf_w = Inches(2.45)
    h.rounded_card(s, left=adf_left, top=src_top, width=adf_w, height=Inches(5.30),
                   fill=h.LIGHT_BLUE, line=h.BLUE)
    h.add_text(s, "Azure Data Factory",
               left=adf_left, top=src_top + Inches(0.08),
               width=adf_w, height=Inches(0.35),
               size=13, bold=True, color=h.NAVY, align=PP_ALIGN.CENTER)
    h.add_text(s, "group3-df  ·  9 pipelines  ·  2 daily triggers",
               left=adf_left, top=src_top + Inches(0.42),
               width=adf_w, height=Inches(0.30),
               size=10, color=h.GREY, align=PP_ALIGN.CENTER)

    pipelines = [
        ("PL_Ingest_Bronze", "Master orchestrator (07:15)"),
        ("PL_Bronze_Solar",       "Inverter CSVs"),
        ("PL_Bronze_Bookings",    "Room reservations"),
        ("PL_Bronze_Meteo",       "SFTP weather"),
        ("PL_Bronze_Conso",       "Power / temp / humidity"),
        ("PL_SAC_Export",         "Gold → file share"),
        ("PL_Upload_Pred_Gold",   "KNIME (09:30)"),
    ]
    py = src_top + Inches(0.85)
    for name, sub in pipelines:
        h.rounded_card(s, left=adf_left + Inches(0.12), top=py,
                       width=adf_w - Inches(0.24), height=Inches(0.55),
                       fill=h.WHITE, line=h.BLUE)
        h.add_text(s, name, left=adf_left + Inches(0.18), top=py + Inches(0.04),
                   width=adf_w - Inches(0.36), height=Inches(0.25),
                   size=10, bold=True, color=h.NAVY)
        h.add_text(s, sub, left=adf_left + Inches(0.18), top=py + Inches(0.28),
                   width=adf_w - Inches(0.36), height=Inches(0.25),
                   size=9, color=h.GREY)
        py += Inches(0.62)

    # arrow → medallion
    h.arrow(s, left=adf_left + adf_w + Inches(0.05),
            top=src_top + Inches(2.0), width=Inches(0.45))

    # ---------- Medallion stack ----------
    med_left = adf_left + adf_w + Inches(0.55)
    med_w = Inches(2.40)
    layer_h = Inches(1.55)
    gap_l = Inches(0.10)

    # Bronze
    _layer_box(s, left=med_left, top=src_top, width=med_w, height=layer_h,
               label="🥉  BRONZE  ·  ADLS Gen2", fill=h.BRONZE_FILL, accent=h.BRONZE)
    h.add_text(s, "Raw CSV (UTF-8 / UTF-16)\nbinary copy, watermarked\ncontainer  bronze/",
               left=med_left + Inches(0.15), top=src_top + Inches(0.45),
               width=med_w - Inches(0.30), height=layer_h - Inches(0.50),
               size=10, color=h.DARK, align=PP_ALIGN.CENTER)
    # Silver
    _layer_box(s, left=med_left, top=src_top + layer_h + gap_l,
               width=med_w, height=layer_h,
               label="🥈  SILVER  ·  ADLS Gen2", fill=h.SILVER_FILL, accent=h.SILVER)
    h.add_text(s, "Parquet · cleaned · typed\nUTF-16 cleanup, GDPR\ndedup, Sierre synthesis",
               left=med_left + Inches(0.15),
               top=src_top + layer_h + gap_l + Inches(0.45),
               width=med_w - Inches(0.30), height=layer_h - Inches(0.50),
               size=10, color=h.DARK, align=PP_ALIGN.CENTER)
    # Gold
    _layer_box(s, left=med_left, top=src_top + (layer_h + gap_l) * 2,
               width=med_w, height=layer_h + Inches(0.30),
               label="🥇  GOLD  ·  Azure SQL", fill=h.GOLD_FILL, accent=h.GOLD)
    h.add_text(s, "Star schema  ·  DevDB\n8 dims  ·  7 facts  ·  7 views\nserverless Gen5",
               left=med_left + Inches(0.15),
               top=src_top + (layer_h + gap_l) * 2 + Inches(0.45),
               width=med_w - Inches(0.30), height=layer_h - Inches(0.30),
               size=10, color=h.DARK, align=PP_ALIGN.CENTER)

    # arrow → consumption
    h.arrow(s, left=med_left + med_w + Inches(0.05),
            top=src_top + Inches(2.0), width=Inches(0.45))

    # ---------- Consumption ----------
    out_left = med_left + med_w + Inches(0.55)
    out_w = Inches(2.55)

    # Databricks badge
    h.rounded_card(s, left=out_left, top=src_top, width=out_w, height=Inches(0.55),
                   fill=h.WHITE, line=h.RED)
    h.add_text(s, "🔴 Databricks · 6 PySpark notebooks",
               left=out_left, top=src_top, width=out_w, height=Inches(0.55),
               size=11, bold=True, color=h.RED,
               align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    # KNIME
    h.rounded_card(s, left=out_left, top=src_top + Inches(0.70),
                   width=out_w, height=Inches(1.30),
                   fill=h.ML_FILL, line=h.ML_PURPLE)
    h.add_text(s, "🤖  KNIME Server",
               left=out_left, top=src_top + Inches(0.75),
               width=out_w, height=Inches(0.35),
               size=12, bold=True, color=h.ML_PURPLE, align=PP_ALIGN.CENTER)
    h.add_text(s, "GBT regressors\nSolar  ·  Consumption\nREST  ·  09:30 daily",
               left=out_left + Inches(0.10), top=src_top + Inches(1.10),
               width=out_w - Inches(0.20), height=Inches(0.85),
               size=10, color=h.DARK, align=PP_ALIGN.CENTER)

    # SAC
    h.rounded_card(s, left=out_left, top=src_top + Inches(2.15),
                   width=out_w, height=Inches(1.30),
                   fill=h.SERVE_FILL, line=h.SERVE_GREEN)
    h.add_text(s, "🟢  SAP Analytics Cloud",
               left=out_left, top=src_top + Inches(2.20),
               width=out_w, height=Inches(0.35),
               size=12, bold=True, color=h.SERVE_GREEN, align=PP_ALIGN.CENTER)
    h.add_text(s, "Gold view CSV →\nFile Share → SAC import\n(inverter combined)",
               left=out_left + Inches(0.10), top=src_top + Inches(2.55),
               width=out_w - Inches(0.20), height=Inches(0.85),
               size=10, color=h.DARK, align=PP_ALIGN.CENTER)

    # Power BI
    h.rounded_card(s, left=out_left, top=src_top + Inches(3.60),
                   width=out_w, height=Inches(1.40),
                   fill=h.GOLD_FILL, line=h.GOLD)
    h.add_text(s, "🟡  Power BI",
               left=out_left, top=src_top + Inches(3.65),
               width=out_w, height=Inches(0.35),
               size=12, bold=True, color=h.ORANGE, align=PP_ALIGN.CENTER)
    h.add_text(s, "Direct Query on Gold\n3 reports / templates\nRLS-aware",
               left=out_left + Inches(0.10), top=src_top + Inches(4.00),
               width=out_w - Inches(0.20), height=Inches(1.00),
               size=10, color=h.DARK, align=PP_ALIGN.CENTER)

    # legend / footer
    h.footer(s)


def architecture_stack(prs):
    s = h.blank(prs)
    h.header_band(s, "4.  Architecture — technology stack",
                  "What runs where, and how it's secured")

    # 4 column groups: Orchestration / Compute / Storage & Serving / Cross-cutting
    col_w = Inches(3.05)
    gap = Inches(0.15)
    top = Inches(1.30)

    columns = [
        ("Orchestration", h.BLUE, h.LIGHT_BLUE, [
            ("Azure Data Factory", "group3-df  ·  9 pipelines  ·  19 datasets  ·  10 linked services"),
            ("Triggers", "TRG_Daily_0715  ·  TRG_Daily_0930"),
            ("Self-Hosted IR", "Windows VM 10.130.25.152 — bridges SMB & SFTP"),
        ]),
        ("Compute & ML", h.RED, RGBColor_safe(h.RED, 0xFFEBEE), [
            ("Azure Databricks", "6 PySpark notebooks · single interactive cluster · JDBC w/ retry-backoff"),
            ("KNIME Server", "Gradient Boosted Trees · 100 trees · lr 0.1 · max_depth 5"),
            ("REST endpoints", "Data_Preparation · Model_Selection (Mon) · Solar · Consumption"),
        ]),
        ("Storage & Serving", h.GOLD, h.GOLD_FILL, [
            ("ADLS Gen2 — adlsbellevuegrp3", "containers: bronze · silver · mldata · sacexport · config"),
            ("Azure SQL — DevDB", "Serverless Gen5  ·  8 dims  ·  7 facts  ·  7 analytical views"),
            ("Azure File Share", "sac-export-share — SAC ingestion drop"),
            ("Power BI", "3 reports/templates · RLS-aware"),
        ]),
        ("Security · Ops · CI/CD", h.SERVE_GREEN, h.SERVE_FILL, [
            ("Azure Key Vault", "DataCycleGroup3Keys — SQL · DBX PAT · KNIME · SHIR · SAC"),
            ("UAMI + OIDC", "gh-datacycle-oidc — GitHub Actions, no client secrets"),
            ("RBAC + RLS", "Director_Role · Technician_Role · BookingDivisionFilter (GDPR)"),
            ("Alerts", "Action Group ar-pl-ingest-bronze-failed (1 h SLA)"),
            ("CI/CD", "validate.yml (PR) · deploy-adf.yml (push to main)"),
            ("IaC (future)", "Bicep + workflows ready, unwired"),
        ]),
    ]

    left = Inches(0.25)
    for name, accent, fill, rows in columns:
        # column header
        h.rounded_card(s, left=left, top=top, width=col_w, height=Inches(0.55),
                       fill=accent, line=accent)
        h.add_text(s, name, left=left, top=top, width=col_w, height=Inches(0.55),
                   size=14, bold=True, color=h.WHITE,
                   align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        # column body
        body_top = top + Inches(0.65)
        body_h = Inches(5.40)
        h.rounded_card(s, left=left, top=body_top, width=col_w, height=body_h,
                       fill=fill, line=accent)
        ry = body_top + Inches(0.10)
        for r_title, r_body in rows:
            h.add_text(s, r_title, left=left + Inches(0.15), top=ry,
                       width=col_w - Inches(0.30), height=Inches(0.30),
                       size=12, bold=True, color=accent)
            h.add_text(s, r_body, left=left + Inches(0.15), top=ry + Inches(0.28),
                       width=col_w - Inches(0.30), height=Inches(0.70),
                       size=10, color=h.DARK)
            ry += Inches(0.95)
        left += col_w + gap

    h.footer(s)


# small helper used above to avoid recreating RGBColor literals already in helpers
def RGBColor_safe(_unused, hex_int):
    from pptx.dml.color import RGBColor
    return RGBColor((hex_int >> 16) & 0xFF, (hex_int >> 8) & 0xFF, hex_int & 0xFF)


if __name__ == "__main__":
    prs = h.open_or_create()
    architecture_components(prs)
    architecture_stack(prs)
    h.save(prs)
    print("ok — architecture slides appended")
