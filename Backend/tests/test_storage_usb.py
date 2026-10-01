import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from app.main import app
from app.hardware.storage.storage_file_manager import validate_sandboxed_path
from app.hardware.storage.storage_manager import storage_manager
from fastapi import HTTPException

client = TestClient(app)


def test_path_traversal_protection():
    mount_dir = Path("./storage/mock_usb").resolve()
    mount_dir.mkdir(parents=True, exist_ok=True)

    # Valid relative path inside mount
    safe_path = validate_sandboxed_path(str(mount_dir), "CEB_DATA")
    assert safe_path.is_relative_to(mount_dir)

    # Path traversal attack tests
    traversal_attempts = [
        "../../etc/passwd",
        "../../../root/.ssh",
        "../..",
        "/etc/shadow",
        "//windows/system32",
    ]

    for attempt in traversal_attempts:
        with pytest.raises(HTTPException) as exc_info:
            validate_sandboxed_path(str(mount_dir), attempt)
        assert exc_info.value.status_code == 400
        assert "traversal" in exc_info.value.detail.lower()


def test_get_storage_devices_and_status():
    # Login as admin
    login_res = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. GET /storage/devices & /api/storage/devices
    res = client.get("/storage/devices", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "devices" in data
    assert len(data["devices"]) > 0

    res_api = client.get("/api/storage/devices", headers=headers)
    assert res_api.status_code == 200
    assert "devices" in res_api.json()

    # 2. GET /storage/status & /api/storage/status
    res_status = client.get("/storage/status", headers=headers)
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert "totalStorageDevices" in status_data
    assert "mountedCount" in status_data
    assert "totalBytes" in status_data
    assert "usedBytes" in status_data
    assert "freeBytes" in status_data


def test_storage_file_management_operations():
    login_res = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    devices = client.get("/storage/devices", headers=headers).json()["devices"]
    device_path = devices[0]["device"]

    # 1. List files in root
    list_res = client.get(f"/storage/files?device={device_path}&path=/", headers=headers)
    assert list_res.status_code == 200
    assert "items" in list_res.json()

    # 2. Create directory
    mkdir_res = client.post(
        "/storage/mkdir",
        json={"device": device_path, "path": "/", "dirName": "TEST_FOLDER"},
        headers=headers,
    )
    assert mkdir_res.status_code == 200

    # 3. Create a test file inside TEST_FOLDER via file operations or directly
    dev_obj = storage_manager.get_device(device_path)
    mount_p = Path(dev_obj.mount_point)
    test_file = mount_p / "TEST_FOLDER" / "sample.txt"
    test_file.write_text("CEB Forensic Test File")

    # 4. Get file metadata
    file_info = client.get(
        f"/storage/file?device={device_path}&path=/TEST_FOLDER/sample.txt",
        headers=headers,
    )
    assert file_info.status_code == 200
    assert file_info.json()["name"] == "sample.txt"
    assert file_info.json()["type"] == "file"

    # 5. Copy file
    copy_res = client.post(
        "/storage/copy",
        json={
            "device": device_path,
            "srcPath": "/TEST_FOLDER/sample.txt",
            "dstPath": "/TEST_FOLDER/sample_copy.txt",
        },
        headers=headers,
    )
    assert copy_res.status_code == 200

    # 6. Delete file
    del_res = client.delete(
        f"/storage/file?device={device_path}&path=/TEST_FOLDER/sample_copy.txt",
        headers=headers,
    )
    assert del_res.status_code == 200

    # Cleanup directory
    client.delete(f"/storage/file?device={device_path}&path=/TEST_FOLDER", headers=headers)


def test_ceb_data_export_to_usb():
    login_res = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    devices = client.get("/storage/devices", headers=headers).json()["devices"]
    device_path = devices[0]["device"]

    export_res = client.post(
        "/storage/export",
        json={
            "device": device_path,
            "includeCases": True,
            "includeEvidence": True,
            "includeCustody": True,
            "includeAuditLogs": True,
        },
        headers=headers,
    )
    assert export_res.status_code == 200
    data = export_res.json()
    assert data["status"] == "success"
    assert "savedPath" in data
    assert "/CEB_DATA/export_" in data["savedPath"]


def test_safe_eject():
    login_res = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    devices = client.get("/storage/devices", headers=headers).json()["devices"]
    device_path = devices[0]["device"]

    eject_res = client.post(
        "/storage/eject",
        json={"device": device_path},
        headers=headers,
    )
    assert eject_res.status_code == 200
    data = eject_res.json()
    assert data["status"] == "ejected"
    assert data["message"] == "USB READY TO REMOVE"
    assert data["readyToRemove"] is True


def test_mock_storage_insertion_and_removal():
    login_res = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Add second mock drive /dev/sdb1
    add_res = client.post(
        "/storage/mock/toggle",
        json={"action": "add", "device": "/dev/sdb1", "name": "Kingston DataTraveler"},
        headers=headers,
    )
    assert add_res.status_code == 200
    assert add_res.json()["action"] == "added"

    # Verify multiple drives connected
    devices_res = client.get("/storage/devices", headers=headers)
    devices = devices_res.json()["devices"]
    dev_paths = [d["device"] for d in devices]
    assert "/dev/sdb1" in dev_paths

    # Remove mock drive
    rem_res = client.post(
        "/storage/mock/toggle",
        json={"action": "remove", "device": "/dev/sdb1"},
        headers=headers,
    )
    assert rem_res.status_code == 200
    assert rem_res.json()["action"] == "removed"


def test_api_path_traversal_rejection():
    login_res = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Ensure device is mounted
    client.post(
        "/storage/mock/toggle",
        json={"action": "add", "device": "/dev/sda1", "name": "SanDisk Ultra"},
        headers=headers,
    )

    # Attempt directory traversal via GET /storage/files
    res = client.get("/storage/files?device=/dev/sda1&path=../../etc", headers=headers)
    assert res.status_code == 400
    assert "traversal" in res.json()["detail"].lower()


