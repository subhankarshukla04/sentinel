# Sentinel

A safeguards / FPIC red-flag screen for carbon-project due diligence.
Built as an interview demo for Qatalyst (Singapore).

**Engine v0.2** — see [`ENGINE.md`](./ENGINE.md) for architecture, test results, and design decisions.

## What it does

Given a carbon project's name + geo-coordinates, Sentinel returns a traffic-light
scorecard for **social-license risk** in ~3 seconds:

- Indigenous-territory overlap (Native Land Digital)
- Adverse multilingual news (GDELT 2.0)
- Active climate litigation (Sabin Center / curated ledger)
- NGO + investigative complaints (curated ledger)
- LLM-synthesized Safeguards section of an IC memo (OpenRouter)

## Quickstart

```bash
cd sentinel
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY
python app.py
```

Then open http://127.0.0.1:5099

The four pre-loaded sample projects are real:

- **Cordillera Azul REDD+** (Peru, VCS 985) — controversial
- **Kariba REDD+** (Zimbabwe, VCS 902) — controversial (the South Pole exit story)
- **Alto Mayo Conservation** (Peru, VCS 934) — contested
- **Mikoko Pamoja Mangrove** (Kenya, Plan Vivo) — clean control

Click any one to run a live screen. Or expand the "ad-hoc" form and paste
coordinates from any PDD.

## Architecture

```
Flask + HTMX + Tailwind  ──▶  ThreadPoolExecutor (3 parallel calls)
                                ├─▶ Native Land Digital  (Indigenous overlay)
                                ├─▶ GDELT 2.0 DOC API    (multilingual news)
                                └─▶ Curated risk ledger  (litigation + NGO)
                              ──▶ OpenRouter (Sonnet 4.6) — IC-memo synthesis
```

No database. No accounts. ~400 lines of Python total. Demonstrates the
*shape* of the build — the moat in v2 would be the curated ledger
maintenance, multilingual translation, and Qatalyst workspace integration.

## Why this, not the other four

See `../03_elimination_audits.md` for how this idea won across five rounds.
TL;DR: it fills the social-license gap the carbon-accounting layer
doesn't cover, it uses entirely free real data sources, and Caroline Guyot's
own launch quote was about indigenous-community consent — Qatalyst already
cares but hasn't productized this surface.
