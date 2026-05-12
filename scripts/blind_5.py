"""Blind test — 5 NEW projects the engine has never seen.
Mix: 2 real & known-covered, 1 obscure-real, 1 fictional, 1 ambiguous.
"""
import json, time, requests

API = "http://127.0.0.1:5099/api/assess"

CASES = [
    {
        "label": "A · Northern Rangelands Trust carbon program (Kenya)",
        "hypothesis": "Heavy NGO + NYT coverage since 2023 on Indigenous-rights concerns (Survival International, Maasai/Samburu communities). Should surface adverse signal. NOT in our curated ledger or sample list.",
        "payload": {"project_id": "adhoc", "name": "Northern Rangelands Trust carbon program", "country": "Kenya", "lat": 0.5, "lng": 37.5, "type": "soil carbon"},
    },
    {
        "label": "B · Bukit Tigapuluh REDD+ (Sumatra, Indonesia)",
        "hypothesis": "Frankfurt Zoological Society project with documented community-displacement history. Should overlap Indonesia geography + some adverse signal in carbon press.",
        "payload": {"project_id": "adhoc", "name": "Bukit Tigapuluh REDD+", "country": "Indonesia", "lat": -0.8, "lng": 102.5, "type": "REDD+"},
    },
    {
        "label": "C · Lower Zambezi REDD+ (Zambia)",
        "hypothesis": "BioCarbon Partners flagship — solid reputation but in low-CPI Zambia (CPI 33). Genuinely unsure what we'll catch; tests engine on obscure-but-real project.",
        "payload": {"project_id": "adhoc", "name": "Lower Zambezi REDD+ Project", "country": "Zambia", "lat": -15.6, "lng": 30.5, "type": "REDD+"},
    },
    {
        "label": "D · Lake Como Reforestation Project (Italy, FICTIONAL)",
        "hypothesis": "Fake project in high-CPI OECD country with stable forest cover. Should return GREEN. Tests no-hallucination on attractive-sounding fake.",
        "payload": {"project_id": "adhoc", "name": "Lake Como Reforestation Project", "country": "Italy", "lat": 46.0, "lng": 9.3, "type": "ARR"},
    },
    {
        "label": "E · Tasmania Blue Carbon Initiative (Australia)",
        "hypothesis": "Ambiguous — there is real blue-carbon research in Tasmania but no specific Verra project by this name. Tests engine on ambiguous-real geography + niche project class.",
        "payload": {"project_id": "adhoc", "name": "Tasmania Blue Carbon Initiative", "country": "Australia", "lat": -42.0, "lng": 147.0, "type": "blue carbon"},
    },
]

def run():
    out = []
    for c in CASES:
        t0 = time.time()
        try:
            r = requests.post(API, json=c["payload"], timeout=60)
            latency = round(time.time() - t0, 2)
            if r.status_code != 200:
                out.append({"label": c["label"], "status": r.status_code, "latency_s": latency, "error": r.text[:200]})
                continue
            d = r.json()
            v = d["verdict"]
            t = d["territory"]
            n = d["news"]
            g = d.get("governance", {})
            e = d.get("environmental", {})
            f = d.get("fpic", {})
            s = d.get("synthesis", {}) or {}
            out.append({
                "label": c["label"],
                "hypothesis": c["hypothesis"],
                "latency_s": latency,
                "verdict_color": v["color"],
                "verdict_score": v["score"],
                "verdict_label": v["label"],
                "territory_source": t.get("source"),
                "territory_count": len(t.get("territories", []) or []),
                "news_total": n.get("total"),
                "news_adverse": n.get("adverse_count"),
                "news_adverse_titles": [a["title"][:120] for a in n.get("articles", []) if a.get("adverse_score", 0) > 0][:5],
                "litigation_count": len(d.get("litigation", [])),
                "ngo_count": len(d.get("ngo_complaints", [])),
                "env_color": e.get("color"),
                "env_band": e.get("band"),
                "gov_color": g.get("color"),
                "gov_rationale": g.get("rationale"),
                "fpic_color": f.get("color"),
                "fpic_label": f.get("label"),
                "fpic_summary": {c["id"]: c["status"] for c in (f.get("checks") or [])},
                "synth_text": (s.get("text") or "")[:600],
                "synth_warnings": s.get("warnings") or [],
            })
        except Exception as ex:
            out.append({"label": c["label"], "status": "EXC", "latency_s": round(time.time()-t0, 2), "error": f"{type(ex).__name__}: {ex}"})
    return out

if __name__ == "__main__":
    print(json.dumps(run(), indent=2, ensure_ascii=False))
