"""Rebuild the full Bellevue_DataCycle.pptx from scratch.

Each per-section module appends slides to whatever deck already exists, so this
script wipes the deck first and then runs the sections in order.
"""
from pathlib import Path

import _pptx_helpers as h
import build_01_intro
import build_02_team
import build_03_organisation
import build_04_architecture
import build_05_dataflow
import build_06_silver
import build_07_gold
import build_08_ml
import build_09_powerbi
import build_10_sac
import build_11_improvements


def main():
    if h.DECK_PATH.exists():
        h.DECK_PATH.unlink()

    prs = h.open_or_create()
    build_01_intro.cover(prs)
    build_01_intro.agenda(prs)
    build_01_intro.introduction(prs)
    build_02_team.slide(prs)
    build_03_organisation.slide(prs)
    build_04_architecture.architecture_components(prs)
    build_04_architecture.architecture_stack(prs)
    build_05_dataflow.timeline(prs)
    build_05_dataflow.bronze_pattern(prs)
    build_06_silver.slide(prs)
    build_07_gold.gold_notebooks(prs)
    build_07_gold.gold_schema(prs)
    build_08_ml.overview(prs)
    build_08_ml.lifecycle(prs)
    build_08_ml.knime_internals(prs)
    build_09_powerbi.slide(prs)
    build_10_sac.slide(prs)
    build_11_improvements.improvements(prs)
    build_11_improvements.closing(prs)
    h.save(prs)

    print(f"✅  deck rebuilt: {h.DECK_PATH}")


if __name__ == "__main__":
    main()
