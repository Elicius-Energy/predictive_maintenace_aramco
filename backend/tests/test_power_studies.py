"""
TDD tests for Power Study recording, unique code generation (LEDL0001...),
multi-login/multi-device concurrency rules, and separate archive DB on admin delete.
"""
from datetime import datetime, timezone, timedelta
import sqlite3
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.db.models import User, Device, DeviceProfile, Reading, UserDeviceAccess
from app.core.security import hash_password, create_access_token
from app.config import settings


@pytest.fixture
def test_env(tmp_path, monkeypatch):
    """Isolated in-memory primary DB + isolated temporary archive SQLite DB on disk."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    archive_db_path = tmp_path / "deleted_studies_archive.db"
    monkeypatch.setenv("DELETED_STUDIES_ARCHIVE_DB_PATH", str(archive_db_path))

    db = TestingSessionLocal()
    admin = User(
        username="admin_test",
        password_hash=hash_password("AdminPass123!@#"),
        role="admin",
        is_active=True,
    )
    analyst = User(
        username="analyst_test",
        password_hash=hash_password("AnalystPass123!@#"),
        role="analyst",
        is_active=True,
    )
    db.add_all([admin, analyst])
    db.flush()

    dev1 = Device(device_id="DEV_001", alias="Ring Frame 1", configured=True)
    dev2 = Device(device_id="DEV_002", alias="Ring Frame 2", configured=True)
    prof1 = DeviceProfile(device_id="DEV_001", customer_name="Default Mill A", motor_rating_kw=15.0, rated_efficiency_pct=90.0)
    prof2 = DeviceProfile(device_id="DEV_002", customer_name="Default Mill B", motor_rating_kw=22.0, rated_efficiency_pct=91.0)
    access1 = UserDeviceAccess(user_id=analyst.id, device_id="DEV_001")
    access2 = UserDeviceAccess(user_id=analyst.id, device_id="DEV_002")
    db.add_all([dev1, dev2, prof1, prof2, access1, access2])

    # Seed telemetry readings for DEV_001 over the last 30 minutes
    now = datetime.now(timezone.utc)
    for i in range(20):
        ts = now - timedelta(minutes=20 - i)
        db.add(
            Reading(
                device_id="DEV_001",
                ts=ts,
                vll_avg=415.0,
                i_avg=18.0,
                t_kw=10.0,
                pf_avg=0.88,
                freq=50.0,
                kwh_imp=1000 + i,
            )
        )
    db.commit()

    def override_get_db():
        s = TestingSessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db

    admin_token = create_access_token({"sub": admin.username, "role": admin.role, "sv": admin.session_version})
    analyst_token = create_access_token({"sub": analyst.username, "role": analyst.role, "sv": analyst.session_version})

    yield {
        "db": db,
        "archive_db_path": archive_db_path,
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "analyst_headers": {"Authorization": f"Bearer {analyst_token}"},
    }

    app.dependency_overrides.clear()
    db.close()


def test_power_study_lifecycle_and_unique_codes(test_env):
    client = TestClient(app)
    headers = test_env["admin_headers"]

    # 1. Start first study on DEV_001 with customer name
    resp = client.post(
        "/api/devices/DEV_001/studies/start",
        json={"customer_name": "Lakshmi Mills Unit 1"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    study1 = resp.json()
    assert study1["study_code"] == "LEDL0001"
    assert study1["customer_name"] == "Lakshmi Mills Unit 1"
    assert study1["device_id"] == "DEV_001"
    assert study1["status"] == "running"
    assert study1["started_at"] is not None
    assert study1["stopped_at"] is None

    # 2. Across different login session (e.g. analyst or second admin login),
    # checking active study for DEV_001 shows the running study LEDL0001
    resp_active = client.get(
        "/api/devices/DEV_001/studies/active",
        headers=test_env["analyst_headers"],
    )
    assert resp_active.status_code == 200
    active_data = resp_active.json()
    assert active_data is not None
    assert active_data["study_code"] == "LEDL0001"
    assert active_data["status"] == "running"
    assert active_data["customer_name"] == "Lakshmi Mills Unit 1"

    # 3. Attempting to start a second study on the SAME device DEV_001 while one is running must fail with 409
    resp_dup = client.post(
        "/api/devices/DEV_001/studies/start",
        json={"customer_name": "Another Customer"},
        headers=test_env["analyst_headers"],
    )
    assert resp_dup.status_code == 409

    # 4. Simultaneously starting a study on a DIFFERENT device DEV_002 from same or another account succeeds with LEDL0002
    resp_dev2 = client.post(
        "/api/devices/DEV_002/studies/start",
        json={"customer_name": "PSG Textiles"},
        headers=headers,
    )
    assert resp_dev2.status_code == 200
    study2 = resp_dev2.json()
    assert study2["study_code"] == "LEDL0002"
    assert study2["customer_name"] == "PSG Textiles"
    assert study2["device_id"] == "DEV_002"
    assert study2["status"] == "running"

    # 5. Stop study on DEV_001
    resp_stop = client.post(
        "/api/devices/DEV_001/studies/stop",
        json={},
        headers=headers,
    )
    assert resp_stop.status_code == 200
    stopped1 = resp_stop.json()
    assert stopped1["study_code"] == "LEDL0001"
    assert stopped1["status"] == "completed"
    assert stopped1["stopped_at"] is not None
    assert stopped1["duration_seconds"] >= 0
    assert "LEDL0001" in stopped1["display_label"]
    assert "Lakshmi Mills Unit 1" in stopped1["display_label"]


def test_delete_study_archives_to_separate_backend_database(test_env):
    client = TestClient(app)
    admin_headers = test_env["admin_headers"]
    analyst_headers = test_env["analyst_headers"]
    archive_db_path = test_env["archive_db_path"]

    # Start and stop a test study
    start_resp = client.post(
        "/api/devices/DEV_001/studies/start",
        json={"customer_name": "Test Customer DeleteCheck"},
        headers=admin_headers,
    )
    assert start_resp.status_code == 200
    study_id = start_resp.json()["id"]
    study_code = start_resp.json()["study_code"]
    assert study_code == "LEDL0001"

    stop_resp = client.post(
        "/api/devices/DEV_001/studies/stop",
        json={},
        headers=admin_headers,
    )
    assert stop_resp.status_code == 200

    # Non-admin cannot delete a study
    forbid_resp = client.delete(f"/api/studies/{study_id}", headers=analyst_headers)
    assert forbid_resp.status_code == 403

    # Admin deletes the study
    del_resp = client.delete(f"/api/studies/{study_id}", headers=admin_headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["study_code"] == "LEDL0001"
    assert del_resp.json()["archived"] is True

    # Verify it is removed from active studies list
    list_resp = client.get("/api/studies", headers=admin_headers)
    assert list_resp.status_code == 200
    assert all(s["study_code"] != "LEDL0001" for s in list_resp.json())

    # Verify it is stored in the SEPARATE backend SQLite database with duration and customer name
    assert archive_db_path.exists()
    conn = sqlite3.connect(str(archive_db_path))
    cur = conn.cursor()
    cur.execute(
        "SELECT study_code, customer_name, device_id, started_at, stopped_at, duration_seconds, deleted_by FROM deleted_power_studies WHERE study_code = ?",
        ("LEDL0001",),
    )
    row = cur.fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "LEDL0001"
    assert row[1] == "Test Customer DeleteCheck"
    assert row[2] == "DEV_001"
    assert row[3] is not None
    assert row[4] is not None
    assert row[5] is not None and row[5] >= 0
    assert row[6] == "admin_test"

    # Verify next study code does NOT reuse LEDL0001 even after deletion
    next_resp = client.post(
        "/api/devices/DEV_001/studies/start",
        json={"customer_name": "Second Study After Delete"},
        headers=admin_headers,
    )
    assert next_resp.status_code == 200
    assert next_resp.json()["study_code"] == "LEDL0002"
