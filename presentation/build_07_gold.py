"""Topic 7 — Gold Transformation.

Two slides:
  7a — dimensions notebook + facts notebook (responsibilities, idempotency)
  7b — gold star schema overview (8 dims, 7 facts, 7 views)
"""
from pptx.util import Inches
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

import _pptx_helpers as h


def gold_notebooks(prs):
    s = h.blank(prs)
    h.header_band(s, "7.  Gold Transformation — notebooks",
                  "Silver Parquet → Azure SQL DevDB  ·  serverless Gen5",
                  color=h.GOLD)

    # left card — dimensions
    h.rounded_card(s, left=Inches(0.30), top=Inches(1.25),
                   width=Inches(6.30), height=Inches(5.65),
                   fill=h.GOLD_FILL, line=h.GOLD)
    h.add_text(s, "silver_gold_dimensions.py",
               left=Inches(0.50), top=Inches(1.35),
               width=Inches(6.0), height=Inches(0.40),
               size=18, bold=True, color=h.NAVY)
    h.add_text(s, "Idempotent MERGE pattern  ·  insert-only by default",
               left=Inches(0.50), top=Inches(1.75),
               width=Inches(6.0), height=Inches(0.30),
               size=11, color=h.GREY)
    h.add_bullets(s, [
        "8 dimensions: dim_inverter, dim_inverter_status, dim_weather_site, dim_measurement_type, dim_division, dim_room, dim_prediction_model, ref_electricity_tariff.",
        "LEFT ANTI JOIN against existing dim rows → INSERT only new keys.",
        "dim_prediction_model: payload diff → UPDATE when KNIME metadata drifts.",
        "ref_electricity_tariff: SCD2 — old row EffectiveTo = today-1, new row inserted.",
        "Seeds dim_inverter_status with sentinel StatusCode = 99 (Unknown) for missing codes.",
    ], left=Inches(0.50), top=Inches(2.10),
       width=Inches(6.0), height=Inches(2.5), size=12)

    # quick callout
    h.rounded_card(s, left=Inches(0.50), top=Inches(5.55),
                   width=Inches(5.90), height=Inches(1.20),
                   fill=h.WHITE, line=h.GOLD)
    h.add_text(s, "Why MERGE not TRUNCATE?",
               left=Inches(0.65), top=Inches(5.62),
               width=Inches(5.60), height=Inches(0.30),
               size=12, bold=True, color=h.GOLD)
    h.add_text(s,
               "Surrogate keys must remain stable so existing facts keep their joins. "
               "Re-runs are safe — no duplicates, no orphaned facts.",
               left=Inches(0.65), top=Inches(5.92),
               width=Inches(5.60), height=Inches(0.80),
               size=10, color=h.DARK)

    # right card — facts
    h.rounded_card(s, left=Inches(6.75), top=Inches(1.25),
                   width=Inches(6.30), height=Inches(5.65),
                   fill=h.GOLD_FILL, line=h.GOLD)
    h.add_text(s, "silver_gold_facts.py",
               left=Inches(6.95), top=Inches(1.35),
               width=Inches(6.0), height=Inches(0.40),
               size=18, bold=True, color=h.NAVY)
    h.add_text(s, "Watermark incremental load  ·  JDBC append + retry/backoff",
               left=Inches(6.95), top=Inches(1.75),
               width=Inches(6.0), height=Inches(0.30),
               size=11, color=h.GREY)

    h.add_bullets(s, [
        "Watermark — SELECT MAX(DateKey) FROM <fact> → keep silver rows strictly newer.",
        "DateKey = yyyyMMdd::int  ·  TimeKey = hour*60 + minute::smallint (cheap joins).",
        "fact_environment uses FULL OUTER JOIN of temperature & humidity (single-sensor reads survive).",
        "Bookings: French dates parsed with custom helper before try_to_date.",
        "Computed cols (RetailValue_CHF, CostCHF, IsRecurring) — SQL-side, not in INSERT list.",
        "Serverless pause? JDBC retry-with-backoff (20–80 s, max 5 attempts).",
    ], left=Inches(6.95), top=Inches(2.10),
       width=Inches(6.0), height=Inches(3.0), size=12)

    h.rounded_card(s, left=Inches(6.95), top=Inches(5.40),
                   width=Inches(5.90), height=Inches(1.40),
                   fill=h.WHITE, line=h.GOLD)
    h.add_text(s, "7 fact tables",
               left=Inches(7.10), top=Inches(5.47),
               width=Inches(5.60), height=Inches(0.30),
               size=12, bold=True, color=h.GOLD)
    h.add_text(s,
               "fact_solar_inverter · fact_solar_production · fact_energy_consumption · "
               "fact_environment · fact_weather_forecast · fact_room_booking · fact_energy_prediction",
               left=Inches(7.10), top=Inches(5.78),
               width=Inches(5.60), height=Inches(1.00),
               size=10, color=h.DARK)

    h.footer(s)


