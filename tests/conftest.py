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

    with app.app_context():
        db.drop_tables([Event, Url, User])
        if not db.is_closed():
            db.close()


@pytest.fixture
def client(app):
    return app.test_client()
