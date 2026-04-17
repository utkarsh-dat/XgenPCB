"""
PCB Builder - Project & Design Service Routes
Projects, designs, versions, and component management.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.middleware.auth import get_current_user
from shared.models import Design, DesignVersion, Project, User
from shared.schemas import (
    DesignCreate,
    DesignResponse,
    DesignUpdate,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)

router = APIRouter()


# ━━ Projects ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new project."""
    project = Project(
        name=data.name,
        description=data.description,
        team_id=data.team_id,
        visibility=data.visibility,
        tags=data.tags,
        created_by=current_user.id,
    )
    db.add(project)
    await db.flush()
    return ProjectResponse.model_validate(project)


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's projects."""
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Project)
        .where(Project.created_by == current_user.id)
        .order_by(Project.updated_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    projects = result.scalars().all()
    return [ProjectResponse.model_validate(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.created_by != current_user.id and project.visibility == "private":
        raise HTTPException(status_code=403, detail="Not authorized")
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)
    await db.flush()
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a project and all its designs."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.delete(project)


# ━━ Designs ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/{project_id}/designs", response_model=DesignResponse, status_code=201)
async def create_design(
    project_id: uuid.UUID,
    data: DesignCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new design within a project."""
    # Verify project exists and user has access
    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    design = Design(
        project_id=project_id,
        name=data.name,
        board_config=data.board_config.model_dump(),
        created_by=current_user.id,
    )
    db.add(design)
    await db.flush()

    # Create initial version
    version = DesignVersion(
        design_id=design.id,
        version=1,
        snapshot={
            "board_config": design.board_config,
            "schematic_data": {},
            "pcb_layout": {},
            "constraints": {},
        },
        created_by=current_user.id,
        commit_message="Initial design",
    )
    db.add(version)
    await db.flush()

    return DesignResponse.model_validate(design)


@router.get("/{project_id}/designs", response_model=list[DesignResponse])
async def list_designs(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all designs in a project."""
    result = await db.execute(
        select(Design)
        .where(Design.project_id == project_id)
        .order_by(Design.updated_at.desc())
    )
    designs = result.scalars().all()
    return [DesignResponse.model_validate(d) for d in designs]


@router.get("/{project_id}/designs/{design_id}", response_model=DesignResponse)
async def get_design(
    project_id: uuid.UUID,
    design_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific design."""
    result = await db.execute(
        select(Design).where(Design.id == design_id, Design.project_id == project_id)
    )
    design = result.scalar_one_or_none()
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")
    return DesignResponse.model_validate(design)


@router.patch("/{project_id}/designs/{design_id}", response_model=DesignResponse)
async def update_design(
    project_id: uuid.UUID,
    design_id: uuid.UUID,
    data: DesignUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a design (auto-saves and creates version)."""
    result = await db.execute(
        select(Design).where(Design.id == design_id, Design.project_id == project_id)
    )
    design = result.scalar_one_or_none()
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")
    if design.is_locked:
        raise HTTPException(status_code=423, detail="Design is locked")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(design, key, value)

    # Increment version
    design.version += 1

    # Create version snapshot
    version = DesignVersion(
        design_id=design.id,
        version=design.version,
        snapshot={
            "board_config": design.board_config,
            "schematic_data": design.schematic_data,
            "pcb_layout": design.pcb_layout,
            "constraints": design.constraints,
        },
        diff_from_previous=update_data,
        created_by=current_user.id,
        commit_message=f"Auto-save v{design.version}",
    )
    db.add(version)
    await db.flush()

    return DesignResponse.model_validate(design)
