import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture
def app_client():
    from app import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c
