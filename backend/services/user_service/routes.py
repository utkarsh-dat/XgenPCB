"""
PCB Builder - User Service Routes
Authentication, profile management, and team operations.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.middleware.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from shared.models import Team, TeamMember, User
from shared.schemas import (
    TeamCreate,
    TeamResponse,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from shared.config import get_settings

settings = get_settings()
router = APIRouter()


# ━━ Authentication ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    # Check if email exists
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
    )
    db.add(user)
    await db.flush()

    token = create_access_token(user.id)

    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expiration_hours * 3600,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login with email and password."""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    token = create_access_token(user.id)

    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expiration_hours * 3600,
        user=UserResponse.model_validate(user),
    )


# ━━ Profile ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    updates: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user profile."""
    allowed_fields = {"full_name", "avatar_url", "preferences"}
    for key, value in updates.items():
        if key in allowed_fields:
            setattr(current_user, key, value)
    await db.flush()
    return UserResponse.model_validate(current_user)


# ━━ Teams ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/teams", response_model=TeamResponse, status_code=201)
async def create_team(
    data: TeamCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new team."""
    team = Team(name=data.name, owner_id=current_user.id)
    db.add(team)
    await db.flush()

    # Add owner as team member
    member = TeamMember(team_id=team.id, user_id=current_user.id, role="owner")
    db.add(member)
    await db.flush()

    return TeamResponse.model_validate(team)


@router.get("/teams", response_model=list[TeamResponse])
async def list_teams(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List teams the current user belongs to."""
    result = await db.execute(
        select(Team)
        .join(TeamMember, Team.id == TeamMember.team_id)
        .where(TeamMember.user_id == current_user.id)
    )
    teams = result.scalars().all()
    return [TeamResponse.model_validate(t) for t in teams]


@router.post("/teams/{team_id}/invite", status_code=200)
async def invite_to_team(
    team_id: uuid.UUID,
    email: str,
    role: str = "member",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Invite a user to a team."""
    # Verify requester is admin/owner
    member_check = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.role.in_(["owner", "admin"]),
        )
    )
    if not member_check.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not authorized to invite members")

    # Find user by email
    user_result = await db.execute(select(User).where(User.email == email))
    invitee = user_result.scalar_one_or_none()
    if not invitee:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if already a member
    existing = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id, TeamMember.user_id == invitee.id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User already in team")

    member = TeamMember(team_id=team_id, user_id=invitee.id, role=role)
    db.add(member)

    return {"message": f"Invited {email} as {role}"}
