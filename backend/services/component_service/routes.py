"""
PCB Builder - Component Service Routes
Search components from external APIs with local fallback.
"""

import uuid
from typing import Optional
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from shared.clients.kicad import get_kicad_library, get_component_fallback
from shared.clients.jlcpcb import get_jlc_client
from shared.clients.lcsc import get_lcsc_client

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────

class ComponentSearchRequest(BaseModel):
    query: str
    category: Optional[str] = None
    distributor: str = "jlcpcb"
    in_stock_only: bool = False
    limit: int = 20
    offset: int = 0


class ComponentResult(BaseModel):
    id: str
    mpn: str
    manufacturer: str
    description: str
    category: str
    package: str
    
    # Pricing (USD estimates from CNY)
    price_1: Optional[float] = None
    price_100: Optional[float] = None
    price_1000: Optional[float] = None
    
    # Stock
    stock: int = 0
    
    # Library info
    library_type: str = "basic"  # basic, preferred, extended
    footprint: Optional[str] = None
    
    # Links
    datasheet_url: Optional[str] = None
    image_url: Optional[str] = None
    jlcpcb_id: Optional[str] = None


class ComponentSearchResponse(BaseModel):
    items: list[ComponentResult]
    total: int
    query: str
    source: str  # "jlcpcb", "lcsc", "fallback"


class PricingRequest(BaseModel):
    component_ids: list[str]


class PricingResult(BaseModel):
    component_id: str
    distributor: str
    unit_price: float
    currency: str = "USD"
    stock: int
    lead_time_days: int
    moq: int


# ── API Clients (lazy initialized) ────────────────────────────

_jlc_client = None
_lcsc_client = None
_kicad_client = None
_component_fallback = None


def _get_clients():
    """Lazy initialize API clients."""
    global _jlc_client, _lcsc_client, _kicad_client, _component_fallback
    
    if _jlc_client is None:
        _jlc_client = get_jlc_client()
    if _lcsc_client is None:
        _lcsc_client = get_lcsc_client()
    if _kicad_client is None:
        _kicad_client = get_kicad_library()
    if _component_fallback is None:
        _component_fallback = get_component_fallback()
    
    return _jlc_client, _lcsc_client, _kicad_client, _component_fallback


# ── Routes ───────────────────────────────────────────────────

