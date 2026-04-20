"""
PCB Builder - Footprint/Component Library Fallback
Uses KiCad GitHub libraries when external APIs unavailable.
"""

import httpx
import json
from typing import Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class KiCadFootprint:
    name: str
    library: str
    path: str
    description: str
    pad_count: int
    smd: bool


@dataclass
class KiCadSymbol:
    name: str
    library: str
    unit_count: int
    description: str
    pins: int


class KiCadLibraryClient:
    """
    KiCad official library fallback.
    https://github.com/KiCad/kicad-packages6
    """
    
    FOOTPRINT_REPOS = [
        "https://api.github.com/repos/KiCad/kicad-packages6/contents",
    ]
    
    SYMBOL_REPOS = [
        "https://api.github.com/repos/KiCad/kicad-symbols/contents",
    ]
    
    # Local cache directory
    CACHE_DIR = Path("data/kicad_cache")
    
    def __init__(self, use_cache: bool = True):
        self.use_cache = use_cache
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "XgenPCB/1.0",
            }
        )
        if use_cache:
            self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    async def search_footprints(
        self,
        query: str,
        package_type: Optional[str] = None,
        limit: int = 20,
    ) -> list[KiCadFootprint]:
        """
        Search KiCad footprints by name/package.
        
        Falls back to local cache or embedded list.
        """
        # First try GitHub API (may be rate limited)
        footprints = await self._search_github(query, limit)
        
        # Fallback to embedded common footprints
        if not footprints:
            footprints = self._get_embedded_footprints(query, limit)
        
        # Filter by package type if specified
        if package_type and footprints:
            footprints = [
                f for f in footprints 
                if package_type.lower() in f.name.lower()
            ][:limit]
        
        return footprints[:limit]
    
    async def _search_github(self, query: str, limit: int) -> list[KiCadFootprint]:
        """Search via GitHub API."""
        footprints = []
        
        try:
            response = await self.client.get(
                "https://api.github.com/search/code",
                params={
                    "q": f"{query} extension:.kicad_mod in:path path:footprints",
                    "per_page": limit,
                }
            )
            response.raise_for_status()
            data = response.json()
            
            for item in data.get("items", []):
                path = item.get("path", "")
                name = Path(path).stem
                
                # Simplify - actual would fetch full content
                footprints.append(KiCadFootprint(
                    name=name,
                    library=path.split("/")[0] if "/" in path else "custom",
                    path=path,
                    description=name,
                    pad_count=0,  # Would need content parse
                    smd="SMD" in name.upper() or "SMD" in item.get("name", "").upper(),
                ))
        
        except httpx.HTTPError:
            pass
        
        return footprints
    
    def _get_embedded_footprints(self, query: str, limit: int) -> list[KiCadFootprint]:
        """
        Embedded common footprints when API unavailable.
        These are the most commonly used packages.
        """
        common_footprints = [
            # Resistors
            {"name": "R_0402_1005Metric", "package": "0402", "pads": 2, "smd": True},
            {"name": "R_0603_1608Metric", "package": "0603", "pads": 2, "smd": True},
            {"name": "R_0805_2012Metric", "package": "0805", "pads": 2, "smd": True},
            {"name": "R_1206_3216Metric", "package": "1206", "pads": 2, "smd": True},
            
            # Capacitors
            {"name": "C_0402_1005Metric", "package": "0402", "pads": 2, "smd": True},
            {"name": "C_0603_1608Metric", "package": "0603", "pads": 2, "smd": True},
            {"name": "C_0805_2012Metric", "package": "0805", "pads": 2, "smd": True},
            {"name": "C_1206_3216Metric", "package": "1206", "pads": 2, "smd": True},
            
            # Inductors
            {"name": "L_0402_1005Metric", "package": "0402", "pads": 2, "smd": True},
            {"name": "L_0603_1608Metric", "package": "0603", "pads": 2, "smd": True},
            {"name": "L_0805_2012Metric", "package": "0805", "pads": 2, "smd": True},
            
            # ICs - QFN
            {"name": "QFN-48-1EP_7x7Metric_P0.5mm", "package": "QFN-48", "pads": 48, "smd": True},
            {"name": "QFN-32-1EP_5x5Metric_P0.5mm", "package": "QFN-32", "pads": 32, "smd": True},
            {"name": "QFN-20-1EP_4x4Metric_P0.5mm", "package": "QFN-20", "pads": 20, "smd": True},
            
            # ICs - TSSOP
            {"name": "TSSOP-48_6x12mm_P0.5mm", "package": "TSSOP-48", "pads": 48, "smd": True},
            {"name": "TSSOP-28_4.4x9.7mm_P0.65mm", "package": "TSSOP-28", "pads": 28, "smd": True},
            
            # ICs - SOIC
            {"name": "SOIC-8_3.9x4.9mm_P1.27mm", "package": "SOIC-8", "pads": 8, "smd": True},
            {"name": "SOIC-16_3.9x9.9mm_P1.27mm", "package": "SOIC-16", "pads": 16, "smd": True},
            
            # ICs - LQFP
            {"name": "LQFP-64-1EP_10x10mm_P0.5mm", "package": "LQFP-64", "pads": 64, "smd": True},
            {"name": "LQFP-48-1EP_7x7mm_P0.5mm", "package": "LQFP-48", "pads": 48, "smd": True},
            {"name": "LQFP-32-1EP_7x7mm_P0.8mm", "package": "LQFP-32", "pads": 32, "smd": True},
            
            # Connectors - USB
            {"name": "USB-C_Receptacle", "package": "USB-C", "pads": 24, "smd": True},
            {"name": "Micro-USB_Molex-105017", "package": "Micro-USB", "pads": 10, "smd": True},
            
            # Connectors - Pin Headers
            {"name": "Pin_Header_1x02_P2.54mm_Vertical", "package": "HDR-1x2", "pads": 2, "smd": False},
            {"name": "Pin_Header_1x04_P2.54mm_Vertical", "package": "HDR-1x4", "pads": 4, "smd": False},
            {"name": "Pin_Header_1x06_P2.54mm_Vertical", "package": "HDR-1x6", "pads": 6, "smd": False},
            {"name": "Pin_Header_1x10_P2.54mm_Vertical", "package": "HDR-1x10", "pads": 10, "smd": False},
            {"name": "Pin_Header_2x03_P2.54mm_Vertical", "package": "HDR-2x3", "pads": 6, "smd": False},
            {"name": "Pin_Header_2x05_P2.54mm_Vertical", "package": "HDR-2x5", "pads": 10, "smd": False},
            {"name": "Pin_Header_2x10_P2.54mm_Vertical", "package": "HDR-2x10", "pads": 20, "smd": False},
            
            # Crystals
            {"name": "Crystal_GND24_HC49_SMD", "package": "HC49", "pads": 2, "smd": True},
            {"name": "Crystal_SMD_3225", "package": "3225", "pads": 2, "smd": True},
            {"name": "Crystal_SMD_5032", "package": "5032", "pads": 2, "smd": True},
            
            # LEDs
            {"name": "LED_0603_1608Metric", "package": "0603", "pads": 2, "smd": True},
            {"name": "LED_0805_2012Metric", "package": "0805", "pads": 2, "smd": True},
            {"name": "LED_3mm", "package": "PTH-3mm", "pads": 2, "smd": False},
            {"name": "LED_5mm", "package": "PTH-5mm", "pads": 2, "smd": False},
            
            # Diodes
            {"name": "D_SOD-123", "package": "SOD-123", "pads": 2, "smd": True},
            {"name": "D_SOD-323", "package": "SOD-323", "pads": 2, "smd": True},
            
            # MOSFETs
            {"name": "MOSFET_SOT-23", "package": "SOT-23", "pads": 3, "smd": True},
            {"name": "MOSFET_SOT-223", "package": "SOT-223", "pads": 3, "smd": True},
            
            # ICs - SOIC wide
            {"name": "SOIC-28W_7.5x17.9mm_P1.27mm", "package": "SOIC-28W", "pads": 28, "smd": True},
        ]
        
        # Filter by query
        query_lower = query.lower()
        results = [
            KiCadFootprint(
                name=f["name"],
                library="kicad_builtin",
                path=f"name",
                description=f"{f['package']} package",
                pad_count=f["pads"],
                smd=f["smd"],
            )
            for f in common_footprints
            if query_lower in f["name"].lower() or query_lower in f["package"].lower()
        ]
        
        return results[:limit]
    
    async def get_footprint(self, footprint_name: str) -> Optional[KiCadFootprint]:
        """Get single footprint by name."""
        footprints = await self.search_footprints(footprint_name, limit=1)
        return footprints[0] if footprints else None
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


