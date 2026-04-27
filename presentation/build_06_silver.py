"""Topic 6 — Silver Transformation."""
from pptx.util import Inches
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

import _pptx_helpers as h


def slide(prs):
    s = h.blank(prs)
    h.header_band(s, "6.  Silver Transformation",
                  "silver_transformation.py  ·  Bronze CSV → Silver Parquet (overwrite)",
                  color=h.SILVER)

    # left — what it produces
    h.add_text(s, "Output tables  ·  silver/  container",
               left=Inches(0.5), top=Inches(1.25),
               width=Inches(6), height=Inches(0.4),
               size=16, bold=True, color=h.SILVER)

    tables = [
        ("solar_inverters",          "1 row / inverter / minute (5 inverters)"),
        ("solar_aggregated",         "Daily PV roll-up (production_delta_kwh)"),
        ("weather_forecasts",        "Past weather, multi-site"),
        ("weather_future_forecasts", "Forward 3 h forecast"),
        ("bookings",                 "Room reservations (GDPR-masked)"),
        ("consumption",              "Energy delta_kwh per 15 min"),
        ("temperature",              "Per-sensor readings"),
        ("humidity",                 "Per-sensor readings"),
    ]
    ty = Inches(1.75)
    for name, body in tables:
        h.rounded_card(s, left=Inches(0.5), top=ty, width=Inches(6.0), height=Inches(0.55),
                       fill=h.SILVER_FILL, line=h.SILVER)
        h.add_text(s, name, left=Inches(0.65), top=ty + Inches(0.05),
                   width=Inches(2.6), height=Inches(0.45),
                   size=12, bold=True, color=h.DARK,
                   anchor=MSO_ANCHOR.MIDDLE)
        h.add_text(s, body, left=Inches(3.30), top=ty + Inches(0.05),
                   width=Inches(3.10), height=Inches(0.45),
                   size=11, color=h.GREY, anchor=MSO_ANCHOR.MIDDLE)
        ty += Inches(0.62)

    # right — key transformations
    h.add_text(s, "Key transformations",
               left=Inches(7.0), top=Inches(1.25),
               width=Inches(6), height=Inches(0.4),
               size=16, bold=True, color=h.SILVER)

    cards = [
        ("UTF-16 BOM cleanup", "translate(col, '\\u0000', '') before any regex — handles UTF-16 LE files (PV, conso, temp, humidity)."),
        ("Dual date parsing", "regexp_extract dd.MM.yy and dd.MM.yyyy → coalesce — survives mixed source formats."),
        ("Solar unpivot", "5 inverters per row → array<struct> + explode() to 1 row per inverter."),
        ("Counter-reset logic", "Cumulative meter goes down ⇒ delta = NULL; lag() recomputes downstream."),
        ("Sierre weather synthesis", "No physical station — average Sion + Visp forecasts to a synthetic 'Sierre' site."),
        ("GDPR masking", "SHA-256 over Professeur / Utilisateur → ProfessorMasked / UserMasked."),
    ]
    ry = Inches(1.75)
    for title, body in cards:
        h.rounded_card(s, left=Inches(7.0), top=ry, width=Inches(5.85), height=Inches(0.85),
                       fill=h.WHITE, line=h.SILVER)
        h.add_text(s, title, left=Inches(7.15), top=ry + Inches(0.06),
                   width=Inches(5.55), height=Inches(0.30),
                   size=12, bold=True, color=h.NAVY)
        h.add_text(s, body, left=Inches(7.15), top=ry + Inches(0.32),
                   width=Inches(5.55), height=Inches(0.55),
                   size=10, color=h.DARK)
        ry += Inches(0.83)

    h.footer(s)


if __name__ == "__main__":
    prs = h.open_or_create()
    slide(prs)
    h.save(prs)
    print("ok — silver slide appended")