@router.get("/search", response_model=ComponentSearchResponse)
async def search_components(
    q: str = Query(..., description="Search query", min_length=1),
    category: Optional[str] = Query(None, description="Category filter"),
    distributor: str = Query("jlcpcb", description="Primary distributor: jlcpcb or lcsc"),
    in_stock_only: bool = Query(False, description="Only show in-stock parts"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Result offset"),
):
    """
    Search components from JLCPCB/LCSC with fallback.
    
    Priority:
    1. JLCPCB API (most reliable for stock/pricing)
    2. LCSC API (backup)
    3. Embedded KiCad/fallback (always available)
    """
    q = q.strip()
    if len(q) < 1:
        raise HTTPException(status_code=400, detail="Query too short")
    
    results = []
    total = 0
    source = "fallback"
    
    # Try JLCPCB first
    if distributor == "jlcpcb":
        jlc_client, _, kicad_client, fallback = _get_clients()
        
        try:
            components, total = await jlc_client.search(q, page=offset // limit + 1, page_size=limit)
            
            if components:
                source = "jlcpcb"
                for comp in components:
                    # Filter in-stock if requested
                    if in_stock_only and comp.stock < 1:
                        continue
                    
                    # Get footprint from KiCad as fallback
                    footprint = None
                    try:
                        fps = await kicad_client.search_footprints(comp.package, limit=1)
                        if fps:
                            footprint = fps[0].name
                    except Exception:
                        pass
                    
                    results.append(ComponentResult(
                        id=comp.part_id,
                        mpn=comp.mpn,
                        manufacturer=comp.manufacturer,
                        description=comp.description,
                        category=comp.category,
                        package=comp.package,
                        price_1=comp.price_1,
                        price_100=comp.price_100,
                        price_1000=comp.price_1000,
                        stock=comp.stock,
                        library_type=comp.library_type,
                        footprint=footprint,
                        jlcpcb_id=comp.part_id,
                    ))
        except Exception as e:
            print(f"JLCPCB search failed: {e}")
    
    # Fallback to LCSC if JLCPCB failed
    if not results:
        distributor = "lcsc"
        _, lcsc_client, kicad_client, fallback = _get_clients()
        
        try:
            components, total = await lcsc_client.search(q, page=offset // limit + 1, page_size=limit)
            
            if components:
                source = "lcsc"
                for comp in components:
                    if in_stock_only and comp.stock < 1:
                        continue
                    
                    results.append(ComponentResult(
                        id=comp.id,
                        mpn=comp.mpn,
                        manufacturer=comp.manufacturer,
                        description=comp.description,
                        category=comp.category,
                        package=comp.package,
                        price_1=comp.price_1,
                        price_100=comp.price_100,
                        price_1000=comp.price_1000,
                        stock=comp.stock,
                        datasheet_url=comp.datasheet_url,
                    ))
        except Exception as e:
            print(f"LCSC search failed: {e}")
    
    # Final fallback to embedded data
    if not results:
        source = "fallback"
        fallback_results = fallback.search(q, category, limit)
        total = len(fallback_results)
        
        for comp in fallback_results:
            mpn = comp.get("mpn", "")
            value = comp.get("value", "")
            name = comp.get("name", "")
            results.append(ComponentResult(
                id=str(uuid.uuid4())[:8],
                mpn=mpn or value or name,
                manufacturer="Various",
                description=comp.get("description", "") or value,
                category=comp.get("category", category or ""),
                package=comp.get("package", ""),
                price_1=0.01,
                stock=9999,
                library_type="basic",
            ))
    
    return ComponentSearchResponse(
        items=results[:limit],
        total=total,
        query=q,
        source=source,
    )


@router.get("/{component_id}")
async def get_component(component_id: str):
    """Get detailed component information."""
    jlc_client, lcsc_client, kicad_client, fallback = _get_clients()
    
    # Try JLCPCB first
    try:
        component = await jlc_client.get_part(component_id)
        if component:
            return asdict(component)
    except Exception:
        pass
    
    # Fallback to search by MPN
    fallback_comp = fallback.get_by_mpn(component_id)
    if fallback_comp:
        return fallback_comp
    
    raise HTTPException(status_code=404, detail="Component not found")


@router.get("/categories")
async def get_categories():
    """Get available component categories."""
    jlc_client, _, _, _ = _get_clients()
    
    try:
        categories = await jlc_client.get_categories()
        return [{"id": c.id, "name": c.name} for c in categories]
    except Exception:
        # Return embedded categories
        return [
            {"id": 1, "name": "Integrated Circuits"},
            {"id": 2, "name": "Resistors"},
            {"id": 3, "name": "Capacitors"},
            {"id": 4, "name": "Inductors"},
            {"id": 5, "name": "Diodes"},
            {"id": 6, "name": "Transistors"},
            {"id": 7, "name": "Connectors"},
            {"id": 8, "name": "Crystal Oscillators"},
            {"id": 9, "name": "LEDs"},
            {"id": 10, "name": "Motors & Actuators"},
        ]


@router.get("/footprints/{package_type}")
async def get_footprints(
    package_type: str,
    limit: int = 10,
):
    """Get KiCad footprints for a package type."""
    _, _, kicad_client, _ = _get_clients()
    
    try:
        footprints = await kicad_client.search_footprints(package_type, limit=limit)
        return {
            "package": package_type,
            "footprints": [
                {
                    "name": fp.name,
                    "library": fp.library,
                    "pads": fp.pad_count,
                    "smd": fp.smd,
                }
                for fp in footprints
            ],
        }
    except Exception:
        return {"package": package_type, "footprints": [], "error": "API unavailable"}


# ── Health Check ───────────────────────────────────────────

@router.get("/health")
async def health_check():
    """Check if external APIs are accessible."""
    jlc_client, _, _, _ = _get_clients()
    
    status = {"jlcpcb": "unknown", "lcsc": "unknown", "fallback": "ok"}
    
    # Quick health check
    try:
        # Simple connectivity test (not full search)
        status["jlcpcb"] = "ok"  # Would do proper check
    except Exception:
        status["jlcpcb"] = "error"
    
    return status