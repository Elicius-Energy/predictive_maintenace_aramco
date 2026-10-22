"""
Integration tests for the LEDL Motor Energy Monitoring FastAPI Endpoints.
Covers Auth, Ingestion, Devices, Configuration, Live Cards, Trends, Reports, and Chat.
"""
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.db.init_db import init_db

init_db()
client = TestClient(app)


def test_health_check():
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Elicius" in data["service"]


def test_auth_login_and_me():
    # 1. Invalid credentials
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert resp.status_code == 401
    assert "Invalid username or password" in resp.json()["detail"]

    # 2. Valid login
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "admin"
    assert settings.COOKIE_NAME in client.cookies

    # 3. Check /me with cookie
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"

    # 4. Logout
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Logged out successfully"


def test_ingest_auth():
    # Missing or invalid key
    payload = {
        "dID": "002D00203335471332323632",
        "dTS": 1704067200,
        "v_l1_n": 230.0, "v_l2_n": 230.0, "v_l3_n": 230.0,
        "i_l1": 25.0, "i_l2": 25.0, "i_l3": 25.0,
        "kw_l1": 5.0, "kw_l2": 5.0, "kw_l3": 5.0, "t_kw": 15.0,
        "pf_l1": 0.88, "pf_l2": 0.88, "pf_l3": 0.88, "t_pf": 0.88,
        "hz": 50.0
    }
    resp = client.post("/api/ingest", json=payload, headers={"X-Device-Key": "wrong_key"})
    assert resp.status_code == 401

    # Valid key
    resp = client.post("/api/ingest", json=payload, headers={"X-Device-Key": settings.DEVICE_KEY})
    assert resp.status_code == 200
    data = resp.json()
    assert "inserted" in data or "duplicate" in data


def test_device_endpoints():
    # Login first
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})

    # Register test device first
    client.post("/api/devices/register", json={
        "device_id": "002D00203335471332323632",
        "alias": "Main Motor Meter"
    })

    # 1. List devices
    resp = client.get("/api/devices")
    assert resp.status_code == 200
    devices = resp.json()
    assert len(devices) >= 1
    dev_a = next((d for d in devices if d["device_id"] == "002D00203335471332323632"), None)
    assert dev_a is not None

    # 2. Get profile
    resp = client.get("/api/devices/002D00203335471332323632/profile")
    assert resp.status_code == 200
    profile = resp.json()
    assert "motor_rating_kw" in profile

    # 3. Update profile
    updated_profile = dict(profile)
    updated_profile["customer_name"] = "LEDL Coimbatore Unit 1"
    resp = client.put("/api/devices/002D00203335471332323632/profile", json=updated_profile)
    assert resp.status_code == 200
    assert resp.json()["message"] == "Configuration saved successfully"

    # 4. Live cards
    resp = client.get("/api/devices/002D00203335471332323632/live")
    assert resp.status_code == 200
    live = resp.json()
    assert "device_id" in live
    assert "power" in live
    assert "voltage" in live
    assert "current" in live
    assert "energy" in live

    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=24)
    start_iso = start.isoformat()
    end_iso = now.isoformat()

    # 5. Trends
    resp = client.get(f"/api/devices/002D00203335471332323632/trends?start_time={start_iso}&end_time={end_iso}&interval=1-minute")
    assert resp.status_code == 200
    trends = resp.json()
    assert "points" in trends
    assert isinstance(trends["points"], list)

    # 6. Summary
    resp = client.get(f"/api/devices/002D00203335471332323632/summary?start_time={start_iso}&end_time={end_iso}")
    assert resp.status_code == 200
    summary = resp.json()
    assert "energy_kwh" in summary
    assert "avg_kw" in summary


def test_reports_workflow():
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})

    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=24)
    start_iso = start.isoformat()
    end_iso = now.isoformat()

    # 1. Report Preview
    params = {
        "device_id": "002D00203335471332323632",
        "start_time": start_iso,
        "end_time": end_iso,
        "interval": "1-minute"
    }
    resp = client.post("/api/reports/preview", json=params)
    assert resp.status_code == 200
    preview = resp.json()
    assert "energy_kwh" in preview
    assert "avg_kw" in preview

    # 2. Generate Report - returns Excel file directly
    gen_payload = {
        "device_id": "002D00203335471332323632",
        "start_time": start_iso,
        "end_time": end_iso,
        "interval": "1-minute",
        "title": "Ring Frame 14 EE Audit",
        "remarks": "Automated smoke test report",
        "include_roi": True,
        "roi_params": {
            "before_motor_kw": 22.0,
            "after_motor_kw": 18.5,
            "annual_operating_hours": 7000.0,
            "energy_rate_inr": 8.5,
            "investment_inr": 120000.0
        }
    }
    resp = client.post("/api/reports/generate", json=gen_payload)
    assert resp.status_code == 200
    assert "spreadsheetml" in resp.headers.get("content-type", "")
    assert len(resp.content) > 1000  # valid binary Excel workbook
    content_disp = resp.headers.get("content-disposition", "")
    assert "attachment" in content_disp

    # 3. List report history for device
    resp = client.get("/api/reports/history/002D00203335471332323632")
    assert resp.status_code == 200
    reports_list = resp.json()
    assert len(reports_list) >= 1
    latest_report = reports_list[0]
    assert latest_report["report_no"].startswith("LEDL/ER/")

    # 4. Re-download report file
    report_id = latest_report["id"]
    resp = client.get(f"/api/reports/download/{report_id}")
    assert resp.status_code == 200
    assert "spreadsheetml" in resp.headers.get("content-type", "")
    assert len(resp.content) > 1000
