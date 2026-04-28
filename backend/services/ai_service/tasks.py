"""
PCB Builder - AI Service Celery Tasks (Refactored with Agent Pipeline)
Long-running AI jobs for PCB generation using the multi-agent pipeline.
"""

import json
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded

from shared.agents import AgentOrchestrator
from shared.celery_app import celery_app
from shared.config import get_settings
from shared.database import async_session_factory
from shared.logging_config import logger
from shared.models import Design, Job, Project
from shared.schemas import DRCRequest
from shared.validation import (
    generate_candidates,
    generate_explanation,
    run_dfm_analysis,
    run_physics_drc,
    run_si_analysis,
)

settings = get_settings()


async def _update_job_in_db(job_id: str, update: dict):
    """Update job status in database."""
    from sqlalchemy import select
    async with async_session_factory() as db:
        result = await db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
        job = result.scalar_one_or_none()
        if job:
            for key, value in update.items():
                if value is not None:
                    setattr(job, key, value)
            job.updated_at = datetime.now(timezone.utc)
            await db.commit()


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="ai",
    name="services.ai_service.tasks.generate_pcb_pipeline_task",
)
def generate_pcb_pipeline_task(self, job_id: str, request_data: dict, user_id: str, api_key: str | None = None):
    """Celery task for PCB generation using the full agent pipeline."""
    import asyncio
    asyncio.run(_generate_pcb_pipeline_async(self, job_id, request_data, user_id, api_key))


