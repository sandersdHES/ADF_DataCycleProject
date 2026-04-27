"""Topic 5 — Data Flow.

Two slides:
  5a — daily timeline of the two triggers
  5b — bronze ingestion pattern (incremental copy)
"""
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

import _pptx_helpers as h


def timeline(prs):
    s = h.blank(prs)
    h.header_band(s, "5.  Data Flow — daily orchestration",
                  "Two ADF triggers drive the entire cycle  ·  fully deterministic")

    # Trigger 1 — refresh
    h.rounded_card(s, left=Inches(0.30), top=Inches(1.20),
                   width=Inches(12.6), height=Inches(2.55),
                   fill=h.LIGHT_BLUE, line=h.BLUE)
    h.add_text(s, "TRG_Daily_0715  ·  Refresh",
               left=Inches(0.50), top=Inches(1.30),
               width=Inches(12.0), height=Inches(0.35),
               size=15, bold=True, color=h.NAVY)
    h.add_text(s, "Master pipeline PL_Ingest_Bronze, then Databricks ETL, then SAC export",
               left=Inches(0.50), top=Inches(1.65),
               width=Inches(12.0), height=Inches(0.30),
               size=10, color=h.GREY)

    steps_1 = [
        ("07:15", "PL_Ingest_Bronze", "4 parallel sub-pipelines\n(Solar · Bookings · Meteo · Conso)", h.BLUE),
        ("07:45", "silver_transformation", "Bronze → Silver (Parquet)\nUTF-16, GDPR, dedup", h.SILVER),
        ("08:15", "silver_gold_dimensions  ‖  ml_export_to_knime", "Dim MERGE  ·  ML CSV export\n(parallel)", h.GOLD),
        ("08:35", "silver_gold_facts", "Watermark incremental load\n7 fact tables", h.GOLD),
        ("09:05", "PL_SAC_Export", "Coalesced CSV → File Share\n→ SAC import", h.SERVE_GREEN),
    ]
    box_w = Inches(2.40)
    box_h = Inches(1.50)
    gap = Inches(0.10)
    total = box_w * len(steps_1) + gap * (len(steps_1) - 1)
    sx = (h.SLIDE_W - total) / 2
    by = Inches(2.05)
    for i, (t, name, body, color) in enumerate(steps_1):
        x = sx + (box_w + gap) * i
        h.rounded_card(s, left=x, top=by, width=box_w, height=box_h,
                       fill=h.WHITE, line=color)
        # time chip
        h.rounded_card(s, left=x + Inches(0.10), top=by + Inches(0.08),
                       width=Inches(0.85), height=Inches(0.30), fill=color)
        h.add_text(s, t, left=x + Inches(0.10), top=by + Inches(0.08),
                   width=Inches(0.85), height=Inches(0.30),
                   size=10, bold=True, color=h.WHITE,
                   align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        h.add_text(s, name,
                   left=x + Inches(0.10), top=by + Inches(0.45),
                   width=box_w - Inches(0.20), height=Inches(0.40),
                   size=11, bold=True, color=h.DARK)
        h.add_text(s, body,
                   left=x + Inches(0.10), top=by + Inches(0.85),
                   width=box_w - Inches(0.20), height=Inches(0.60),
                   size=9, color=h.GREY)
        if i < len(steps_1) - 1:
            h.arrow(s, left=x + box_w - Inches(0.05),
                    top=by + Inches(0.65), width=gap + Inches(0.10),
                    height=Inches(0.20), color=h.GREY)

    # Trigger 2 — ML
    h.rounded_card(s, left=Inches(0.30), top=Inches(3.95),
                   width=Inches(12.6), height=Inches(2.85),
                   fill=h.ML_FILL, line=h.ML_PURPLE)
    h.add_text(s, "TRG_Daily_0930  ·  ML Inference",
               left=Inches(0.50), top=Inches(4.05),
               width=Inches(12.0), height=Inches(0.35),
               size=15, bold=True, color=h.ML_PURPLE)
    h.add_text(s, "PL_Upload_Pred_Gold — KNIME REST + ml_load_predictions",
               left=Inches(0.50), top=Inches(4.40),
               width=Inches(12.0), height=Inches(0.30),
               size=10, color=h.GREY)

    steps_2 = [
        ("09:30", "Data_Preparation", "KNIME REST · always", h.ML_PURPLE),
        ("09:35", "Model_Selection", "KNIME REST · Mondays only\n(re-evaluate active model)", h.ML_PURPLE),
        ("09:45", "Solar  ‖  Consumption predictors", "Two GBT regressors\nrun in parallel", h.ML_PURPLE),
        ("10:00", "ml_load_predictions", "Idempotent DELETE→INSERT\nfact_energy_prediction", h.ML_PURPLE),
        ("10:10", "sp_backfill_prediction_actuals", "Joins yesterday's actuals\n→ vw_prediction_accuracy", h.NAVY),
    ]
    by2 = Inches(4.85)
    for i, (t, name, body, color) in enumerate(steps_2):
        x = sx + (box_w + gap) * i
        h.rounded_card(s, left=x, top=by2, width=box_w, height=box_h,
                       fill=h.WHITE, line=color)
        h.rounded_card(s, left=x + Inches(0.10), top=by2 + Inches(0.08),
                       width=Inches(0.85), height=Inches(0.30), fill=color)
        h.add_text(s, t, left=x + Inches(0.10), top=by2 + Inches(0.08),
                   width=Inches(0.85), height=Inches(0.30),
                   size=10, bold=True, color=h.WHITE,
                   align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        h.add_text(s, name,
                   left=x + Inches(0.10), top=by2 + Inches(0.45),
                   width=box_w - Inches(0.20), height=Inches(0.40),
                   size=11, bold=True, color=h.DARK)
        h.add_text(s, body,
                   left=x + Inches(0.10), top=by2 + Inches(0.85),
                   width=box_w - Inches(0.20), height=Inches(0.60),
                   size=9, color=h.GREY)
        if i < len(steps_2) - 1:
            h.arrow(s, left=x + box_w - Inches(0.05),
                    top=by2 + Inches(0.65), width=gap + Inches(0.10),
                    height=Inches(0.20), color=h.GREY)

    h.footer(s)


def bronze_pattern(prs):
    s = h.blank(prs)
    h.header_band(s, "5.  Data Flow — Bronze ingestion pattern",
                  "PL_Bronze_*  ·  incremental binary copy via Self-Hosted IR")

    # Left — pattern explanation
    h.add_text(s, "Common shape — 4 sub-pipelines",
               left=Inches(0.5), top=Inches(1.25), width=Inches(6), height=Inches(0.4),
               size=18, bold=True, color=h.NAVY)

    steps = [
        ("1", "GetMetadata · source", "List files on the SMB / SFTP share"),
        ("2", "GetMetadata · destination", "List files already in bronze/"),
        ("3", "Filter", "Keep filenames not yet ingested"),
        ("4", "ForEach (batch 50)", "Binary Copy → bronze/<area>/"),
    ]
    sy = Inches(1.80)
    for n, title, body in steps:
        badge = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.5), sy, Inches(0.55), Inches(0.55))
        badge.fill.solid(); badge.fill.fore_color.rgb = h.BRONZE; badge.line.fill.background()
        h.add_text(s, n, left=Inches(0.5), top=sy, width=Inches(0.55), height=Inches(0.55),
                   size=14, bold=True, color=h.WHITE,
                   align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        h.add_text(s, title, left=Inches(1.20), top=sy - Inches(0.02),
                   width=Inches(5.4), height=Inches(0.32),
                   size=14, bold=True, color=h.DARK)
        h.add_text(s, body, left=Inches(1.20), top=sy + Inches(0.27),
                   width=Inches(5.4), height=Inches(0.32),
                   size=11, color=h.GREY)
        sy += Inches(0.85)

    # Right — sub-pipelines + special cases
    h.add_text(s, "Sub-pipelines",
               left=Inches(7.0), top=Inches(1.25), width=Inches(6), height=Inches(0.4),
               size=18, bold=True, color=h.NAVY)

    pipes = [
        ("PL_Bronze_Solar",   "Sungrow inverter CSVs (UTF-8) + PV daily rollups (UTF-16 LE)"),
        ("PL_Bronze_Conso",   "Energy / temperature / humidity. Dynamic folder routing by filename prefix."),
        ("PL_Bronze_Bookings","Room reservations (TSV). French dates parsed in Silver."),
        ("PL_Bronze_Meteo",   "Past weather via SFTP."),
    ]
    py = Inches(1.80)
    for name, body in pipes:
        h.rounded_card(s, left=Inches(7.0), top=py, width=Inches(5.85), height=Inches(0.85),
                       fill=h.LIGHT_BLUE, line=h.BLUE)
        h.add_text(s, name, left=Inches(7.15), top=py + Inches(0.08),
                   width=Inches(5.55), height=Inches(0.30),
                   size=12, bold=True, color=h.NAVY)
        h.add_text(s, body, left=Inches(7.15), top=py + Inches(0.36),
                   width=Inches(5.55), height=Inches(0.45),
                   size=10, color=h.DARK)
        py += Inches(0.95)

    # callout — orphan pipeline
    h.rounded_card(s, left=Inches(7.0), top=Inches(5.65), width=Inches(5.85),
                   height=Inches(1.20), fill=h.GOLD_FILL, line=h.ORANGE)
    h.add_text(s, "⚠  Known limitation",
               left=Inches(7.15), top=Inches(5.72),
               width=Inches(5.55), height=Inches(0.30),
               size=12, bold=True, color=h.ORANGE)
    h.add_text(s,
               "PL_Bronze_MeteoFuture exists but is not wired into PL_Ingest_Bronze.\n"
               "Future-forecast files are still consumed from whatever already sits in bronze.",
               left=Inches(7.15), top=Inches(6.00),
               width=Inches(5.55), height=Inches(0.85),
               size=10, color=h.DARK)

    h.footer(s)


if __name__ == "__main__":
    prs = h.open_or_create()
    timeline(prs)
    bronze_pattern(prs)
    h.save(prs)
    print("ok — data flow slides appended")
