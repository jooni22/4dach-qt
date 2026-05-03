import pytest

from core.models import Bounds2D, Point2D, Polygon2D, SheetPlacement
from ui.canvas.sheet_geometry import build_sheet_render_items, clip_polygon_to_vertical_span
from ui.canvas.snap_helpers import build_draw_inferences, resolve_axis_snap


def test_sheet_geometry_clip_polygon_to_vertical_span_trims_polygon():
    clipped = clip_polygon_to_vertical_span(
        Polygon2D.rectangle(50, 100),
        20.0,
        80.0,
    )

    assert clipped is not None
    assert clipped.bounds().min_y == 20.0
    assert clipped.bounds().max_y == 80.0
    assert clipped.area() == 3000.0


def test_sheet_geometry_build_sheet_render_items_sorts_auto_before_manual():
    auto = SheetPlacement(
        id="plane-1-b1-s0-r0",
        band_index=1,
        x_left_cm=0.0,
        x_right_cm=40.0,
        y_top_cm=0.0,
        y_bottom_cm=80.0,
        raw_length_cm=80.0,
        final_length_cm=80.0,
        source="auto",
    )
    manual = SheetPlacement(
        id="manual-1",
        band_index=1,
        x_left_cm=40.0,
        x_right_cm=80.0,
        y_top_cm=0.0,
        y_bottom_cm=80.0,
        raw_length_cm=80.0,
        final_length_cm=80.0,
        source="manual",
    )

    items = build_sheet_render_items(
        [{"band_index": 1, "segments": [{"segment_index": 0, "placement_id": auto.id}]}],
        [manual, auto],
    )

    assert [item.placement_id for item in items] == [auto.id, manual.id]
    assert items[0].polygons[0].bounds() == Bounds2D(0.0, 0.0, 40.0, 80.0)
    assert items[1].polygons[0].bounds() == Bounds2D(40.0, 0.0, 80.0, 80.0)


def test_snap_helpers_build_draw_inferences_is_canvas_free():
    lines = build_draw_inferences(
        raw_point=Point2D(21.0, 39.0),
        start=None,
        previous_point=None,
        target_vertices=[Point2D(20.0, 40.0)],
        target_edges=[(Point2D(0.0, 0.0), Point2D(100.0, 0.0))],
        bounds=Bounds2D(0.0, 0.0, 100.0, 100.0),
        radius=3.0,
    )

    assert {line.kind for line in lines} == {"horizontal", "vertical"}


def test_snap_helpers_resolve_axis_snap_returns_locked_point_and_label():
    state = resolve_axis_snap(
        Point2D(8.0, 0.2),
        Point2D(0.0, 0.0),
        threshold_deg=5.0,
    )

    assert state is not None
    assert state.kind == "axis"
    assert state.point.x == pytest.approx(8.002499609497024)
    assert state.point.y == pytest.approx(0.0)
    assert state.label == "0°"