async def _generate_pcb_pipeline_async(task, job_id: str, request_data: dict, user_id: str, api_key: str | None):
    """Async implementation of the full agent pipeline."""
    job_uuid = uuid.UUID(job_id)
    user_uuid = uuid.UUID(user_id)

    # Set API key for this task
    if api_key:
        settings.nvidia_api_key = api_key

    async with async_session_factory() as db:
        from sqlalchemy import select

        result = await db.execute(select(Job).where(Job.id == job_uuid))
        job = result.scalar_one_or_none()
        if not job:
            logger.error("Job not found", job_id=job_id)
            return

        job.status = "running"
        job.stage = "pipeline_start"
        job.started_at = datetime.now(timezone.utc)
        job.progress = 0.0
        await db.commit()

    try:
        # Build user input
        input_type = request_data["input_type"]
        if input_type == "text":
            user_input = request_data.get("description", "")
        elif input_type == "bom_netlist":
            user_input = f"Design PCB from BOM: {json.dumps(request_data.get('components', []))} with nets: {json.dumps(request_data.get('nets', []))}"
        else:
            user_input = f"Convert existing design: {request_data.get('file_type', '')}"

        board_config = request_data.get("board_config", {})

        # Create orchestrator with DB update callback
        orchestrator = AgentOrchestrator(
            job_id=job_id,
            user_id=user_id,
            update_callback=_update_job_in_db,
        )

        # Run the full pipeline
        pipeline_result = await orchestrator.run_pipeline(
            user_input=user_input,
            board_config=board_config,
        )

        if pipeline_result["status"] == "completed":
            design_data = pipeline_result["design"]

            # Run physics-aware validation
            await _update_job_in_db(job_id, {"stage": "physics_validation", "message": "Running physics-aware DRC/DFM/SI..."})
            drc_result = run_physics_drc(design_data)
            dfm_result = run_dfm_analysis(design_data)
            si_result = run_si_analysis(design_data)

            # Generate explainability report
            await _update_job_in_db(job_id, {"stage": "explainability", "message": "Generating design explanations..."})
            explanation = generate_explanation(design_data, pipeline_result.get("pipeline_results", []))

            # Multi-candidate generation (if enabled)
            candidates = None
            enable_multi = request_data.get("options", {}).get("multi_candidate", False)
            if enable_multi:
                await _update_job_in_db(job_id, {"stage": "multi_candidate", "message": "Generating alternative layouts..."})
                try:
                    from shared.validation.multi_candidate import MultiCandidateGenerator
                    gen = MultiCandidateGenerator(num=3)
                    candidates = await gen.generate_candidates(
                        requirements=design_data.get("requirements", {}),
                        schematic=design_data.get("schematic", {}),
                        board_config=design_data.get("board_config", {}),
                    )
                except Exception as e:
                    logger.warning("Multi-candidate generation failed", error=str(e))

            # Save design to database
            async with async_session_factory() as db:
                from sqlalchemy import select

                result_proj = await db.execute(
                    select(Project).where(Project.created_by == user_uuid).order_by(Project.created_at.desc())
                )
                project = result_proj.scalar_one_or_none()
                if not project:
                    project = Project(name="AI Generated", created_by=user_uuid)
                    db.add(project)
                    await db.flush()

                design = Design(
                    name=f"PCB {int(time.time())}",
                    project_id=project.id,
                    board_config=design_data.get("board_config", {}),
                    schematic_data=design_data.get("schematic", {}),
                    design_reasoning=design_data.get("design_reasoning", ""),
                    pcb_layout={
                        "placed_components": design_data.get("placed_components", []),
                        "tracks": design_data.get("tracks", []),
                        "vias": design_data.get("vias", []),
                    },
                    constraints=design_data.get("drc_rules", {}),
                    created_by=user_uuid,
                    status="generated",
                )
                db.add(design)
                await db.commit()
                await db.refresh(design)

                # Generate KiCad file
                import tempfile
                from services.eda_service.routes import write_kicad_board
                from services.storage_service import storage_service

                with tempfile.TemporaryDirectory() as tmpdir:
                    project_path = Path(tmpdir) / "design"
                    project_path.mkdir()
                    kicad_path = write_kicad_board(
                        project_path,
                        design_data.get("board_config", {}),
                        design.pcb_layout,
                    )
                    content = kicad_path.read_text()
                    filename = f"{design.name}.kicad_pcb"
                    storage_result = await storage_service.upload_dual(
                        design.id, filename, content.encode("utf-8"), "application/octet-stream"
                    )
                    design.local_path = storage_result["local_path"]
                    design.minio_key = storage_result.get("minio_key")
                    await db.commit()

                # Build output data
                output_data = {
                    "design_id": str(design.id),
                    "board_config": design_data.get("board_config", {}),
                    "pipeline_results": pipeline_result.get("pipeline_results", []),
                    "validation": {
                        "drc": {
                            "passed": drc_result.passed,
                            "score": drc_result.score,
                            "violations": len(drc_result.violations),
                            "critical": len(drc_result.by_severity.get("critical", [])),
                            "rule_set": drc_result.summary.get("rule_set", ""),
                        },
                        "dfm": {
                            "passed": dfm_result.passed,
                            "score": dfm_result.score,
                            "test_point_coverage": dfm_result.test_point_coverage,
                        },
                        "si": {
                            "passed": si_result.passed,
                            "score": si_result.score,
                            "high_speed_nets": len(si_result.high_speed_nets),
                        },
                    },
                    "explanation": {
                        "design_philosophy": explanation.design_philosophy,
                        "risk_assessment": explanation.risk_assessment,
                        "optimization_notes": explanation.optimization_notes,
                        "critical_choices_count": len(explanation.critical_choices),
                    },
                    "candidates": [
                        {
                            "candidate_id": c.candidate_id,
                            "rank": c.rank,
                            "selected": c.selected,
                            "metrics": {
                                "overall_score": c.metrics.overall_score,
                                "drc_score": c.metrics.drc_score,
                                "dfm_score": c.metrics.dfm_score,
                                "si_score": c.metrics.si_score,
                                "via_count": c.metrics.via_count,
                                "cost_estimate": c.metrics.manufacturing_cost_estimate_usd,
                            },
                            "reasoning": c.reasoning,
                        }
                        for c in (candidates or [])
                    ] if candidates else None,
                }

                # Update job as completed
                await _update_job_in_db(job_id, {
                    "status": "completed",
                    "progress": 1.0,
                    "output_data": output_data,
                    "completed_at": datetime.now(timezone.utc),
                })

                logger.info(
                    "PCB pipeline completed successfully",
                    job_id=job_id,
                    design_id=str(design.id),
                    stages=len(pipeline_result.get("pipeline_results", [])),
                    drc_score=drc_result.score,
                    dfm_score=dfm_result.score,
                    si_score=si_result.score,
                )

        else:
            # Pipeline failed
            failed_stage = pipeline_result.get("failed_stage", "unknown")
            error = pipeline_result.get("error", "Unknown error")

            await _update_job_in_db(job_id, {
                "status": "failed",
                "error_message": f"Pipeline failed at {failed_stage}: {error}",
                "output_data": {
                    "failed_stage": failed_stage,
                    "error": error,
                    "pipeline_results": pipeline_result.get("pipeline_results", []),
                },
                "completed_at": datetime.now(timezone.utc),
            })

            logger.error(
                "PCB pipeline failed",
                job_id=job_id,
                failed_stage=failed_stage,
                error=error,
            )

    except SoftTimeLimitExceeded:
        await _update_job_in_db(job_id, {
            "status": "failed",
            "error_message": "Pipeline timed out after 55 minutes",
            "completed_at": datetime.now(timezone.utc),
        })
        logger.error("PCB pipeline timed out", job_id=job_id)

    except Exception as e:
        error_msg = str(e)
        tb = traceback.format_exc()
        await _update_job_in_db(job_id, {
            "status": "failed",
            "error_message": error_msg,
            "traceback": tb,
            "completed_at": datetime.now(timezone.utc),
        })
        logger.error("PCB pipeline error", job_id=job_id, error=error_msg, exc_info=True)
        raise


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="ai",
    name="services.ai_service.tasks.generate_pcb_task",
)
def generate_pcb_task(self, job_id: str, request_data: dict, user_id: str, api_key: str | None = None):
    """Legacy task - now delegates to the pipeline task."""
    return generate_pcb_pipeline_task(self, job_id, request_data, user_id, api_key)
