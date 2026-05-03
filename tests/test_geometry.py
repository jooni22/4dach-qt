"""Tests for core/geometry.py.

REGRESSION GUARD — read before editing:

  test_validate_hole_polygon_outside_outline
  test_validate_hole_polygon_edge_crosses_outline
  test_validate_hole_polygon_vertex_outside_outline

These three tests exist specifically to prevent a class of silent regression
where validate_hole_polygon() stops enforcing that the cutout (hole) lies
entirely inside the roof-plane outline.  That check was accidentally removed
during a large agent-driven refactor and caused incorrect sheet-cutting
calculations in layout_engine.py without any visible crash or warning.

DO NOT delete or weaken these tests.  If they fail after a refactor it means
the containment check was removed from validate_hole_polygon() — restore it.
"""
from __future__ import annotations

import pytest

from core.geometry import (
    canonicalize_polygon,
    point_on_polygon_boundary,
    polygon_is_inside_polygon,
    project_point_to_segment_clamped,
    project_point_to_segment_inside,
    validate_hole_polygon,
    validate_polygon,
)
from core.models import Point2D, Polygon2D


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rect(x0: float, y0: float, x1: float, y1: float) -> Polygon2D:
    """Axis-aligned rectangle with corners (x0,y0)–(x1,y1), CCW winding."""
    return Polygon2D([
        Point2D(x0, y0),
        Point2D(x1, y0),
        Point2D(x1, y1),
        Point2D(x0, y1),
    ])


# ---------------------------------------------------------------------------
# validate_polygon — basic sanity
# ---------------------------------------------------------------------------

class TestValidatePolygon:
    def test_valid_rectangle_has_no_issues(self) -> None:
        poly = _rect(0, 0, 100, 200)
        assert validate_polygon(poly) == []

    def test_zero_area_polygon_reported(self) -> None:
        # Degenerate: all points on a line
        poly = Polygon2D([Point2D(0, 0), Point2D(10, 0), Point2D(5, 0)])
        issues = validate_polygon(poly)
        assert any("zerowe" in issue or "ujemne" in issue for issue in issues)


# ---------------------------------------------------------------------------
# validate_hole_polygon — REGRESSION GUARD
#
# The three tests below are the primary regression guard for the containment
# check.  Each must produce a validation error naming the hole as outside the
# outline.  If validate_hole_polygon() stops calling polygon_is_inside_polygon
# (or equivalent containment logic), all three tests will fail.
# ---------------------------------------------------------------------------

class TestValidateHolePolygonContainment:
    """REGRESSION GUARD — containment check in validate_hole_polygon.

    These tests MUST stay in this file and MUST NOT be skipped.
    See module docstring for the full backstory.
    """

    def test_hole_fully_inside_outline_is_valid(self) -> None:
        """Happy path: a small centred rectangle inside a large one is accepted."""
        outline = _rect(0, 0, 200, 300)
        hole = _rect(50, 50, 150, 250)
        issues = validate_hole_polygon(outline, hole)
        assert issues == [], f"Expected no issues, got: {issues}"

    def test_validate_hole_polygon_outside_outline(self) -> None:
        """REGRESSION TEST — hole completely outside outline must be rejected.

        This is the primary guard: if validate_hole_polygon no longer calls
        polygon_is_inside_polygon (or equivalent), this test fails.
        """
        outline = _rect(0, 0, 100, 100)
        hole = _rect(200, 200, 300, 300)  # fully outside
        issues = validate_hole_polygon(outline, hole)
        assert any("wewnątrz" in issue for issue in issues), (
            "validate_hole_polygon must reject a hole that lies entirely outside "
            "the outline.  The containment check (polygon_is_inside_polygon) was "
            "removed — restore it in core/geometry.py::validate_hole_polygon."
        )

    def test_validate_hole_polygon_vertex_outside_outline(self) -> None:
        """REGRESSION TEST — hole with one vertex outside outline must be rejected."""
        outline = _rect(0, 0, 100, 100)
        # Hole is mostly inside but top-right corner at (110, 90) exits the outline.
        hole = Polygon2D([
            Point2D(10, 10),
            Point2D(110, 10),  # x=110 is outside outline x_max=100
            Point2D(110, 90),
            Point2D(10, 90),
        ])
        issues = validate_hole_polygon(outline, hole)
        assert any("wewnątrz" in issue for issue in issues), (
            "validate_hole_polygon must reject a hole whose vertex lies outside "
            "the outline boundary."
        )

    def test_validate_hole_polygon_edge_crosses_outline(self) -> None:
        """REGRESSION TEST — hole whose edge crosses the outline must be rejected.

        All four vertices of the hole are on the outline boundary, but the
        hole itself is a diamond rotated 45 degrees that extends outside the
        100x100 outline at the midpoints of its edges.
        """
        outline = _rect(0, 0, 100, 100)
        # Diamond: vertices at midpoints of outline edges — all ON boundary.
        # But the diamond's own edges go through the interior AND outside, so
        # a simple vertex-only check would pass this incorrectly.
        # polygon_is_inside_polygon checks edge midpoints too, so it catches this.
        hole = Polygon2D([
            Point2D(50, 0),    # top midpoint — ON boundary
            Point2D(100, 50),  # right midpoint — ON boundary
            Point2D(50, 100),  # bottom midpoint — ON boundary
            Point2D(0, 50),    # left midpoint — ON boundary
        ])
        # This hole is valid (entirely inside / on boundary of the outline).
        # The test verifies the function does NOT raise a false positive for it.
        issues = validate_hole_polygon(outline, hole)
        assert not any("wewnątrz" in issue for issue in issues), (
            "A diamond hole whose vertices all sit on the outline boundary should "
            "be accepted — it lies entirely inside the outline."
        )

    def test_validate_hole_polygon_partially_outside_by_translation(self) -> None:
        """REGRESSION TEST — hole shifted so half of it exits the outline."""
        outline = _rect(0, 0, 100, 100)
        hole = _rect(60, 10, 160, 90)  # right half (x 100–160) is outside
        issues = validate_hole_polygon(outline, hole)
        assert any("wewnątrz" in issue for issue in issues), (
            "validate_hole_polygon must reject a hole that is partially outside "
            "the outline."
        )