def gold_schema(prs):
    s = h.blank(prs)
    h.header_band(s, "7.  Gold Transformation — schema & analytical views",
                  "DevDB  ·  8 dims  ·  7 facts  ·  7 BI-ready views",
                  color=h.GOLD)

    # 3 columns: dims | facts | views
    col_w = Inches(4.20)
    gap = Inches(0.10)
    top = Inches(1.30)
    left = Inches(0.30)

    columns = [
        ("Dimensions  (8)", h.NAVY, h.LIGHT_BLUE, [
            "dim_inverter",
            "dim_inverter_status",
            "dim_weather_site",
            "dim_measurement_type",
            "dim_division",
            "dim_room",
            "dim_prediction_model",
            "ref_electricity_tariff (SCD2)",
            "+ dim_date · dim_time (out-of-band)",
        ]),
        ("Facts  (7)", h.GOLD, h.GOLD_FILL, [
            "fact_solar_inverter   — (DateKey, TimeKey, InverterKey)",
            "fact_solar_production — (DateKey, TimeKey)",
            "fact_energy_consumption — (DateKey, TimeKey)",
            "fact_environment — (DateKey, TimeKey)",
            "fact_weather_forecast — (Date, Time, Site, Measurement, Horizon)",
            "fact_room_booking — Surrogate BookingKey",
            "fact_energy_prediction — (Date, Time, Model, RunDate)",
        ]),
        ("Analytical views  (7)", h.SERVE_GREEN, h.SERVE_FILL, [
            "vw_inverter_status_breakdown",
            "vw_inverter_performance",
            "vw_prediction_accuracy   (MAPE)",
            "vw_daily_energy_balance  (CHF balance)",
            "vw_building_occupation",
            "vw_kpi_dashboard_home",
            "vw_weather_vs_production",
        ]),
    ]
    for name, accent, fill, items in columns:
        h.rounded_card(s, left=left, top=top, width=col_w, height=Inches(0.55),
                       fill=accent, line=accent)
        h.add_text(s, name, left=left, top=top, width=col_w, height=Inches(0.55),
                   size=14, bold=True, color=h.WHITE,
                   align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        h.rounded_card(s, left=left, top=top + Inches(0.65),
                       width=col_w, height=Inches(4.20),
                       fill=fill, line=accent)
        ry = top + Inches(0.80)
        for it in items:
            h.add_text(s, "•  " + it, left=left + Inches(0.18),
                       top=ry, width=col_w - Inches(0.30), height=Inches(0.40),
                       size=11, color=h.DARK)
            ry += Inches(0.42)
        left += col_w + gap

    # bottom — security model
    h.rounded_card(s, left=Inches(0.30), top=Inches(6.10),
                   width=Inches(12.70), height=Inches(0.95),
                   fill=h.LIGHT_GREY, line=h.NAVY)
    h.add_text(s, "Security model",
               left=Inches(0.45), top=Inches(6.18),
               width=Inches(2.2), height=Inches(0.30),
               size=12, bold=True, color=h.NAVY)
    h.add_text(s,
               "Director_Role · Technician_Role · BookingDivisionFilter (RLS) — fn_division_security maps each Director "
               "login to allowed DivisionKey via ref_user_division_access. db_owner / Technician bypass the filter.",
               left=Inches(0.45), top=Inches(6.45),
               width=Inches(12.4), height=Inches(0.55),
               size=10, color=h.DARK)

    h.footer(s)


if __name__ == "__main__":
    prs = h.open_or_create()
    gold_notebooks(prs)
    gold_schema(prs)
    h.save(prs)
    print("ok — gold slides appended")
