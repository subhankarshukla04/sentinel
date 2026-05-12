from services import http


class FakeResponse:
    def __init__(self, status_code=200, text="", json_data=None):
        self.status_code = status_code
        self.text = text
        self._json = json_data

    def json(self):
        if self._json is None:
            raise ValueError("not json")
        return self._json


def test_get_json_happy(mocker):
    mocker.patch("services.http.requests.get", return_value=FakeResponse(200, "{}", {"hello": "world"}))
    r = http.get_json("http://x")
    assert r["ok"] is True
    assert r["data"] == {"hello": "world"}


def test_get_json_returns_text_error_on_200_with_text_body(mocker):
    mocker.patch("services.http.requests.get", return_value=FakeResponse(200, "Please limit your requests"))
    r = http.get_json("http://x")
    assert r["ok"] is False
    assert "Please" in r["error"]


def test_get_json_invalid_json_returns_error(mocker):
    mocker.patch("services.http.requests.get", return_value=FakeResponse(200, "{not json}"))
    r = http.get_json("http://x")
    assert r["ok"] is False


def test_get_json_retries_on_429(mocker):
    seq = [FakeResponse(429, ""), FakeResponse(200, "{}", {"ok": 1})]
    mocker.patch("services.http.requests.get", side_effect=seq)
    mocker.patch("services.http.time.sleep", return_value=None)
    r = http.get_json("http://x", retries=2)
    assert r["ok"] is True


def test_get_json_returns_error_on_404(mocker):
    mocker.patch("services.http.requests.get", return_value=FakeResponse(404, "not found"))
    r = http.get_json("http://x")
    assert r["ok"] is False
    assert r["status"] == 404


def test_get_text_happy(mocker):
    mocker.patch("services.http.requests.get", return_value=FakeResponse(200, "<rss/>"))
    r = http.get_text("http://x")
    assert r["ok"] is True
    assert r["text"] == "<rss/>"


def test_get_text_handles_timeout(mocker):
    import requests
    mocker.patch("services.http.requests.get", side_effect=requests.Timeout("slow"))
    mocker.patch("services.http.time.sleep", return_value=None)
    r = http.get_text("http://x", retries=1)
    assert r["ok"] is False
