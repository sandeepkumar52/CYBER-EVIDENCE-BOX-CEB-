from fastapi import APIRouter, Depends
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
    """
    Returns the current status of the physical Cyber Evidence Box hardware.
    Currently uses the mock adapter until serial implementation is provided.
    """
    return hardware_manager.get_status()
