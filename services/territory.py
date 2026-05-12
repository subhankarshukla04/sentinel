"""Indigenous-territory overlap engine.

Multi-tier resolution. Each tier is independently testable and falls through
on failure so the overall call always returns *something* useful — never None,
never an exception bubbling to the user.

Tiers, in priority order:
 1. Native Land Digital live API   (best, requires NATIVE_LAND_API_KEY)
 2. OSM Overpass aboriginal_lands  (free, global, flaky — single try with short timeout)
 3. Cached per-project overlay     (curated for the four sample projects + future curation)
 4. Empty result with coverage_note (honest "we don't know")
"""
import os
import json
import os.path
from . import http

NL_API = "https://native-land.ca/api/index.php"
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def _via_native_land(lat: float, lng: float) -> dict | None:
    api_key = os.environ.get("NATIVE_LAND_API_KEY")
    if not api_key:
        return None
    res = http.get_json(NL_API, params={"maps": "territories", "position": f"{lat},{lng}", "key": api_key}, timeout=6.0)
    if not res.get("ok"):
        return None
    data = res.get("data") or []
    territories = []
    for feature in data:
        props = feature.get("properties", {}) if isinstance(feature, dict) else {}
        name = props.get("Name") or props.get("name")
        if not name:
            continue
        territories.append({"name": name, "url": props.get("description")})
    return {"source": "native-land-live", "territories": territories}


def _via_overpass(lat: float, lng: float, radius_km: float = 30.0) -> dict | None:
    radius_m = int(radius_km * 1000)
    query = (
        f'[out:json][timeout:4];'
        f'(nwr["boundary"="aboriginal_lands"](around:{radius_m},{lat},{lng});'
        f'nwr["protected_area"~"indigenous|aboriginal",i](around:{radius_m},{lat},{lng});'
        f');out tags center 20;'
    )
    for endpoint in OVERPASS_ENDPOINTS[:1]:  # Single endpoint, no inter-mirror retry — too slow.
        try:
            import requests
            r = requests.post(endpoint, data={"data": query}, timeout=4.0,
                              headers={"User-Agent": http.UA})
            if r.status_code != 200:
                continue
            text = r.text
            if not text.strip().startswith("{"):
                continue
            data = json.loads(text)
        except Exception:
            continue
        elements = data.get("elements") or []
        names = []
        for el in elements:
            tags = el.get("tags") or {}
            name = tags.get("name") or tags.get("name:en") or tags.get("official_name")
            if not name:
                continue
            if name not in names:
                names.append(name)
        if names:
            return {
                "source": "openstreetmap",
                "territories": [{"name": n, "url": None} for n in names[:10]],
            }
    return None


def _via_cached(cached: list | None) -> dict | None:
    if cached is None:
        return None
    return {"source": "curated-cache", "territories": list(cached)}


def territories_at(lat: float, lng: float, cached: list | None = None) -> dict:
    """Return Indigenous territories overlapping (lat, lng).

    Tier order (each falls through on miss):
      1. Native Land Digital live API   (NATIVE_LAND_API_KEY required)
      2. OSM Overpass                   (SENTINEL_USE_OVERPASS=1 — opt-in; slow + sparse)
      3. Curated cached overlay         (per-project, hand-curated)
      4. Empty result with coverage=unknown (honest "we don't know")

    Coverage flag distinguishes 'high' (live API), 'curated' (empty cache that's
    been verified by a curator), 'partial' (cache with hits), 'unknown' (no source).
    """
    tiers = [(lambda: _via_native_land(lat, lng), "high")]
    if os.environ.get("SENTINEL_USE_OVERPASS") == "1":
        tiers.append((lambda: _via_overpass(lat, lng), "high"))
    tiers.append((lambda: _via_cached(cached), "partial" if cached else "curated"))

    for fn, coverage in tiers:
        result = fn()
        if result is not None:
            count = len(result["territories"])
            return {
                "ok": True,
                "source": result["source"],
                "territories": result["territories"],
                "count": count,
                "coverage": coverage if (coverage != "partial" or count) else "curated",
            }
    return {
        "ok": True,
        "source": "none",
        "territories": [],
        "count": 0,
        "coverage": "unknown",
        "note": "no Indigenous-territory data source available; set NATIVE_LAND_API_KEY for live coverage.",
    }
