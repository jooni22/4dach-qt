"""core/app_settings.py — Central application-level settings.

Stored under the 'app_settings' key in config.json.
Kept separate from per-plane GenerationSettings on purpose:
these are business-rule parameters, not per-project geometry choices.
However, to ensure reproducibility of estimates, the value used
during layout generation is always snapshotted per LayoutResult
(see layout_engine.py) — so reloading a project with different
app_settings does NOT retroactively change already-computed layouts.
"""
from __future__ import annotations

from dataclasses import dataclass

SHIFT_DRAG_BEHAVIOR_FREE_MOVE = "free_move"
SHIFT_DRAG_BEHAVIOR_ORTHOGONAL_LOCK = "orthogonal_lock"
_VALID_SHIFT_DRAG_BEHAVIORS = {
    SHIFT_DRAG_BEHAVIOR_FREE_MOVE,
    SHIFT_DRAG_BEHAVIOR_ORTHOGONAL_LOCK,
}
LIVE_ANGLE_MODE_ABSOLUTE = "absolute"
LIVE_ANGLE_MODE_RELATIVE_TO_PREV = "relative_to_prev"
_VALID_LIVE_ANGLE_MODES = {
    LIVE_ANGLE_MODE_ABSOLUTE,
    LIVE_ANGLE_MODE_RELATIVE_TO_PREV,
}
EDGE_DRAG_MODE_MOVE_VERTICES = "move_vertices"
EDGE_DRAG_MODE_INSERT_VERTEX = "insert_vertex"
_VALID_EDGE_DRAG_MODES = {
    EDGE_DRAG_MODE_MOVE_VERTICES,
    EDGE_DRAG_MODE_INSERT_VERTEX,
}


