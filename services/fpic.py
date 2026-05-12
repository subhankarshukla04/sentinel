"""FPIC procedural checklist.

Free, Prior and Informed Consent is a *procedural* standard from the UN
Declaration on the Rights of Indigenous Peoples (UNDRIP, 2007) and ILO
Convention 169. It is not a yes/no flag — it is a documented sequence of
four obligations. This module evaluates each obligation against the
evidence the engine has already gathered (territory overlap, news,
litigation, NGO complaints) and returns a checklist an analyst can use
to direct deep DD.

Anchors:
  • UNDRIP Articles 10, 19, 32 — UN, 2007
  • ILO Convention 169 — Indigenous and Tribal Peoples Convention, 1989
  • UN-REDD Programme Guidelines on Free, Prior and Informed Consent, 2013
  • Cancun Safeguards (UNFCCC Decision 1/CP.16, Appendix I) — for REDD+ projects

We deliberately return *"insufficient evidence"* by default when the engine
cannot see procedural documentation directly. That is the honest answer —
a screen reads public signals; a DD analyst reads project documents.
"""
from __future__ import annotations

CHECK_PASS = "pass"
CHECK_FAIL = "fail"
CHECK_INSUFFICIENT = "insufficient"
CHECK_NA = "not applicable"


def _title(a: dict) -> str:
    return (a.get("title") or "").lower()


def _any_phrase(articles: list[dict], phrases: list[str]) -> list[dict]:
    out = []
    for a in articles:
        t = _title(a)
        if any(p in t for p in phrases):
            out.append(a)
    return out


