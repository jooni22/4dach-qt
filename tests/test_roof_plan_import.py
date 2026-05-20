from __future__ import annotations

import pytest

from core.models import Point2D
from core.roof_plan_import import (
    cleanup_import_points,
    normalize_polygon_to_reference_edge,
    validate_import_polygon,
)


def test_normalize_polygon_to_reference_edge_scales_and_moves_to_local_origin():
    polygon = normalize_polygon_to_reference_edge(
        [Point2D(20, 10), Point2D(120, 10), Point2D(120, 60), Point2D(20, 60)],
        reference_edge_index=0,
        reference_length_cm=250,
    )

    assert polygon.points == [
        Point2D(0.0, 0.0),
        Point2D(250.0, 0.0),
        Point2D(250.0, 125.0),
        Point2D(0.0, 125.0),
    ]


def test_validate_import_polygon_rejects_too_few_points_self_intersections_and_zero_edges():
    assert validate_import_polygon([Point2D(0, 0), Point2D(10, 0)]) == [
        "Połać musi mieć co najmniej 3 punkty"
    ]

    bowtie_issues = validate_import_polygon(
        [Point2D(0, 0), Point2D(10, 10), Point2D(0, 10), Point2D(10, 0)]
    )
    assert "Polygon zawiera samoprzecięcia" in bowtie_issues

    zero_edge_issues = validate_import_polygon(
        [Point2D(0, 0), Point2D(0, 0), Point2D(10, 0), Point2D(0, 10)],
        cleanup=False,
    )
    assert "Polygon zawiera zduplikowane punkty" in zero_edge_issues
    assert "Polygon zawiera krawędź o zerowej długości" in zero_edge_issues


def test_cleanup_import_points_removes_near_duplicates_and_collinear_points():
    points = cleanup_import_points(
        [
            Point2D(0.0, 0.0),
            Point2D(0.01, 0.01),
            Point2D(100.0, 0.0),
            Point2D(200.0, 0.0),
            Point2D(200.0, 100.0),
            Point2D(0.0, 100.0),
        ],
        duplicate_tolerance=0.1,
        collinear_tolerance=0.001,
    )

    assert points == [
        Point2D(0.0, 0.0),
        Point2D(200.0, 0.0),
        Point2D(200.0, 100.0),
        Point2D(0.0, 100.0),
    ]


def test_normalize_polygon_to_reference_edge_rejects_invalid_reference_dimension():
    with pytest.raises(ValueError, match="Długość referencyjna musi być dodatnia"):
        normalize_polygon_to_reference_edge(
            [Point2D(0, 0), Point2D(10, 0), Point2D(0, 10)],
            reference_edge_index=0,
            reference_length_cm=0,
        )
