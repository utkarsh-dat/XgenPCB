"""
PCB Builder - JLCPCB API Client
Fetches components, pricing, and stock from JLCPCB.
https://jlcpcb.com
"""

import httpx
from typing import Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class JLCCategory:
    id: int
    name: str
    parent_id: Optional[int]


@dataclass
class JLCComponent:
    part_id: str  # JLCPCB internal ID
    mpn: str  # Manufacturer part number
    manufacturer: str
    category: str
    description: str
    package: str  # Footprint type
    
    # Pricing (CNY)
    price_1: float
    price_10: float
    price_100: float
    price_1000: float
    
    # Stock
    stock: int
    warehouse: str
    
    # Additional
    brand: str
    priority: int
    assemble: bool
    library_type: str  # Basic, Preferred, Extended
    
    # Timestamps
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


@dataclass
class JLCDatasheet:
    name: str
    url: str


class JLCPCBClient:
    """Client for JLCPCB parts API."""
    
    BASE_URL = "https://cart.jlcpcb.com"
    SEARCH_URL = f"{BASE_URL}/service/v1/parts/advanced-search"
    DETAIL_URL = f"{BASE_URL}/service/v1/parts"
    
    def __init__(self, session_cookie: Optional[str] = None, csrf_token: Optional[str] = None):
        self.session_cookie = session_cookie or ""
        self.csrf_token = csrf_token or ""
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
    
    def _get_headers(self) -> dict:
        """Build request headers."""
        headers = {}
        if self.session_cookie:
            headers["Cookie"] = self.session_cookie
        if self.csrf_token:
            headers["x-csrf-token"] = self.csrf_token
        return headers
    
    async def search(
        self,
        query: str,
        category_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[JLCComponent], int]:
        """
        Search components by query.
        
        Returns:
            (components, total_count)
        """
        search_params = {
            "keyword": query,
            "page": {
                "pageNumber": page - 1,  # JLC uses 0-indexed
                "pageSize": page_size,
            },
            "sorts": [
                {"field": "stock", "direction": "desc"},
            ],
        }
        
        if category_id:
            search_params["categoryIds"] = [category_id]
        
        try:
            response = await self.client.post(
                self.SEARCH_URL,
                json=search_params,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError:
            # Return empty on error - fallback will handle
            return [], 0
        
        components = []
        total = data.get("totalCount", 0)
        
        for item in data.get("list", []):
            try:
                comp = self._parse_component(item)
                components.append(comp)
            except (KeyError, ValueError):
                continue
        
        return components, total
    
    def _parse_component(self, item: dict) -> JLCComponent:
        """Parse API response into component object."""
        # Price tiers
        price_info = item.get("priceInfo", {})
        
        return JLCComponent(
            part_id=str(item.get("partId", "")),
            mpn=item.get("MPN", ""),
            manufacturer=item.get("brand", {}).get("name", "Unknown"),
            category=item.get("categoryName", ""),
            description=item.get("description", ""),
            package=item.get("package", ""),
            
            price_1=price_info.get("1", 0) / 1000,  # Convert to CNY from 10x
            price_10=price_info.get("10", 0) / 1000,
            price_100=price_info.get("100", 0) / 1000,
            price_1000=price_info.get("1000", 0) / 1000,
            
            stock=item.get("stock", {}).get("quantity", 0),
            warehouse=item.get("stock", {}).get("warehouse", ""),
            
            brand=item.get("brand", {}).get("name", ""),
            priority=item.get("priority", 0),
            assemble=item.get("assemble", True),
            library_type=item.get("libraryType", "basic"),
            
            created_at=None,
            updated_at=None,
        )
    
    async def get_categories(self) -> list[JLCCategory]:
        """Get all component categories."""
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/service/v2/category",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError:
            return []
        
        categories = []
        for item in data:
            try:
                categories.append(JLCCategory(
                    id=item.get("categoryId", 0),
                    name=item.get("categoryName", ""),
                    parent_id=item.get("parentId"),
                ))
            except (KeyError, ValueError):
                continue
        
        return categories
    
    async def get_part(self, part_id: str) -> Optional[JLCComponent]:
        """Get single component by ID."""
        try:
            response = await self.client.get(
                f"{self.DETAIL_URL}/{part_id}",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()
            return self._parse_component(data)
        except httpx.HTTPError:
            return None
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Default client factory
def get_jlc_client() -> JLCPCBClient:
    """Create JLCPCB client. Configure with session for authenticated requests."""
    return JLCPCBClient()


# Fallback search when API unavailable
async def search_jlc_fallback(query: str, page: int = 1, page_size: int = 50) -> list[dict]:
    """
    Fallback search using JLCPCB's public search API.
    Less reliable but doesn't require auth.
    """
    # This is a simplified fallback - real implementation would need
    # proper session handling
    return []