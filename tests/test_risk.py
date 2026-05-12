from services import risk


def test_curated_returns_for_known_id():
    r = risk._curated("vcs-985", "Cordillera Azul")
    assert len(r["litigation"]) >= 1
    assert any("Kichwa" in c["title"] for c in r["litigation"])


def test_curated_fuzzy_match_by_name():
    # adhoc id but a name that overlaps Cordillera Azul should still hit
    r = risk._curated("adhoc", "Cordillera Azul National Park REDD+")
    assert len(r["ngo_complaints"]) >= 1


def test_curated_unknown_returns_empty():
    r = risk._curated("adhoc", "Some Brand New Project Name 12345")
    assert r["litigation"] == []
    assert r["ngo_complaints"] == []


def test_inferred_from_news_promotes_ngo_outlets():
    articles = [
        {"title": "Investigation into project X", "url": "http://mongabay.com/x", "domain": "mongabay.com", "seendate": "20240601"},
    ]
    r = risk._inferred_from_news(articles)
    assert len(r["ngo_complaints"]) == 1
    assert r["ngo_complaints"][0]["org"] == "Mongabay"
    assert r["ngo_complaints"][0]["inferred"] is True


def test_inferred_from_news_picks_up_litigation():
    articles = [
        {"title": "Court rules against carbon project Y", "url": "http://news.example.com/y", "domain": "news.example.com", "seendate": "20240601"},
    ]
    r = risk._inferred_from_news(articles)
    assert len(r["litigation"]) == 1
    assert r["litigation"][0]["inferred"] is True


def test_inferred_handles_empty_input():
    r = risk._inferred_from_news([])
    assert r == {"ngo_complaints": [], "litigation": []}


def test_collect_merges_and_deduplicates():
    # Curated entry has a known NGO complaint at forestpeoples.org/cordillera-azul
    articles = [
        {"title": "Cordillera Azul REDD+ exposed", "url": "https://www.forestpeoples.org/en/cordillera-azul",
         "domain": "forestpeoples.org", "seendate": "20240601"},
        {"title": "Court ruling against Cordillera Azul", "url": "http://example.com/court", "domain": "example.com", "seendate": "20240601"},
    ]
    r = risk.collect("vcs-985", "Cordillera Azul", articles)
    # Curated NGO complaints + 0 inferred (because URL already in curated) + 1 inferred litigation
    assert r["curated_count"] >= 1
    assert any(x.get("inferred") for x in r["litigation"])


def test_collect_with_no_articles():
    r = risk.collect("vcs-1722", "Mikoko Pamoja", [])
    assert r["litigation"] == []
    assert r["ngo_complaints"] == []
