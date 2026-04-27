"""Topic 8 — Machine Learning.

KNIME workflow internals are NOT in this repo (they live on the KNIME Server).
What we DO have access to and document here:
  - the two ML stories US#29 / US#30 and their targets
  - feature sets engineered in ml_export_to_knime.py
  - model type & hyperparameters from config/ml_models_config.json
  - the orchestration flow (ADF Run_Knime → KNIME REST → ml_load_predictions)
  - idempotency strategy and accuracy tracking (sp_backfill + vw_prediction_accuracy)

Slide 8c is a placeholder for the KNIME node graph — fill from KNIME Hub later.
"""
from pptx.util import Inches
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

import _pptx_helpers as h


def overview(prs):
    s = h.blank(prs)
    h.header_band(s, "8.  Machine Learning — overview",
                  "Two daily forecasts: solar production & building consumption",
                  color=h.ML_PURPLE)

    # 2 model cards
    def model_card(left, code, name, target, features, story):
        h.rounded_card(s, left=left, top=Inches(1.25),
                       width=Inches(6.30), height=Inches(5.60),
                       fill=h.ML_FILL, line=h.ML_PURPLE)
        # header
        h.rounded_card(s, left=left + Inches(0.20), top=Inches(1.40),
                       width=Inches(1.35), height=Inches(0.40),
                       fill=h.ML_PURPLE)
        h.add_text(s, code, left=left + Inches(0.20), top=Inches(1.40),
                   width=Inches(1.35), height=Inches(0.40),
                   size=12, bold=True, color=h.WHITE,
                   align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        h.add_text(s, story, left=left + Inches(1.65), top=Inches(1.40),
                   width=Inches(4.50), height=Inches(0.40),
                   size=12, bold=True, color=h.ML_PURPLE,
                   anchor=MSO_ANCHOR.MIDDLE)
        # name
        h.add_text(s, name, left=left + Inches(0.20), top=Inches(1.95),
                   width=Inches(6.0), height=Inches(0.40),
                   size=16, bold=True, color=h.NAVY)
        # target
        h.add_text(s, "Target",
                   left=left + Inches(0.20), top=Inches(2.45),
                   width=Inches(6.0), height=Inches(0.30),
                   size=11, bold=True, color=h.GREY)
        h.add_text(s, target,
                   left=left + Inches(0.20), top=Inches(2.70),
                   width=Inches(6.0), height=Inches(0.30),
                   size=12, color=h.DARK)
        # features
        h.add_text(s, "Features",
                   left=left + Inches(0.20), top=Inches(3.10),
                   width=Inches(6.0), height=Inches(0.30),
                   size=11, bold=True, color=h.GREY)
        h.add_text(s, features,
                   left=left + Inches(0.20), top=Inches(3.35),
                   width=Inches(6.0), height=Inches(1.50),
                   size=11, color=h.DARK)
        # algo
        h.add_text(s, "Algorithm & hyperparameters",
                   left=left + Inches(0.20), top=Inches(5.05),
                   width=Inches(6.0), height=Inches(0.30),
                   size=11, bold=True, color=h.GREY)
        h.add_text(s,
                   "Gradient Boosted Trees Regressor\n"
                   "100 trees  ·  learning rate 0.1  ·  max depth 5\n"
                   "Trained 2023-02-20 → 2023-04-19  ·  KNIME Analytics Platform",
                   left=left + Inches(0.20), top=Inches(5.35),
                   width=Inches(6.0), height=Inches(1.30),
                   size=11, color=h.DARK)

    model_card(Inches(0.30), "PV_PROD_V1",
               "Solar Production Prediction v1",
               "production_delta_kwh",
               "irradiance_wm2,  temp_c,  hour, minute, month, day_of_week, "
               "is_weekend, quarter_hour",
               "User Story 29")

    model_card(Inches(6.75), "CONS_V1",
               "Building Consumption Prediction v1",
               "consumption_delta_kwh",
               "temp_c, humidity_pct, precipitation_kgm2, "
               "room_occupation_pct, hour, minute, month, day_of_week, "
               "is_weekend, is_academic_day, quarter_hour",
               "User Story 30")

    h.footer(s)


def lifecycle(prs):
    s = h.blank(prs)
    h.header_band(s, "8.  Machine Learning — lifecycle & integration",
                  "ml_export_to_knime → KNIME Server → ml_load_predictions",
                  color=h.ML_PURPLE)

    # horizontal flow
    steps = [
        ("Databricks", "ml_export_to_knime.py",
         "Read Silver  ·  feature engineering\n3 h → 15 min weather forward-fill\nroom_occupation_pct via slot explode\nWrites two CSVs to mldata/knime_input/", h.RED),
        ("ADLS Gen2", "mldata / knime_input",
         "solar_production_features.csv\nconsumption_features.csv\n(coalesce 1, UTF-8, header)", h.NAVY),
        ("KNIME Server", "REST deployments",
         "Data_Preparation (every run)\nModel_Selection (Mondays)\nSolar  ‖  Consumption predictors", h.ML_PURPLE),
        ("ADLS Gen2", "mldata / knime_output",
         "production_predictions.csv\nconsumption_predictions.csv", h.NAVY),
        ("Databricks", "ml_load_predictions.py",
         "Resolve ModelKey from dim_prediction_model\nClamp negative preds to 0\nDELETE→INSERT per run date\nWrites back ml_models_config.json", h.RED),
        ("Azure SQL", "fact_energy_prediction",
         "+ EXEC sp_backfill_prediction_actuals\nfeeds vw_prediction_accuracy (MAPE)", h.GOLD),
    ]
    box_w = Inches(2.05)
    box_h = Inches(2.85)
    gap = Inches(0.05)
    total = box_w * len(steps) + gap * (len(steps) - 1)
    sx = (h.SLIDE_W - total) / 2
    by = Inches(1.40)
    for i, (host, name, body, color) in enumerate(steps):
        x = sx + (box_w + gap) * i
        h.rounded_card(s, left=x, top=by, width=box_w, height=box_h,
                       fill=h.WHITE, line=color)
        # host strip
        h.rounded_card(s, left=x, top=by, width=box_w, height=Inches(0.35),
                       fill=color)
        h.add_text(s, host, left=x, top=by, width=box_w, height=Inches(0.35),
                   size=10, bold=True, color=h.WHITE,
                   align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        # name + body
        h.add_text(s, name, left=x + Inches(0.10), top=by + Inches(0.45),
                   width=box_w - Inches(0.20), height=Inches(0.45),
                   size=11, bold=True, color=h.DARK,
                   align=PP_ALIGN.CENTER)
        h.add_text(s, body, left=x + Inches(0.10), top=by + Inches(0.95),
                   width=box_w - Inches(0.20), height=box_h - Inches(1.05),
                   size=9, color=h.GREY, align=PP_ALIGN.CENTER)
        if i < len(steps) - 1:
            h.arrow(s, left=x + box_w - Inches(0.02),
                    top=by + Inches(1.20), width=gap + Inches(0.07),
                    height=Inches(0.20), color=h.GREY)

    # bottom row: idempotency / cadence / monitoring
    cards = [
        ("Idempotency",
         "DELETE FROM fact_energy_prediction WHERE PredictionRunDateKey = <today> "
         "before INSERT — full replace per run date.",
         h.NAVY, h.LIGHT_BLUE),
        ("Cadence",
         "TRG_Daily_0930 fires PL_Upload_Pred_Gold every day. Model_Selection re-evaluates "
         "the active model on Mondays only (pipeline().TriggerTime.DayOfWeek).",
         h.ML_PURPLE, h.ML_FILL),
        ("Accuracy tracking",
         "sp_backfill_prediction_actuals joins yesterday's actuals onto earlier predictions; "
         "vw_prediction_accuracy exposes MAPE for BI.",
         h.GOLD, h.GOLD_FILL),
    ]
    cy = Inches(4.55)
    cx = Inches(0.30)
    cw = (h.SLIDE_W - Inches(0.6) - Inches(0.4)) / 3
    for title, body, accent, fill in cards:
        h.rounded_card(s, left=cx, top=cy, width=cw, height=Inches(2.10),
                       fill=fill, line=accent)
        h.add_text(s, title, left=cx + Inches(0.18), top=cy + Inches(0.10),
                   width=cw - Inches(0.36), height=Inches(0.35),
                   size=14, bold=True, color=accent)
        h.add_text(s, body, left=cx + Inches(0.18), top=cy + Inches(0.55),
                   width=cw - Inches(0.36), height=Inches(1.45),
                   size=11, color=h.DARK)
        cx += cw + Inches(0.20)

    h.footer(s)


def knime_internals(prs):
    """Placeholder — KNIME .knwf workflows are NOT in this repo."""
    s = h.blank(prs)
    h.header_band(s, "8.  Machine Learning — KNIME workflow internals",
                  "Placeholder — fill from KNIME Hub before delivery",
                  color=h.ML_PURPLE)

    # warning ribbon
    h.rounded_card(s, left=Inches(0.30), top=Inches(1.25),
                   width=Inches(12.70), height=Inches(0.85),
                   fill=h.GOLD_FILL, line=h.ORANGE)
    h.add_text(s, "ℹ  KNIME workflows live on the server — not in the Git repo.",
               left=Inches(0.50), top=Inches(1.30),
               width=Inches(12.4), height=Inches(0.35),
               size=14, bold=True, color=h.ORANGE)
    h.add_text(s,
               "We have the model metadata (hyperparameters, features, training window) "
               "and the integration flow, but the node graph itself sits inside KNIME deployments. "
               "Replace this slide with screenshots / node descriptions exported from KNIME.",
               left=Inches(0.50), top=Inches(1.65),
               width=Inches(12.4), height=Inches(0.45),
               size=11, color=h.DARK)

    # what's known: REST deployments table
    h.add_text(s, "REST deployments invoked by ADF (Run_Knime pipeline)",
               left=Inches(0.5), top=Inches(2.40),
               width=Inches(12), height=Inches(0.4),
               size=15, bold=True, color=h.NAVY)

    rows = [
        ("Step",                  "Cadence",          "KNIME deployment"),
        ("Data_Preparation",      "Every run",        "rest:e481f0fd-89ba-409a-aaa2-d8a648956949"),
        ("Model_Selection",       "Mondays only",     "rest:509f9c76-1fd3-444d-80a6-4df7848b1621"),
        ("Consumption predictor", "Every run · ‖",    "rest:348633fa-f10f-4a27-99de-11e1707190cb"),
        ("Solar predictor",       "Every run · ‖",    "rest:eb96aa91-239b-4cf2-8c7e-a8a40516d4f3"),
    ]
    ty = Inches(2.90)
    col_left = [Inches(0.5), Inches(4.0), Inches(6.5)]
    col_w =    [Inches(3.4), Inches(2.4), Inches(6.4)]
    for ri, row in enumerate(rows):
        is_head = ri == 0
        for ci in range(3):
            cell = h.rounded_card(s, left=col_left[ci], top=ty,
                                  width=col_w[ci], height=Inches(0.45),
                                  fill=(h.NAVY if is_head else (h.LIGHT_GREY if ri % 2 else h.WHITE)),
                                  line=h.NAVY)
            h.add_text(s, row[ci], left=col_left[ci] + Inches(0.15),
                       top=ty, width=col_w[ci] - Inches(0.30), height=Inches(0.45),
                       size=11, bold=is_head,
                       color=(h.WHITE if is_head else h.DARK),
                       anchor=MSO_ANCHOR.MIDDLE)
        ty += Inches(0.50)

    # what to add later
    h.add_text(s, "What to drop on this slide before delivery",
               left=Inches(0.5), top=Inches(5.55),
               width=Inches(12), height=Inches(0.4),
               size=15, bold=True, color=h.NAVY)
    h.add_bullets(s, [
        "Screenshot of each KNIME workflow (Data_Preparation, Model_Selection, Solar, Consumption).",
        "Per-node summary: CSV reader → joins / time features → GBT learner → predictor → CSV writer.",
        "Cross-validation / split strategy used during training.",
        "Holdout MAPE figures to compare to vw_prediction_accuracy in production.",
    ], left=Inches(0.5), top=Inches(5.95),
       width=Inches(12), height=Inches(1.10), size=12)

    h.footer(s)


if __name__ == "__main__":
    prs = h.open_or_create()
    overview(prs)
    lifecycle(prs)
    knime_internals(prs)
    h.save(prs)
    print("ok — ML slides appended")
