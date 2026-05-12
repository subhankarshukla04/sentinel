import pytest
from services import news


class TestAdverseScore:
    def test_zero_for_innocuous(self):
        assert news._adverse_score("Mangrove restoration project announces new vintage", "example.com") == 0

    def test_picks_up_topic_and_claim(self):
        # 'carbon'/'credits' (topic) + 'lawsuit' (claim) + 'court' (claim) — 2 claim hits, topic present
        s = news._adverse_score("Lawsuit filed in court over carbon credits", None)
        assert s >= 2

    def test_topic_only_no_score(self):
        # 'indigenous'/'consent' are TOPIC words only — without an adverse claim, score must be 0.
        # This is the fix for the v0.2 false positive on titles like "Project secures FPIC".
        assert news._adverse_score("Indigenous community grants project FPIC consent", "x.com") == 0

    def test_claim_only_no_score(self):
        # 'sued' is an adverse-claim word but no safeguards topic — must be 0 (irrelevant subject).
        assert news._adverse_score("Mining company sued by competitor", "x.com") == 0

    def test_ngo_domain_boost_requires_adverse(self):
        # NGO domain alone is not enough — title must have topic+claim co-occurrence.
        assert news._adverse_score("Some neutral title about a project", "mongabay.com") == 0
        # With topic+claim, domain bonus applies.
        s = news._adverse_score("Indigenous community sued over carbon credits", "mongabay.com")
        assert s >= 2

    def test_handles_none(self):
        assert news._adverse_score(None, None) == 0

    def test_combines_topic_claim_and_domain(self):
        # 'indigenous' (topic) + 'lawsuit' (claim) + carbonmarketwatch.org (NGO domain).
        s = news._adverse_score("Indigenous lawsuit over carbon project", "carbonmarketwatch.org")
        assert s >= 2


class TestNormalize:
    def test_returns_required_fields(self):
        a = news._normalize_article("X", "u", "d", "en", "20240101", "US", "gdelt")
        for f in ("title", "url", "domain", "language", "seendate", "country", "source", "adverse_score"):
            assert f in a


class TestDedupe:
    def test_drops_exact_dupes(self):
        a = [
            {"title": "Same Title Here", "domain": "x.com"},
            {"title": "Same Title Here", "domain": "x.com"},
        ]
        assert len(news._dedupe(a)) == 1

    def test_keeps_same_title_different_domain(self):
        a = [
            {"title": "Same Title Here", "domain": "x.com"},
            {"title": "Same Title Here", "domain": "y.com"},
        ]
        assert len(news._dedupe(a)) == 2

    def test_normalizes_punctuation(self):
        a = [
            {"title": "Carbon: Credits, Fail", "domain": "x.com"},
            {"title": "carbon credits fail", "domain": "x.com"},
        ]
        assert len(news._dedupe(a)) == 1

    def test_drops_empty_titles(self):
        a = [{"title": "", "domain": "x.com"}, {"title": None, "domain": "y.com"}]
        assert news._dedupe(a) == []


class TestAdverseNewsContract:
    def test_empty_name_returns_error(self):
        r = news.adverse_news("")
        assert r["ok"] is False
        assert r["articles"] == []

    def test_returns_consistent_shape_on_failure(self, mocker):
        mocker.patch.object(news, "_via_gdelt", return_value=[])
        mocker.patch.object(news, "_via_google_news", return_value=[])
        r = news.adverse_news("Imaginary Project XYZ")
        assert r["ok"] is True
        assert r["articles"] == []
        assert r["adverse_count"] == 0
        assert r["total"] == 0
        assert r["sources_used"] == []

    def test_merges_and_dedupes_across_sources(self, mocker):
        gd = [news._normalize_article("Lawsuit over X", "u1", "x.com", "en", "20240101", "US", "gdelt")]
        gn = [news._normalize_article("Lawsuit over X", "u2", "x.com", "en", "20240101", None, "google-news")]
        mocker.patch.object(news, "_via_gdelt", return_value=gd)
        mocker.patch.object(news, "_via_google_news", return_value=gn)
        r = news.adverse_news("Anything")
        assert r["total"] == 1
        assert "gdelt" in r["sources_used"]
        assert "google-news" in r["sources_used"]

    def test_adverse_count_filters_by_score(self, mocker):
        # Topic ('carbon credits') + claim ('lawsuit', 'fraud') → adverse. Visitor-center title → not adverse.
        a1 = news._normalize_article("Lawsuit and fraud over carbon credits at project X", "u1", "mongabay.com", "en", "20240101", None, "g")
        a2 = news._normalize_article("Project X opens new visitor center", "u2", "blog.example", "en", "20240101", None, "g")
        mocker.patch.object(news, "_via_gdelt", return_value=[a1, a2])
        mocker.patch.object(news, "_via_google_news", return_value=[])
        r = news.adverse_news("Project X")
        assert r["total"] == 2
        assert r["adverse_count"] == 1


