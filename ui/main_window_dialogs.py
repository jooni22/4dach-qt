"""Small dialog-flow helpers used by MainWindow without changing ownership."""

from __future__ import annotations

from typing import Protocol, Sequence

from PySide6.QtWidgets import QDialog

from core.models import Polygon2D


class _PlaneWithCutouts(Protocol):
    outline: Polygon2D | None
    holes: Sequence[Polygon2D]


def dialog_accepted(dialog: QDialog) -> bool:
    return dialog.exec() == QDialog.DialogCode.Accepted


def remember_shape_config(config_data: dict, shape_key: str, values: dict) -> None:
    config_data.setdefault("ksztalty", {})[shape_key] = values


def build_centered_hole(plane: _PlaneWithCutouts, width_cm: int, height_cm: int) -> Polygon2D:
    if plane.outline is None:
        return Polygon2D.rectangle(width_cm, height_cm, 0.0, 0.0)

    points = plane.outline.points
    center_x = sum(point.x for point in points) / len(points)
    center_y = sum(point.y for point in points) / len(points)
    offset_x = center_x - width_cm / 2.0
    offset_y = center_y - height_cm / 2.0
    if plane.holes:
        offset_x = max(hole.bounds().max_x for hole in plane.holes) + 10.0
    return Polygon2D.rectangle(width_cm, height_cm, offset_x, offset_y)
