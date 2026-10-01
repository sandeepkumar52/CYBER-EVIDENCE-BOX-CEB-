import logging
import os
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Evidence, EvidenceEncryption, User
from ..security.auth import get_current_user, require_role
from ..hardware.hardware_interface import hardware_manager
from ..hardware.usb.usb_manager import usb_manager
from ..hardware.usb.usb_events import hardware_events
from ..hardware.usb.usb_detector import DetectedUSBDevice, is_valid_device_path
from ..services.audit_service import log_audit_event
from ..services.encryption_service import encryption_service
from ..services.key_manager import get_key_manager
from ..services.storage_service import get_evidence_vault_path
from ..services.usb_service import usb_service

logger = logging.getLogger("ceb.routers.hardware")

router = APIRouter(
    prefix="/hardware",
    tags=["Hardware & USB Subsystem"],
)


# ==========================================
# Pydantic Schemas for Forensic USB Requests
# ==========================================
class USBScanRequest(BaseModel):
    device_id: str


class AcquireFileRequest(BaseModel):
    case_id: int
    mount_point: str
    file_path: str
    relative_path: str
    sha256: str
    file_size: int
    mime_type: str


# ==========================================
# Pydantic Schemas for Serial Hardware USB Requests
# ==========================================
class USBConnectRequest(BaseModel):
    device_path: str = Field(..., alias="devicePath", description="Path of USB/Serial device, e.g. /dev/ttyUSB0 or COM3")
    baud_rate: Optional[int] = Field(None, alias="baudRate", description="Serial baud rate, e.g. 115200 or 9600")
    data_bits: Optional[int] = Field(8, alias="dataBits", ge=5, le=8)
    stop_bits: Optional[float] = Field(1, alias="stopBits")
    parity: Optional[str] = Field("none", description="Parity: none, even, odd, mark, space")
    timeout: Optional[float] = Field(1.0, ge=0.1, le=10.0)

    model_config = ConfigDict(populate_by_name=True)


class USBDisconnectRequest(BaseModel):
    device_path: str = Field(..., alias="devicePath", description="Path of USB device to disconnect")

    model_config = ConfigDict(populate_by_name=True)


class USBWriteRequest(BaseModel):
    device_path: str = Field(..., alias="devicePath", description="Path of connected serial device")
    data: str = Field(..., max_length=4096, description="Data string or command payload to transmit")

    model_config = ConfigDict(populate_by_name=True)


class MockDeviceToggleRequest(BaseModel):
    action: str = Field("add", description="'add' or 'remove'")
    device_path: str = Field(..., alias="devicePath")
    role: Optional[str] = Field("esp32", description="esp32, gps, sensor_controller")
    product: Optional[str] = Field("Simulated USB Device")


