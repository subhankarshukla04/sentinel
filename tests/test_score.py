from services.score import overall_risk


def test_zero_signals_is_low():
    r = overall_risk(0, 0, 0, 0)
    assert r["color"] == "green"
    assert r["score"] == 0
    assert r["label"].startswith("LOW")


def test_one_litigation_is_medium():
    r = overall_risk(0, 0, 1, 0)
    assert r["color"] == "amber"


def test_litigation_dominates():
    r = overall_risk(0, 0, 3, 0)
    assert r["color"] == "red"
    assert r["score"] == 9


def test_news_capped_at_5():
    r1 = overall_risk(0, 5, 0, 0)
    r2 = overall_risk(0, 1000, 0, 0)
    assert r1["score"] == r2["score"] == 5


def test_territories_capped_at_2_hits():
    r1 = overall_risk(2, 0, 0, 0)
    r2 = overall_risk(99, 0, 0, 0)
    assert r1["score"] == r2["score"] == 4


def test_combined_signals_red():
    # Cordillera-style: 3 territories + a few news + lit + 2 NGO
    r = overall_risk(3, 4, 1, 2)
    assert r["color"] == "red"


def test_negative_inputs_treated_as_zero():
    r = overall_risk(-5, -3, -1, -10)
    assert r["score"] == 0
    assert r["color"] == "green"


def test_string_inputs_coerced():
    r = overall_risk("0", "0", "0", "0")
    assert r["score"] == 0


def test_returns_coverage_flag():
    r = overall_risk(0, 0, 0, 0, territory_coverage="partial")
    assert r["territory_coverage"] == "partial"


def test_thresholds_at_boundaries():
    assert overall_risk(0, 2, 0, 0)["color"] == "green"
    assert overall_risk(0, 3, 0, 0)["color"] == "amber"
    assert overall_risk(0, 7, 0, 0)["color"] == "amber"
    assert overall_risk(0, 0, 2, 1)["color"] == "red"
