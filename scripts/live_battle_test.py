"""Live battle test — hit the engine against arbitrary real projects + edge cases.

This is the "doesn't break no matter what situation" check. Calls the real
APIs (GDELT, Google News, OSM Overpass), measures latency, and prints a
matrix of (project, hits per signal, verdict, time).

Run: python scripts/live_battle_test.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import _assess
from services.validation import clean_name, clean_coord, ValidationError

# Mix of: known-controversial, large-but-clean, small-niche, edge cases.
SCENARIOS = [
    # name, country, lat, lng, project_id (or None)
    ("Cordillera Azul REDD+", "Peru", -7.65, -76.0, "vcs-985"),
    ("Kariba REDD+", "Zimbabwe", -16.55, 28.85, "vcs-902"),
    ("Alto Mayo Conservation", "Peru", -5.7, -77.7, "vcs-934"),
    ("Mikoko Pamoja Mangrove", "Kenya", -4.39, 39.51, "vcs-1722"),
    # Real projects NOT in the curated ledger — engine must still work
    ("Rimba Raya Biodiversity Reserve", "Indonesia", -3.07, 113.0, None),
    ("Katingan Mentaya REDD+", "Indonesia", -2.5, 113.5, None),
    ("Northern Kenya Grassland Carbon", "Kenya", 1.5, 37.0, None),
    ("Madre de Dios Amazon REDD+", "Peru", -12.5, -69.5, None),
    ("Sebangau Forest", "Indonesia", -2.3, 113.9, None),
    # Likely-clean
    ("Bhutan National Reforestation", "Bhutan", 27.5, 90.5, None),
    # Edge cases
    ("Mid-Ocean test point", None, 0.0, 0.0, None),
    ("North Pole edge", None, 89.9, 0.0, None),
    ("South Pole edge", None, -89.9, 0.0, None),
    ("Antimeridian edge", None, 0.0, 179.9, None),
    ("Unicode Ñame Ámazon", "Brasil", -3.0, -60.0, None),
    ("Extremely Long Project Name " * 5, "Test", 0.1, 0.1, None),
]


def fmt_row(label, terr_count, news_count, lit_count, ngo_count, color, score, ms, sources, coverage):
    badge = {"red": "🔴", "amber": "🟡", "green": "🟢"}.get(color, "⚪")
    return f"{badge} {label[:38]:<38} | terr={terr_count:>2} news={news_count:>2}({sources or '-':<15}) lit={lit_count:>2} ngo={ngo_count:>2} | {score:>2}={color:<5} cov={coverage:<7} | {ms:>5}ms"


def run_scenario(name, country, lat, lng, project_id):
    t0 = time.time()
    try:
        clean_name(name)
        lat_f, lng_f = clean_coord(lat, lng)
    except ValidationError as e:
        return {"label": name[:38], "error": f"validation: {e}", "ms": 0}

    if project_id:
        from services import registry
        project = registry.get_project(project_id)
        if not project:
            project = None
    else:
        project = None

    if project is None:
        project = {
            "id": "adhoc",
            "name": clean_name(name),
            "country": country,
            "lat": lat_f,
            "lng": lng_f,
            "registry": "ad hoc",
            "type": "live-test",
            "cached_territories": None,
        }

    try:
        bundle = _assess(project)
        ms = int((time.time() - t0) * 1000)
        return {
            "label": name,
            "terr_count": len(bundle["territories"]),
            "news_count": bundle["news"].get("adverse_count", 0),
            "news_total": bundle["news"].get("total", 0),
            "lit_count": len(bundle["litigation"]),
            "ngo_count": len(bundle["ngo"]),
            "color": bundle["overall"]["color"],
            "score": bundle["overall"]["score"],
            "coverage": bundle["overall"]["territory_coverage"],
            "sources": ",".join(bundle["news"].get("sources_used", []) or []),
            "ms": ms,
        }
    except Exception as e:
        ms = int((time.time() - t0) * 1000)
        return {"label": name, "error": f"{type(e).__name__}: {e}", "ms": ms}


def main():
    print()
    print("=" * 110)
    print(f"{'BATTLE TEST: Sentinel engine v0.2 across {} scenarios'.format(len(SCENARIOS)):^110}")
    print("=" * 110)
    print()

    crashed = 0
    high_count = 0
    medium_count = 0
    low_count = 0
    total_ms = 0
    for sc in SCENARIOS:
        res = run_scenario(*sc)
        if "error" in res:
            print(f"❌ {res['label'][:38]:<38} | CRASHED: {res['error']}")
            crashed += 1
            continue
        total_ms += res["ms"]
        if res["color"] == "red":
            high_count += 1
        elif res["color"] == "amber":
            medium_count += 1
        else:
            low_count += 1
        print(fmt_row(
            res["label"], res["terr_count"], res["news_count"],
            res["lit_count"], res["ngo_count"], res["color"], res["score"],
            res["ms"], res["sources"], res["coverage"],
        ))
        time.sleep(1.5)  # be polite to free APIs

    print()
    print("=" * 110)
    print(f"  Crashed:  {crashed}")
    print(f"  HIGH:     {high_count}")
    print(f"  MEDIUM:   {medium_count}")
    print(f"  LOW:      {low_count}")
    if (len(SCENARIOS) - crashed) > 0:
        print(f"  Avg time: {total_ms // max(1, (len(SCENARIOS) - crashed))} ms")
    print("=" * 110)
    print()

    return 0 if crashed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
