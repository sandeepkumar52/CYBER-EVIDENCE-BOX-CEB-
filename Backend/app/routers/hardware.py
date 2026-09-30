from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from ..security.auth import get_current_user
from ..hardware.hardware_interface import hardware_manager

router = APIRouter(
    prefix="/hardware",
    tags=["hardware"],
)

@router.get("/status")
def get_hardware_status(
    current_user: User = Depends(get_current_user),
):
    Returns the current status of the physical Cyber Evidence Box hardware.
    Currently uses the mock adapter until serial implementation is provided.
    """
    return hardware_manager.get_status()

from pydantic import BaseModel

class USBScanRequest(BaseModel):
    device_id: str

@router.post("/usb/scan")
def scan_usb_device(
    request: USBScanRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Mounts a USB device read-only and scans it for files, returning the file tree,
    hashes, and malware status without modifying the source filesystem.
    """
    from ..services.usb_service import usb_service
    
    try:
        mount_point = usb_service.mount_usb(request.device_id)
        files = usb_service.scan_filesystem(mount_point)
        # We leave it mounted for acquisition, or unmount it and remount later.
        # For this workflow, it's safer to unmount if we are just scanning, but
        # since it's a read-only mount, keeping it mounted until acquisition finishes is fine.
        # However, to be clean, we can return the mount_point as a session token of sorts.
        return {
            "device_id": request.device_id,
            "mount_point": mount_point,
            "files": files
        }
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/usb/unmount")
def unmount_usb_device(
    mount_point: str,
    current_user: User = Depends(get_current_user),
):
    from ..services.usb_service import usb_service
    try:
        usb_service.unmount_usb(mount_point)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AcquireFileRequest(BaseModel):
    case_id: int
    mount_point: str
    file_path: str
    relative_path: str
    sha256: str
    file_size: int
    mime_type: str

@router.post("/usb/acquire-file")
def acquire_usb_file(
    request: AcquireFileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from ..services.storage_service import get_evidence_vault_path
    from ..services.encryption_service import encryption_service
    from ..services.key_manager import get_key_manager
    from ..services.audit_service import log_audit_event
    from ..models import Evidence, EvidenceEncryption
    import os
    import uuid

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
            status="Secured"
        )
        db.add(new_evidence)
        db.flush()
        
        encryption_meta = EvidenceEncryption(
            evidence_id=new_evidence.id,
            encryption_algorithm="AES-256-GCM",
            encrypted_dek=wrapped_dek,
            nonce=nonce,
            authentication_tag=tag
        )
        db.add(encryption_meta)
        
        log_audit_event(db, "EVIDENCE_ACQUIRED", f"Evidence {evidence_id} acquired directly from USB and encrypted.", current_user.id)
        
        db.commit()
        db.refresh(new_evidence)
        
        return {"status": "success", "evidence_id": evidence_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
