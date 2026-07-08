from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel


class EngagementCreate(BaseModel):
    name: str
    description: str = ""
    scope: List[str]


class EngagementUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    scope: Optional[List[str]] = None
    status: Optional[str] = None


class EngagementResponse(BaseModel):
    id: UUID
    name: str
    description: str
    scope: List[str]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TargetCreate(BaseModel):
    value: str
    type: str


class TargetResponse(BaseModel):
    id: UUID
    engagement_id: UUID
    value: str
    type: str
    status: str
    is_alive: bool
    added_by: str

    model_config = {"from_attributes": True}


class ScanResponse(BaseModel):
    id: UUID
    target_id: UUID
    engagement_id: UUID
    plugin_name: str
    stage: str
    status: str
    raw_output: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class FindingResponse(BaseModel):
    id: UUID
    engagement_id: UUID
    target_id: UUID
    scan_id: Optional[UUID]
    title: str
    severity: str
    cvss_score: Optional[float]
    description: str
    evidence: Any
    cve_id: Optional[str]
    mitre_technique: Optional[str]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class FindingUpdate(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None


class RunEngagementRequest(BaseModel):
    stages: Optional[List[str]] = None
