"""Topic 10 — SAC Dashboards."""
from pptx.util import Inches
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

import _pptx_helpers as h


def slide(prs):
    s = h.blank(prs)
    h.header_band(s, "10.  SAC Dashboards",
                  "SAP Analytics Cloud  ·  fed via Azure File Share",
                  color=h.SERVE_GREEN)

    # left — export pipeline
    h.add_text(s, "Export pipeline",
               left=Inches(0.5), top=Inches(1.30),
               width=Inches(6), height=Inches(0.4),
               size=18, bold=True, color=h.SERVE_GREEN)

    flow = [
        ("sac_export_to_adls.py",
         "Reads two gold views via JDBC:\n"
         "vw_inverter_status_breakdown\nvw_inverter_performance\n\n"
         "LEFT JOIN at (FullDate, InverterID) → coalesce(1) "
         "writes sacexport/sac_inverter_combined.csv.",
         h.RED),
        ("PL_SAC_Export",
         "ADF Copy activity — binary copy to the\n"
         "sac-export-share Azure File Share.\n\n"
         "Authenticated via LS_AzureFileShare_SAC\n"
         "(sacpassword from Key Vault).",
         h.BLUE),
        ("SAP Analytics Cloud",
         "Polls the file share, ingests the CSV,\n"
         "refreshes the dashboard models.",
         h.SERVE_GREEN),
    ]
    sy = Inches(1.85)
    for title, body, color in flow:
        h.rounded_card(s, left=Inches(0.5), top=sy, width=Inches(6.0), height=Inches(1.55),
                       fill=h.WHITE, line=color)
        # color stripe
        h.rounded_card(s, left=Inches(0.5), top=sy, width=Inches(0.18), height=Inches(1.55),
                       fill=color)
        h.add_text(s, title,
                   left=Inches(0.85), top=sy + Inches(0.10),
                   width=Inches(5.5), height=Inches(0.35),
                   size=14, bold=True, color=color)
        h.add_text(s, body,
                   left=Inches(0.85), top=sy + Inches(0.45),
                   width=Inches(5.5), height=Inches(1.05),
                   size=10, color=h.DARK)
        if sy < Inches(4.80):
            h.arrow(s, left=Inches(3.30), top=sy + Inches(1.55),
                    width=Inches(0.40), height=Inches(0.20), color=h.GREY)
            # rotate horizontal arrow into a downward-feel using a small shape
        sy += Inches(1.70)

    # right — what SAC visualises
    h.add_text(s, "Solar panel failure dashboard  (US#25)",
               left=Inches(7.0), top=Inches(1.30),
               width=Inches(6), height=Inches(0.4),
               size=18, bold=True, color=h.SERVE_GREEN)

    cards = [
        ("Status breakdown",
         "PctOfDayReadings per inverter status — "
         "spot inverters that spend more than X % of the day in fault states."),
        ("Performance ratio",
         "Actual AC power / rated capacity — separates a poorly-performing "
         "inverter from one simply running on a cloudy day."),
        ("Combined view",
         "The CSV joins both views at (FullDate, InverterID) so SAC "
         "models a single fact table with status + performance attributes."),
        ("Why SAC, not Power BI?",
         "SAC was a customer requirement — fits the existing SAP landscape "
         "and reaches a different audience (operations / facilities)."),
    ]
    cy = Inches(1.85)
    for title, body in cards:
        h.rounded_card(s, left=Inches(7.0), top=cy,
                       width=Inches(5.85), height=Inches(1.20),
                       fill=h.SERVE_FILL, line=h.SERVE_GREEN)
        h.add_text(s, title,
                   left=Inches(7.18), top=cy + Inches(0.10),
                   width=Inches(5.55), height=Inches(0.30),
                   size=12, bold=True, color=h.SERVE_GREEN)
        h.add_text(s, body,
                   left=Inches(7.18), top=cy + Inches(0.40),
                   width=Inches(5.55), height=Inches(0.80),
                   size=10, color=h.DARK)
        cy += Inches(1.30)

    h.footer(s)


if __name__ == "__main__":
    prs = h.open_or_create()
    slide(prs)
    h.save(prs)
    print("ok — SAC slide appended")
