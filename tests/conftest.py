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
    app = create_app()
    app.config["TESTING"] = True

    yield app

    # Cleanup: drop test tables
    with app.app_context():
        db.drop_tables([Event, Url, User])
        if not db.is_closed():
            db.close()


@pytest.fixture(autouse=True)
def clean_tables(app):
    """Truncate all tables between tests."""
    with app.app_context():
        db.connect(reuse_if_open=True)
        Event.delete().execute()
        Url.delete().execute()
        User.delete().execute()
        # Reset sequences
        for table in ["users", "urls", "events"]:
            db.execute_sql(
                f"ALTER SEQUENCE {table}_id_seq RESTART WITH 1"
            )
    yield


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sample_user(app):
    """Create a sample user for tests."""
    with app.app_context():
        db.connect(reuse_if_open=True)
        user = User.create(
            username="testuser",
            email="test@example.com",
            created_at="2025-01-01 00:00:00",
        )
        return user.id


@pytest.fixture
def sample_url(app, sample_user):
    """Create a sample URL for tests."""
    with app.app_context():
        db.connect(reuse_if_open=True)
        url = Url.create(
            user_id=sample_user,
            short_code="abc123",
            original_url="https://example.com",
            title="Example",
            is_active=True,
            created_at="2025-01-01 00:00:00",
            updated_at="2025-01-01 00:00:00",
        )
        return url.id


@pytest.fixture
def sample_event(app, sample_url, sample_user):
    """Create a sample event for tests."""
    import json

    with app.app_context():
        db.connect(reuse_if_open=True)
        event = Event.create(
            url_id=sample_url,
            user_id=sample_user,
            event_type="created",
            timestamp="2025-01-01 00:00:00",
            details=json.dumps(
                {"short_code": "abc123", "original_url": "https://example.com"}
            ),
        )
        return event.id