class TestQueryVariants:
    def test_short_name_single_variant(self):
        v = news._build_query_variants("Kariba", "Zimbabwe")
        assert len(v) == 1
        assert v[0] == ('"Kariba" Zimbabwe', '"Kariba"')

    def test_long_name_strips_redd_suffix(self):
        # "Bukit Tigapuluh REDD+ Project" → strips both REDD+ and Project,
        # producing a stripped variant that matches real coverage titles.
        v = news._build_query_variants("Bukit Tigapuluh REDD+ Project", "Indonesia")
        google_queries = [g for _, g in v]
        assert '"Bukit Tigapuluh REDD+ Project"' in google_queries
        assert '"Bukit Tigapuluh"' in google_queries

    def test_distinctive_core_for_very_long_names(self):
        # "Northern Rangelands Trust carbon program" — the core "Northern Rangelands Trust"
        # is what major outlets actually print in headlines.
        v = news._build_query_variants("Northern Rangelands Trust carbon program", "Kenya")
        google_queries = [g for _, g in v]
        # First-three-words core should appear
        assert '"Northern Rangelands Trust"' in google_queries

    def test_no_duplicate_variants(self):
        # If stripped == name, we shouldn't emit a duplicate.
        v = news._build_query_variants("Kariba", "Zimbabwe")
        google_queries = [g for _, g in v]
        assert len(google_queries) == len(set(google_queries))

    def test_empty_name_returns_empty(self):
        assert news._build_query_variants("", "Kenya") == []
        assert news._build_query_variants("   ", None) == []

    def test_country_optional(self):
        v = news._build_query_variants("Foo Bar Project", None)
        assert all(g.startswith('"') for g, _ in v)  # no country appended

    def test_cascading_fan_out_stops_early_when_target_met(self, mocker):
        # If variant 1 already yields enough articles, variants 2+ shouldn't fire.
        gd = [
            news._normalize_article(f"Carbon lawsuit at X {i}", f"u{i}", "x.com", "en", "20240101", None, "gdelt")
            for i in range(5)
        ]
        m_g = mocker.patch.object(news, "_via_gdelt", return_value=gd)
        m_n = mocker.patch.object(news, "_via_google_news", return_value=[])
        r = news.adverse_news("Bukit Tigapuluh REDD+ Project", country="Indonesia", min_articles_target=3)
        assert r["total"] >= 3
        # Variant 1 was sufficient — no second-variant call to either upstream.
        assert m_g.call_count == 1
        assert m_n.call_count == 1

    def test_cascading_fan_out_retries_when_variant_1_empty(self, mocker):
        # Variant 1 empty → falls through to variant 2.
        gd_results = [[], [news._normalize_article("Carbon lawsuit at X", "u", "x.com", "en", "20240101", None, "g")]]
        m_g = mocker.patch.object(news, "_via_gdelt", side_effect=gd_results)
        m_n = mocker.patch.object(news, "_via_google_news", return_value=[])
        r = news.adverse_news("Bukit Tigapuluh REDD+ Project", country="Indonesia", min_articles_target=1)
        assert m_g.call_count >= 2
        assert r["total"] >= 1
