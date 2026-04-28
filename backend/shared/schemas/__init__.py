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
# ── PCB Generation Input Types ────────────────────────────────

class PlainTextInput(BaseModel):
    """Plain English text description."""
    description: str = Field(min_length=10, max_length=10000)


class BOMNetlistInput(BaseModel):
    """Bill of Materials + Netlist spreadsheet data."""
    components: list[dict] = Field(min_length=1)
    nets: list[dict] = Field(min_length=1)


class ExistingDesignInput(BaseModel):
    """Existing KiCad/schematic file to convert."""
    file_type: str = Field(description="kicad_sch, kicad_pcb, eagle, altium")
    file_content: str = Field(description="Base64 encoded file content or file URL")


# ── PCB Generation Request ────────────────────────────────

class PCBGenerationInput(BaseModel):
    """Input for PCB generation - supports 3 input types."""
    input_type: str = Field(description="text, bom_netlist, existing_design")
    
    # For text input
    description: Optional[str] = None
    
    # For BOM+netlist input
    components: Optional[list[dict]] = None
    nets: Optional[list[dict]] = None
    
    # For existing design conversion
    file_type: Optional[str] = None
    file_url: Optional[str] = None
    
    # Generation options
    board_config: Optional[BoardConfig] = None
    auto_route: bool = True
    generate_3d_model: bool = True


class ComponentPlacement(BaseModel):
    """Placed component with position."""
    id: str
    name: str
    mpn: Optional[str] = None
    footprint: str
    x: float
    y: float
    rotation: float = 0.0
    layer: str = "F"


class NetConnection(BaseModel):
    """Net connection between pins."""
    name: str
    pins: list[dict]  # [{"component_id": str, "pin": str}, ...]


class PCBGenerationOutput(BaseModel):
    """Output from PCB generation."""
    design_id: Optional[uuid.UUID] = None
    
    # Board definition
    board_config: dict
    
    # Placed components
    placed_components: list[ComponentPlacement]
    
    # Routed nets
    nets: list[NetConnection]
    tracks: list[dict]  # [{"start": [x,y], "end": [x,y], "width": float, "layer": str}, ...]
    vias: list[dict]  # [{"x": float, "y": float, "from_layer": int, "to_layer": int}, ...]
    
    # Generation metadata
    generation_time_ms: int
    tokens_used: int
    
    # Output files
    gerber_zip_url: Optional[str] = None
    step_model_url: Optional[str] = None
    
    # Warnings/Issues
    warnings: list[str] = []
    
    model_config = {"from_attributes": True}


class IntentRequest(BaseModel):
    user_input: str = Field(min_length=1, max_length=2000)
    design_context: Optional[dict] = None
    allowed_actions: list[str] = [
        "place_component", "route_net", "add_constraint",
        "generate_bom", "run_drc", "auto_route", "fix_violation",
    ]


# ━━ PCB Generation ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PCBGenerationOptions(BaseModel):
    """Options for PCB generation."""
    multi_candidate: bool = False
    num_candidates: int = Field(default=3, ge=1, le=5)
    enable_explainability: bool = True
    target_manufacturer: str = "JLCPCB Standard"
    ipc_class: str = "Class 2"
    prioritize: str = "balanced"  # "cost", "performance", "density", "balanced"


class PCBGenerateRequest(BaseModel):
    """Request to generate a complete PCB design."""
    input_type: str = Field(description="text, bom_netlist, existing_design")
    
    # For text input
    description: Optional[str] = None
    
    # For BOM+netlist input
    components: Optional[list[dict]] = None
    nets: Optional[list[dict]] = None
    
    # For existing design conversion
    file_type: Optional[str] = None
    file_url: Optional[str] = None
    
    # Generation options
    board_config: Optional[BoardConfig] = None
    auto_route: bool = True
    generate_3d_model: bool = True
    options: Optional[PCBGenerationOptions] = None


class PCBGenerateResponse(BaseModel):
    """Response with generated PCB design."""
    design_id: uuid.UUID
    board_config: dict
    pcb_layout: dict
    
    # Generation metadata
    generation_time_ms: int
    tokens_used: int
    
    # Output files (URLs if requested)
    gerber_url: Optional[str] = None
    step_url: Optional[str] = None
    
    # Warnings from generation
    warnings: list[str] = []


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


class DRCViolationDetail(BaseModel):
    rule_id: str
    rule_name: str
    category: str
    severity: str
    message: str
    location: dict
    affected_nets: list[str] = []
    measured_value: Optional[float] = None
    required_value: Optional[float] = None
    unit: str = "mm"
    suggestion: str = ""
    ipc_reference: str = ""
    fix_strategy: str = ""


class DRCReport(BaseModel):
    passed: bool
    score: float
    violations: list[DRCViolationDetail] = []
    summary: dict = {}
    ipc_compliance: dict = {}


class DFMReport(BaseModel):
    passed: bool
    score: float
    fabrication_issues: list[DRCViolationDetail] = []
    assembly_issues: list[DRCViolationDetail] = []
    copper_balance: dict = {}
    test_point_coverage: float = 0.0
    summary: dict = {}
    manufacturer_recommendations: list[str] = []


class SIReport(BaseModel):
    passed: bool
    score: float
    impedance_issues: list[DRCViolationDetail] = []
    length_mismatch_issues: list[DRCViolationDetail] = []
    crosstalk_issues: list[DRCViolationDetail] = []
    return_path_issues: list[DRCViolationDetail] = []
    high_speed_nets: list[dict] = []
    summary: dict = {}


class ValidationReport(BaseModel):
    drc: DRCReport
    dfm: DFMReport
    si: SIReport
    overall_score: float
    ready_for_fab: bool
    critical_issues: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []


class CandidateMetricsResponse(BaseModel):
    routing_completion: float
    drc_score: float
    drc_violations: int
    drc_critical: int
    drc_warnings: int
    dfm_score: float
    si_score: float
    thermal_score: float
    overall_score: float
    via_count: int
    total_trace_length_mm: float
    board_area_utilization: float
    manufacturing_cost_estimate_usd: float
    estimated_cleanup_time_min: float


class LayoutCandidateResponse(BaseModel):
    candidate_id: str
    metrics: CandidateMetricsResponse
    rank: int
    selected: bool
    reasoning: str
    differences_from_best: list[str]


class ExplanationResponse(BaseModel):
    overall_reasoning: str
    design_philosophy: str
    critical_choices: list[dict]
    risk_assessment: dict
    optimization_notes: list[str]
    decisions: list[dict]


class JobResponse(BaseModel):
    id: uuid.UUID
    job_type: str
    status: str
    progress: float
    stage: Optional[str] = None
    retries: int
    max_retries: int
    input_data: dict
    output_data: Optional[dict] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IdempotencyConflictResponse(BaseModel):
    error_code: str = "IDEMPOTENCY_CONFLICT"
    message: str
    details: str
    suggestion: str = "Use a new idempotency key if this is a different request."


class RateLimitResponse(BaseModel):
    error_code: str = "RATE_LIMIT_EXCEEDED"
    message: str
    details: str
    suggestion: str = "Wait before retrying or upgrade your plan."
    retry_after: int


class ValidationErrorDetail(BaseModel):
    field: str
    issue: str
    constraint: Optional[str] = None
    suggestion: Optional[str] = None


class ValidationErrorResponse(BaseModel):
    error_code: str = "VALIDATION_ERROR"
    message: str
    details: list[ValidationErrorDetail]
    suggestion: str = "Review and correct the listed fields before resubmitting."


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    checks: dict
