import io
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_auth_login_default_users():
    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "Admin"


def test_full_forensic_workflow():
    # 1. Login as investigator
    login_res = client.post(
        "/auth/login",
        json={"username": "investigator01", "password": "investigator123"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get Current User /auth/me
    me_res = client.get("/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "investigator01"

    # 3. Create Case
    case_payload = {
        "case_id": "CASE-TEST-101",
        "case_name": "Test Forensic Investigation",
        "description": "Integration test case for evidence acquisition",
        "status": "Active",
    }
    case_res = client.post("/cases", json=case_payload, headers=headers)
    assert case_res.status_code == 201
    case_data = case_res.json()
    assert case_data["case_id"] == "CASE-TEST-101"
    case_pk = case_data["id"]

    # 4. List Cases
    list_cases_res = client.get("/cases", headers=headers)
    assert list_cases_res.status_code == 200
    assert any(c["case_id"] == "CASE-TEST-101" for c in list_cases_res.json())

    # 5. Register Evidence under Case
    evidence_payload = {
        "evidence_id": "EVID-TEST-001",
        "case_id": case_pk,
        "evidence_type": "Disk Image",
        "description": "Primary forensic image of suspect laptop drive",
        "device_identifier": "NVMe Drive SN: 9812739",
        "hash_algorithm": "SHA-256",
    }
    ev_res = client.post("/evidence", json=evidence_payload, headers=headers)
    assert ev_res.status_code == 201
    ev_data = ev_res.json()
    assert ev_data["evidence_id"] == "EVID-TEST-001"
    assert ev_data["status"] == "Registered"

    # 6. Upload Evidence File & Calculate Hash
    dummy_file_content = b"CYBER EVIDENCE BOX FORENSIC CONTENT TEST DATA 2026"
    files = {"file": ("suspect_disk.bin", io.BytesIO(dummy_file_content), "application/octet-stream")}
    upload_res = client.post(
        f"/evidence/{ev_data['evidence_id']}/upload",
        files=files,
        headers=headers,
    )
    assert upload_res.status_code == 200
    uploaded_ev = upload_res.json()
    assert uploaded_ev["status"] == "Acquired"
    assert uploaded_ev["hash_value"] is not None
    recorded_hash = uploaded_ev["hash_value"]

    # 7. Verify Evidence Integrity
    verify_res = client.post(
        f"/evidence/{ev_data['evidence_id']}/verify",
        headers=headers,
    )
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["is_valid"] is True
    assert verify_data["computed_hash"] == recorded_hash

    # 8. Create Custody Event
    custody_payload = {
        "action": "Evidence Secured in Vault",
        "location": "Evidence Room Locker A-12",
        "remarks": "Placed in static-shielding evidence bag",
    }
    custody_res = client.post(
        f"/evidence/{ev_data['evidence_id']}/custody",
        json=custody_payload,
        headers=headers,
    )
    assert custody_res.status_code == 201

    # 9. Get Chain of Custody History
    custody_history_res = client.get(
        f"/evidence/{ev_data['evidence_id']}/custody",
        headers=headers,
    )
    assert custody_history_res.status_code == 200
    history = custody_history_res.json()
    assert len(history) >= 2  # Registration + Secured

    # 10. Check Audit Logs
    audit_res = client.get("/audit-logs", headers=headers)
    assert audit_res.status_code == 200
    audit_logs = audit_res.json()
    assert len(audit_logs) > 0


def test_duplicate_case_id_rejection():
    login_res = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    case_payload = {
        "case_id": "CASE-DUP-001",
        "case_name": "Duplicate Test Case",
    }
    res1 = client.post("/cases", json=case_payload, headers=headers)
    assert res1.status_code == 201

    res2 = client.post("/cases", json=case_payload, headers=headers)
    assert res2.status_code == 409
