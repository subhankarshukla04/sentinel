"""Governance signal — Transparency International Corruption Perceptions Index 2024.

Bands are anchored to two TI-published numbers, not invented cut-offs:
  • CPI < 30 → TI's own descriptor "serious corruption problems"
  • CPI 30–42 → below the TI 2024 global average of 43
  • CPI ≥ 43 → at or above TI 2024 global average
Source: Transparency International, "Corruption Perceptions Index 2024 — Methodology and Results,"
https://www.transparency.org/en/cpi/2024
"""
from __future__ import annotations
import json
import os

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cpi.json")


def _load() -> dict:
    with open(DATA_PATH) as f:
        return json.load(f)


def country_governance(country: str | None) -> dict:
    """Return {ok, country, cpi_score, band, source} for a given country name."""
    if not country:
        return {"ok": False, "note": "no country provided", "cpi_score": None, "band": "unknown"}
    blob = _load()
    scores = blob.get("scores", {})
    # case-insensitive lookup
    score = None
    matched = None
    target = country.strip().lower()
    for k, v in scores.items():
        if k.lower() == target:
            score, matched = v, k
            break
    if score is None:
        return {"ok": True, "country": country, "cpi_score": None, "band": "uncovered",
                "note": "not in CPI hotspot subset; production would fall back to live API.",
                "source": blob.get("_source")}

    # Bands anchored to TI-published numbers (see module docstring).
    if score < 30:
        band, color = "serious corruption problems (TI descriptor)", "red"
        rationale = "Below 30 — TI 2024: 'countries with serious corruption problems.'"
    elif score < 43:
        band, color = "below TI 2024 global average", "amber"
        rationale = f"CPI {score} is below the TI 2024 global average of 43."
    else:
        band, color = "at or above TI 2024 global average", "green"
        rationale = f"CPI {score} meets or exceeds the TI 2024 global average of 43."

    return {
        "ok": True,
        "country": matched,
        "cpi_score": score,
        "band": band,
        "color": color,
        "rationale": rationale,
        "global_avg_2024": 43,
        "source": blob.get("_source"),
        "source_url": blob.get("_url"),
    }
