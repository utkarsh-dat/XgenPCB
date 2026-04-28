"""
PCB Builder - Design Comparison & Diff Engine
Compare two PCB designs and generate visual diffs.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class DiffResult:
    """Result of comparing two PCB designs."""
    identical: bool
    added_components: list[dict] = field(default_factory=list)
    removed_components: list[dict] = field(default_factory=list)
    modified_components: list[dict] = field(default_factory=list)
    added_tracks: list[dict] = field(default_factory=list)
    removed_tracks: list[dict] = field(default_factory=list)
    added_nets: list[dict] = field(default_factory=list)
    removed_nets: list[dict] = field(default_factory=list)
    board_config_changes: list[dict] = field(default_factory=list)
    drc_changes: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


class DesignComparator:
    """Compares two PCB designs and generates detailed diffs."""

    def compare(self, design_a: dict, design_b: dict) -> DiffResult:
        """Compare two designs and return differences."""
        result = DiffResult(identical=False)

        # Compare board config
        result.board_config_changes = self._diff_dicts(
            design_a.get("board_config", {}),
            design_b.get("board_config", {}),
            "board_config",
        )

        # Compare components
        comps_a = {c.get("id"): c for c in design_a.get("placed_components", [])}
        comps_b = {c.get("id"): c for c in design_b.get("placed_components", [])}

        for cid, comp in comps_b.items():
            if cid not in comps_a:
                result.added_components.append(comp)
            elif self._component_changed(comps_a[cid], comp):
                result.modified_components.append({
                    "id": cid,
                    "from": comps_a[cid],
                    "to": comp,
                    "changes": self._component_diff(comps_a[cid], comp),
                })

        for cid, comp in comps_a.items():
            if cid not in comps_b:
                result.removed_components.append(comp)

        # Compare tracks
        tracks_a = self._normalize_tracks(design_a.get("tracks", []))
        tracks_b = self._normalize_tracks(design_b.get("tracks", []))

        track_set_a = set(json.dumps(t, sort_keys=True) for t in tracks_a)
        track_set_b = set(json.dumps(t, sort_keys=True) for t in tracks_b)

        for t in tracks_b:
            if json.dumps(t, sort_keys=True) not in track_set_a:
                result.added_tracks.append(t)
        for t in tracks_a:
            if json.dumps(t, sort_keys=True) not in track_set_b:
                result.removed_tracks.append(t)

        # Compare nets
        nets_a = {n.get("name"): n for n in design_a.get("nets", [])}
        nets_b = {n.get("name"): n for n in design_b.get("nets", [])}

        for name, net in nets_b.items():
            if name not in nets_a:
                result.added_nets.append(net)
        for name, net in nets_a.items():
            if name not in nets_b:
                result.removed_nets.append(net)

        # DRC changes
        drc_a = design_a.get("drc_rules", {})
        drc_b = design_b.get("drc_rules", {})
        result.drc_changes = self._diff_dicts(drc_a, drc_b, "drc_rule")

        # Summary
        result.identical = (
            not result.added_components
            and not result.removed_components
            and not result.modified_components
            and not result.added_tracks
            and not result.removed_tracks
            and not result.board_config_changes
        )

        result.summary = {
            "components_added": len(result.added_components),
            "components_removed": len(result.removed_components),
            "components_modified": len(result.modified_components),
            "tracks_added": len(result.added_tracks),
            "tracks_removed": len(result.removed_tracks),
            "nets_added": len(result.added_nets),
            "nets_removed": len(result.removed_nets),
            "board_config_changes": len(result.board_config_changes),
            "drc_changes": len(result.drc_changes),
            "identical": result.identical,
        }

        return result

    def _diff_dicts(self, a: dict, b: dict, prefix: str) -> list[dict]:
        """Compare two dicts and list changes."""
        changes = []
        all_keys = set(a.keys()) | set(b.keys())
        for key in all_keys:
            val_a = a.get(key)
            val_b = b.get(key)
            if val_a != val_b:
                changes.append({
                    "field": f"{prefix}.{key}",
                    "from": val_a,
                    "to": val_b,
                })
        return changes

    def _component_changed(self, a: dict, b: dict) -> bool:
        """Check if a component has changed."""
        fields = ["x", "y", "rotation", "layer", "footprint", "mpn"]
        return any(a.get(f) != b.get(f) for f in fields)

    def _component_diff(self, a: dict, b: dict) -> list[str]:
        """List specific changes in a component."""
        changes = []
        fields = ["x", "y", "rotation", "layer", "footprint", "mpn"]
        for f in fields:
            if a.get(f) != b.get(f):
                changes.append(f"{f}: {a.get(f)} -> {b.get(f)}")
        return changes

    def _normalize_tracks(self, tracks: list[dict]) -> list[dict]:
        """Normalize tracks for comparison."""
        normalized = []
        for t in tracks:
            nt = {
                "net": t.get("net", ""),
                "layer": t.get("layer", "F.Cu"),
                "width": round(float(t.get("width", 0.25)), 3),
                "start": [round(float(t["start"][0]), 2), round(float(t["start"][1]), 2)] if "start" in t else [0, 0],
                "end": [round(float(t["end"][0]), 2), round(float(t["end"][1]), 2)] if "end" in t else [0, 0],
            }
            normalized.append(nt)
        return normalized

    def generate_changelog(self, design_a: dict, design_b: dict, commit_msg: str = "") -> str:
        """Generate a human-readable changelog between designs."""
        diff = self.compare(design_a, design_b)

        if diff.identical:
            return "No changes detected between designs."

        lines = [f"# Design Changes", ""]
        if commit_msg:
            lines.append(f"**Commit:** {commit_msg}")
            lines.append("")

        lines.append(f"## Summary")
        lines.append(f"- Components: +{diff.summary['components_added']}/-{diff.summary['components_removed']}/~{diff.summary['components_modified']}")
        lines.append(f"- Tracks: +{diff.summary['tracks_added']}/-{diff.summary['tracks_removed']}")
        lines.append(f"- Nets: +{diff.summary['nets_added']}/-{diff.summary['nets_removed']}")
        lines.append("")

        if diff.added_components:
            lines.append("## Added Components")
            for c in diff.added_components:
                lines.append(f"- **{c.get('id', '?')}**: {c.get('name', '?')} ({c.get('footprint', '?')})")
            lines.append("")

        if diff.removed_components:
            lines.append("## Removed Components")
            for c in diff.removed_components:
                lines.append(f"- **{c.get('id', '?')}**: {c.get('name', '?')}")
            lines.append("")

        if diff.modified_components:
            lines.append("## Modified Components")
            for m in diff.modified_components:
                lines.append(f"- **{m['id']}**:")
                for change in m['changes']:
                    lines.append(f"  - {change}")
            lines.append("")

        if diff.board_config_changes:
            lines.append("## Board Configuration Changes")
            for c in diff.board_config_changes:
                lines.append(f"- {c['field']}: {c['from']} -> {c['to']}")
            lines.append("")

        return "\n".join(lines)
