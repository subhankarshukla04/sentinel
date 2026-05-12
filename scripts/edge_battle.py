"""
Edge-case battle test — 10 projects the engine has never seen.
None are in data/sample_projects.json or data/known_risks.json.
Goal: honest performance check, no curated padding.
"""
import json, time, requests, sys

API = "http://127.0.0.1:5099/api/assess"

CASES = [
    {
        "label": "01 · Mai Ndombe REDD+",
        "hypothesis": "Documented community-rights controversy (Wildlife Works flagship). Should detect via news/litigation/NGO inference. NOT in ledger.",
        "payload": {"project_id": "adhoc", "name": "Mai Ndombe REDD+", "country": "DRC", "lat": -2.5, "lng": 18.3, "type": "REDD+"},
    },
    {
        "label": "02 · Katingan Mentaya Peat REDD+",
        "hypothesis": "Indonesian peat REDD+, well-documented in carbon press. Should produce some adverse news + community signals.",
        "payload": {"project_id": "adhoc", "name": "Katingan Mentaya Project", "country": "Indonesia", "lat": -2.7, "lng": 113.2, "type": "REDD+"},
    },
    {
        "label": "03 · Pacajai REDD+",
        "hypothesis": "Verra-flagged Amazon project; smaller media footprint, less curated coverage — tests news depth.",
        "payload": {"project_id": "adhoc", "name": "Pacajai REDD+ Project", "country": "Brazil", "lat": -1.6, "lng": -50.5, "type": "REDD+"},
    },
    {
        "label": "04 · Surui Forest Carbon",
        "hypothesis": "Historic Indigenous-led project with over-crediting controversy. Should overlap Suruí territory + some adverse news.",
        "payload": {"project_id": "adhoc", "name": "Surui Forest Carbon Project", "country": "Brazil", "lat": -10.9, "lng": -61.7, "type": "REDD+"},
    },
    {
        "label": "05 · Rimba Raya Biodiversity Reserve",
        "hypothesis": "Indonesian Verra project, recent press on community grievances and contract disputes.",
        "payload": {"project_id": "adhoc", "name": "Rimba Raya Biodiversity Reserve", "country": "Indonesia", "lat": -3.0, "lng": 112.5, "type": "REDD+"},
    },
    {
        "label": "06 · Larimar Pine Plantation (FICTIONAL clean control)",
        "hypothesis": "Fake project name in Dominican Republic. Should return LOW / GREEN with zero signal — proves engine doesn't hallucinate risk.",
        "payload": {"project_id": "adhoc", "name": "Larimar Pine Plantation", "country": "Dominican Republic", "lat": 18.6, "lng": -71.4, "type": "ARR"},
    },
    {
        "label": "07 · Highland Carbon Scotland (FICTIONAL clean control)",
        "hypothesis": "Fake UK project, high-CPI country. Should return LOW / GREEN — proves no false positives in OECD geographies.",
        "payload": {"project_id": "adhoc", "name": "Highland Carbon Scotland", "country": "United Kingdom", "lat": 57.0, "lng": -4.5, "type": "ARR"},
    },
    {
        "label": "08 · 大兴安岭碳汇项目 (Greater Khingan, Unicode + China)",
        "hypothesis": "Non-ASCII name + low-press, low-CPI country. Tests Unicode handling and whether news scraper can match Chinese-character query.",
        "payload": {"project_id": "adhoc", "name": "大兴安岭碳汇项目", "country": "China", "lat": 51.5, "lng": 124.5, "type": "ARR"},
    },
    {
        "label": "09 · Null Island Carbon (0,0)",
        "hypothesis": "Coords on the equator/prime meridian intersection — mid-Atlantic. Should return zero territory overlap, no crash.",
        "payload": {"project_id": "adhoc", "name": "Null Island Carbon", "country": "International Waters", "lat": 0.001, "lng": 0.001, "type": "blue carbon"},
    },
    {
        "label": "10 · Polar Cap Reforestation (Antarctica)",
        "hypothesis": "Invalid geography for forestry. Should not crash; ideally flag low/no signal coverage.",
        "payload": {"project_id": "adhoc", "name": "Polar Cap Reforestation", "country": "Antarctica", "lat": -89.5, "lng": 0.0, "type": "ARR"},
    },
]

def run():
    results = []
    for c in CASES:
        t0 = time.time()
        try:
            r = requests.post(API, json=c["payload"], timeout=45)
            latency = time.time() - t0
            ok = r.status_code == 200
            if ok:
                data = r.json()
                v = data.get("verdict", {})
                territory = data.get("territory", {})
                news = data.get("news", {})
                litigation = data.get("litigation", [])
                ngo = data.get("ngo_complaints", [])
                synth = data.get("synthesis", {}) or {}
                results.append({
                    "label": c["label"],
                    "hypothesis": c["hypothesis"],
                    "status": r.status_code,
                    "latency_s": round(latency, 2),
                    "verdict": v.get("color"),
                    "score": v.get("score"),
                    "label_text": v.get("label"),
                    "territory_source": territory.get("source"),
                    "territory_coverage": territory.get("coverage"),
                    "territory_count": len(territory.get("territories", []) or []),
                    "news_sources": news.get("sources_used"),
                    "news_total": news.get("total"),
                    "news_adverse": news.get("adverse_count"),
                    "litigation_count": len(litigation),
                    "ngo_count": len(ngo),
                    "synth_first_line": (synth.get("safeguards_section") or synth.get("note") or "")[:200],
                    "synth_warnings": synth.get("warnings") or synth.get("flags"),
                })
            else:
                results.append({
                    "label": c["label"],
                    "hypothesis": c["hypothesis"],
                    "status": r.status_code,
                    "latency_s": round(latency, 2),
                    "error": r.text[:300],
                })
        except Exception as e:
            results.append({
                "label": c["label"],
                "hypothesis": c["hypothesis"],
                "status": "EXCEPTION",
                "latency_s": round(time.time() - t0, 2),
                "error": f"{type(e).__name__}: {e}",
            })
    return results

if __name__ == "__main__":
    out = run()
    print(json.dumps(out, indent=2, ensure_ascii=False))
