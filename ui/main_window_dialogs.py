"""Small dialog-flow helpers used by MainWindow without changing ownership."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from PySide6.QtWidgets import QDialog

from core.geometry import make_rectangle, make_trapezoid, make_triangle
from core.models import Point2D, Polygon2D


class _PlaneWithCutouts(Protocol):
    outline: Polygon2D | None
    holes: Sequence[Polygon2D]


def dialog_accepted(dialog: QDialog) -> bool:
    return dialog.exec() == QDialog.DialogCode.Accepted


def remember_shape_config(config_data: dict, shape_key: str, values: dict) -> None:
    config_data.setdefault("ksztalty", {})[shape_key] = values


def build_shape_outline(shape_key: str, values: dict) -> Polygon2D:
    if shape_key == "prostokat":
        return make_rectangle(values["szerokosc"], values["wysokosc"])
    if shape_key == "trojkat":
        side = values["ramie"] if values.get("ramie_enabled") else None
        return make_triangle(values["typ"], values["podstawa"], values["wysokosc"], side)
    if shape_key == "trapez":
        return make_trapezoid(
            values["typ"],
            values["podstawa_dolna"],
            values["podstawa_gorna"],
            values["wysokosc"],
        )
    raise ValueError(f"Nieobsługiwany kształt połaci: {shape_key}")


def flip_polygon_in_bounds(
    polygon: Polygon2D,
    *,
    horizontal: bool = False,
    vertical: bool = False,
) -> Polygon2D:
    if not horizontal and not vertical:
        return polygon.copy()

    bounds = polygon.bounds()

    def _map_point(point: Point2D) -> Point2D:
        next_x = bounds.max_x - (point.x - bounds.min_x) if horizontal else point.x
        next_y = bounds.max_y - (point.y - bounds.min_y) if vertical else point.y
        return Point2D(next_x, next_y)

    return Polygon2D([_map_point(point) for point in polygon.points])


def build_centered_rectangular_cutout(outline: Polygon2D, width_cm: int, height_cm: int) -> Polygon2D:
    bounds = outline.bounds()
    origin_x = bounds.min_x + (bounds.width - width_cm) / 2.0
    origin_y = bounds.min_y + (bounds.height - height_cm) / 2.0
    return Polygon2D.rectangle(width_cm, height_cm, origin_x, origin_y)


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
