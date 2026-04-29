from __future__ import annotations

import pytest

from core.geometry import (
    delete_polygon_point,
    insert_polygon_point,
    replace_polygon_point,
    translate_polygon,
    validate_hole_polygon,
    validate_polygon,
)
from core.models import Point2D, Polygon2D


def test_validate_polygon_detects_self_intersection():
    polygon = Polygon2D(
        [
            Point2D(0, 0),
            Point2D(100, 100),
            Point2D(0, 100),
            Point2D(100, 0),
        ]
    )

    issues = validate_polygon(polygon)

    assert "Polygon zawiera samoprzecięcia" in issues


def test_validate_hole_polygon_allows_hole_outside_outline():
    outline = Polygon2D.rectangle(300, 200)
    hole = Polygon2D.rectangle(60, 60, origin_x=260, origin_y=30)

    issues = validate_hole_polygon(outline, hole)

    assert issues == []


def test_polygon_edit_operations_keep_expected_points_order():
    polygon = Polygon2D.rectangle(100, 80)

    inserted = insert_polygon_point(polygon, 0, Point2D(100, 20))
    replaced = replace_polygon_point(inserted, 1, Point2D(100, 10))
    moved = translate_polygon(replaced, 5, -5)
    reduced = delete_polygon_point(moved, 1)

    assert len(inserted.points) == 5
    assert replaced.points[1] == Point2D(100, 10)
    assert moved.points[0] == Point2D(5, -5)
    assert len(reduced.points) == 4


def test_delete_polygon_point_rejects_triangle_reduction():
    triangle = Polygon2D([Point2D(0, 0), Point2D(100, 0), Point2D(0, 100)])

    with pytest.raises(ValueError):
        delete_polygon_point(triangle, 1)
