import os

import pytest

from app import create_app
from app.database import db
from app.models import Event, Url, User


@pytest.fixture(scope="session")
def app():
    """Create a test app with a separate test database."""
    os.environ["DATABASE_NAME"] = os.environ.get(
        "TEST_DATABASE_NAME", "hackathon_test_db"
    )
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
    app = create_app()
    app.config["TESTING"] = True

    yield app

    with app.app_context():
        db.drop_tables([Event, Url, User])
        if not db.is_closed():
            db.close()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def flush_redis():
    """Flush the test Redis database before each test."""
    import app.cache as _cache_mod

    # Reset module-level disabled flag so Redis is re-attempted
    _cache_mod._DISABLED = False
    _cache_mod._redis = None

    r = _cache_mod._get_redis()
    if r is not None:
        r.flushdb()
    yield
    if r is not None:
        r.flushdb()
