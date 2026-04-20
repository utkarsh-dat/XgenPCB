"""
PCB Builder - LCSC API Client
LCSC (EasyEDA) component API - best for pricing.
https://lcsc.com
"""

import httpx
from typing import Optional
from dataclasses import dataclass


@dataclass
class LCSCComponent:
    id: str
    mpn: str
    manufacturer: str
    category: str
    description: str
    package: str
    
    # Pricing
    price_1: float
    price_10: float
    price_100: float
    price_1000: float
    price_5000: float
    
    # Stock
    stock: int
    
    # Additional
    type: str
    certified: bool
    
    # Links
    image_url: str
    datasheet_url: Optional[str]


@dataclass
class LCSCCategory:
    id: int
    name: str
    parent_id: Optional[int]


class LCSCClient:
    """Client for LCSC/easyeda parts API."""
    
    BASE_URL = "https://easyeda.com/api"
    SEARCH_URL = f"{BASE_URL}/parts/search"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or ""
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
    
    async def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = 50,
        category_id: Optional[int] = None,
    ) -> tuple[list[LCSCComponent], int]:
        """
        Search components.
        
        Returns:
            (components, total_count)
        """
        search_params = {
            "search_term": query,
            "page": page - 1,
            "page_size": page_size,
            "ext_params": {},
        }
        
        if self.api_key:
            search_params["ext_params"]["api_key"] = self.api_key
        
        if category_id:
            search_params["ext_params"]["category_id"] = category_id
        
        try:
            response = await self.client.post(
                self.SEARCH_URL,
                json=search_params,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError:
            return [], 0
        
        components = []
        total = len(data.get("results", []))
        
        for item in data.get("results", []):
            try:
                comp = self._parse_component(item)
                components.append(comp)
            except (KeyError, ValueError):
                continue
        
        return components, total
    
    def _parse_component(self, item: dict) -> LCSCComponent:
        """Parse API response."""
        # Price tiers
        price_tiers = item.get("price", [])
        
        return LCSCComponent(
            id=str(item.get("id", "")),
            mpn=item.get("mpn", ""),
            manufacturer=item.get("brand_name", "Unknown"),
            category=item.get("category", ""),
            description=item.get("description", ""),
            package=item.get("package", ""),
            
            price_1=self._get_price(price_tiers, 1),
            price_10=self._get_price(price_tiers, 10),
            price_100=self._get_price(price_tiers, 100),
            price_1000=self._get_price(price_tiers, 1000),
            price_5000=self._get_price(price_tiers, 5000),
            
            stock=item.get("stock", 0),
            
            type=item.get("type", ""),
            certified=item.get("is_pl", False),
            
            image_url=item.get("image", ""),
            datasheet_url=item.get("datasheet", ""),
        )
    
    def _get_price(self, tiers: list, qty: int) -> float:
        """Extract price for quantity."""
        for tier in tiers:
            if tier.get("num", 0) <= qty:
                return float(tier.get("price", 0))
        return 0.0
    
    async def get_categories(self) -> list[LCSCCategory]:
        """Get all categories."""
        # LCSC categories are available via separate endpoint
        return []
    
    async def get_part(self, part_id: str) -> Optional[LCSCComponent]:
        """Get single component by ID."""
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/parts/{part_id}",
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
def get_lcsc_client(api_key: str = "") -> LCSCClient:
    """Create LCSC client."""
    return LCSCClient(api_key)


# Fallback search using web scraping (last resort)
async def search_lcsc_web(query: str) -> list[dict]:
    """
    Web scraper fallback - uses LCSC search page.
    Rate limited, not for production use.
    """
    from bs4 import BeautifulSoup
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://lcsc.com/search?keywords={query}",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=30.0,
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Simplified parsing - actual implementation
            # would need proper CSS selector discovery
            for product in soup.select('.product-item')[:20]:
                results.append({
                    "id": product.get("data-id", ""),
                    "name": product.select_one('.name').text if product.select_one('.name') else "",
                    "price": product.select_one('.price').text if product.select_one('.price') else "",
                })
            
            return results
        
        except Exception:
            return []