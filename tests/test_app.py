"""Integration tests against the Flask app, with all external services mocked."""
import pytest


@pytest.fixture(autouse=True)
def _mock_external(mocker):
    # Block all real HTTP from these tests
    mocker.patch("services.territory._via_native_land", return_value=None)
    mocker.patch("services.territory._via_overpass", return_value=None)
    mocker.patch("services.news._via_gdelt", return_value=[])
    mocker.patch("services.news._via_google_news", return_value=[])


def test_homepage_renders(app_client):
    r = app_client.get("/")
    assert r.status_code == 200
    assert b"Sentinel" in r.data
    assert b"Cordillera Azul" in r.data


def test_healthz(app_client):
    r = app_client.get("/healthz")
    assert r.status_code == 200
    assert r.get_json() == {"ok": True, "service": "sentinel", "version": "0.3"}


def test_assess_known_project_renders(app_client):
    r = app_client.post("/assess", data={"project_id": "vcs-985"})
    assert r.status_code == 200
    assert b"Cordillera Azul" in r.data
    assert b"SAFEGUARDS VERDICT" in r.data


def test_assess_clean_project_is_green(app_client):
    r = app_client.post("/assess", data={"project_id": "vcs-1722"})
    assert r.status_code == 200
    assert b"Mikoko Pamoja" in r.data
    assert b"LOW social-license risk" in r.data


def test_assess_adhoc_with_invalid_lat(app_client):
    r = app_client.post("/assess", data={
        "project_id": "adhoc",
        "name": "Some Project",
        "lat": "999",
        "lng": "0",
    })
    assert r.status_code == 400
    assert b"latitude" in r.data.lower()


def test_assess_adhoc_with_empty_name(app_client):
    r = app_client.post("/assess", data={
        "project_id": "adhoc",
        "name": "",
        "lat": "0",
        "lng": "0",
    })
    assert r.status_code == 400


def test_assess_adhoc_with_garbage_coords(app_client):
    r = app_client.post("/assess", data={
        "project_id": "adhoc",
        "name": "Test Project",
        "lat": "not-a-number",
        "lng": "0",
    })
    assert r.status_code == 400


def test_api_assess_returns_json(app_client):
    r = app_client.post("/api/assess", json={"project_id": "vcs-1722"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True
    assert "verdict" in body
    assert "territory" in body
    assert "news" in body


def test_api_assess_unknown_project_id(app_client):
    r = app_client.post("/api/assess", json={"project_id": "vcs-doesnt-exist"})
    assert r.status_code == 404


def test_api_assess_validation_error_returns_400(app_client):
    r = app_client.post("/api/assess", json={"project_id": "adhoc", "name": "ab", "lat": 0, "lng": 0})
    assert r.status_code == 400
    assert r.get_json()["ok"] is False


def test_api_assess_adhoc_happy_path(app_client):
    r = app_client.post("/api/assess", json={
        "project_id": "adhoc",
        "name": "My New Carbon Project",
        "country": "Brazil",
        "lat": -3.0,
        "lng": -60.0,
    })
    assert r.status_code == 200
    body = r.get_json()
    assert body["project"]["name"] == "My New Carbon Project"
    assert body["verdict"]["color"] in ("green", "amber", "red")


def test_assess_does_not_crash_when_news_returns_garbage(app_client, mocker):
    # Make news return non-list garbage
    mocker.patch("services.news.adverse_news", return_value={"ok": False, "articles": [], "adverse_count": 0, "total": 0, "sources_used": []})
    r = app_client.post("/assess", data={"project_id": "vcs-985"})
    assert r.status_code == 200
