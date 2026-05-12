"""Risk classifier — pulls litigation + NGO complaints from two sources:

 1. Curated ledger (data/known_risks.json) — keyed by project_id and by name fuzz-match
 2. Inferred from the news stream — articles from NGO/investigative outlets,
    or articles with legal-language hits, get reclassified into the right bucket.

This means an unknown project still surfaces NGO + litigation signals when
its news coverage shows them, instead of returning all-zeros.
"""
from __future__ import annotations
import json
import os
import re
from . import registry

# Heuristic: which substrings in a domain mark it as NGO/investigative
NGO_DOMAIN_HINTS = {
    "mongabay": "Mongabay",
    "carbonmarketwatch": "Carbon Market Watch",
    "survivalinternational": "Survival International",
    "forestpeoples": "Forest Peoples Programme",
    "rainforestfoundation": "Rainforest Foundation",
    "intercontinentalcry": "Intercontinental Cry",
    "climateinvestigation": "Climate Investigations Center",
    "oxfam": "Oxfam",
    "amnesty": "Amnesty International",
    "hrw": "Human Rights Watch",
}

LITIGATION_KEYWORDS = [
    "lawsuit", "sued", "sue ", "court ", "tribunal", "ruling",
    "injunction", "complaint filed", "litigation", "v\\.", "petitioner",
    "plaintiff", "verdict", "appeal",
]

LITIGATION_RE = re.compile(r"|".join(LITIGATION_KEYWORDS), re.IGNORECASE)


def _curated(project_id: str | None, project_name: str | None) -> dict:
    """Look up the curated ledger by exact project_id, then fuzzy match by name."""
    direct = registry.known_risks(project_id) if project_id else None
    if direct and (direct.get("litigation") or direct.get("ngo_complaints")):
        return direct

    # Fuzzy: try matching on a normalized project name
    if project_name:
        norm = re.sub(r"[^a-z0-9]+", "", project_name.lower())
        for entry in registry.all_risk_entries():
            ent_id = entry.get("id", "")
            ent_aliases = [ent_id] + (entry.get("aliases") or [])
            for alias in ent_aliases:
                if re.sub(r"[^a-z0-9]+", "", alias.lower()) and re.sub(r"[^a-z0-9]+", "", alias.lower()) in norm:
                    return {
                        "litigation": entry.get("litigation", []),
                        "ngo_complaints": entry.get("ngo_complaints", []),
                    }
    return {"litigation": [], "ngo_complaints": []}


def _inferred_from_news(articles: list[dict]) -> dict:
    """Promote articles from NGO outlets to NGO-complaints; legal-language hits to litigation."""
    inferred_ngo = []
    inferred_lit = []
    seen_ngo = set()
    seen_lit = set()
    for a in articles or []:
        title = a.get("title") or ""
        domain = (a.get("domain") or "").lower()
        url = a.get("url") or ""
        # NGO inference
        for hint, org in NGO_DOMAIN_HINTS.items():
            if hint in domain and url not in seen_ngo:
                inferred_ngo.append({
                    "org": org,
                    "year": (a.get("seendate") or "")[:4] or None,
                    "headline": title,
                    "url": url,
                    "inferred": True,
                })
                seen_ngo.add(url)
                break
        # Litigation inference
        if LITIGATION_RE.search(title) and url not in seen_lit:
            inferred_lit.append({
                "title": title,
                "court": "(inferred from news mention)",
                "year": (a.get("seendate") or "")[:4] or None,
                "status": "Reported",
                "url": url,
                "summary": "Article mentions litigation or legal action — verify with primary source.",
                "inferred": True,
            })
            seen_lit.add(url)
    return {"ngo_complaints": inferred_ngo, "litigation": inferred_lit}


def collect(project_id: str | None, project_name: str, articles: list[dict]) -> dict:
    """Return merged litigation + NGO list, curated entries first then inferred."""
    curated = _curated(project_id, project_name)
    inferred = _inferred_from_news(articles)

    lit_urls = {x.get("url") for x in curated["litigation"] if x.get("url")}
    ngo_urls = {x.get("url") for x in curated["ngo_complaints"] if x.get("url")}
    lit_extra = [x for x in inferred["litigation"] if x.get("url") not in lit_urls]
    ngo_extra = [x for x in inferred["ngo_complaints"] if x.get("url") not in ngo_urls]

    return {
        "litigation": curated["litigation"] + lit_extra,
        "ngo_complaints": curated["ngo_complaints"] + ngo_extra,
        "curated_count": len(curated["litigation"]) + len(curated["ngo_complaints"]),
        "inferred_count": len(lit_extra) + len(ngo_extra),
    }