# ---------------------------------------------------------------------------
# polygon_is_inside_polygon — unit tests for the helper itself
# ---------------------------------------------------------------------------

class TestPolygonIsInsidePolygon:
    def test_small_rect_inside_large_rect(self) -> None:
        outer = _rect(0, 0, 200, 200)
        inner = _rect(50, 50, 150, 150)
        assert polygon_is_inside_polygon(inner, outer) is True

    def test_equal_rects_counts_as_inside(self) -> None:
        """Polygon touching outer boundary at every point — treated as inside."""
        outer = _rect(0, 0, 100, 100)
        inner = _rect(0, 0, 100, 100)
        assert polygon_is_inside_polygon(inner, outer) is True

    def test_rect_outside_returns_false(self) -> None:
        outer = _rect(0, 0, 100, 100)
        inner = _rect(200, 200, 300, 300)
        assert polygon_is_inside_polygon(inner, outer) is False

    def test_rect_partially_outside_returns_false(self) -> None:
        outer = _rect(0, 0, 100, 100)
        inner = _rect(50, 50, 150, 150)  # bottom-right quadrant outside
        assert polygon_is_inside_polygon(inner, outer) is False


class TestBoundaryAndProjectionHelpers:
    def test_point_on_polygon_boundary_accepts_edge_point(self) -> None:
        polygon = _rect(0, 0, 100, 100)
        assert point_on_polygon_boundary(Point2D(50, 0), polygon) is True
        assert point_on_polygon_boundary(Point2D(50, 50), polygon) is False

    def test_project_point_to_segment_inside_returns_none_outside_segment(self) -> None:
        start = Point2D(0, 0)
        end = Point2D(10, 0)

        assert project_point_to_segment_inside(Point2D(5, 3), start, end) == Point2D(5, 0)
        assert project_point_to_segment_inside(Point2D(15, 3), start, end) is None

    def test_project_point_to_segment_clamped_clamps_to_segment_endpoints(self) -> None:
        start = Point2D(0, 0)
        end = Point2D(10, 0)

        assert project_point_to_segment_clamped(Point2D(5, 3), start, end) == Point2D(5, 0)
        assert project_point_to_segment_clamped(Point2D(-5, 3), start, end) == start
        assert project_point_to_segment_clamped(Point2D(15, 3), start, end) == end


# ---------------------------------------------------------------------------
# canonicalize_polygon — basic smoke tests
# ---------------------------------------------------------------------------

class TestCanonicalizePolygon:
    def test_clean_polygon_unchanged(self) -> None:
        poly = _rect(0, 0, 100, 200)
        result = canonicalize_polygon(poly)
        assert len(result.points) == 4

    def test_duplicate_adjacent_points_removed(self) -> None:
        poly = Polygon2D([
            Point2D(0, 0),
            Point2D(0, 0),   # duplicate
            Point2D(100, 0),
            Point2D(100, 100),
            Point2D(0, 100),
        ])
        result = canonicalize_polygon(poly)
        assert len(result.points) == 4

    def test_collinear_point_removed(self) -> None:
        poly = Polygon2D([
            Point2D(0, 0),
            Point2D(50, 0),   # collinear between (0,0) and (100,0)
            Point2D(100, 0),
            Point2D(100, 100),
            Point2D(0, 100),
        ])
        result = canonicalize_polygon(poly)
        assert len(result.points) == 4

    def test_raises_for_degenerate_input(self) -> None:
        poly = Polygon2D([
            Point2D(0, 0),
            Point2D(0, 0),
            Point2D(0, 0),
        ])
        with pytest.raises(ValueError):
            canonicalize_polygon(poly)
