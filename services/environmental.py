"""Environmental signal — country forest-cover trend via World Bank API.

Pulls the AG.LND.FRST.ZS indicator (forest area % of land area) over the last
five available years and returns the trend. A declining forest-cover trend in
the host country is a meta-signal: it doesn't tell you about a single project,
but it tells the analyst whether they're operating in a deforestation-active
geography. Free, no auth, takes ~600ms.
"""
from __future__ import annotations
import re
from . import http

WB = "https://api.worldbank.org/v2/country/{iso}/indicator/AG.LND.FRST.ZS"

# Minimal name→ISO2 mapping for carbon-project hotspot countries.
ISO2 = {
    "peru": "PE", "brazil": "BR", "colombia": "CO", "ecuador": "EC", "bolivia": "BO",
    "indonesia": "ID", "malaysia": "MY", "philippines": "PH", "vietnam": "VN",
    "cambodia": "KH", "laos": "LA", "thailand": "TH", "myanmar": "MM",
    "kenya": "KE", "tanzania": "TZ", "uganda": "UG", "zimbabwe": "ZW",
    "mozambique": "MZ", "madagascar": "MG", "zambia": "ZM", "ghana": "GH",
    "nigeria": "NG", "sierra leone": "SL", "liberia": "LR",
    "democratic republic of the congo": "CD", "republic of the congo": "CG",
    "central african republic": "CF", "cameroon": "CM", "gabon": "GA", "ethiopia": "ET",
    "bangladesh": "BD", "india": "IN", "pakistan": "PK", "nepal": "NP",
    "bhutan": "BT", "sri lanka": "LK", "papua new guinea": "PG",
    "australia": "AU", "new zealand": "NZ", "costa rica": "CR", "mexico": "MX",
    "chile": "CL", "argentina": "AR", "paraguay": "PY", "suriname": "SR", "guyana": "GY",
}


def country_environment(country: str | None) -> dict:
    """Return forest-cover trend bundle for the country."""
    if not country:
        return {"ok": False, "note": "no country provided", "trend": None, "band": "unknown"}
    iso = ISO2.get(country.strip().lower())
    if not iso:
        return {"ok": True, "country": country, "trend": None, "band": "uncovered",
                "note": "country not in ISO map; v0.3 stretches the lookup to a complete table."}

    res = http.get_json(WB.format(iso=iso), params={"format": "json", "date": "2019:2023"}, timeout=4.0)
    if not res.get("ok") or not res.get("data"):
        return {"ok": False, "country": country, "trend": None, "band": "unreachable",
                "note": f"World Bank API: {res.get('error', 'no data')}"}

    data = res["data"]
    if not isinstance(data, list) or len(data) < 2:
        return {"ok": False, "country": country, "trend": None, "band": "unreachable"}

    rows = data[1] if isinstance(data[1], list) else []
    points = []
    for row in rows:
        if isinstance(row, dict) and row.get("value") is not None:
            try:
                points.append((int(row["date"]), float(row["value"])))
            except (TypeError, ValueError):
                continue
    points.sort()

    if len(points) < 2:
        return {"ok": False, "country": country, "trend": None, "band": "unreachable",
                "note": "insufficient World Bank data points"}

    start_year, start_pct = points[0]
    end_year, end_pct = points[-1]
    delta = end_pct - start_pct
    annual = delta / max(1, (end_year - start_year))

    if annual <= -0.3:
        band, color = "active deforestation context", "red"
    elif annual <= -0.05:
        band, color = "gradual forest loss", "amber"
    elif annual < 0.1:
        band, color = "stable forest cover", "green"
    else:
        band, color = "net reforestation context", "green"

    return {
        "ok": True,
        "country": country,
        "iso2": iso,
        "start_year": start_year,
        "end_year": end_year,
        "start_pct": round(start_pct, 2),
        "end_pct": round(end_pct, 2),
        "annual_change_pp": round(annual, 3),
        "band": band,
        "color": color,
        "points": points,
        "source": "World Bank — Forest Area (% of land area)",
        "source_url": "https://data.worldbank.org/indicator/AG.LND.FRST.ZS",
    }
