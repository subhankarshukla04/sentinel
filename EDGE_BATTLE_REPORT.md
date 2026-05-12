# Edge-case battle report — 10 unseen projects

**Date:** 2026-05-11 · **Engine:** Sentinel v0.3 (Flask) · **API:** `POST /api/assess`

10 projects the engine had **never seen**: 5 real & known-controversial (none in the curated ledger), 2 fictional clean controls, 1 Unicode/Chinese-language case, 2 geographic boundary cases. No fixtures added. Full raw output: `/tmp/edge_battle.json`.

## Headline

**6 / 10 reasonable. 4 / 10 problematic. 0 crashes.**

The engine doesn't fall over, doesn't hallucinate green→red on fakes, and **does** catch some known-bad projects from cold news inference. But it has three real gaps I had been understating, and one of them is severe enough that the demo's "six signals" claim is only half-true in practice.

## Per-case verdicts

| # | Project | Expected | Got | Honest call |
|---|---------|----------|-----|-------------|
| 01 | Mai Ndombe REDD+ (DRC) | Signal — documented carbon-press controversy | **GREEN 0** (run 1) → **AMBER 3** (run 2) | ⚠️ **Non-deterministic.** First run missed entirely (0 of 9 articles scored adverse). Second run caught 1 Mongabay hit. Means the verdict swings on which Google-News page returns. |
| 02 | Katingan Mentaya Peat REDD+ (Indonesia) | AMBER/RED — well-covered controversy | **AMBER 4** (12 news / 1 adverse / 1 NGO) | ✅ Reasonable — but it grabbed *one* adverse and one auto-promoted NGO. Defensible, not impressive. |
| 03 | Pacajai REDD+ (Brazil) | Signal — Verra-flagged | **AMBER 5** (6 news / 3 adverse) | ✅ **Real catch.** Engine surfaced 3 adverse articles from cold. |
| 04 | Surui Forest Carbon (Brazil) | RED — Indigenous + over-credit history | **RED 11** (10 news / 6 adverse / 2 NGO) | ✅ **Best catch of the run.** Most adverse articles + 2 NGO complaints surfaced without curation. BUT: the LLM memo says "no documented Indigenous overlap" — for a project literally named after the Suruí nation. |
| 05 | Rimba Raya (Indonesia) | Signal — community grievances | **AMBER 4** (12 news / 1 adverse / 0 NGO) | ⚠️ Weak. Real controversy in carbon press; we got 1 adverse hit. |
| 06 | Larimar Pine Plantation (DR, **FAKE**) | GREEN 0 | **GREEN 0** | ✅ Did not hallucinate risk. LLM correctly returned "Evidence is insufficient." |
| 07 | Highland Carbon Scotland (UK, **FAKE**) | GREEN 0 | **GREEN 0** | ✅ Same — clean OECD geography passed cleanly. |
| 08 | 大兴安岭碳汇项目 (China, Unicode) | At minimum: no crash | **GREEN 0** (no news matched) | ⚠️ Didn't crash — but the news layer matched zero Chinese-character results. Engine is effectively blind to non-English-language sources. |
| 09 | Null Island Carbon (lat 0, lng 0) | GREEN, no crash | **GREEN 0** | ✅ Boundary handled. |
| 10 | Polar Cap Reforestation (Antarctica) | No crash; flag absurdity | **GREEN 0** | ⚠️ No crash — but engine silently rated an Antarctic forestry project as "LOW risk." No sanity check. |

## What this exposes — honestly

### 1. The territory signal is non-functional outside the curated 4 projects

**Every uncurated project returned `"territory_source": "none"`, `"coverage": "unknown"`, 0 territories.** That means today, the engine has **five signals, not six** — unless the project is one of the four pre-loaded ones. Native Land Digital deprecated its free tier in late 2025, and without an API key, the territory layer is dead. The README admits this; the demo language does not.

**Impact:** For Surui — a project named after an Indigenous nation — the memo wrote *"no documented Indigenous overlap."* That's not a small seam.

### 2. News-driven verdicts are non-deterministic

Mai Ndombe ran twice in this session: first GREEN 0, then AMBER 3. Same engine, same query, ~15 minutes apart. Google News RSS shifts results constantly, and we don't cache. **Investors hitting the same project on Monday and Tuesday could see different verdicts.** This wasn't acknowledged before.

### 3. The grounding sniff produces false positives

The post-LLM warning system flagged **"Evidence"** (a generic English word), **"Limited"** (an adjective), and **"Wall / Street / Journal"** (sliced from "Wall Street Journal") as ungrounded terms. None are real hallucinations. The sniff exists to catch invented citations — instead it's flagging stop-words.

### 4. Subtle LLM hallucinations the sniff did miss

For Surui, the LLM wrote *"two Mongabay entries (Thu, Tue)"* — it read RFC-2822 day-of-week strings ("Thu," "Tue,") from article dates as if they were entry labels. Similarly *"year 'Thu,'"* on Mai Ndombe. These slipped past the grounding check because they technically appeared in the evidence JSON.

### 5. Latency is wider than advertised

Range: **5.0s – 32.5s.** The "~3s" homepage claim is the *parallel data-fetch* time. **LLM synthesis adds 5–25s** depending on how much evidence it has to chew. Median full-run: ~12s. Worst: 32s (Pacajai).

### 6. The engine does not flag absurd geography

Antarctica forestry → GREEN. Mid-ocean → GREEN. No "this project location doesn't make sense" gate.

## What the engine actually does well

- **No crashes** on any of the 10. Unicode, mid-ocean, polar, fake-name — all returned a clean shape.
- **Two real cold catches** (Pacajai AMBER 5, Surui RED 11) from projects that have never been told about. The news scoring + auto-promotion path works *when* the controversy is in English-language outlets that GDELT/Google index.
- **Zero false positives on the fakes.** The fake Highland Carbon Scotland and Larimar Pine returned GREEN 0 with the LLM correctly outputting *"Evidence is insufficient."* This is the most important property and it held.
- **Shape stability:** all 10 returned the full JSON contract. No KeyError, no half-formed responses.

## What I had been overstating

| Claim | Reality |
|---|---|
| "6-signal engine" | 5 signals for any uncurated project today. Indigenous-territory is dark without a paid API key. |
| "0 crashes / 125 tests" | True. But those 125 are mostly internal unit tests and structured live queries — not adversarial unseen names. This 10-case run is a closer proxy to production load. |
| "~3s per screen" | ~3s for data fetch alone. **End-to-end median 12s, max 32s** including LLM synthesis. |
| "Anti-hallucination grounding sniff" | Catches generic English words as "ungrounded terms"; misses real LLM misreadings of date strings as entities. Needs work. |
| Verdicts are reproducible | They aren't. News results shift run-to-run; AMBER↔GREEN swings observed within minutes. |

## The honest pitch for Kopal

Sentinel **does** prove the thesis: cold, uncurated projects can be screened and a non-trivial fraction surface real signals. Surui returning RED 11 and Pacajai AMBER 5 from zero priors is the demo moment.

But this is a **prototype with three named gaps** — territory data source, English-only news, no result caching — that are roadmap items, not "implementation detail." The honest framing to her:

> "This is a working v0.3 prototype. It catches roughly half of known-bad projects from cold inference, doesn't hallucinate risk on clean ones, and exposes its own seams in the brief. The territory layer needs a paid Native Land API key, the news layer needs multilingual sources, and we need caching to make verdicts reproducible day-over-day. Those are weeks of work, not months."

That's the version of the story that holds up under her questions.
