# Sentinel Engine v0.2 — Engineering Notes

## What changed from v0.1

v0.1 was a hardcoded demo that worked for 4 sample projects. **v0.2 is a real engine** that handles arbitrary carbon projects, with multi-tier data sources, structured fallbacks, and a full test suite.

## Architecture

```
                 ┌────────────────────────────────────────────┐
   Form / JSON ─▶│  validation.clean_*  (boundary check)      │
                 └──────────────────┬─────────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
   ┌──────────────────┐  ┌───────────────────┐  ┌────────────────┐
   │ territory.       │  │ news.adverse_news │  │ registry +     │
   │ territories_at   │  │  (parallel fan-   │  │ risk.collect   │
   │  ┌─Native Land   │  │   out)            │  │  (curated +    │
   │  ├─Overpass(opt) │  │  ┌─GDELT 2.0      │  │   inferred)    │
   │  └─Cache         │  │  └─Google News    │  │                │
   └──────────────────┘  └───────────────────┘  └────────────────┘
              │                     │                     │
              └─────────────────────┼─────────────────────┘
                                    ▼
                         ┌──────────────────┐
                         │ score.overall    │
                         └────────┬─────────┘
                                  ▼
                         ┌──────────────────┐
                         │ synth.synthesize │
                         │  (OpenRouter,    │
                         │   optional)      │
                         └──────────────────┘
```

Every external call is non-blocking-on-failure: if Overpass times out, GDELT
rate-limits, OpenRouter is unconfigured — the rest of the engine still
returns a usable scorecard.

## Test results

### Unit + integration suite — 84 tests, 0.47s
```
tests/test_app.py         12  (Flask routes, JSON API, validation, error paths)
tests/test_http.py         7  (retry, backoff, rate-limit handling, malformed responses)
tests/test_news.py        14  (adverse-tone scoring, dedupe, source merging)
tests/test_risk.py         8  (curated lookup, fuzzy match, news-inferred classification)
tests/test_score.py       10  (composite scoring, capping, threshold boundaries)
tests/test_synth.py        5  (LLM call, missing key, exception handling)
tests/test_territory.py    7  (multi-tier resolution, coverage flags, opt-in Overpass)
tests/test_validation.py  21  (lat/lng range, name length, unicode, edge cases)
─────────────────────────
Total                     84   ✅ all pass
```

### Live battle test — 16 real-world scenarios, 0 crashes
Mix of: 4 known-controversial projects, 6 ad-hoc real projects not in the curated ledger, 6 edge cases (poles, antimeridian, unicode names, mid-ocean).

| Iteration | Avg latency | Crashes | Notes |
|---|---|---|---|
| Round 1 | 21,307ms | 0 | Baseline; per-call timeouts of 8-10s + 2 retries |
| Round 2 | 4,907ms | 0 | After dropping retries to 0, timeouts to 4-5s |
| Round 3 | 3,320ms | 0 | After making Overpass opt-in (default off) |

**6.4× speedup, zero crashes, verdict stability across rounds.**

### Fuzz / stress test — 25 calls, 0 crashes
- 12 random valid inputs (random lat/lng, mix of unicode, emoji, punctuation in names)
- 13 adversarial inputs (out-of-range coords, None names, whitespace, unknown project IDs)
- All 12 valid → HTTP 200 with valid color verdict
- All 13 adversarial → HTTP 400 or 404 with structured error message

## Key design decisions

**1. No silent failures.** Every external service returns `{ok: bool, ...}`. The orchestrator inspects ok and falls through to the next tier rather than crashing.

**2. Coverage flags, not confidence scores.** Rather than fake a confidence interval the model can't justify, the territory engine reports `coverage: high|partial|curated|unknown` so the analyst reads the verdict honestly.

**3. News inference for unknown projects.** The curated ledger only has 4 entries. For any other project, `risk.collect` scans the news stream itself for NGO-domain signals and litigation keywords, then promotes them into the right bucket marked `inferred: true`. **Northern Kenya Grassland Carbon scored RED 16 with zero curated entries** — entirely from news inference.

**4. Adverse-tone keyword scoring.** Every article gets a 0–N score based on title keywords (lawsuit, fraud, FPIC, Indigenous…) plus +1 if it comes from an NGO/investigative outlet. Only `adverse_score >= 1` articles count toward the rollup, so a clean project's positive coverage doesn't trigger false positives.

**5. Overpass is opt-in.** Real-world hit rate was 0/16 across the live battle and Overpass eats a 4-second budget per failed call. Default off; enable with `SENTINEL_USE_OVERPASS=1` once OSM tagging matures.

**6. JSON API alongside the HTML route.** `POST /api/assess` returns the same intelligence as a structured payload — so this engine plugs straight into Qatalyst's existing project workspace as a "Safeguards" tab without a UI rewrite.

## Configuration

| Env var | Effect | Default |
|---|---|---|
| `OPENROUTER_API_KEY` | Enables LLM IC-memo synthesis | unset (synthesis skipped, evidence panels still live) |
| `OPENROUTER_MODEL` | Override model (e.g. `anthropic/claude-haiku-4`) | `anthropic/claude-sonnet-4` |
| `NATIVE_LAND_API_KEY` | Enables live Indigenous-territory polygon lookup | unset (falls back to curated cache) |
| `SENTINEL_USE_OVERPASS` | Enables OSM Overpass fallback for territory data | unset (skipped — slow + sparse) |

## How to verify

```bash
cd sentinel
source .venv/bin/activate
python -m pytest tests/                 # 84 unit + integration tests
python scripts/live_battle_test.py      # 16 real scenarios + edge cases
python scripts/fuzz_test.py             # 25-call adversarial fuzz
```

## What would v0.3 look like

1. **Curated ledger pipeline** — scheduled scraper for Carbon Market Watch + Forest Peoples Programme + Mongabay carbon vertical, weekly diff posted to a `data/known_risks.json` PR.
2. **Multilingual GDELT priority** — currently GDELT is rate-limited from a single IP; production should use the GKG Big Query export.
3. **Polygon-based Indigenous overlay** — bundle a GeoJSON of the top 50 Indigenous territories in carbon-project hotspots (Amazon, Congo, SE Asia) with local Shapely point-in-polygon checks.
4. **Webhook into Qatalyst's project workspace** — assessment becomes a "Safeguards" tab on every existing project, re-screened weekly with diff alerts.
5. **Confidence layer** — separate from the verdict, expose how *strong* the evidence is so the analyst can prioritize where to dig.
