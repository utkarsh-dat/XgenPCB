"""
PCB Builder - Analytics Routes
Dashboard data, metrics, and insights endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.middleware.auth import get_current_user
from shared.middleware.rate_limit import limiter
from shared.models import User
from shared.schemas import PaginatedResponse
from services.analytics_service import AnalyticsService

router = APIRouter()
analytics = AnalyticsService()


@router.get("/dashboard")
@limiter.limit("60/minute")
async def get_dashboard(
    request: Request,
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's dashboard analytics."""
    data = await analytics.get_user_dashboard(current_user.id, db, days=days)
    return data


@router.get("/designs/{design_id}/metrics")
@limiter.limit("60/minute")
async def get_design_metrics(
    request: Request,
    design_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed metrics for a specific design."""
    import uuid
    data = await analytics.get_design_metrics(uuid.UUID(design_id), db)
    if not data:
        raise HTTPException(status_code=404, detail="Design not found")
    return data


@router.get("/platform")
@limiter.limit("30/minute")
async def get_platform_stats(
    request: Request,
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get platform-wide statistics (admin only)."""
    # Check if user is admin
    if current_user.subscription_tier not in ["admin", "enterprise"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    data = await analytics.get_platform_stats(db, days=days)
    return data