class ComponentLibraryFallback:
    """
    Fallback component data when APIs unavailable.
    Uses common components that are always available.
    """
    
    # Common components with basic specs
    COMMON_COMPONENTS = {
        "resistors": [
            {"value": "10Ω", "package": "0805", "power": "0.125W", "tolerance": "1%"},
            {"value": "100Ω", "package": "0805", "power": "0.125W", "tolerance": "1%"},
            {"value": "1K", "package": "0805", "power": "0.125W", "tolerance": "1%"},
            {"value": "10K", "package": "0805", "power": "0.125W", "tolerance": "1%"},
            {"value": "47K", "package": "0805", "power": "0.125W", "tolerance": "1%"},
            {"value": "100K", "package": "0805", "power": "0.125W", "tolerance": "1%"},
            {"value": "1M", "package": "0805", "power": "0.125W", "tolerance": "1%"},
        ],
        "capacitors": [
            {"value": "10pF", "package": "0603", "voltage": "25V", "type": "C0G/NP0"},
            {"value": "100pF", "package": "0603", "voltage": "25V", "type": "C0G/NP0"},
            {"value": "1nF", "package": "0603", "voltage": "25V", "type": "X7R"},
            {"value": "10nF", "package": "0603", "voltage": "25V", "type": "X7R"},
            {"value": "100nF", "package": "0603", "voltage": "25V", "type": "X7R"},
            {"value": "1μF", "package": "0603", "voltage": "16V", "type": "X7R"},
            {"value": "10μF", "package": "0805", "voltage": "16V", "type": "X7R"},
            {"value": "100μF", "package": "1206", "voltage": "10V", "type": "X7R"},
        ],
        "ICs": [
            {"mpn": "ESP32-WROOM-32", "package": "QFN-48", "description": "WiFi+BT MCU"},
            {"mpn": "STM32F103C8T6", "package": "LQFP-48", "description": "ARM Cortex-M3"},
            {"mpn": "ATmega328P", "package": "TQFP-32", "description": "8-bit AVR"},
            {"mpn": "RP2040", "package": "QFN-48", "description": "Dual-core MCU"},
            {"mpn": "Arduino Nano", "package": "Custom", "description": "ATmega328P module"},
            {"mpn": "FT232RL", "package": "SSOP-28", "description": "USB-UART"},
            {"mpn": "AMS1117-3.3", "package": "SOT-223", "description": "3.3V LDO"},
            {"mpn": "CH340G", "package": "SOIC-16", "description": "USB-UART"},
            {"mpn": "NE555", "package": "SOIC-8", "description": "Timer IC"},
            {"mpn": "LM358", "package": "SOIC-8", "description": "Dual Op-Amp"},
            {"mpn": "LM317", "package": "SOT-223", "description": "Adjustable LDO"},
            {"mpn": "ULN2803", "package": "SOIC-18", "description": "Darlington array"},
            {"mpn": "74HC595", "package": "SOIC-16", "description": "8-bit shift register"},
            {"mpn": "MAX485", "package": "SOIC-8", "description": "RS-485 transceiver"},
        ],
        "connectors": [
            {"mpn": "USB-C-connector", "package": "USB-C", "description": "Type-C receptacle"},
            {"mpn": "Micro-USB", "package": "Micro-USB", "description": "Micro-USB-B"},
            {"mpn": "2P-2.54mm", "package": "HDR-1x2", "description": "Pin header"},
            {"mpn": "4P-2.54mm", "package": "HDR-1x4", "description": "Pin header"},
            {"mpn": "6P-2.54mm", "package": "HDR-1x6", "description": "Pin header"},
            {"mpn": "8P-2.54mm", "package": "HDR-1x8", "description": "Pin header"},
            {"mpn": "10P-2.54mm", "package": "HDR-1x10", "description": "Pin header"},
            {"mpn": "DC-power-jack", "package": "DC-Jack", "description": "5.5mm barrel jack"},
        ],
    }
    
    def search(self, query: str, category: Optional[str] = None, limit: int = 20) -> list[dict]:
        """Search common components."""
        query_lower = query.lower()
        results = []
        
        categories = [category] if category else list(self.COMMON_COMPONENTS.keys())
        
        for cat in categories:
            if cat in self.COMMON_COMPONENTS:
                for comp in self.COMMON_COMPONENTS[cat]:
                    # Check if matches query
                    values = list(comp.values())
                    if any(query_lower in str(v).lower() for v in values):
                        comp_copy = comp.copy()
                        comp_copy["category"] = cat
                        results.append(comp_copy)
        
        return results[:limit]
    
    def get_by_mpn(self, mpn: str) -> Optional[dict]:
        """Find component by MPN."""
        mpn_lower = mpn.lower()
        
        for cat, components in self.COMMON_COMPONENTS.items():
            for comp in components:
                if comp.get("mpn", "").lower() == mpn_lower:
                    result = comp.copy()
                    result["category"] = cat
                    return result
        
        return None


# Default instances
def get_kicad_library() -> KiCadLibraryClient:
    return KiCadLibraryClient()


def get_component_fallback() -> ComponentLibraryFallback:
    return ComponentLibraryFallback()