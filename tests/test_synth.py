from services import synth


def test_no_key_returns_graceful_message(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    r = synth.synthesize({"name": "X", "country": "Y"}, [], [], [], [])
    assert r["ok"] is False
    assert "OPENROUTER_API_KEY" in r["text"]


def test_with_key_calls_model(mocker, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-fake")
    # Reset the cached client so it picks up the test env
    synth._client = None

    class FakeMessage:
        content = "Test synthesized memo content."

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]

    class FakeChat:
        def create(self, **kwargs):
            return FakeResponse()

    class FakeCompletions:
        completions = FakeChat()

    class FakeClient:
        chat = FakeCompletions()

    mocker.patch.object(synth, "_get_client", return_value=FakeClient())
    r = synth.synthesize(
        {"name": "Cordillera Azul", "country": "Peru"},
        [{"name": "Kichwa"}],
        [{"title": "Lawsuit X", "domain": "mongabay.com", "language": "en", "seendate": "20240601", "adverse_score": 2}],
        [{"title": "Case Y", "court": "Superior", "year": 2020, "summary": "..."}],
        [{"org": "Survival Intl", "year": 2023, "headline": "Z"}],
        coverage="partial",
    )
    assert r["ok"] is True
    assert r["text"] == "Test synthesized memo content."


def test_handles_llm_exception(mocker, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-fake")
    synth._client = None

    class FakeChat:
        def create(self, **kwargs):
            raise RuntimeError("upstream timeout")

    class FakeCompletions:
        completions = FakeChat()

    class FakeClient:
        chat = FakeCompletions()

    mocker.patch.object(synth, "_get_client", return_value=FakeClient())
    r = synth.synthesize({"name": "X", "country": "Y"}, [], [], [], [])
    assert r["ok"] is False
    assert "RuntimeError" in r["text"] or "upstream timeout" in r["text"]


def test_evidence_block_truncates_articles_to_8():
    articles = [{"title": f"A{i}", "domain": "x.com", "adverse_score": 2, "language": "en", "seendate": "2024", "url": ""} for i in range(20)]
    block = synth._build_evidence({"name": "X", "country": "Y", "type": "T", "registry": "R"},
                                  [], articles, [], [], "high")
    import json
    parsed = json.loads(block)
    # Synth caps to 4 adverse-news entries in the token-tight evidence block.
    assert len(parsed["adverse_news"]) <= 4


def test_evidence_block_filters_non_adverse_articles():
    articles = [
        {"title": "Adverse", "domain": "x.com", "adverse_score": 2, "language": "en", "seendate": "2024", "url": ""},
        {"title": "Neutral", "domain": "y.com", "adverse_score": 0, "language": "en", "seendate": "2024", "url": ""},
    ]
    block = synth._build_evidence({"name": "X", "country": "Y", "type": "T", "registry": "R"},
                                  [], articles, [], [], "high")
    import json
    parsed = json.loads(block)
    # Synth uses key 't' for title in the compressed evidence block.
    titles = [a["t"] for a in parsed["adverse_news"]]
    assert "Adverse" in titles
    assert "Neutral" not in titles
