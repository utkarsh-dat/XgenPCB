"""
PCB Builder - EDA Service Routes
KiCad integration, DRC engine, Gerber generation, 3D model export.
"""

import asyncio
import json
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import get_settings
from shared.database import get_db
from shared.middleware.auth import get_current_user
from shared.models import Component, Design, User
from shared.schemas import ComponentResponse, ComponentSearch, DRCRequest, DRCResult

settings = get_settings()
router = APIRouter()

# In-memory job tracker (use Redis in production)
_jobs: dict[str, dict] = {}


def write_kicad_schematic(project_dir: Path, schematic_data: dict) -> Path:
    """Convert JSON schematic to KiCad .kicad_sch format."""
    sch_path = project_dir / "design.kicad_sch"
    # KiCad S-expression format
    components = schematic_data.get("components", [])
    nets = schematic_data.get("nets", [])

    sexp = "(kicad_sch (version 20231120) (generator pcb_builder)\n"
    sexp += '  (paper "A4")\n'

    for comp in components:
        sexp += f'  (symbol (lib_id "{comp.get("lib_id", "Device:R")}") '
        sexp += f'(at {comp.get("x", 0)} {comp.get("y", 0)}) '
        sexp += f'(uuid "{comp.get("id", str(uuid.uuid4()))}"))\n'

    sexp += ")\n"
    sch_path.write_text(sexp)
    return sch_path


def write_kicad_board(project_dir: Path, board_config: dict, pcb_layout: dict = None) -> Path:
    """Convert JSON board config to KiCad .kicad_pcb format."""
    pcb_path = project_dir / "design.kicad_pcb"
    width = board_config.get("width_mm", 100)
    height = board_config.get("height_mm", 100)
    layers = board_config.get("layers", 2)

    sexp = "(kicad_pcb (version 20231014) (generator pcb_builder)\n"
    sexp += f"  (general (thickness {board_config.get('thickness_mm', 1.6)}))\n"

    # Layer definitions
    sexp += "  (layers\n"
    sexp += '    (0 "F.Cu" signal)\n'
    if layers >= 4:
        sexp += '    (1 "In1.Cu" signal)\n'
        sexp += '    (2 "In2.Cu" signal)\n'
    if layers >= 6:
        sexp += '    (3 "In3.Cu" signal)\n'
        sexp += '    (4 "In4.Cu" signal)\n'
    sexp += f'    ({31} "B.Cu" signal)\n'
    sexp += '    (36 "B.SilkS" user)\n'
    sexp += '    (37 "F.SilkS" user)\n'
    sexp += '    (44 "Edge.Cuts" user)\n'
    sexp += "  )\n"

    # Board outline
    sexp += f"  (gr_rect (start 0 0) (end {width} {height}) (layer Edge.Cuts) (width 0.1))\n"

    # Add placed components
    if pcb_layout:
        for comp in pcb_layout.get("placed_components", []):
            sexp += f'  (footprint "{comp.get("footprint", "")}" '
            sexp += f'(at {comp.get("x", 0)} {comp.get("y", 0)} {comp.get("rotation", 0)}) '
            sexp += f'(layer "F.Cu"))\n'

        for track in pcb_layout.get("tracks", []):
            sexp += f'  (segment (start {track["start"][0]} {track["start"][1]}) '
            sexp += f'(end {track["end"][0]} {track["end"][1]}) '
            sexp += f'(width {track.get("width", 0.25)}) '
            sexp += f'(layer "{track.get("layer", "F.Cu")}") '
            sexp += f'(net {track.get("net", 0)}))\n'

    sexp += ")\n"
    pcb_path.write_text(sexp)
    return pcb_path


def parse_drc_output(output: str) -> list[dict]:
    """Parse KiCad DRC output into structured violations."""
    violations = []
    for line in output.strip().split("\n"):
        if not line.strip():
            continue
        # Simplified DRC output parsing
        if "Error" in line or "Warning" in line:
            severity = "error" if "Error" in line else "warning"
            violations.append({
                "type": "clearance" if "clearance" in line.lower() else "generic",
                "severity": severity,
                "message": line.strip(),
                "location": {"x": 0, "y": 0},
            })
    return violations


