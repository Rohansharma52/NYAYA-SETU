"""Shared pytest fixtures for NYAYA SETU backend tests.

Isolation strategy
------------------
* One in-memory SQLite engine for the whole session.
* Tables are created once (session scope) and dropped at the end.
* Each test gets a *connection* wrapped in a transaction that is rolled back
  after the test, keeping the DB pristine between tests.
* The db fixture returns a Session bound to that connection so that commits
  inside fixtures and application code all land in the same transaction and
  are undone automatically.

bcrypt workaround
-----------------
bcrypt==5.0.0 changed its API and broke passlib's wrap-bug detection
(raises ValueError: password cannot be longer than 72 bytes).
We replace the CryptContext with sha256_crypt before importing app code.

email-validator note
--------------------
email-validator rejects .test TLD as reserved.  All fixture emails use
the IANA-reserved example.com domain which email-validator accepts.
"""

# ── bcrypt patch (MUST come before any app import) ───────────────────────────
from passlib.context import CryptContext as _CC
_test_ctx = _CC(schemes=["sha256_crypt"], deprecated="auto")
import app.core.security as _sec  # noqa: E402
_sec.pwd_context = _test_ctx
# ─────────────────────────────────────────────────────────────────────────────

from app.core.config import settings as _settings  # noqa: E402
_settings.ALERT_SCAN_ENABLED = False  # no background scanner during tests

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from app.main import app
from app.db.session import get_db
from app.db.base import Base
from app.core.security import get_password_hash
from app.models.user import User, UserRole, AccountStatus
from app.models.bureau import Bureau
from app.models.institution import Institution
from app.models.case import Case, CaseStatus, CasePriority


# ── Engine (session-scoped, shared across all tests) ─────────────────────────

@pytest.fixture(scope="session")
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


# ── Per-test transaction isolation ───────────────────────────────────────────

@pytest.fixture
def db(engine):
    """
    Yields a SQLAlchemy Session whose transaction is always rolled back after
    the test.  Any savepoints created by application code are also rolled back.
    """
    connection = engine.connect()
    trans = connection.begin()

    TestSession = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    session = TestSession()

    yield session

    session.close()
    trans.rollback()
    connection.close()


# ── TestClient ────────────────────────────────────────────────────────────────

@pytest.fixture
def client(db):
    """TestClient with get_db overridden to use the isolated test session."""
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ── Data fixtures ─────────────────────────────────────────────────────────────
# NOTE: All emails use example.com — email-validator rejects .test TLD.

@pytest.fixture
def bureau(db):
    b = Bureau(code="RB", name="Regulation Bureau", is_active=True)
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


@pytest.fixture
def admin_user(db):
    user = User(
        email="admin@example.com",
        full_name="Test Admin",
        hashed_password=get_password_hash("AdminPass1"),
        role=UserRole.SYSTEM_ADMIN,
        account_status=AccountStatus.ACTIVE,
        is_active=True,
        is_superuser=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def officer_user(db, bureau):
    user = User(
        email="officer@example.com",
        full_name="Test Officer",
        hashed_password=get_password_hash("OfficerPass1"),
        role=UserRole.BUREAU_OFFICER,
        account_status=AccountStatus.ACTIVE,
        is_active=True,
        is_superuser=False,
        bureau_id=bureau.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def reviewer_user(db):
    user = User(
        email="reviewer@example.com",
        full_name="Test Reviewer",
        hashed_password=get_password_hash("ReviewerPass1"),
        role=UserRole.COORDINATION_REVIEWER,
        account_status=AccountStatus.ACTIVE,
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def institution(db):
    inst = Institution(
        canonical_name="Test Engineering College",
        short_name="TEC",
        state="Maharashtra",
        institution_type="college",
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


# ── Token / header fixtures ───────────────────────────────────────────────────

@pytest.fixture
def admin_token(client, admin_user):
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": admin_user.email, "password": "AdminPass1"},
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture
def officer_token(client, officer_user):
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": officer_user.email, "password": "OfficerPass1"},
    )
    assert resp.status_code == 200, f"Officer login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture
def reviewer_token(client, reviewer_user):
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": reviewer_user.email, "password": "ReviewerPass1"},
    )
    assert resp.status_code == 200, f"Reviewer login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def officer_headers(officer_token):
    return {"Authorization": f"Bearer {officer_token}"}


@pytest.fixture
def reviewer_headers(reviewer_token):
    return {"Authorization": f"Bearer {reviewer_token}"}
