import hashlib
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TMP_DIR = tempfile.mkdtemp(prefix="quest-tests-")
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if TEST_DATABASE_URL:
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
else:
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{TMP_DIR}/test.db")
os.environ.setdefault("QUESTIONS_CONFIG_PATH", str(ROOT / "config" / "questions.yaml"))
os.environ.setdefault("QUESTIONS_WATCH_ENABLED", "false")
os.environ.setdefault("UPLOAD_DIR", f"{TMP_DIR}/uploads")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("SECRET_KEY", "test-secret")

from fastapi.testclient import TestClient  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User, UserSession  # noqa: E402


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def create_user_session(display_name: str = "Test User"):
    """Create a user and a valid session; returns (user, raw_session_token)."""
    db = SessionLocal()
    user = User(display_name=display_name)
    db.add(user)
    db.flush()
    raw_token = f"session-{user.id}"
    db.add(
        UserSession(
            user_id=user.id,
            session_token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
            expires_at=datetime.utcnow() + timedelta(days=1),
        )
    )
    db.commit()
    user_id = user.id
    db.close()
    return user_id, raw_token


@pytest.fixture()
def auth_client(client):
    user_id, raw_token = create_user_session()
    client.cookies.set("quest_session", raw_token)
    return client


def create_profile(client, slug: str = "tester"):
    response = client.post(
        "/api/profiles",
        json={"slug": slug, "display_name": "Tester", "bio": "test bio"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    return data["profile"]["id"], data["edit_token"]
