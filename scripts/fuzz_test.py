"""Fuzz / stress test — hammer the API 25 times with random + adversarial inputs.

The point: confirm the engine never crashes, always returns valid shape,
and behaves correctly on garbage input.
"""
import os
import sys
import time
import random
import string

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app

PROJECT_NAMES = [
    "Cordillera Azul REDD+",
    "Kariba REDD+",
    "Mikoko Pamoja",
    "Random Project Z",
    "OurForest 2026",
    "Project   With   Whitespace",
    "Floresta Amazônica",
    "Project: with! punct?",
    "中国碳项目",
    "🌳 Tree Project",
]

def random_lat_lng():
    return random.uniform(-90, 90), random.uniform(-180, 180)


def adversarial_inputs():
    """Inputs designed to break things."""
    return [
        {},  # empty
        {"project_id": ""},  # empty id
        {"project_id": "vcs-doesnt-exist"},  # unknown id
        {"project_id": "adhoc"},  # adhoc with no other fields
        {"project_id": "adhoc", "name": "ab"},  # too short
        {"project_id": "adhoc", "name": "Z" * 500, "lat": 0, "lng": 0},  # too long
        {"project_id": "adhoc", "name": "ok", "lat": "blah", "lng": "blah"},  # garbage coords
        {"project_id": "adhoc", "name": "ok", "lat": 91, "lng": 0},  # out of range
        {"project_id": "adhoc", "name": "ok", "lat": -91, "lng": 0},
        {"project_id": "adhoc", "name": "ok", "lat": 0, "lng": 181},
        {"project_id": "adhoc", "name": "ok", "lat": 0, "lng": -181},
        {"project_id": "adhoc", "name": None, "lat": 0, "lng": 0},  # None name
        {"project_id": "adhoc", "name": " ", "lat": 0, "lng": 0},  # whitespace name
    ]


def main():
    client = app.test_client()
    crashes = 0
    valid_responses = 0
    expected_400s = 0
    expected_200s = 0
    total = 0

    print()
    print("=" * 80)
    print(f"{'FUZZ / STRESS TEST: 25 calls, mixed valid + adversarial':^80}")
    print("=" * 80)

    # 12 random valid adhoc projects via API
    for i in range(12):
        total += 1
        name = random.choice(PROJECT_NAMES)
        lat, lng = random_lat_lng()
        payload = {
            "project_id": "adhoc",
            "name": name,
            "country": random.choice(["Peru", "Brazil", "Indonesia", None, ""]),
            "lat": lat,
            "lng": lng,
        }
        try:
            r = client.post("/api/assess", json=payload)
            body = r.get_json()
            if r.status_code != 200:
                print(f"❌ random {i+1:>2}: HTTP {r.status_code} — {body}")
                crashes += 1
                continue
            assert "verdict" in body and body["verdict"]["color"] in ("red", "amber", "green")
            assert "territory" in body and "news" in body
            valid_responses += 1
            expected_200s += 1
            print(f"✅ random {i+1:>2}: {name[:30]:<30} @ {lat:>7.2f},{lng:>8.2f} → {body['verdict']['color']:<5}")
        except Exception as e:
            print(f"❌ random {i+1:>2}: CRASHED — {type(e).__name__}: {e}")
            crashes += 1

    # 13 adversarial inputs
    for i, payload in enumerate(adversarial_inputs(), 1):
        total += 1
        try:
            r = client.post("/api/assess", json=payload)
            body = r.get_json() if r.is_json else {}
            if r.status_code in (400, 404):
                expected_400s += 1
                print(f"✅ adv  {i:>2}: HTTP {r.status_code} (rejected)  payload={str(payload)[:55]}")
            elif r.status_code == 200 and body.get("ok"):
                # An adversarial input that survives validation must still produce valid output.
                expected_200s += 1
                print(f"✅ adv  {i:>2}: HTTP 200 valid               payload={str(payload)[:55]}")
            else:
                print(f"❌ adv  {i:>2}: HTTP {r.status_code} unexpected   payload={str(payload)[:55]}")
                crashes += 1
        except Exception as e:
            print(f"❌ adv  {i:>2}: CRASHED — {type(e).__name__}: {e}  payload={str(payload)[:50]}")
            crashes += 1

    print()
    print("=" * 80)
    print(f"  Total calls:        {total}")
    print(f"  Crashes / unexpect: {crashes}")
    print(f"  Valid 2xx:          {expected_200s}")
    print(f"  Expected 4xx:       {expected_400s}")
    print("=" * 80)
    print()
    return 0 if crashes == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
