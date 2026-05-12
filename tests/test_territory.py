from services import territory


def test_falls_through_to_cached_when_no_apis():
    cached = [{"name": "Test Nation", "url": None}]
    r = territory.territories_at(0.0, 0.0, cached=cached)
    assert r["ok"] is True
    assert r["count"] == 1
    assert r["source"] == "curated-cache"
    assert r["coverage"] == "partial"


def test_returns_empty_with_unknown_coverage_when_nothing_works(mocker):
    mocker.patch.object(territory, "_via_native_land", return_value=None)
    mocker.patch.object(territory, "_via_overpass", return_value=None)
    r = territory.territories_at(0.0, 0.0, cached=None)
    assert r["ok"] is True
    assert r["count"] == 0
    assert r["coverage"] == "unknown"
    assert "note" in r


def test_uses_native_land_when_key_present(mocker, monkeypatch):
    monkeypatch.setenv("NATIVE_LAND_API_KEY", "sk-test")
    fake = [{"properties": {"Name": "Kichwa", "description": "https://x"}}]
    mocker.patch.object(territory.http, "get_json", return_value={"ok": True, "data": fake, "status": 200})
    r = territory.territories_at(-7.65, -76.0)
    assert r["source"] == "native-land-live"
    assert r["count"] == 1
    assert r["territories"][0]["name"] == "Kichwa"


def test_native_land_failure_falls_through_to_overpass(mocker, monkeypatch):
    monkeypatch.setenv("NATIVE_LAND_API_KEY", "sk-test")
    monkeypatch.setenv("SENTINEL_USE_OVERPASS", "1")
    mocker.patch.object(territory.http, "get_json", return_value={"ok": False, "error": "boom"})
    mocker.patch.object(territory, "_via_overpass", return_value={"source": "openstreetmap", "territories": [{"name": "Foo", "url": None}]})
    r = territory.territories_at(0.0, 0.0)
    assert r["source"] == "openstreetmap"


def test_overpass_returns_high_coverage_label(mocker, monkeypatch):
    monkeypatch.setenv("SENTINEL_USE_OVERPASS", "1")
    mocker.patch.object(territory, "_via_native_land", return_value=None)
    mocker.patch.object(territory, "_via_overpass", return_value={"source": "openstreetmap", "territories": [{"name": "X", "url": None}]})
    r = territory.territories_at(0.0, 0.0)
    assert r["coverage"] == "high"


def test_overpass_disabled_by_default(mocker, monkeypatch):
    monkeypatch.delenv("SENTINEL_USE_OVERPASS", raising=False)
    spy = mocker.spy(territory, "_via_overpass")
    mocker.patch.object(territory, "_via_native_land", return_value=None)
    territory.territories_at(0.0, 0.0, cached=None)
    assert spy.call_count == 0


def test_empty_cache_returns_curated_coverage(mocker, monkeypatch):
    monkeypatch.delenv("NATIVE_LAND_API_KEY", raising=False)
    monkeypatch.delenv("SENTINEL_USE_OVERPASS", raising=False)
    r = territory.territories_at(0.0, 0.0, cached=[])
    # empty curated list = explicit "we checked, nothing here"
    assert r["coverage"] == "curated"
    assert r["count"] == 0
