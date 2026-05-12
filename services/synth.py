"""LLM synthesis of the Safeguards section. Robust to missing key + API errors."""
import os
import json
from openai import OpenAI

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.environ.get("OPENROUTER_API_KEY", "no-key"),
            base_url="https://openrouter.ai/api/v1",
        )
    return _client


SYSTEM = """You are a buy-side carbon DD analyst writing the Safeguards section of an IC memo. Output exactly two short prose paragraphs (no bullets, no headings) starting with "**Safeguards.**".

Paragraph 1: verdict in one sentence, then cite the evidence — name Indigenous nations, outlets+counts, courts+years, NGO orgs, and E/G bands if present.

Paragraph 2: recommendation ("proceed" / "proceed with conditions" / "pass") + concrete follow-ups tied to specific evidence gaps.

HARD RULES (no exceptions):
1. Every name, number, date, court, outlet, country MUST appear verbatim in the evidence JSON. Never invent.
2. No statistics, percentages, or rankings not in evidence.
3. No invented projects, developers, registries, methodologies, or standards.
4. No speculation on cause, motive, or consequence. Restrict to what evidence says.
5. No direct quotes — never fabricate quotes.
6. If territory coverage is "partial" or "unknown", say so in paragraph 1.
7. If news returns 0 articles, say "no signal in 24-month window" — NOT "no concerns".
8. If E or G context absent, say nothing about them.
9. Maximum 180 words. Neutral evidentiary tone. No advocacy or alarmism.

If evidence is too thin, output only: "**Safeguards.** Evidence is insufficient for a defensible memo."
"""


def _build_evidence(project: dict, territories, articles, litigation, ngo, coverage: str,
                    env: dict | None = None, gov: dict | None = None) -> str:
    payload = {
        "project": project.get("name"),
        "country": project.get("country"),
        "territory_coverage": coverage,
        "indigenous_overlap": [t.get("name") for t in (territories or [])],
        "adverse_news": [
            {"t": (a.get("title") or "")[:80], "outlet": a.get("domain")}
            for a in (articles or [])[:4] if a.get("adverse_score", 0) >= 1
        ],
        "litigation": [
            {"case": (x.get("title") or "")[:80], "court": x.get("court"), "year": x.get("year")}
            for x in (litigation or [])[:3]
        ],
        "ngo": [{"org": x.get("org"), "year": x.get("year")} for x in (ngo or [])[:3]],
        "env": {"band": env.get("band"), "delta": env.get("annual_change_pp")} if env and env.get("ok") else None,
        "gov": {"band": gov.get("band"), "cpi": gov.get("cpi_score")} if gov and gov.get("ok") else None,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def synthesize(project: dict, territories, articles, litigation, ngo, coverage: str = "unknown",
               env: dict | None = None, gov: dict | None = None) -> dict:
    if not os.environ.get("OPENROUTER_API_KEY"):
        return {
            "ok": False,
            "text": "[OPENROUTER_API_KEY not set — synthesis skipped. The four evidence panels above are still live.]",
        }

    user = (
        "Write the Safeguards section of the IC memo for this project, using ONLY the evidence below. "
        "Cover Environmental, Social, and Governance dimensions where evidence is present.\n\n"
        f"```json\n{_build_evidence(project, territories, articles, litigation, ngo, coverage, env=env, gov=gov)}\n```"
    )

    model = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4")
    try:
        resp = _get_client().chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user},
            ],
            temperature=0.1,  # tight — evidentiary prose, not creative writing
            max_tokens=150,
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            return {"ok": False, "text": "[Empty synthesis returned by model.]"}
        # Lightweight grounding sniff: every word in the output that looks like a proper noun
        # (capitalised, >3 chars, not a sentence-start) should appear in the evidence block.
        evidence_text = _build_evidence(project, territories, articles, litigation, ngo, coverage, env=env, gov=gov)
        warnings = _ground_check(text, evidence_text)
        return {"ok": True, "text": text, "model": model, "warnings": warnings}
    except Exception as e:
        return {"ok": False, "text": f"[LLM call failed: {type(e).__name__}: {e}]"}


def _ground_check(output: str, evidence: str) -> list[str]:
    """Sniff for ungrounded proper nouns — flag any capitalised >3-char token in the output
    that doesn't appear in the evidence. Cheap pre-filter, not a guarantee, surfaces obvious leaks."""
    import re
    SAFE = {
        "Safeguards", "Indigenous", "Investors", "Investor", "ESG", "FPIC",
        "Verra", "VVB", "ICVCM", "CCP", "REDD", "IUCN", "GLAD", "CPI",
        "IC", "DD", "Memo", "Analysts", "Analyst",
        # months
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
        # common sentence-start verbs/nouns in IC memos
        "Proceed", "Pass", "The", "This", "These", "Those", "Conditions",
        "Recommendation", "Verify", "Confirm", "Engage", "Obtain", "Implement",
        "Independent", "Project", "Environmental", "Social", "Governance",
        # adjectives common in evidentiary prose
        "Active", "Multilingual", "Recent", "Reported", "Inferred", "Curated", "Country",
        # additions — generic English Title-Case words that surfaced as false positives in v0.3 battle
        "Evidence", "Insufficient", "Limited", "Moderate", "High", "Low",
        "Sustainable", "Sustainability", "Permanence", "Leakage",
        "Wall", "Street", "Journal", "New", "York", "Times", "Financial", "Bloomberg",
        "Reuters", "Mongabay", "Carbon", "Market", "Watch",
        "Defensible", "Defensibly", "Robust", "Material", "Materially",
        "Without", "Within", "Above", "Below", "Between", "Around",
        "However", "Although", "Therefore", "Further", "Moreover", "Additionally",
        "Such", "Several", "Numerous", "Various",
    }
    tokens = re.findall(r"\b[A-Z][A-Za-z]{3,}\b", output)
    evidence_lower = evidence.lower()
    warnings = []
    for t in set(tokens):
        if t in SAFE:
            continue
        if t.lower() not in evidence_lower:
            warnings.append(f"ungrounded term: {t!r}")
    return warnings[:8]
