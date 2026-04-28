"""
PCB Builder - Analytics Service
Metrics, insights, and dashboard data for PCB designs.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import AIGeneration, Design, Job, Project, User


class AnalyticsService:
    """Provides analytics and insights for the dashboard."""

    async def get_user_dashboard(
        self,
        user_id: uuid.UUID,
        db: AsyncSession,
        days: int = 30,
    ) -> dict:
        """Get user dashboard analytics."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Project stats
        proj_result = await db.execute(
            select(func.count()).select_from(Project).where(
                Project.created_by == user_id,
                Project.created_at >= since,
            )
        )
        projects_count = proj_result.scalar_one()

        # Design stats
        design_result = await db.execute(
            select(func.count()).select_from(Design).where(
                Design.created_by == user_id,
                Design.created_at >= since,
            )
        )
        designs_count = design_result.scalar_one()

        # Job stats
        job_stats = await db.execute(
            select(
                func.count().label("total"),
                func.sum(func.case((Job.status == "completed", 1), else_=0)).label("completed"),
                func.sum(func.case((Job.status == "failed", 1), else_=0)).label("failed"),
                func.avg(Job.progress * 100).label("avg_progress"),
            ).where(
                Job.user_id == user_id,
                Job.created_at >= since,
            )
        )
        job_row = job_stats.one()

        # AI generations
        gen_result = await db.execute(
            select(func.count()).select_from(AIGeneration).where(
                AIGeneration.user_id == user_id,
                AIGeneration.created_at >= since,
            )
        )
        generations_count = gen_result.scalar_one()

        # Recent activity
        recent_jobs = await db.execute(
            select(Job).where(
                Job.user_id == user_id,
                Job.created_at >= since,
            ).order_by(Job.created_at.desc()).limit(10)
        )
        jobs = recent_jobs.scalars().all()

        # DRC score trend
        drc_scores = []
        for job in jobs:
            if job.output_data and "validation" in job.output_data:
                drc = job.output_data["validation"].get("drc", {})
                if "score" in drc:
                    drc_scores.append({
                        "date": job.created_at.isoformat(),
                        "score": drc["score"],
                    })

        return {
            "period_days": days,
            "summary": {
                "projects_created": projects_count,
                "designs_created": designs_count,
                "jobs_submitted": job_row.total or 0,
                "jobs_completed": job_row.completed or 0,
                "jobs_failed": job_row.failed or 0,
                "ai_generations": generations_count,
                "success_rate": round((job_row.completed / max(job_row.total, 1)) * 100, 1),
            },
            "drc_trend": drc_scores,
            "recent_jobs": [
                {
                    "id": str(j.id),
                    "type": j.job_type,
                    "status": j.status,
                    "progress": float(j.progress) if j.progress else 0,
                    "stage": j.stage,
                    "created_at": j.created_at.isoformat(),
                }
                for j in jobs
            ],
        }

    async def get_platform_stats(
        self,
        db: AsyncSession,
        days: int = 30,
    ) -> dict:
        """Get platform-wide statistics (admin only)."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # User stats
        user_result = await db.execute(
            select(func.count()).select_from(User).where(
                User.created_at >= since,
            )
        )
        new_users = user_result.scalar_one()

        total_users = await db.execute(select(func.count()).select_from(User))
        total_users_count = total_users.scalar_one()

        # Job stats
        job_stats = await db.execute(
            select(
                func.count().label("total"),
                func.sum(func.case((Job.status == "completed", 1), else_=0)).label("completed"),
                func.avg(Job.generation_time_ms).label("avg_time_ms"),
            ).where(Job.created_at >= since)
        )
        job_row = job_stats.one()

        # Design stats
        design_stats = await db.execute(
            select(
                func.count().label("total"),
                func.avg(Design.version).label("avg_versions"),
            ).where(Design.created_at >= since)
        )
        design_row = design_stats.one()

        return {
            "period_days": days,
            "users": {
                "total": total_users_count,
                "new": new_users,
            },
            "jobs": {
                "total": job_row.total or 0,
                "completed": job_row.completed or 0,
                "avg_generation_time_ms": round(job_row.avg_time_ms or 0, 0),
            },
            "designs": {
                "total": design_row.total or 0,
                "avg_versions": round(float(design_row.avg_versions or 0), 1),
            },
        }

    async def get_design_metrics(
        self,
        design_id: uuid.UUID,
        db: AsyncSession,
    ) -> dict:
        """Get detailed metrics for a specific design."""
        result = await db.execute(select(Design).where(Design.id == design_id))
        design = result.scalar_one_or_none()
        if not design:
            return {}

        layout = design.pcb_layout or {}
        components = layout.get("placed_components", [])
        tracks = layout.get("tracks", [])
        vias = layout.get("vias", [])

        board = design.board_config or {}
        area = board.get("width_mm", 0) * board.get("height_mm", 0)

        # Component breakdown
        comp_types = {}
        for c in components:
            cat = "unknown"
            name = c.get("name", "").upper()
            if any(x in name for x in ["C", "CAP"]):
                cat = "capacitor"
            elif any(x in name for x in ["R", "RES"]):
                cat = "resistor"
            elif any(x in name for x in ["L", "IND"]):
                cat = "inductor"
            elif any(x in name for x in ["D", "DIODE", "LED"]):
                cat = "diode"
            elif any(x in name for x in ["Q", "MOSFET", "TRANSISTOR"]):
                cat = "transistor"
            elif any(x in name for x in ["U", "IC", "MCU", "CPU"]):
                cat = "ic"
            elif any(x in name for x in ["J", "CONN", "USB", "HEADER"]):
                cat = "connector"
            comp_types[cat] = comp_types.get(cat, 0) + 1

        # Track metrics
        total_length = sum(
            ((t["end"][0] - t["start"][0]) ** 2 + (t["end"][1] - t["start"][1]) ** 2) ** 0.5
            for t in tracks
        )

        return {
            "design_id": str(design_id),
            "name": design.name,
            "status": design.status,
            "version": design.version,
            "board": {
                "width_mm": board.get("width_mm", 0),
                "height_mm": board.get("height_mm", 0),
                "layers": board.get("layers", 2),
                "area_mm2": area,
            },
            "components": {
                "total": len(components),
                "by_type": comp_types,
            },
            "routing": {
                "tracks": len(tracks),
                "vias": len(vias),
                "total_trace_length_mm": round(total_length, 1),
                "avg_trace_length_mm": round(total_length / max(len(tracks), 1), 1),
            },
            "density": {
                "components_per_cm2": round(len(components) / max(area / 100, 1), 2),
                "tracks_per_cm2": round(len(tracks) / max(area / 100, 1), 2),
            },
            "created_at": design.created_at.isoformat() if design.created_at else None,
            "updated_at": design.updated_at.isoformat() if design.updated_at else None,
        }