@dataclass
class AppSettings:
    """Central application-level settings.

    Fields:
        partial_cutout_top_extra_cm: Extra material added to the top portion
            of a sheet when a cutout only partially covers the band width.
            Defaults to 15.0 cm.  Must be >= 0.
        grid_size_cm: Size of the editing grid square in domain centimetres.
            Defaults to 10.0 cm. Must be > 0.
        shift_drag_behavior: Defines how holding Shift modifies movement.
            `free_move` bypasses snapping, while `orthogonal_lock` constrains
            movement to one axis using 1 cm increments.
    """

    partial_cutout_top_extra_cm: float = 15.0
    grid_size_cm: float = 10.0
    shift_drag_behavior: str = SHIFT_DRAG_BEHAVIOR_FREE_MOVE
    show_axis_overlay: bool = True
    grid_major_cm: int = 100
    grid_minor_cm: int = 10
    show_crosshair: bool = True
    live_angle_mode: str = LIVE_ANGLE_MODE_ABSOLUTE
    show_decimal_cm: bool = False
    show_angle_arc: bool = True
    show_guide_lines: bool = True
    close_on_rmb: bool = True
    snap_to_grid: bool = True
    snap_to_axis: bool = True
    snap_to_45deg: bool = True
    snap_to_3060deg: bool = False
    snap_to_points: bool = True
    show_inferences: bool = True
    snap_axis_threshold_deg: float = 3.0
    snap_45_threshold_deg: float = 2.5
    snap_radius_px: int = 12
    edge_drag_mode: str = EDGE_DRAG_MODE_MOVE_VERTICES
    show_edge_length_labels: bool = True
    show_vertex_angle_labels: bool = False
    label_always_visible: bool = False
    undo_stack_depth: int = 50

    @classmethod
    def from_dict(cls, data: dict | None) -> "AppSettings":
        d = data or {}
        raw = d.get("partial_cutout_top_extra_cm", 15.0)
        try:
            value = float(raw)
        except (TypeError, ValueError):
            value = 15.0
        raw_grid = d.get("grid_size_cm", 10.0)
        try:
            grid_size = float(raw_grid)
        except (TypeError, ValueError):
            grid_size = 10.0
        if grid_size <= 0:
            grid_size = 10.0
        shift_drag_behavior = str(d.get("shift_drag_behavior", SHIFT_DRAG_BEHAVIOR_FREE_MOVE))
        if shift_drag_behavior not in _VALID_SHIFT_DRAG_BEHAVIORS:
            shift_drag_behavior = SHIFT_DRAG_BEHAVIOR_FREE_MOVE
        show_axis_overlay = bool(d.get("show_axis_overlay", True))
        show_crosshair = bool(d.get("show_crosshair", True))
        try:
            grid_major_cm = int(d.get("grid_major_cm", 100))
        except (TypeError, ValueError):
            grid_major_cm = 100
        if grid_major_cm <= 0:
            grid_major_cm = 100
        try:
            grid_minor_cm = int(d.get("grid_minor_cm", 10))
        except (TypeError, ValueError):
            grid_minor_cm = 10
        if grid_minor_cm <= 0:
            grid_minor_cm = 10
        live_angle_mode = str(d.get("live_angle_mode", LIVE_ANGLE_MODE_ABSOLUTE))
        if live_angle_mode not in _VALID_LIVE_ANGLE_MODES:
            live_angle_mode = LIVE_ANGLE_MODE_ABSOLUTE
        edge_drag_mode = str(d.get("edge_drag_mode", EDGE_DRAG_MODE_MOVE_VERTICES))
        if edge_drag_mode not in _VALID_EDGE_DRAG_MODES:
            edge_drag_mode = EDGE_DRAG_MODE_MOVE_VERTICES
        try:
            snap_axis_threshold_deg = float(d.get("snap_axis_threshold_deg", 3.0))
        except (TypeError, ValueError):
            snap_axis_threshold_deg = 3.0
        if snap_axis_threshold_deg <= 0:
            snap_axis_threshold_deg = 3.0
        try:
            snap_45_threshold_deg = float(d.get("snap_45_threshold_deg", 2.5))
        except (TypeError, ValueError):
            snap_45_threshold_deg = 2.5
        if snap_45_threshold_deg <= 0:
            snap_45_threshold_deg = 2.5
        try:
            snap_radius_px = int(d.get("snap_radius_px", 12))
        except (TypeError, ValueError):
            snap_radius_px = 12
        if snap_radius_px <= 0:
            snap_radius_px = 12
        try:
            undo_stack_depth = int(d.get("undo_stack_depth", 50))
        except (TypeError, ValueError):
            undo_stack_depth = 50
        if undo_stack_depth <= 0:
            undo_stack_depth = 50
        return cls(
            partial_cutout_top_extra_cm=max(0.0, value),
            grid_size_cm=grid_size,
            shift_drag_behavior=shift_drag_behavior,
            show_axis_overlay=show_axis_overlay,
            grid_major_cm=grid_major_cm,
            grid_minor_cm=grid_minor_cm,
            show_crosshair=show_crosshair,
            live_angle_mode=live_angle_mode,
            show_decimal_cm=bool(d.get("show_decimal_cm", False)),
            show_angle_arc=bool(d.get("show_angle_arc", True)),
            show_guide_lines=bool(d.get("show_guide_lines", True)),
            close_on_rmb=bool(d.get("close_on_rmb", True)),
            snap_to_grid=bool(d.get("snap_to_grid", True)),
            snap_to_axis=bool(d.get("snap_to_axis", True)),
            snap_to_45deg=bool(d.get("snap_to_45deg", True)),
            snap_to_3060deg=bool(d.get("snap_to_3060deg", False)),
            snap_to_points=bool(d.get("snap_to_points", True)),
            show_inferences=bool(d.get("show_inferences", True)),
            snap_axis_threshold_deg=snap_axis_threshold_deg,
            snap_45_threshold_deg=snap_45_threshold_deg,
            snap_radius_px=snap_radius_px,
            edge_drag_mode=edge_drag_mode,
            show_edge_length_labels=bool(d.get("show_edge_length_labels", True)),
            show_vertex_angle_labels=bool(d.get("show_vertex_angle_labels", False)),
            label_always_visible=bool(d.get("label_always_visible", False)),
            undo_stack_depth=undo_stack_depth,
        )

    def to_dict(self) -> dict:
        return {
            "partial_cutout_top_extra_cm": self.partial_cutout_top_extra_cm,
            "grid_size_cm": self.grid_size_cm,
            "shift_drag_behavior": self.shift_drag_behavior,
            "show_axis_overlay": self.show_axis_overlay,
            "grid_major_cm": self.grid_major_cm,
            "grid_minor_cm": self.grid_minor_cm,
            "show_crosshair": self.show_crosshair,
            "live_angle_mode": self.live_angle_mode,
            "show_decimal_cm": self.show_decimal_cm,
            "show_angle_arc": self.show_angle_arc,
            "show_guide_lines": self.show_guide_lines,
            "close_on_rmb": self.close_on_rmb,
            "snap_to_grid": self.snap_to_grid,
            "snap_to_axis": self.snap_to_axis,
            "snap_to_45deg": self.snap_to_45deg,
            "snap_to_3060deg": self.snap_to_3060deg,
            "snap_to_points": self.snap_to_points,
            "show_inferences": self.show_inferences,
            "snap_axis_threshold_deg": self.snap_axis_threshold_deg,
            "snap_45_threshold_deg": self.snap_45_threshold_deg,
            "snap_radius_px": self.snap_radius_px,
            "edge_drag_mode": self.edge_drag_mode,
            "show_edge_length_labels": self.show_edge_length_labels,
            "show_vertex_angle_labels": self.show_vertex_angle_labels,
            "label_always_visible": self.label_always_visible,
            "undo_stack_depth": self.undo_stack_depth,
        }
