"""
TDD tests for Motor Nameplate image preview, deletion, and OCR details reset
so stale nameplate photos and OCR fields never leak into subsequent studies.
"""
from datetime import datetime, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.db.models import User, Device, DeviceProfile, Reading
from app.core.security import hash_password, create_access_token
from app.config import settings


@pytest.fixture
def nameplate_env(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "REPORTS_DIR", str(reports_dir))

    nameplates_dir = tmp_path / "nameplates"
    nameplates_dir.mkdir(parents=True, exist_ok=True)
    # Create a valid dummy JPEG header file for DEV_NP_01
    fake_jpg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"
    (nameplates_dir / "DEV_NP_01.jpg").write_bytes(fake_jpg)

    db = TestingSessionLocal()
    admin = User(
        username="admin_np",
        password_hash=hash_password("AdminPass123!@#"),
        role="admin",
        is_active=True,
    )
    db.add(admin)
    db.flush()

    dev = Device(device_id="DEV_NP_01", alias="Carding Motor 3", configured=True)
    prof = DeviceProfile(
        device_id="DEV_NP_01",
        customer_name="Aramco Mill",
        motor_make="ABB",
        motor_rating_kw=15.0,
        frame_size="160M",
        rated_current_amps=28.5,
        rated_speed_rpm=1470.0,
        rated_voltage=415.0,
        rated_efficiency_pct=92.1,
        motor_connection="Delta",
        motor_duty="S1",
        insulation_class="F",
        motor_type="IE3 Premium Efficiency",
        serial_number="ABB-998877",
    )
    reading = Reading(
        device_id="DEV_NP_01",
        ts=datetime.now(timezone.utc),
        t_kw=11.2,
        raw={"motor_nameplate": {"motor_make": "ABB", "serial_number": "ABB-998877"}},
    )
    db.add_all([dev, prof, reading])
    db.commit()

    def override_get_db():
        s = TestingSessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token({"sub": admin.username, "role": admin.role, "sv": admin.session_version})

    yield {
        "db": db,
        "nameplates_dir": nameplates_dir,
        "headers": {"Authorization": f"Bearer {token}"},
    }

    app.dependency_overrides.clear()
    db.close()


def test_nameplate_preview_and_delete_clears_image_and_ocr_details(nameplate_env):
    client = TestClient(app)
    headers = nameplate_env["headers"]
    nameplate_file = nameplate_env["nameplates_dir"] / "DEV_NP_01.jpg"
    assert nameplate_file.exists()

    # 1. Profile endpoint exposes has_nameplate_image and nameplate_image_url
    prof_resp = client.get("/api/devices/DEV_NP_01/profile", headers=headers)
    assert prof_resp.status_code == 200
    prof_data = prof_resp.json()
    assert prof_data["has_nameplate_image"] is True
    assert prof_data["nameplate_image_url"] == "/api/devices/DEV_NP_01/motor-nameplate-image"
    assert prof_data["motor_make"] == "ABB"

    # 2. Image endpoint serves the stored motor nameplate image
    img_resp = client.get("/api/devices/DEV_NP_01/motor-nameplate-image", headers=headers)
    assert img_resp.status_code == 200
    assert img_resp.headers["content-type"].startswith("image/")
    assert len(img_resp.content) > 10

    # 3. Deleting the motor nameplate removes the image file AND clears stale OCR nameplate fields
    del_resp = client.delete("/api/devices/DEV_NP_01/motor-nameplate", headers=headers)
    assert del_resp.status_code == 200
    del_data = del_resp.json()
    assert del_data["success"] is True
    assert not nameplate_file.exists()

    # 4. Subsequent profile fetch shows has_nameplate_image=False and cleared OCR motor fields
    prof_after = client.get("/api/devices/DEV_NP_01/profile", headers=headers).json()
    assert prof_after["has_nameplate_image"] is False
    assert prof_after["nameplate_image_url"] is None
    assert prof_after["motor_make"] in ("", None)
    assert prof_after["frame_size"] in ("", None)
    assert prof_after["serial_number"] in ("", None)
    assert prof_after["rated_current_amps"] is None
    assert prof_after["rated_speed_rpm"] is None
    assert prof_after["rated_voltage"] is None
    assert prof_after["motor_rating_kw"] is None
    assert prof_after["rated_efficiency_pct"] is None

    # 5. Image endpoint now returns 404
    img_after = client.get("/api/devices/DEV_NP_01/motor-nameplate-image", headers=headers)
    assert img_after.status_code == 404

    # 6. Saving profile when nameplate is not available (rated_efficiency_pct is None) succeeds
    save_resp = client.put("/api/devices/DEV_NP_01/profile", json=prof_after, headers=headers)
    assert save_resp.status_code == 200
