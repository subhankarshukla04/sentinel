"""Composite risk score from the four signal counts."""

def overall_risk(territories_count: int, adverse_news_count: int,
                 litigation_count: int, ngo_count: int,
                 territory_coverage: str = "unknown",
                 env_color: str | None = None,
                 gov_color: str | None = None,
                 fpic_color: str | None = None) -> dict:
    """Roll up signals into a traffic light.

    Heuristic, deliberately simple and transparent (rule-based, not a model):
      +2 per indigenous-territory hit (capped at 4)  — proxy for FPIC obligation existing
      +1 per adverse news article (capped at 5)     — adverse = topic+claim co-occurrence (see news.py)
      +3 per active litigation                       — Sabin Center registry + news inference
      +2 per NGO complaint                           — curated ledger + auto-promoted news
      +2 / +1 Environmental band red / amber         — World Bank forest-cover trend (country-level proxy)
      +2 / +1 Governance band red / amber            — TI CPI bands anchored to TI 2024 global avg of 43
      +2 / +1 FPIC procedural red / amber            — 4-check procedural framework (UNDRIP/ILO 169/Cancun)

    We *don't* down-weight when coverage is low — instead the result includes
    the coverage flag so the analyst can read the verdict honestly.
    """
    territories_count = max(0, int(territories_count or 0))
    adverse_news_count = max(0, int(adverse_news_count or 0))
    litigation_count = max(0, int(litigation_count or 0))
    ngo_count = max(0, int(ngo_count or 0))

    score = 0
    score += min(territories_count, 2) * 2
    score += min(adverse_news_count, 5)
    score += litigation_count * 3
    score += ngo_count * 2
    # Environmental + Governance pillars contribute small but real points.
    score += {"red": 2, "amber": 1}.get(env_color or "", 0)
    score += {"red": 2, "amber": 1}.get(gov_color or "", 0)
    # FPIC procedural verdict contributes — small weight because it derives from
    # the same evidence pool; avoids double-counting while keeping the signal.
    score += {"red": 2, "amber": 1}.get(fpic_color or "", 0)

    if score >= 8:
        label, color = "HIGH social-license risk", "red"
    elif score >= 3:
        label, color = "MEDIUM social-license risk", "amber"
    else:
        label, color = "LOW social-license risk", "green"

    return {
        "score": score,
        "label": label,
        "color": color,
        "territory_coverage": territory_coverage,
    }
