import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..security.auth import get_current_user, require_role
from ..hardware.storage.storage_manager import storage_manager
from ..hardware.storage.storage_file_manager import storage_file_manager
from ..hardware.storage.storage_exporter import storage_exporter

logger = logging.getLogger("ceb.routers.storage")

router = APIRouter(
    prefix="/storage",
    tags=["USB Storage & Pendrive Management"],
)


# Request Models
class MkdirRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    device: str = Field(..., description="Device path or mount point identifier, e.g. /dev/sda1")
    path: str = Field("/", description="Parent directory path within USB mount")
    dir_name: str = Field(..., alias="dirName", min_length=1, max_length=100, description="New directory name")


class CopyMoveRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    device: str = Field(..., description="Device path or mount point identifier, e.g. /dev/sda1")
    src_path: str = Field(..., alias="srcPath", description="Source path within USB mount")
    dst_path: str = Field(..., alias="dstPath", description="Destination path within USB mount")


class EjectRequest(BaseModel):
    device: str = Field(..., description="Device path or mount point to safely unmount and eject")


class ExportRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    device: str = Field(..., description="Target USB device path or mount point, e.g. /dev/sda1")
    include_cases: bool = Field(True, alias="includeCases")
    include_evidence: bool = Field(True, alias="includeEvidence")
    include_custody: bool = Field(True, alias="includeCustody")
    include_audit_logs: bool = Field(True, alias="includeAuditLogs")


class MockStorageToggleRequest(BaseModel):
    action: str = Field("add", description="'add' or 'remove'")
    device: str = Field("/dev/sda1", description="Device path identifier")
    name: Optional[str] = Field("Simulated USB Flash Drive")


def _resolve_device_mount(device_path: str) -> str:
    dev = storage_manager.get_device(device_path)
    if not dev:
        # Check by mount point
        dev = next((d for d in storage_manager._known_devices.values() if d.mount_point == device_path), None)

    if not dev or not dev.mount_point:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"USB Storage device '{device_path}' not found or not mounted",
        )
    return dev.mount_point


@router.get("/devices")
def get_storage_devices(
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Returns all detected USB storage devices, pendrives, and external disks.
    """
    devices = storage_manager.get_all_devices()
    return {"devices": devices}


@router.get("/status")
def get_storage_status(
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Returns storage subsystem health, total/used/free capacity, and mount status.
    """
    return storage_manager.get_status()


@router.get("/files")
def list_storage_files(
    device: str = Query(..., description="Device path, e.g. /dev/sda1"),
    path: str = Query("/", description="Directory path within USB drive"),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Lists files and directories on a selected mounted USB storage device.
    Strictly sandboxed inside the USB mount point.
    """
    mount_point = _resolve_device_mount(device)
    return storage_file_manager.list_files(mount_point, rel_path=path)


@router.get("/file")
def get_file_metadata(
    device: str = Query(..., description="Device path, e.g. /dev/sda1"),
    path: str = Query(..., description="File path within USB drive"),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Returns metadata for a specific file or folder inside the USB storage.
    """
    mount_point = _resolve_device_mount(device)
    return storage_file_manager.get_file_info(mount_point, rel_path=path)


@router.post("/mkdir")
def make_storage_directory(
    payload: MkdirRequest,
    current_user: User = Depends(require_role(["Admin", "Investigator"])),
):
    """
    Creates a new directory inside the mounted USB drive.
    """
    mount_point = _resolve_device_mount(payload.device)
    return storage_file_manager.make_directory(mount_point, payload.path, payload.dir_name)


@router.post("/copy")
def copy_storage_file(
    payload: CopyMoveRequest,
    current_user: User = Depends(require_role(["Admin", "Investigator"])),
):
    """
    Copies a file or folder inside the mounted USB drive.
    """
    mount_point = _resolve_device_mount(payload.device)
    return storage_file_manager.copy_item(mount_point, payload.src_path, payload.dst_path)


@router.post("/move")
def move_storage_file(
    payload: CopyMoveRequest,
    current_user: User = Depends(require_role(["Admin", "Investigator"])),
):
    """
    Moves or renames a file or folder inside the mounted USB drive.
    """
    mount_point = _resolve_device_mount(payload.device)
    return storage_file_manager.move_item(mount_point, payload.src_path, payload.dst_path)


@router.delete("/file")
def delete_storage_file(
    device: str = Query(..., description="Device path, e.g. /dev/sda1"),
    path: str = Query(..., description="Relative path of file/folder to delete"),
    current_user: User = Depends(require_role(["Admin", "Investigator"])),
):
    """
    Deletes a file or directory inside the mounted USB storage.
    Cannot delete the root mount point.
    """
    mount_point = _resolve_device_mount(device)
    return storage_file_manager.delete_item(mount_point, rel_path=path)


@router.post("/eject")
def eject_storage_device(
    payload: EjectRequest,
    current_user: User = Depends(require_role(["Admin", "Investigator"])),
):
    """
    Safely flushes pending writes and unmounts the USB storage device.
    Displays 'USB READY TO REMOVE'.
    """
    try:
        return storage_manager.safe_eject(payload.device)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"Error ejecting storage device {payload.device}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/export")
def export_ceb_data_to_usb(
    payload: ExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Investigator"])),
):
    """
    Exports CEB forensic case records, evidence metadata, chain of custody,
    and audit trail to the selected USB storage drive in structured JSON/CSV formats.
    """
    mount_point = _resolve_device_mount(payload.device)
    try:
        return storage_exporter.export_ceb_data_to_usb(
            mount_point=mount_point,
            db=db,
            include_cases=payload.include_cases,
            include_evidence=payload.include_evidence,
            include_custody=payload.include_custody,
            include_audit_logs=payload.include_audit_logs,
            exported_by=current_user.username,
        )
    except Exception as e:
        logger.error(f"Error during USB export to {payload.device}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Export failed: {str(e)}")


@router.post("/mock/toggle")
def toggle_mock_storage(
    payload: MockStorageToggleRequest,
    current_user: User = Depends(require_role(["Admin"])),
):
    """
    Development endpoint: Dynamically plug/unplug a simulated USB storage device.
    """
    if payload.action == "add":
        from ..hardware.storage.storage_detector import USBStorageDevice
        from ..config import MOCK_USB_STORAGE_DIR

        dev = USBStorageDevice(
            device=payload.device,
            name=payload.name or "Simulated USB Drive",
            mount_point=str(MOCK_USB_STORAGE_DIR),
            filesystem="exfat",
            total_bytes=64_000_000_000,
            used_bytes=14_000_000_000,
            free_bytes=50_000_000_000,
            mounted=True,
            status="mounted",
            is_mock=True,
        )
        storage_manager.detector.add_mock_storage(dev)
        storage_manager.scan_storage()
        return {"message": f"Added mock storage {payload.device}", "action": "added", "device": dev.to_dict()}
    else:
        storage_manager.detector.remove_mock_storage(payload.device)
        storage_manager.scan_storage()
        return {"message": f"Removed mock storage {payload.device}", "action": "removed"}
