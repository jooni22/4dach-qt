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
        return cls(
            partial_cutout_top_extra_cm=max(0.0, value),
            grid_size_cm=grid_size,
            shift_drag_behavior=shift_drag_behavior,
            show_axis_overlay=show_axis_overlay,
            grid_major_cm=grid_major_cm,
            grid_minor_cm=grid_minor_cm,
            show_crosshair=show_crosshair,
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
        }
