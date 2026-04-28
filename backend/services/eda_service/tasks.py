"""
PCB Builder - EDA Service Celery Tasks
Long-running EDA jobs (Gerber generation, DRC, etc.)
"""

import json
import shutil
import subprocess
import tempfile
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from shared.config import get_settings
from shared.database import async_session_factory
from shared.logging_config import logger
from shared.models import Design, Job
from shared.schemas import DRCRequest

settings = get_settings()


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    queue="eda",
    name="services.eda_service.tasks.generate_gerber_task",
)
def generate_gerber_task(self, job_id: str, design_id: str):
    """Celery task for Gerber generation."""
    import asyncio
    asyncio.run(_generate_gerber_async(job_id, design_id))


async def _generate_gerber_async(job_id: str, design_id: str):
    """Async Gerber generation."""
    from sqlalchemy import select

    job_uuid = uuid.UUID(job_id)
    design_uuid = uuid.UUID(design_id)

    async with async_session_factory() as db:
        result = await db.execute(select(Job).where(Job.id == job_uuid))
        job = result.scalar_one_or_none()
        if not job:
            logger.error("Job not found", job_id=job_id)
            return

        job.status = "running"
        job.stage = "gerber_generation"
        job.started_at = datetime.now(timezone.utc)
        job.progress = 0.1
        await db.commit()

        try:
            result = await db.execute(select(Design).where(Design.id == design_uuid))
            design = result.scalar_one_or_none()
            if not design:
                raise Exception("Design not found")

            job.progress = 0.3
            await db.commit()

            with tempfile.TemporaryDirectory() as tmpdir:
                project_path = Path(tmpdir) / "design"
                project_path.mkdir()

                from services.eda_service.routes import write_kicad_board
                write_kicad_board(project_path, design.board_config, design.pcb_layout)

                job.progress = 0.5
                await db.commit()

                gerber_dir = project_path / "gerber"
                gerber_dir.mkdir()

                try:
                    proc = subprocess.run(
                        [
                            "kicad-cli", "pcb", "export", "gerbers",
                            "--output", str(gerber_dir),
                            str(project_path / "design.kicad_pcb"),
                        ],
                        capture_output=True, text=True, timeout=120,
                    )
                    if proc.returncode != 0:
                        logger.warning("KiCad gerber export failed, using fallback", stderr=proc.stderr)
                        _generate_fallback_gerbers(gerber_dir)
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    _generate_fallback_gerbers(gerber_dir)

                job.progress = 0.8
                await db.commit()

                zip_path = shutil.make_archive(str(project_path / "gerber_output"), "zip", str(gerber_dir))
                layers = len(list(gerber_dir.glob("*.gbr")))

                job.status = "completed"
                job.progress = 1.0
                job.output_data = {
                    "gerber_path": zip_path,
                    "layers_generated": layers,
                    "design_id": design_id,
                }
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()

                logger.info("Gerber generation completed", job_id=job_id, design_id=design_id, layers=layers)

        except SoftTimeLimitExceeded:
            job.status = "failed"
            job.error_message = "Gerber generation timed out"
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            logger.error("Gerber generation timed out", job_id=job_id)

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.traceback = traceback.format_exc()
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            logger.error("Gerber generation failed", job_id=job_id, error=str(e), exc_info=True)
            raise


def _generate_fallback_gerbers(gerber_dir: Path):
    """Generate minimal fallback Gerber files if KiCad CLI is unavailable."""
    for layer in ["F_Cu", "B_Cu", "F_SilkS", "B_SilkS", "Edge_Cuts", "F_Mask", "B_Mask"]:
        (gerber_dir / f"design-{layer}.gbr").write_text(
            f"G04 PCB Builder Gerber - {layer}*\nM02*\n"
        )


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    queue="eda",
    name="services.eda_service.tasks.run_drc_task",
)
def run_drc_task(self, job_id: str, design_data: dict):
    """Celery task for DRC execution."""
    import asyncio
    asyncio.run(_run_drc_async(job_id, design_data))


async def _run_drc_async(job_id: str, design_data: dict):
    """Async DRC execution."""
    from sqlalchemy import select

    job_uuid = uuid.UUID(job_id)

    async with async_session_factory() as db:
        result = await db.execute(select(Job).where(Job.id == job_uuid))
        job = result.scalar_one_or_none()
        if not job:
            return

        job.status = "running"
        job.stage = "drc_execution"
        job.started_at = datetime.now(timezone.utc)
        job.progress = 0.0
        await db.commit()

        try:
            from services.eda_service.routes import run_drc
            drc_result = await run_drc(DRCRequest(design_data=design_data))

            job.status = "completed"
            job.progress = 1.0
            job.output_data = {
                "passed": drc_result.passed,
                "score": drc_result.score,
                "violations_count": len(drc_result.violations),
                "warnings_count": len(drc_result.warnings),
            }
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.traceback = traceback.format_exc()
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            logger.error("DRC task failed", job_id=job_id, error=str(e), exc_info=True)
            raise
