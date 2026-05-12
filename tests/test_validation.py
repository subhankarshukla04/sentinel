import pytest
from services.validation import ValidationError, clean_name, clean_coord, clean_country


class TestCleanName:
    def test_strips_whitespace(self):
        assert clean_name("  Cordillera Azul  ") == "Cordillera Azul"

    def test_collapses_internal_whitespace(self):
        assert clean_name("Cordillera   Azul\t\nREDD+") == "Cordillera Azul REDD+"

    def test_rejects_empty(self):
        with pytest.raises(ValidationError):
            clean_name("")

    def test_rejects_none(self):
        with pytest.raises(ValidationError):
            clean_name(None)

    def test_rejects_too_short(self):
        with pytest.raises(ValidationError):
            clean_name("ab")

    def test_rejects_too_long(self):
        with pytest.raises(ValidationError):
            clean_name("x" * 250)

    def test_accepts_unicode(self):
        assert clean_name("Floresta Amazônica REDD+") == "Floresta Amazônica REDD+"

    def test_rejects_non_string(self):
        with pytest.raises(ValidationError):
            clean_name(12345)


class TestCleanCoord:
    def test_accepts_float_strings(self):
        assert clean_coord("-7.65", "-76.0") == (-7.65, -76.0)

    def test_accepts_floats(self):
        assert clean_coord(0.0, 0.0) == (0.0, 0.0)

    def test_accepts_extremes(self):
        assert clean_coord(-90.0, -180.0) == (-90.0, -180.0)
        assert clean_coord(90.0, 180.0) == (90.0, 180.0)

    def test_rejects_lat_too_high(self):
        with pytest.raises(ValidationError):
            clean_coord(91.0, 0.0)

    def test_rejects_lat_too_low(self):
        with pytest.raises(ValidationError):
            clean_coord(-91.0, 0.0)

    def test_rejects_lng_too_high(self):
        with pytest.raises(ValidationError):
            clean_coord(0.0, 181.0)

    def test_rejects_lng_too_low(self):
        with pytest.raises(ValidationError):
            clean_coord(0.0, -181.0)

    def test_rejects_garbage(self):
        with pytest.raises(ValidationError):
            clean_coord("not-a-number", "0.0")

    def test_rejects_none(self):
        with pytest.raises(ValidationError):
            clean_coord(None, None)


class TestCleanCountry:
    def test_returns_none_for_empty(self):
        assert clean_country("") is None
        assert clean_country(None) is None
        assert clean_country("   ") is None

    def test_strips(self):
        assert clean_country("  Peru  ") == "Peru"

    def test_returns_none_for_too_long(self):
        assert clean_country("x" * 200) is None

    def test_returns_none_for_non_string(self):
        assert clean_country(12345) is None
