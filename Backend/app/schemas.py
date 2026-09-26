from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

UserRole = Literal["Admin", "Investigator", "Viewer"]

EvidenceType = Literal[
    "Disk Image",
    "USB Device",
    "Memory Dump",
    "Log File",
    "Document",
    "Mobile Device",
    "Network Capture",
    "Other",
]

EvidenceStatus = Literal[
    "Registered",
    "Acquired",
    "Verified",
    "Secured",
    "Transferred",
    "Archived",
]

CaseStatus = Literal["Active", "Under Investigation", "Closed", "Archived"]


# User Schemas
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6)
    role: UserRole = "Investigator"


class UserUpdate(BaseModel):
    role: UserRole | None = None
    password: str | None = Field(None, min_length=6)


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Auth Schemas
class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6)
    role: UserRole = "Investigator"


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# Case Schemas
class CaseCreate(BaseModel):
    case_id: str = Field(..., min_length=3, max_length=50)
    case_name: str = Field(..., min_length=3, max_length=200)
    description: str | None = None
    status: CaseStatus = "Active"
    created_by: int | None = None  # Populated automatically from Auth token if omitted


class CaseUpdate(BaseModel):
    case_name: str | None = None
    description: str | None = None
    status: CaseStatus | None = None
    is_archived: bool | None = None


class CaseResponse(BaseModel):
    id: int
    case_id: str
    case_name: str
    description: str | None = None
    status: str
    is_archived: bool = False
    created_by: int
    created_at: datetime
    creator: UserResponse | None = None
    evidence_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# Evidence Schemas
class EvidenceCreate(BaseModel):
    evidence_id: str = Field(..., min_length=3, max_length=50)
    case_id: int
    evidence_type: EvidenceType
    description: str | None = None
    device_identifier: str | None = None
    hash_algorithm: str = "SHA-256"
    hash_value: str | None = None


class EvidenceUpdate(BaseModel):
    description: str | None = None
    device_identifier: str | None = None
    status: EvidenceStatus | None = None


class EvidenceResponse(BaseModel):
    id: int
    evidence_id: str
    case_id: int
    evidence_type: str
    description: str | None = None
    device_identifier: str | None = None
    hash_algorithm: str | None = "SHA-256"
    hash_value: str | None = None
    storage_path: str | None = None
    file_size_bytes: int | None = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvidenceVerifyResponse(BaseModel):
    evidence_id: str
    is_valid: bool
    expected_hash: str | None
    computed_hash: str | None
    message: str


# Custody Event Schemas
class CustodyEventCreate(BaseModel):
    action: str = Field(..., min_length=2, max_length=100)
    location: str | None = None
    remarks: str | None = None


class CustodyEventResponse(BaseModel):
    id: int
    evidence_id: int
    user_id: int
    action: str
    location: str | None = None
    remarks: str | None = None
    timestamp: datetime
    user: UserResponse | None = None

    model_config = ConfigDict(from_attributes=True)


# Audit Log Schemas
class AuditLogResponse(BaseModel):
    id: int
    user_id: int | None = None
    event: str
    details: str | None = None
    timestamp: datetime
    user: UserResponse | None = None

    model_config = ConfigDict(from_attributes=True)


# Dashboard Stats
class DashboardStatsResponse(BaseModel):
    total_cases: int
    active_cases: int
    total_evidence: int
    verified_evidence: int
    storage_used_bytes: int
    recent_custody_events: list[CustodyEventResponse]
    recent_audit_logs: list[AuditLogResponse]