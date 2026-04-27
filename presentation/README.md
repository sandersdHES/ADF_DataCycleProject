# Project presentation — Bellevue Data Cycle

`Bellevue_DataCycle.pptx` — 19-slide deck covering the topics requested for the
Sprint 6 final review.

## Topics

1. Introduction
2. Team Presentation *(placeholder names — replace before delivery)*
3. How we organised the work
4. Architecture *(2 slides — components view + tech stack)*
5. Data Flow *(2 slides — daily timeline + Bronze ingestion pattern)*
6. Silver Transformation
7. Gold Transformation *(2 slides — notebooks + schema/views)*
8. Machine Learning *(3 slides — overview, lifecycle, KNIME internals placeholder)*
9. Power BI Dashboards
10. SAC Dashboards
11. Further improvements possible

A cover, agenda and closing slide bracket the topics.

## Regenerate

The deck is built deterministically from the `build_*.py` scripts.

```bash
pip install python-pptx
cd presentation
python3 build_all.py
```

Each `build_NN_*.py` script can also be run individually — it appends its own
slides to whatever `Bellevue_DataCycle.pptx` already exists in this folder.

## Manual edits to do before delivery

- **Slide 4 (Team)** — replace the 5 placeholder member cards with real
  names, photos and roles.
- **Slide 15 (KNIME workflow internals)** — drop screenshots / node-graph
  exports from KNIME Hub. The workflows are not in this Git repository
  (they live on the KNIME Server), so the slide ships with the integration
  context filled in and a reminder banner.
- Anything else: tweak the matching `build_*.py` and re-run `build_all.py`.
