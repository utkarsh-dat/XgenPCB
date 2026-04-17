"""
PCB Builder - Pydantic Validation Schemas
Request/Response models for all API endpoints.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ━━ Auth ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    subscription_tier: str
    created_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


# ━━ Teams ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class TeamResponse(BaseModel):
    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    plan_type: str
    max_members: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ━━ Projects ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    team_id: Optional[uuid.UUID] = None
    visibility: str = "private"
    tags: Optional[list[str]] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    visibility: Optional[str] = None
    tags: Optional[list[str]] = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    team_id: Optional[uuid.UUID]
    visibility: str
    tags: Optional[list[str]]
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ━━ Designs ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class BoardConfig(BaseModel):
    width_mm: float = 100.0
    height_mm: float = 100.0
    layers: int = 2
    thickness_mm: float = 1.6
    copper_weight: str = "1oz"
    material: str = "FR4"
    surface_finish: str = "HASL"


class DesignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    project_id: uuid.UUID
    board_config: BoardConfig = BoardConfig()


class DesignUpdate(BaseModel):
    name: Optional[str] = None
    board_config: Optional[dict] = None
    schematic_data: Optional[dict] = None
    pcb_layout: Optional[dict] = None
    constraints: Optional[dict] = None


class DesignResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    board_config: dict
    schematic_data: dict
    pcb_layout: dict
    constraints: dict
    version: int
    status: str
    is_locked: bool
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ━━ AI ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class IntentRequest(BaseModel):
    user_input: str = Field(min_length=1, max_length=2000)
    design_context: Optional[dict] = None
    allowed_actions: list[str] = [
        "place_component", "route_net", "add_constraint",
        "generate_bom", "run_drc", "auto_route", "fix_violation",
    ]


class IntentResult(BaseModel):
    action_type: str
    parameters: dict
    confidence: float
    explanation: str


class ChatMessage(BaseModel):
    role: str
    content: str
    actions: Optional[list[dict]] = None


class ChatRequest(BaseModel):
    design_id: uuid.UUID
    message: str = Field(min_length=1, max_length=5000)
    context: Optional[dict] = None


class AutoFixRequest(BaseModel):
    violations: list[dict]
    design_data: dict


class DesignReviewRequest(BaseModel):
    design_data: dict
    review_type: str = "full"


# ━━ DRC ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class DRCRequest(BaseModel):
    design_data: dict
    rules: dict = {}


class DRCViolation(BaseModel):
    type: str
    severity: str
    message: str
    location: dict
    affected_nets: Optional[list[str]] = None


class DRCResult(BaseModel):
    violations: list[DRCViolation]
    warnings: list[DRCViolation]
    score: float
    passed: bool


# ━━ Components ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ComponentSearch(BaseModel):
    query: str
    category: Optional[str] = None
    manufacturer: Optional[str] = None
    package_type: Optional[str] = None
    limit: int = 20
    offset: int = 0


class ComponentResponse(BaseModel):
    id: uuid.UUID
    mpn: str
    name: str
    description: Optional[str]
    category: Optional[str]
    manufacturer: Optional[str]
    package_type: Optional[str]
    pin_count: Optional[int]
    datasheet_url: Optional[str]
    datasheet_data: dict

    model_config = {"from_attributes": True}


# ━━ Fabrication ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class FabQuoteRequest(BaseModel):
    design_id: uuid.UUID
    options: dict = {}
    prefer_indian: bool = True


class FabQuoteResponse(BaseModel):
    fabricator_name: str
    price: float
    currency: str = "INR"
    lead_time_days: int
    options: dict
    url: Optional[str] = None


# ━━ Generic ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    has_next: bool


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: Optional[float] = None
    result: Optional[dict] = None
    error: Optional[str] = None
