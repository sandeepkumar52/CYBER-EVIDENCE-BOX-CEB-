from datetime import datetime

from pydantic import BaseModel, ConfigDict

class UserCreate(BaseModel):
    username: str
    role: str = "Investigator"


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
class CaseCreate(BaseModel):
    case_id: str
    case_name: str
    description: str | None = None
    status: str = "Active"
    created_by: int


class CaseResponse(BaseModel):
    id: int
    case_id: str
    case_name: str
    description: str | None
    status: str
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)