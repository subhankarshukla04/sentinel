# Sentinel

A safeguards / social-license screen for the buy-side carbon DD workflow.

Sits next to the carbon-accounting stack (registries, VVBs, raters) and covers the surface that stack doesn't touch: Indigenous consent, NGO complaints, and active climate litigation — the headline-risk vector that hits a project *after* its credits have already cleared methodology review, and that lands on the buyer, not the registry.

First-line evaluation, evidence-cited, IC-memo-ready.

## What it screens

Given a project name + coordinates, Sentinel returns a traffic-light scorecard in ~3 seconds. Every signal is cited.

- **FPIC overlay** — Indigenous-territory intersection (Native Land Digital)
- **Adverse press** — multilingual coverage against the project (GDELT 2.0)
- **Active litigation** — climate cases naming the project or developer (Sabin Center + curated ledger)
- **NGO + investigative complaints** — Survival International, FIDH, Mongabay, Climate Home (curated ledger)
- **Safeguards memo paragraph** — synthesized into IC-memo prose with inline citations (OpenRouter / Sonnet 4.6)

Output is shape-stable and appendable to a project file — every field is either a green / amber / red bucket or a cited source URL. Nothing is editorial; the engine never assigns a rating it can't link to evidence.

## Why a separate surface

Carbon-accounting risk has converged. CCP, the methodology-change-and-requantification procedure, and the rater layer (BeZero, Sylvera, Calyx, Renoster) all triangulate the credits themselves. None of them watch the project's standing in its host community.

That's where the next Cordillera Azul / Kariba / NRT story lands. Sentinel is the screen that catches it before the IC vote.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add OPENROUTER_API_KEY
python app.py
```

http://127.0.0.1:5099

Four pre-loaded projects are real:

- **Cordillera Azul REDD+** (Peru, VCS 985) — controversial
- **Kariba REDD+** (Zimbabwe, VCS 902) — the South Pole exit
- **Alto Mayo Conservation** (Peru, VCS 934) — contested
- **Mikoko Pamoja Mangrove** (Kenya, Plan Vivo) — clean control

Or paste any project's name + coordinates from a PDD into the ad-hoc form. Engine fires the same screen either way.

## Engine

Multi-tier resolver. Every external call has a graceful fallback. Every result is shape-stable. Every input is validated.

```
Flask + HTMX + Tailwind  ──▶  ThreadPoolExecutor (3 parallel calls)
                                ├─▶ Native Land Digital  (Indigenous overlay)
                                ├─▶ GDELT 2.0 DOC API    (multilingual news)
                                └─▶ Curated risk ledger  (litigation + NGO)
                              ──▶ OpenRouter (Sonnet 4.6) — IC-memo synthesis
```

94 unit + integration tests. 15 live blind screens on previously-unseen projects: zero crashes. Northern Rangelands Trust (Kenya) — not in the curated ledger, never seen by the engine — returned RED 11 with three adverse articles surfaced from cold news inference (Mongabay, Survival International, FIDH).

See [`ENGINE.md`](./ENGINE.md) for architecture detail and [`STANDARDS.md`](./STANDARDS.md) for the build standard.

## Where this extends

- Curated ledger maintenance — the moat. Has to be hand-tended, like a credit-research desk.
- Multilingual press scoring — engine already reads it; the ledger doesn't yet weight it.
- Workspace integration — project file, audit trail, versioned analyst notes.
