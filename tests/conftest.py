import pytest

from app import create_app, ratelimit


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    ratelimit.reset()


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path))
    app.config["TESTING"] = True
    return app.test_client()