# ==========================================
# Forensic USB Endpoints (GitHub Base)
# ==========================================
@router.post("/usb/scan")
def scan_usb_device(
    request: USBScanRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Mounts a USB evidence source read-only and scans it for files, returning the file tree,
    SHA-256 hashes, and malware status without modifying the source filesystem.
    """
    try:
        mount_point = usb_service.mount_usb(request.device_id)
        files = usb_service.scan_filesystem(mount_point)
        return {
            "device_id": request.device_id,
            "mount_point": mount_point,
            "files": files,
        }
    except Exception as e:
        logger.error(f"Error scanning USB device {request.device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/usb/unmount")
def unmount_usb_device(
    mount_point: str,
    current_user: User = Depends(get_current_user),
):
    """
    Safely unmounts the forensic USB device read-only mount point.
    """
    try:
        usb_service.unmount_usb(mount_point)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error unmounting USB {mount_point}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/usb/acquire-file")
def acquire_usb_file(
    request: AcquireFileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Acquires an individual file directly from a read-only forensic USB mount,
    encrypts it straight into the AES-256-GCM vault, generates evidence metadata,
    records chain of custody, and creates an audit trail entry.
    """
    if not os.path.exists(request.file_path):
        raise HTTPException(status_code=404, detail="File not found on USB mount")

    evidence_id = f"EV-{uuid.uuid4().hex[:8].upper()}"
    vault_rel_path, vault_full_path = get_evidence_vault_path(evidence_id)

    key_manager = get_key_manager()
    dek = key_manager.generate_dek()
    wrapped_dek = key_manager.wrap_dek(dek)

    try:
        # Encrypt straight from USB mount to vault
        nonce, tag = encryption_service.encrypt_evidence(dek, request.file_path, str(vault_full_path))

        # Create DB records
        new_evidence = Evidence(
            evidence_id=evidence_id,
            case_id=request.case_id,
            evidence_type="USB Device",
            description=request.relative_path,
            hash_algorithm="SHA-256",
            hash_value=request.sha256,
            storage_path=vault_rel_path,
            file_size_bytes=request.file_size,
            status="Secured",
        )
        db.add(new_evidence)
        db.flush()

        encryption_meta = EvidenceEncryption(
            evidence_id=new_evidence.id,
            encryption_algorithm="AES-256-GCM",
            encrypted_dek=wrapped_dek,
            nonce=nonce,
            authentication_tag=tag,
            encrypted_sha256=encryption_service.calculate_hash(str(vault_full_path)),
        )
        db.add(encryption_meta)

        log_audit_event(
            db,
            "EVIDENCE_ACQUIRED",
            f"Evidence {evidence_id} acquired directly from USB and encrypted into vault.",
            current_user.id,
        )

        db.commit()
        db.refresh(new_evidence)

        return {"status": "success", "evidence_id": evidence_id}
    except Exception as e:
        db.rollback()
        logger.error(f"Error acquiring file {request.file_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# General Hardware & Serial Subsystem Endpoints
# ==========================================
@router.get("/status")
def get_hardware_status(
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Returns the current comprehensive status of physical and virtual CEB hardware.
    """
    return hardware_manager.get_status()


@router.get("/gps")
def get_gps_data(
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Returns GNSS / GPS telemetry. If no GPS fix exists, reports an appropriate unavailable/no-fix state.
    """
    status = hardware_manager.get_status()
    return status.get("gps", {"available": False, "status": "unavailable", "latitude": None, "longitude": None})


@router.get("/health")
def get_hardware_health():
    """
    Hardware health monitoring endpoint for overall CEB hardware readiness.
    """
    return usb_manager.get_health()


@router.get("/usb")
@router.get("/usb/devices")
def get_usb_devices(
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Returns all currently detected USB & serial devices.
    """
    devices = usb_manager.get_all_devices()
    return {"devices": devices}


@router.get("/usb/status")
def get_usb_subsystem_status(
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Returns the complete USB hardware subsystem status including mode and scan parameters.
    """
    return usb_manager.get_subsystem_status()


@router.post("/usb/connect")
def connect_usb_device(
    payload: USBConnectRequest,
    current_user: User = Depends(require_role(["Admin", "Investigator"])),
):
    """
    Connect to a selected USB/serial device with configurable parameters.
    """
    if not is_valid_device_path(payload.device_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid device path format: '{payload.device_path}'",
        )

    try:
        success = usb_manager.connect_device(
            device_path=payload.device_path,
            baud_rate=payload.baud_rate,
            data_bits=payload.data_bits or 8,
            stop_bits=int(payload.stop_bits or 1),
            parity=payload.parity or "none",
            timeout=payload.timeout or 1.0,
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to establish serial connection to {payload.device_path}",
            )
        return {
            "status": "connected",
            "devicePath": payload.device_path,
            "message": f"Successfully connected to {payload.device_path}",
        }
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error connecting to USB device {payload.device_path}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/usb/disconnect")
def disconnect_usb_device(
    payload: USBDisconnectRequest,
    current_user: User = Depends(require_role(["Admin", "Investigator"])),
):
    """
    Disconnect from an active USB/serial device.
    """
    if not is_valid_device_path(payload.device_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid device path format: '{payload.device_path}'",
        )

    try:
        usb_manager.disconnect_device(payload.device_path)
        return {
            "status": "disconnected",
            "devicePath": payload.device_path,
            "message": f"Successfully disconnected from {payload.device_path}",
        }
    except Exception as e:
        logger.error(f"Error disconnecting USB device {payload.device_path}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/usb/write")
def write_usb_device(
    payload: USBWriteRequest,
    current_user: User = Depends(require_role(["Admin", "Investigator"])),
):
    """
    Send data or commands to a connected serial USB device.
    """
    if not is_valid_device_path(payload.device_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid device path format: '{payload.device_path}'",
        )

    try:
        success = usb_manager.write_to_device(payload.device_path, payload.data)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Write failed to {payload.device_path}",
            )
        return {
            "status": "written",
            "devicePath": payload.device_path,
            "bytesSent": len(payload.data.encode("utf-8")),
        }
    except RuntimeError as re:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(re))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error writing to USB device {payload.device_path}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/usb/read")
def read_usb_device(
    device_path: str = Query(..., alias="devicePath", description="Path of connected device"),
    limit: int = Query(50, ge=1, le=200, description="Max lines of buffer to return"),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Return recently received data buffer lines from a connected device.
    """
    if not is_valid_device_path(device_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid device path format: '{device_path}'",
        )

    lines = usb_manager.read_from_device(device_path, limit=limit)
    return {
        "devicePath": device_path,
        "lines": lines,
        "count": len(lines),
    }


@router.post("/usb/mock/toggle")
def toggle_mock_device(
    payload: MockDeviceToggleRequest,
    current_user: User = Depends(require_role(["Admin"])),
):
    """
    Development endpoint: Dynamically plug/unplug a simulated USB device to test hot-plug events.
    """
    if payload.action == "add":
        new_dev = DetectedUSBDevice(
            device_path=payload.device_path,
            vendor_id="10C4" if payload.role == "esp32" else "1546",
            product_id="EA60" if payload.role == "esp32" else "01A7",
            manufacturer="CEB Simulated Labs",
            product=payload.product or f"Simulated {payload.role.upper()}",
            serial_number=f"SIM-{payload.device_path}",
            type="serial",
            is_mock=True,
            description="Simulated hardware device for development testing",
        )
        usb_manager.detector.add_mock_device(new_dev)
        return {"message": f"Added mock device {payload.device_path}", "device": new_dev.to_dict()}
    else:
        usb_manager.detector.remove_mock_device(payload.device_path)
        return {"message": f"Removed mock device {payload.device_path}"}


@router.websocket("/ws")
async def hardware_websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time hardware status and telemetry events.
    Emits events: usb:connected, usb:disconnected, usb:data, usb:error, usb:status.
    """
    await hardware_events.connect(websocket)
    try:
        current_status = usb_manager.get_subsystem_status()
        await websocket.send_json({
            "event": "usb:status",
            "status": current_status,
        })

        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
            elif "scan" in msg:
                await usb_manager.perform_scan()
                await websocket.send_json({
                    "event": "usb:status",
                    "status": usb_manager.get_subsystem_status(),
                })
    except WebSocketDisconnect:
        hardware_events.disconnect(websocket)
    except Exception as e:
        logger.debug(f"Hardware WebSocket exception: {e}")
        hardware_events.disconnect(websocket)