def assess_fpic(territories: list[dict], articles: list[dict],
                litigation: list[dict], ngo: list[dict],
                territory_coverage: str = "unknown") -> dict:
    """Return a 4-item FPIC procedural checklist.

    Each item: {status, rationale, evidence (titles/items used)}.
    Status is one of: pass | fail | insufficient | not applicable.
    """
    has_indigenous_overlap = bool(territories)
    coverage_dark = territory_coverage in ("unknown", "none", "")

    # ---------- 1. Consultation documented ----------
    no_consult_signals = _any_phrase(articles, [
        "without consultation", "no consultation", "lack of consultation",
        "failed to consult", "did not consult",
    ])
    if no_consult_signals:
        check_1 = {
            "id": "consultation",
            "label": "Consultation with affected Indigenous communities documented",
            "status": CHECK_FAIL,
            "rationale": "Public reporting alleges consultation was absent or inadequate.",
            "evidence": [a.get("title") for a in no_consult_signals[:3]],
        }
    elif not has_indigenous_overlap and coverage_dark:
        check_1 = {
            "id": "consultation",
            "label": "Consultation with affected Indigenous communities documented",
            "status": CHECK_INSUFFICIENT,
            "rationale": "Territory coverage is dark; consultation cannot be assessed from public signals.",
            "evidence": [],
        }
    elif not has_indigenous_overlap:
        check_1 = {
            "id": "consultation",
            "label": "Consultation with affected Indigenous communities documented",
            "status": CHECK_NA,
            "rationale": "No Indigenous-territory overlap detected; consultation obligation may not apply.",
            "evidence": [],
        }
    else:
        check_1 = {
            "id": "consultation",
            "label": "Consultation with affected Indigenous communities documented",
            "status": CHECK_INSUFFICIENT,
            "rationale": "Indigenous overlap exists; consultation evidence requires project-document review (PDD, monitoring reports).",
            "evidence": [],
        }

    # ---------- 2. Consent obtained ----------
    no_consent_signals = _any_phrase(articles, [
        "without consent", "no consent", "withdrew consent", "withdrawn consent",
        "rejected consent", "consent denied", "violated consent",
    ])
    if no_consent_signals:
        check_2 = {
            "id": "consent",
            "label": "Free, prior and informed consent obtained (or refusal respected)",
            "status": CHECK_FAIL,
            "rationale": "Public reporting alleges consent was absent, withheld, or withdrawn.",
            "evidence": [a.get("title") for a in no_consent_signals[:3]],
        }
    elif not has_indigenous_overlap and coverage_dark:
        check_2 = {
            "id": "consent",
            "label": "Free, prior and informed consent obtained (or refusal respected)",
            "status": CHECK_INSUFFICIENT,
            "rationale": "Territory coverage is dark; consent cannot be assessed.",
            "evidence": [],
        }
    elif not has_indigenous_overlap:
        check_2 = {
            "id": "consent",
            "label": "Free, prior and informed consent obtained (or refusal respected)",
            "status": CHECK_NA,
            "rationale": "No Indigenous-territory overlap detected; consent obligation may not apply.",
            "evidence": [],
        }
    else:
        check_2 = {
            "id": "consent",
            "label": "Free, prior and informed consent obtained (or refusal respected)",
            "status": CHECK_INSUFFICIENT,
            "rationale": "Indigenous overlap exists; consent evidence requires project-document review.",
            "evidence": [],
        }

    # ---------- 3. Grievance mechanism active ----------
    if ngo or litigation:
        check_3 = {
            "id": "grievance",
            "label": "Operational grievance mechanism (Cancun safeguard 2(d))",
            "status": CHECK_FAIL,
            "rationale": "Active NGO complaints or litigation suggest grievances have escalated outside any project-internal mechanism.",
            "evidence": [
                *[n.get("title") or n.get("source") for n in (ngo or [])[:2]],
                *[l.get("case_name") or l.get("title") for l in (litigation or [])[:2]],
            ],
        }
    else:
        check_3 = {
            "id": "grievance",
            "label": "Operational grievance mechanism (Cancun safeguard 2(d))",
            "status": CHECK_INSUFFICIENT,
            "rationale": "No escalated grievances detected — absence of complaint is not proof of mechanism. Requires project-document review.",
            "evidence": [],
        }

    # ---------- 4. Withdrawal / displacement protections ----------
    displacement_signals = _any_phrase(articles, [
        "evicted", "eviction", "displaced", "displacement", "forced relocation",
        "expelled", "land grab", "land grabbing", "forcibly removed",
    ])
    if displacement_signals:
        check_4 = {
            "id": "withdrawal",
            "label": "Right to withdraw consent / no forced displacement (UNDRIP Art. 10)",
            "status": CHECK_FAIL,
            "rationale": "Public reporting alleges displacement or eviction linked to the project area.",
            "evidence": [a.get("title") for a in displacement_signals[:3]],
        }
    else:
        check_4 = {
            "id": "withdrawal",
            "label": "Right to withdraw consent / no forced displacement (UNDRIP Art. 10)",
            "status": CHECK_INSUFFICIENT if has_indigenous_overlap else CHECK_NA,
            "rationale": (
                "No displacement signal in news; project-document review still required."
                if has_indigenous_overlap
                else "No Indigenous-territory overlap detected; protection obligation may not apply."
            ),
            "evidence": [],
        }

    checks = [check_1, check_2, check_3, check_4]
    fails = sum(1 for c in checks if c["status"] == CHECK_FAIL)
    insufficient = sum(1 for c in checks if c["status"] == CHECK_INSUFFICIENT)
    passes = sum(1 for c in checks if c["status"] == CHECK_PASS)

    if fails >= 2:
        verdict_color = "red"
        verdict_label = "Multiple FPIC obligations show adverse signal"
    elif fails == 1:
        verdict_color = "amber"
        verdict_label = "One FPIC obligation shows adverse signal"
    elif insufficient and not passes:
        verdict_color = "amber"
        verdict_label = "FPIC obligations unassessed from public signals — DD required"
    else:
        verdict_color = "green"
        verdict_label = "No FPIC adverse signals detected"

    return {
        "checks": checks,
        "fails": fails,
        "insufficient": insufficient,
        "passes": passes,
        "color": verdict_color,
        "label": verdict_label,
        "anchors": [
            "UNDRIP Articles 10, 19, 32",
            "ILO Convention 169",
            "UN-REDD FPIC Guidelines 2013",
            "Cancun Safeguards (UNFCCC 1/CP.16, Appendix I)",
        ],
    }