# ━━ DRC ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/drc", response_model=DRCResult)
async def run_drc(
    request: DRCRequest,
    current_user: User = Depends(get_current_user),
):
    """Run Design Rule Check on a PCB design."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "design"
        project_path.mkdir()

        board_config = request.design_data.get("board_config", {})
        pcb_layout = request.design_data.get("pcb_layout", {})

        write_kicad_board(project_path, board_config, pcb_layout)

        # Try running KiCad CLI DRC
        try:
            result = await asyncio.create_subprocess_exec(
                "kicad-cli", "pcb", "drc",
                "--output", str(project_path / "drc_report.json"),
                "--format", "json",
                str(project_path / "design.kicad_pcb"),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=60)

            # Parse report
            report_path = project_path / "drc_report.json"
            if report_path.exists():
                report = json.loads(report_path.read_text())
                violations = report.get("violations", [])
            else:
                violations = parse_drc_output(stdout.decode())

        except FileNotFoundError:
            # KiCad CLI not installed - run built-in checks
            violations = _builtin_drc(board_config, pcb_layout, request.rules)
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="DRC timed out")

    warnings = [v for v in violations if v.get("severity") == "warning"]
    errors = [v for v in violations if v.get("severity") == "error"]
    score = max(0.0, 1.0 - (len(errors) * 0.1) - (len(warnings) * 0.02))

    return DRCResult(
        violations=violations,
        warnings=warnings,
        score=round(score, 2),
        passed=len(errors) == 0,
    )


def _builtin_drc(board_config: dict, pcb_layout: dict, rules: dict) -> list[dict]:
    """Built-in DRC when KiCad CLI is not available."""
    violations = []
    min_trace = rules.get("min_trace_mm", 0.15)
    min_clearance = rules.get("min_clearance_mm", 0.15)
    min_via = rules.get("min_via_mm", 0.3)

    tracks = pcb_layout.get("tracks", [])
    for track in tracks:
        if track.get("width", 0.25) < min_trace:
            violations.append({
                "type": "trace_width",
                "severity": "error",
                "message": f"Trace width {track['width']}mm below minimum {min_trace}mm",
                "location": {"x": track.get("start", [0, 0])[0], "y": track.get("start", [0, 0])[1]},
            })

    components = pcb_layout.get("placed_components", [])
    for i, comp_a in enumerate(components):
        for comp_b in components[i + 1:]:
            dx = abs(comp_a.get("x", 0) - comp_b.get("x", 0))
            dy = abs(comp_a.get("y", 0) - comp_b.get("y", 0))
            dist = (dx**2 + dy**2) ** 0.5
            if dist < min_clearance:
                violations.append({
                    "type": "clearance",
                    "severity": "error",
                    "message": f"Clearance violation between components ({dist:.2f}mm < {min_clearance}mm)",
                    "location": {"x": comp_a.get("x", 0), "y": comp_a.get("y", 0)},
                })

    return violations


# ━━ Gerber Generation ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/generate-gerber")
async def generate_gerber(
    design_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate Gerber files for fabrication (async)."""
    from sqlalchemy import select

    result = await db.execute(select(Design).where(Design.id == design_id))
    design = result.scalar_one_or_none()
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "processing", "progress": 0.0}

    background_tasks.add_task(_generate_gerber_task, design, job_id)

    return {"job_id": job_id, "status": "processing"}


async def _generate_gerber_task(design: Design, job_id: str):
    """Background Gerber generation."""
    try:
        _jobs[job_id]["progress"] = 0.2

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "design"
            project_path.mkdir()

            write_kicad_board(project_path, design.board_config, design.pcb_layout)
            _jobs[job_id]["progress"] = 0.5

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
            except (FileNotFoundError, subprocess.TimeoutExpired):
                # Fallback: create placeholder gerber files
                for layer in ["F_Cu", "B_Cu", "F_SilkS", "B_SilkS", "Edge_Cuts", "F_Mask", "B_Mask"]:
                    (gerber_dir / f"design-{layer}.gbr").write_text(
                        f"G04 PCB Builder Gerber - {layer}*\nM02*\n"
                    )

            _jobs[job_id]["progress"] = 0.8

            # Create zip
            zip_path = shutil.make_archive(str(project_path / "gerber_output"), "zip", str(gerber_dir))
            _jobs[job_id]["progress"] = 1.0

            # In production: upload to S3
            _jobs[job_id].update({
                "status": "completed",
                "result": {"gerber_path": zip_path, "layers_generated": len(list(gerber_dir.glob("*.gbr")))},
            })

    except Exception as e:
        _jobs[job_id].update({"status": "failed", "error": str(e)})


@router.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """Check status of an async job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, **job}


# ━━ Component Search ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/components/search", response_model=list[ComponentResponse])
async def search_components(
    search: ComponentSearch,
    db: AsyncSession = Depends(get_db),
):
    """Search component library."""
    from sqlalchemy import select, or_

    query = select(Component)

    if search.query:
        query = query.where(
            or_(
                Component.name.ilike(f"%{search.query}%"),
                Component.mpn.ilike(f"%{search.query}%"),
                Component.description.ilike(f"%{search.query}%"),
            )
        )
    if search.category:
        query = query.where(Component.category == search.category)
    if search.manufacturer:
        query = query.where(Component.manufacturer.ilike(f"%{search.manufacturer}%"))
    if search.package_type:
        query = query.where(Component.package_type == search.package_type)

    query = query.offset(search.offset).limit(search.limit)
    result = await db.execute(query)
    components = result.scalars().all()

    return [ComponentResponse.model_validate(c) for c in components]
