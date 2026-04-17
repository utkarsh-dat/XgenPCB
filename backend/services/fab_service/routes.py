"""
PCB Builder - Fabrication Service Routes
Fabricator connectors, quote aggregation, and order management.
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from shared.config import get_settings
from shared.database import get_db
from shared.middleware.auth import get_current_user
from shared.models import Design, FabQuote, Fabricator, User
from shared.schemas import FabQuoteRequest, FabQuoteResponse

settings = get_settings()
router = APIRouter()


# ━━ Fabricator Connectors ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class FabCapability(BaseModel):
    min_layers: int = 1
    max_layers: int = 2
    min_trace_mm: float = 0.15
    min_space_mm: float = 0.15
    min_via_mm: float = 0.3
    materials: list[str] = ["FR4"]
    surface_finish: list[str] = ["HASL", "ENIG"]
    copper_weight: list[str] = ["1oz", "2oz"]


class BaseFabConnector(ABC):
    name: str = "Unknown"

    @abstractmethod
    async def get_quote(self, board_config: dict, options: dict) -> FabQuoteResponse:
        pass

    @abstractmethod
    def get_capabilities(self) -> FabCapability:
        pass


class PCBPowerConnector(BaseFabConnector):
    """PCB Power India connector."""
    name = "PCB Power"

    async def get_quote(self, board_config: dict, options: dict) -> FabQuoteResponse:
        # Simplified pricing model (real integration would call their API)
        layers = board_config.get("layers", 2)
        area_cm2 = (board_config.get("width_mm", 100) * board_config.get("height_mm", 100)) / 100
        qty = options.get("quantity", 5)

        base_price = 200  # INR
        layer_mult = {1: 1.0, 2: 1.0, 4: 2.5, 6: 4.0, 8: 6.0}.get(layers, layers * 1.2)
        area_price = area_cm2 * 3.5 * layer_mult
        qty_discount = min(0.5, qty * 0.01)

        total = max(base_price, (base_price + area_price) * (1 - qty_discount) * qty)
        lead_time = 7 if layers <= 2 else 12

        return FabQuoteResponse(
            fabricator_name=self.name,
            price=round(total, 2),
            currency="INR",
            lead_time_days=lead_time,
            options={
                "layers": layers,
                "quantity": qty,
                "surface_finish": options.get("surface_finish", "HASL"),
                "thickness_mm": board_config.get("thickness_mm", 1.6),
            },
            url="https://pcbpower.in/quote",
        )

    def get_capabilities(self) -> FabCapability:
        return FabCapability(
            min_layers=1, max_layers=8,
            min_trace_mm=0.1, min_space_mm=0.1, min_via_mm=0.2,
            materials=["FR4", "Rogers", "Aluminum"],
            surface_finish=["HASL", "ENIG", "OSP", "Hard Gold"],
            copper_weight=["0.5oz", "1oz", "2oz", "3oz"],
        )


class JLCPCBConnector(BaseFabConnector):
    """JLCPCB connector."""
    name = "JLCPCB"

    async def get_quote(self, board_config: dict, options: dict) -> FabQuoteResponse:
        layers = board_config.get("layers", 2)
        area_cm2 = (board_config.get("width_mm", 100) * board_config.get("height_mm", 100)) / 100
        qty = options.get("quantity", 5)

        # JLCPCB is known for very competitive 2-layer pricing
        if layers <= 2:
            base_price = 2.0  # USD
        else:
            base_price = 10.0 * (layers / 2)

        area_price = area_cm2 * 0.04 if layers <= 2 else area_cm2 * 0.12
        total = max(base_price, (base_price + area_price) * qty)
        # Convert to INR
        total_inr = total * 83.5

        return FabQuoteResponse(
            fabricator_name=self.name,
            price=round(total_inr, 2),
            currency="INR",
            lead_time_days=8 + 5,  # +5 for India shipping
            options={
                "layers": layers,
                "quantity": qty,
                "surface_finish": options.get("surface_finish", "HASL"),
            },
            url="https://jlcpcb.com/order",
        )

    def get_capabilities(self) -> FabCapability:
        return FabCapability(
            min_layers=1, max_layers=14,
            min_trace_mm=0.09, min_space_mm=0.09, min_via_mm=0.15,
            materials=["FR4", "Aluminum", "Rogers"],
            surface_finish=["HASL", "HASL Lead-Free", "ENIG"],
            copper_weight=["1oz", "2oz"],
        )


class RushPCBConnector(BaseFabConnector):
    """Rush PCB India connector."""
    name = "Rush PCB"

    async def get_quote(self, board_config: dict, options: dict) -> FabQuoteResponse:
        layers = board_config.get("layers", 2)
        area_cm2 = (board_config.get("width_mm", 100) * board_config.get("height_mm", 100)) / 100
        qty = options.get("quantity", 5)

        base_price = 350
        layer_mult = {1: 0.8, 2: 1.0, 4: 2.8, 6: 4.5, 8: 6.5, 16: 15.0}.get(layers, layers * 1.5)
        total = max(base_price, (base_price + area_cm2 * 4.0 * layer_mult) * qty * 0.95)

        return FabQuoteResponse(
            fabricator_name=self.name,
            price=round(total, 2),
            currency="INR",
            lead_time_days=5 if layers <= 2 else 10,
            options={
                "layers": layers,
                "quantity": qty,
                "surface_finish": options.get("surface_finish", "HASL"),
            },
            url="https://rushpcb.com/quote",
        )

    def get_capabilities(self) -> FabCapability:
        return FabCapability(
            min_layers=1, max_layers=16,
            min_trace_mm=0.075, min_space_mm=0.075, min_via_mm=0.15,
            materials=["FR4", "Rogers", "Polyimide", "Aluminum"],
            surface_finish=["HASL", "ENIG", "OSP", "Immersion Silver"],
            copper_weight=["0.5oz", "1oz", "2oz", "3oz", "4oz"],
        )


# ━━ Fab Aggregator ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONNECTORS: dict[str, BaseFabConnector] = {
    "pcbpower": PCBPowerConnector(),
    "jlcpcb": JLCPCBConnector(),
    "rushpcb": RushPCBConnector(),
}


async def _safe_quote(connector: BaseFabConnector, board_config: dict, options: dict) -> Optional[FabQuoteResponse]:
    try:
        return await connector.get_quote(board_config, options)
    except Exception:
        return None


# ━━ Routes ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/quotes", response_model=list[FabQuoteResponse])
async def get_quotes(
    request: FabQuoteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get fabrication quotes from multiple manufacturers."""
    # Get design
    result = await db.execute(select(Design).where(Design.id == request.design_id))
    design = result.scalar_one_or_none()
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")

    board_config = design.board_config
    options = request.options

    # Filter connectors
    active_connectors = CONNECTORS
    if request.prefer_indian:
        active_connectors = {k: v for k, v in CONNECTORS.items() if k != "jlcpcb"}

    # Get quotes in parallel
    tasks = [_safe_quote(conn, board_config, options) for conn in active_connectors.values()]
    results = await asyncio.gather(*tasks)

    quotes = [r for r in results if r is not None]
    quotes.sort(key=lambda q: q.price)

    # Save quotes to DB
    for quote in quotes:
        fab_result = await db.execute(
            select(Fabricator).where(Fabricator.name == quote.fabricator_name)
        )
        fabricator = fab_result.scalar_one_or_none()
        if fabricator:
            db_quote = FabQuote(
                design_id=design.id,
                fabricator_id=fabricator.id,
                user_id=current_user.id,
                quote_data=quote.model_dump(),
                status="quoted",
            )
            db.add(db_quote)

    return quotes


@router.get("/fabricators")
async def list_fabricators(db: AsyncSession = Depends(get_db)):
    """List all available fabricators with capabilities."""
    result = await db.execute(select(Fabricator).where(Fabricator.is_active.is_(True)))
    fabs = result.scalars().all()

    return [
        {
            "id": str(f.id),
            "name": f.name,
            "country": f.country,
            "capabilities": f.capabilities,
            "supported_types": f.supported_types,
            "rating": float(f.rating) if f.rating else 0.0,
        }
        for f in fabs
    ]


@router.get("/capabilities/{fabricator_name}")
async def get_fab_capabilities(fabricator_name: str):
    """Get capabilities for a specific fabricator."""
    connector = CONNECTORS.get(fabricator_name.lower())
    if not connector:
        raise HTTPException(status_code=404, detail="Fabricator not found")
    return connector.get_capabilities().model_dump()
