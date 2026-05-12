import json, requests
API = "http://127.0.0.1:5099/api/assess"
CASES = [
    ("Mai Ndombe REDD+", "DRC", -2.5, 18.3),
    ("Surui Forest Carbon Project", "Brazil", -10.9, -61.7),
    ("Larimar Pine Plantation", "Dominican Republic", 18.6, -71.4),
]
for name, country, lat, lng in CASES:
    r = requests.post(API, json={"project_id": "adhoc", "name": name, "country": country, "lat": lat, "lng": lng, "type": "REDD+"}, timeout=45)
    d = r.json()
    print("=" * 80); print(name)
    print("verdict:", d["verdict"]["color"], d["verdict"]["score"])
    s = d.get("synthesis") or {}
    print("synth.ok:", s.get("ok"))
    print("synth.model:", s.get("model"))
    print("synth.warnings:", s.get("warnings"))
    print("--- synth.text ---")
    print(s.get("text") or "[no text returned]")
