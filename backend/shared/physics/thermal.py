"""
PCB Builder - Thermal Engine
Junction temperature estimation, thermal via placement, heat dissipation analysis.
"""

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ThermalIssue:
    """A thermal issue."""
    component_id: str
    component_name: str
    junction_temp_c: float
    max_junction_temp_c: float
    severity: str
    message: str
    suggestion: str = ""


@dataclass
class ThermalResult:
    """Complete thermal analysis result."""
    passed: bool
    score: float
    issues: list[ThermalIssue] = field(default_factory=list)
    component_temps: list[dict] = field(default_factory=list)
    thermal_via_recommendations: list[dict] = field(default_factory=list)
    copper_pour_recommendations: list[str] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


class ThermalEngine:
    """
    Analyzes thermal performance of PCB designs.

    Checks:
    - Junction temperature estimation (theta_JA model)
    - Thermal via placement for QFN/BGA packages
    - Copper pour heat spreading
    - Component spacing for thermal isolation
    """

    AMBIENT_TEMP_C = 25.0
    FR4_THERMAL_CONDUCTIVITY = 0.3  # W/(m*K)
    COPPER_THERMAL_CONDUCTIVITY = 400  # W/(m*K)

    def __init__(self, ambient_temp_c: float = 25.0):
        self.ambient_temp = ambient_temp_c

    def analyze(self, design_data: dict) -> ThermalResult:
        """Run full thermal analysis."""
        components = design_data.get("placed_components", [])
        tracks = design_data.get("tracks", [])
        board = design_data.get("board_config", {})

        issues = []
        component_temps = []
        thermal_via_recs = []

        for comp in components:
            comp_id = comp.get("id", "")
            comp_name = comp.get("name", "")
            footprint = comp.get("footprint", "")
            x = comp.get("x", 0)
            y = comp.get("y", 0)

            # Estimate power dissipation
            power_w = self._estimate_power_dissipation(comp)
            if power_w <= 0:
                continue

            # Get thermal resistance
            theta_ja = self._get_theta_ja(footprint, comp_name)

            # Calculate junction temperature
            t_junction = self.ambient_temp + power_w * theta_ja

            # Get max junction temperature
            t_jmax = self._get_max_junction_temp(comp_name)

            temp_info = {
                "component_id": comp_id,
                "component_name": comp_name,
                "power_w": round(power_w, 3),
                "theta_ja_c_w": round(theta_ja, 1),
                "junction_temp_c": round(t_junction, 1),
                "max_junction_temp_c": t_jmax,
                "margin_c": round(t_jmax - t_junction, 1),
            }
            component_temps.append(temp_info)

            # Check if overheating
            if t_junction > t_jmax:
                issues.append(ThermalIssue(
                    component_id=comp_id,
                    component_name=comp_name,
                    junction_temp_c=round(t_junction, 1),
                    max_junction_temp_c=t_jmax,
                    severity="critical",
                    message=f"{comp_id} ({comp_name}) junction temp {t_junction:.1f}C exceeds max {t_jmax}C",
                    suggestion=self._get_thermal_suggestion(comp, power_w, theta_ja),
                ))
            elif t_junction > t_jmax * 0.85:
                issues.append(ThermalIssue(
                    component_id=comp_id,
                    component_name=comp_name,
                    junction_temp_c=round(t_junction, 1),
                    max_junction_temp_c=t_jmax,
                    severity="warning",
                    message=f"{comp_id} ({comp_name}) junction temp {t_junction:.1f}C approaching max {t_jmax}C",
                    suggestion=self._get_thermal_suggestion(comp, power_w, theta_ja),
                ))

            # Check if thermal vias needed
            if self._needs_thermal_vias(footprint, power_w):
                thermal_via_recs.append({
                    "component_id": comp_id,
                    "footprint": footprint,
                    "power_w": round(power_w, 3),
                    "recommended_vias": self._calculate_thermal_vias(power_w),
                    "via_pattern": "grid under thermal pad",
                })

        # Check thermal coupling between components
        coupling_issues = self._check_thermal_coupling(components, component_temps)
        issues.extend(coupling_issues)

        # Generate copper pour recommendations
        copper_recs = self._recommend_copper_pours(components, component_temps)

        critical_count = sum(1 for i in issues if i.severity == "critical")
        warning_count = sum(1 for i in issues if i.severity == "warning")

        score = 100.0 - critical_count * 25 - warning_count * 5
        score = max(0.0, score)

        max_temp = max((ct["junction_temp_c"] for ct in component_temps), default=25)

        return ThermalResult(
            passed=critical_count == 0,
            score=round(score, 1),
            issues=issues,
            component_temps=component_temps,
            thermal_via_recommendations=thermal_via_recs,
            copper_pour_recommendations=copper_recs,
            summary={
                "total_issues": len(issues),
                "critical": critical_count,
                "warning": warning_count,
                "max_junction_temp_c": round(max_temp, 1),
                "components_analyzed": len(component_temps),
                "thermal_vias_recommended": sum(r["recommended_vias"] for r in thermal_via_recs),
            },
        )

    def _estimate_power_dissipation(self, component: dict) -> float:
        """Estimate power dissipation from component type."""
        name = component.get("name", "").upper()
        footprint = component.get("footprint", "")

        power_map = {
            "REG": 1.0,
            "LDO": 0.5,
            "AMS1117": 1.0,
            "BUCK": 2.0,
            "BOOST": 1.5,
            "DC-DC": 2.0,
            "ESP32": 0.5,
            "ESP8266": 0.3,
            "STM32": 0.3,
            "FPGA": 3.0,
            "CPU": 5.0,
            "MCU": 0.2,
            "LED": 0.06,
            "MOSFET": 1.0,
            "TRANSISTOR": 0.5,
        }

        for key, power in power_map.items():
            if key in name:
                return power

        # Footprint-based estimates
        if footprint in ["SOT-223", "TO-220", "TO-263"]:
            return 1.0
        elif footprint in ["QFN-48", "QFN-32", "BGA"]:
            return 1.5

        return 0.05  # Default for passives

    def _get_theta_ja(self, footprint: str, name: str) -> float:
        """Get junction-to-ambient thermal resistance (C/W)."""
        fp = footprint.upper()

        theta_map = {
            "0402": 200,
            "0603": 150,
            "0805": 120,
            "1206": 100,
            "SOT-23": 200,
            "SOT-223": 60,
            "SOIC-8": 100,
            "SOIC-16": 80,
            "TQFP-48": 40,
            "TQFP-64": 35,
            "QFN-48": 25,
            "QFN-32": 30,
            "BGA": 20,
            "DIP-8": 80,
            "DIP-14": 70,
            "DIP-16": 65,
            "TO-220": 50,
            "TO-263": 40,
        }

        for key, theta in theta_map.items():
            if key in fp:
                return theta

        # Regulators typically have higher thermal resistance
        if any(k in name.upper() for k in ["REG", "LDO", "AMS"]):
            return 60

        return 100  # Default

    def _get_max_junction_temp(self, name: str) -> float:
        """Get maximum junction temperature for component."""
        name_upper = name.upper()

        if any(k in name_upper for k in ["ESP32", "ESP8266", "STM32"]):
            return 125
        elif any(k in name_upper for k in ["FPGA", "CPU"]):
            return 100
        elif any(k in name_upper for k in ["REG", "LDO", "AMS"]):
            return 125
        elif any(k in name_upper for k in ["MOSFET", "TRANSISTOR"]):
            return 150
        elif "LED" in name_upper:
            return 125
        else:
            return 125  # Default for most silicon

    def _get_thermal_suggestion(
        self,
        component: dict,
        power_w: float,
        theta_ja: float,
    ) -> str:
        """Generate thermal improvement suggestion."""
        footprint = component.get("footprint", "")

        suggestions = []

        if power_w > 1.0:
            suggestions.append("Add thermal vias under component thermal pad")
            suggestions.append("Increase copper pour area on adjacent layers")

        if footprint in ["QFN", "BGA"]:
            suggestions.append("Ensure thermal pad is connected to ground plane")
            suggestions.append("Use 0.3mm drill thermal vias in grid pattern")

        if theta_ja > 50:
            suggestions.append("Consider package with lower thermal resistance")

        suggestions.append(f"Current power: {power_w:.1f}W, theta_JA: {theta_ja:.0f}C/W")

        return "; ".join(suggestions)

    def _needs_thermal_vias(self, footprint: str, power_w: float) -> bool:
        """Determine if component needs thermal vias."""
        if power_w < 0.5:
            return False

        fp = footprint.upper()
        return any(k in fp for k in ["QFN", "BGA", "SOT-223", "TO-220", "TO-263"])

    def _calculate_thermal_vias(self, power_w: float) -> int:
        """Calculate recommended number of thermal vias."""
        # Rule of thumb: 1 via per 0.5W for QFN/BGA
        return max(4, int(math.ceil(power_w / 0.5)))

    def _check_thermal_coupling(
        self,
        components: list[dict],
        component_temps: list[dict],
    ) -> list[ThermalIssue]:
        """Check for thermal coupling between hot components."""
        issues = []

        hot_components = [
            ct for ct in component_temps
            if ct["junction_temp_c"] > 60
        ]

        for i, hc1 in enumerate(hot_components):
            for hc2 in hot_components[i + 1:]:
                # Find component positions
                comp1 = next(
                    (c for c in components if c["id"] == hc1["component_id"]),
                    None,
                )
                comp2 = next(
                    (c for c in components if c["id"] == hc2["component_id"]),
                    None,
                )

                if not comp1 or not comp2:
                    continue

                dx = comp1.get("x", 0) - comp2.get("x", 0)
                dy = comp1.get("y", 0) - comp2.get("y", 0)
                dist = math.sqrt(dx**2 + dy**2)

                # Minimum spacing for thermal isolation
                min_spacing = 5.0  # mm for components > 60C

                if dist < min_spacing:
                    issues.append(ThermalIssue(
                        component_id=hc1["component_id"],
                        component_name=hc1["component_name"],
                        junction_temp_c=hc1["junction_temp_c"],
                        max_junction_temp_c=hc1["max_junction_temp_c"],
                        severity="warning",
                        message=f"{hc1['component_id']} and {hc2['component_id']} too close ({dist:.1f}mm) for thermal isolation",
                        suggestion=f"Increase spacing to >{min_spacing}mm or add thermal barrier",
                    ))

        return issues

    def _recommend_copper_pours(
        self,
        components: list[dict],
        component_temps: list[dict],
    ) -> list[str]:
        """Recommend copper pours for heat spreading."""
        recs = []

        hot_components = [
            ct for ct in component_temps
            if ct["junction_temp_c"] > 50
        ]

        if hot_components:
            recs.append(
                f"Add ground plane copper pour under {len(hot_components)} hot component(s) "
                f"for heat spreading"
            )
            recs.append(
                "Use 2oz copper for better thermal conductivity if power > 2W"
            )

        return recs
