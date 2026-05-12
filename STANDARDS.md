# Sentinel — standards anchors

Every threshold the engine uses is anchored to a public, citable source. Where we proxy (because a project-level dataset isn't available on the free tier), we say so explicitly and name the upgrade path.

## Headline frame: ICVCM Core Carbon Principles, CCP #5

Sentinel is a screening layer for **ICVCM Core Carbon Principle #5 — *Sustainable development benefits and safeguards***. CCP #5 requires that carbon credit programs ensure projects:

> *"have in place or specify robust social and environmental safeguards, including provisions to ensure free, prior and informed consent of any Indigenous Peoples or local communities likely to be affected by the project, transparent grievance mechanisms, and procedures to identify, prevent and mitigate adverse social or environmental impacts."*
> — ICVCM, *Core Carbon Principles, Assessment Framework and Assessment Procedure*, March 2023 (Section 5)

We map our six signals to that text. We don't claim to be CCP-certified; we claim to be a defensible first-pass screen *for* a CCP-aligned DD process.

| Sentinel signal | CCP #5 sub-criterion | Anchor |
|---|---|---|
| Indigenous-territory overlap | "ensure free, prior and informed consent of any Indigenous Peoples … likely to be affected" | UNDRIP Articles 10/19/32; ILO Convention 169 |
| FPIC procedural checklist (4 items) | "free, prior and informed consent" — treated as a *procedural* obligation, not a binary | UN-REDD FPIC Guidelines 2013; Cancun safeguards (UNFCCC 1/CP.16, App. I) |
| Adverse news + NGO complaints | "procedures to identify, prevent and mitigate adverse social or environmental impacts" | CCP #5 |
| Active litigation | "grievance mechanisms" — escalated grievances reaching court | CCP #5; Cancun safeguard 2(d) |
| Environmental band (forest-cover trend) | "environmental safeguards" — non-permanence and leakage proxies | CCP #4 (Permanence) overlap; World Bank AG.LND.FRST.ZS |
| Governance band (CPI) | Country-level enabling-environment proxy for safeguards enforcement | TI CPI 2024 |

## Per-signal threshold provenance

### 1. Territory — Indigenous-land overlap
- **Source:** Native Land Digital (free tier deprecated late 2025; bundled overlay used for sample projects).
- **Threshold:** any overlap → flag. Number of overlapping nations contributes to score (capped at 2).
- **Defensibility:** binary detection is the standard for FPIC scoping; severity is left to the analyst.
- **Upgrade path:** wire a Native Land API key for full coverage of uncurated projects.

### 2. News — adverse media (revised v0.3)
- **Sources:** GDELT 2.0 DOC API · Google News RSS.
- **Threshold:** an article is "adverse" only when its title contains **both** a safeguards-topic keyword **and** an adverse-claim keyword. NGO-domain articles get +1 bonus.
- **Defensibility:** topic+claim co-occurrence prevents the *"Project secures FPIC"* false positive that plagued v0.2. NGO domain boost is anchored to the *Carbon Market Watch / Survival International / Mongabay* sources that Bloomberg and FT routinely cite.
- **Upgrade path:** swap keyword scorer for an LLM-per-article claim classifier ("is this article making an adverse claim about the project?"). Significant cost burn; deferred to v0.4.

### 3. Litigation — active climate cases
- **Source:** Sabin Center for Climate Change Law — Climate Case Chart.
- **Threshold:** any case linked by name or developer → flag (`+3` per case).
- **Defensibility:** Sabin Center is the field-standard registry. Cited in IPCC AR6 WG3 Ch. 15.
- **Upgrade path:** severity-weight by stage (injunction > pending > dismissed). Requires Sabin's API.

### 4. NGO complaints
- **Source:** curated ledger (Carbon Market Watch, Survival International, Forest Peoples Programme, Rainforest Foundation) + auto-promoted from NGO-domain adverse articles.
- **Threshold:** any complaint → flag (`+2` per).
- **Defensibility:** the four named NGOs are the orgs most cited by Bloomberg, FT, NYT and Mongabay on carbon-project complaints. Industry-recognised.

### 5. Environmental — country forest-cover trend
- **Source:** World Bank, *Forest Area (% of land area)* — indicator `AG.LND.FRST.ZS`. Five-year window.
- **Bands** (annual percentage-point change):
  - `≤ −0.3 pp/yr` → RED ("active deforestation context")
  - `−0.3 to −0.05 pp/yr` → AMBER ("gradual forest loss")
  - `> −0.05 pp/yr` → GREEN
- **Defensibility:** FAO's *Global Forest Resources Assessment 2020* characterises annual net loss above 0.3% as "high deforestation rate." The amber threshold reflects sustained non-trivial loss.
- **Honest seam:** this is a **country-level** proxy. A REDD+ project covering 0.001% of Brazil's landmass shouldn't be judged by Brazil's national trend. The proper measure is project-polygon GLAD alerts via Global Forest Watch — slated for v0.4.

### 6. Governance — country CPI (revised v0.3)
- **Source:** Transparency International, *Corruption Perceptions Index 2024*.
- **Bands** (anchored to TI's own published numbers, not invented cut-offs):
  - `CPI < 30` → RED — TI 2024 descriptor: *"countries with serious corruption problems"*
  - `30 ≤ CPI < 43` → AMBER — below TI 2024 global average of 43
  - `CPI ≥ 43` → GREEN — at or above TI 2024 global average
- **Defensibility:** every threshold cites a TI-published figure. The 43 global average is in TI's 2024 announcement.
- **Honest seam:** like #5, this is country-level. Useful as an enabling-environment proxy, not a project-level read.

### 7. FPIC procedural checklist (new in v0.3)
- **Anchors:** UNDRIP Articles 10, 19, 32 · ILO Convention 169 · UN-REDD FPIC Guidelines 2013 · Cancun safeguards (UNFCCC 1/CP.16, Appendix I).
- **Checks** (each pass / fail / insufficient / not applicable):
  1. **Consultation documented** — fail if news alleges "without consultation"; N/A if no Indigenous overlap.
  2. **Consent obtained** — fail if news alleges "without consent" or "consent withdrawn"; N/A if no Indigenous overlap.
  3. **Grievance mechanism** — fail if active NGO complaints or litigation (grievances have escalated outside the project mechanism); insufficient otherwise.
  4. **No forced displacement** — fail if news alleges "evicted / displaced / land grab"; N/A if no Indigenous overlap.
- **Verdict rollup:**
  - ≥ 2 fails → RED · 1 fail → AMBER · only insufficiencies → AMBER · clean → GREEN.
- **Defensibility:** the 4-check structure mirrors the UN-REDD FPIC operational checklist (consultation → consent → mechanism → withdrawal). Every check cites a public source. Defaulting to "insufficient" is honest — a screen reads public signals; a DD analyst reads project documents.

## Composite verdict thresholds

- **Score ≥ 8** → RED "HIGH social-license risk"
- **Score 3–7** → AMBER "MEDIUM social-license risk"
- **Score < 3** → GREEN "LOW social-license risk"

These three breakpoints are heuristic — they balance signal severity against false-positive rate. They are *not* claimed to be industry-standard. They are claimed to be *transparent and tunable*: the rule lives in `services/score.py` and an analyst can adjust the breakpoints with a single-line code change. We deliberately chose a rule-based composite over a model because rule-based scores are litigation-defensible; a model's "0.73 risk score" is not.

## What we don't claim

- We do **not** claim to be ICVCM certified or label-eligible.
- We do **not** claim to replace a project workpaper or DD memo.
- We do **not** claim project-polygon precision today; country-level proxies are labelled as such.
- We do **not** claim FPIC adjudication — the checklist *flags* where a DD analyst should pull project documents.

## Roadmap (named gaps, not aspirations)

| Gap | Today | v0.4 plan |
|---|---|---|
| Indigenous overlap dark for uncurated projects | bundled overlay only | Native Land API key wired |
| News scoring keyword-only | topic+claim co-occurrence (v0.3) | LLM-per-article claim classifier |
| Country-level environmental + governance | World Bank + TI CPI | Project-polygon GLAD alerts + WGI Control of Corruption percentile |
| Litigation stage not weighted | flat `+3` per case | Severity weight: injunction > pending > dismissed |
| No recency decay on news | uniform 24-month window | Exponential decay `exp(−days/365)` |
| No developer-level aggregation | per-project only | Developer portfolio rollup |
