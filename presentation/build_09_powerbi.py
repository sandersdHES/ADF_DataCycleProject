"""Topic 9 — Power BI dashboards.

Built from the dashboards/ directory (3 .pbix/.pbit files) and the gold views
that feed them.
"""
from pptx.util import Inches
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

import _pptx_helpers as h


def slide(prs):
    s = h.blank(prs)
    h.header_band(s, "9.  Power BI Dashboards",
                  "3 reports · DirectQuery on Gold · RLS-aware",
                  color=h.GOLD)

    h.add_text(s,
               "Each report queries the analytical views in DevDB rather than the raw fact tables — "
               "centralising metric definitions and inheriting the Row-Level Security policy.",
               left=Inches(0.5), top=Inches(1.25),
               width=Inches(12.3), height=Inches(0.6),
               size=12, color=h.GREY)

    # 3 dashboard cards
    dashboards = [
        ("Solar Production",
         "Dashboard-Solar Production.pbix",
         [("vw_inverter_status_breakdown", "Daily status mix per inverter"),
          ("vw_inverter_performance",      "AC power vs rated capacity"),
          ("vw_weather_vs_production",     "Irradiance vs actual PV (15 min)")],
         "Solar technicians monitor inverter health, identify panel failures and "
         "compare actual production to weather conditions."),
        ("Energy & Financial Overview",
         "Energy & Financial Overview.pbit",
         [("vw_daily_energy_balance", "Production vs consumption, CHF"),
          ("vw_kpi_dashboard_home",   "5 KPIs at a glance"),
          ("vw_prediction_accuracy",  "MAPE — solar & consumption")],
         "Management view: net energy balance, self-sufficiency, daily costs, "
         "and how reliable our forecasts are over time."),
        ("Room Occupancy",
         "PowerBy_RoomOccupacy.pbit",
         [("vw_building_occupation",   "Occupation % per room / day"),
          ("fact_room_booking",        "Through RLS BookingDivisionFilter"),
          ("dim_division · dim_room",  "Division- and room-level slicers")],
         "Director-level view, filtered by ref_user_division_access — each "
         "Director sees only their own divisions (GDPR)."),
    ]

    card_w = (h.SLIDE_W - Inches(0.6) - Inches(0.4)) / 3
    cy = Inches(2.00)
    cx = Inches(0.30)
    for title, file_, sources, audience in dashboards:
        h.rounded_card(s, left=cx, top=cy, width=card_w, height=Inches(4.85),
                       fill=h.GOLD_FILL, line=h.GOLD)
        # title strip
        h.rounded_card(s, left=cx, top=cy, width=card_w, height=Inches(0.55),
                       fill=h.GOLD)
        h.add_text(s, title, left=cx, top=cy, width=card_w, height=Inches(0.55),
                   size=15, bold=True, color=h.WHITE,
                   align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        # filename
        h.add_text(s, file_,
                   left=cx + Inches(0.15), top=cy + Inches(0.65),
                   width=card_w - Inches(0.30), height=Inches(0.30),
                   size=10, color=h.GREY, align=PP_ALIGN.CENTER)
        # sources
        h.add_text(s, "Backed by",
                   left=cx + Inches(0.15), top=cy + Inches(1.00),
                   width=card_w - Inches(0.30), height=Inches(0.28),
                   size=11, bold=True, color=h.NAVY)
        ry = cy + Inches(1.30)
        for src, desc in sources:
            h.add_text(s, "•  " + src,
                       left=cx + Inches(0.20), top=ry,
                       width=card_w - Inches(0.40), height=Inches(0.28),
                       size=11, bold=True, color=h.DARK)
            h.add_text(s, "    " + desc,
                       left=cx + Inches(0.20), top=ry + Inches(0.26),
                       width=card_w - Inches(0.40), height=Inches(0.32),
                       size=10, color=h.GREY)
            ry += Inches(0.62)

        # audience footer
        h.rounded_card(s, left=cx + Inches(0.15), top=cy + Inches(3.55),
                       width=card_w - Inches(0.30), height=Inches(1.15),
                       fill=h.WHITE, line=h.GOLD)
        h.add_text(s, "Audience & purpose",
                   left=cx + Inches(0.30), top=cy + Inches(3.62),
                   width=card_w - Inches(0.60), height=Inches(0.30),
                   size=11, bold=True, color=h.GOLD)
        h.add_text(s, audience,
                   left=cx + Inches(0.30), top=cy + Inches(3.92),
                   width=card_w - Inches(0.60), height=Inches(0.75),
                   size=10, color=h.DARK)

        cx += card_w + Inches(0.20)

    h.footer(s)


if __name__ == "__main__":
    prs = h.open_or_create()
    slide(prs)
    h.save(prs)
    print("ok — Power BI slide appended")
