"""Topic 2 — Team Presentation.

Names/photos are not in the repo, so this slide ships placeholder member
cards with role hints already filled in. Replace the names before delivery.
"""
from pptx.util import Inches
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

import _pptx_helpers as h

ROLES = [
    ("Member 1", "Project lead / Architect", "End-to-end architecture, ADF orchestration, CI/CD."),
    ("Member 2", "Data engineer", "Bronze ingestion, Self-Hosted IR, source connectivity."),
    ("Member 3", "Data engineer", "Silver/Gold notebooks, SQL schema, data quality."),
    ("Member 4", "ML engineer", "Feature engineering, KNIME workflows, model lifecycle."),
    ("Member 5", "BI developer", "Power BI reports, SAC dashboards, RLS."),
]


def slide(prs):
    s = h.blank(prs)
    h.header_band(s, "2.  Team Presentation",
                  "Group 3 — HES-SO  ·  ADF_DataCycleProject")

    h.add_text(s, "A small, cross-functional team — every member owned at least one slice "
                  "of the pipeline (ingestion, transformation, ML or BI) and reviewed each "
                  "other's work via Pull Requests on GitHub.",
               left=Inches(0.5), top=Inches(1.25), width=Inches(12.3), height=Inches(0.7),
               size=14, color=h.GREY)

    # 5 cards — top row of 3, bottom row of 2 centred
    card_w = Inches(3.9); card_h = Inches(2.15); gap = Inches(0.25)
    top1 = Inches(2.15)
    top2 = top1 + card_h + Inches(0.25)
    row1_total = card_w * 3 + gap * 2
    row1_left = (h.SLIDE_W - row1_total) / 2
    row2_total = card_w * 2 + gap * 1
    row2_left = (h.SLIDE_W - row2_total) / 2

    def member_card(left, top, name, role, body):
        h.rounded_card(s, left=left, top=top, width=card_w, height=card_h,
                       fill=h.LIGHT_GREY, line=h.NAVY)
        # avatar circle
        av = s.shapes.add_shape(MSO_SHAPE.OVAL,
                                left + Inches(0.25), top + Inches(0.25),
                                Inches(0.9), Inches(0.9))
        av.fill.solid(); av.fill.fore_color.rgb = h.NAVY; av.line.fill.background()
        h.add_text(s, name[0], left=left + Inches(0.25), top=top + Inches(0.25),
                   width=Inches(0.9), height=Inches(0.9),
                   size=28, bold=True, color=h.WHITE,
                   align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        h.add_text(s, name,
                   left=left + Inches(1.25), top=top + Inches(0.25),
                   width=card_w - Inches(1.4), height=Inches(0.45),
                   size=18, bold=True, color=h.NAVY)
        h.add_text(s, role,
                   left=left + Inches(1.25), top=top + Inches(0.65),
                   width=card_w - Inches(1.4), height=Inches(0.4),
                   size=12, bold=True, color=h.GOLD)
        h.add_text(s, body,
                   left=left + Inches(0.25), top=top + Inches(1.25),
                   width=card_w - Inches(0.5), height=Inches(0.85),
                   size=12, color=h.DARK)

    for i, (name, role, body) in enumerate(ROLES[:3]):
        member_card(row1_left + (card_w + gap) * i, top1, name, role, body)
    for i, (name, role, body) in enumerate(ROLES[3:]):
        member_card(row2_left + (card_w + gap) * i, top2, name, role, body)

    h.add_text(s,
               "✱ Replace placeholder names/photos before delivery.",
               left=Inches(0.5), top=Inches(7.05), width=Inches(12.3), height=Inches(0.3),
               size=10, color=h.RED, align=PP_ALIGN.LEFT)


if __name__ == "__main__":
    prs = h.open_or_create()
    slide(prs)
    h.save(prs)
    print("ok — team slide appended")
