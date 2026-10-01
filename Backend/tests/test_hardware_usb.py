import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.hardware.usb.usb_manager import usb_manager
from app.hardware.usb.usb_detector import is_valid_device_path
from app.hardware.usb.device_registry import device_registry


client = TestClient(app)


def test_device_path_validation():
    # Valid Linux and Windows paths
    assert is_valid_device_path("/dev/ttyUSB0") is True
    assert is_valid_device_path("/dev/ttyACM1") is True
    assert is_valid_device_path("COM3") is True
    assert is_valid_device_path("MOCK_USB0") is True

    # Injection attempts / invalid paths
    assert is_valid_device_path("/dev/ttyUSB0; rm -rf /") is False
    assert is_valid_device_path("COM3 | dir") is False
    assert is_valid_device_path("`cat /etc/passwd`") is False
    assert is_valid_device_path("../../../dev/ttyUSB0") is False
    assert is_valid_device_path("") is False


def test_device_registry_matching():
    # Match ESP32 by Silicon Labs CP2102 VID:PID
    esp_profile = device_registry.match_device("10C4", "EA60")
    assert esp_profile is not None
    assert esp_profile.role == "esp32"
    assert esp_profile.baud_rate == 115200

    # Match GPS by u-blox VID:PID
    gps_profile = device_registry.match_device("1546", "01A7")
    assert gps_profile is not None
    assert gps_profile.role == "gps"
    assert gps_profile.baud_rate == 9600

    # Match by keyword
    kw_profile = device_registry.match_device(None, None, description="u-blox GNSS receiver")
    assert kw_profile is not None
    assert kw_profile.role == "gps"


def test_get_usb_devices_and_status():
    login_res = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Test GET /hardware/usb
    res = client.get("/hardware/usb", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "devices" in data
    assert len(data["devices"]) > 0

    # Test GET /api/hardware/usb (with /api prefix)
    res_api = client.get("/api/hardware/usb", headers=headers)
    assert res_api.status_code == 200
    assert "devices" in res_api.json()

    # Test GET /hardware/usb/status
    res_status = client.get("/hardware/usb/status", headers=headers)
    assert res_status.status_code == 200
    sub_data = res_status.json()
    assert "mode" in sub_data
    assert "totalDevices" in sub_data
    assert "connectedCount" in sub_data


def test_hardware_health_endpoint():
    res = client.get("/hardware/health")
    assert res.status_code == 200
    data = res.json()
    assert data["system"] == "healthy"
    assert "usb" in data
    assert "devices" in data
    assert "timestamp" in data

    # Test with /api prefix
    res_api = client.get("/api/hardware/health")
    assert res_api.status_code == 200


def test_usb_connect_write_read_disconnect_lifecycle():
    login_res = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    devices_res = client.get("/hardware/usb", headers=headers)
    devices = devices_res.json()["devices"]
    assert len(devices) > 0
    target_path = devices[0]["devicePath"]

    # 1. Connect
    conn_res = client.post(
        "/hardware/usb/connect",
        json={"devicePath": target_path, "baudRate": 115200},
        headers=headers,
    )
    assert conn_res.status_code == 200
    assert conn_res.json()["status"] == "connected"

    # Duplicate connect should succeed idempotently
    dup_res = client.post(
        "/hardware/usb/connect",
        json={"devicePath": target_path, "baudRate": 115200},
        headers=headers,
    )
    assert dup_res.status_code == 200

    # 2. Write command
    write_res = client.post(
        "/hardware/usb/write",
        json={"devicePath": target_path, "data": "STATUS_CHECK\n"},
        headers=headers,
    )
    assert write_res.status_code == 200
    assert write_res.json()["status"] == "written"

    # 3. Read buffer
    read_res = client.get(
        f"/hardware/usb/read?devicePath={target_path}&limit=10",
        headers=headers,
    )
    assert read_res.status_code == 200
    lines = read_res.json()["lines"]
    assert len(lines) > 0

    # 4. Disconnect
    disc_res = client.post(
        "/hardware/usb/disconnect",
        json={"devicePath": target_path},
        headers=headers,
    )
    assert disc_res.status_code == 200
    assert disc_res.json()["status"] == "disconnected"


def test_invalid_device_path_rejection():
    login_res = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    malicious_paths = [
        "/dev/ttyUSB0; reboot",
        "COM1 & del C:\\",
        "`cat /etc/shadow`",
    ]

    for p in malicious_paths:
        res = client.post(
            "/hardware/usb/connect",
            json={"devicePath": p},
            headers=headers,
        )
        assert res.status_code == 400


def test_hardware_websocket_events():
    with client.websocket_connect("/hardware/ws") as ws:
        # Initial event should be usb:status
        data = ws.receive_json()
        assert data["event"] == "usb:status"
        assert "status" in data

        # Send ping
        ws.send_text("ping")
        resp = ws.receive_text()
        assert resp == "pong"
