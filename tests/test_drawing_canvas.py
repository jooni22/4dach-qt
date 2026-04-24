from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPalette
from PySide6.QtTest import QTest

from core.canvas_mapper import CanvasMapper
from core.geometry import point_in_polygon
from core.geometry import segment_length
from core.layout_engine import generate_layout
from core.models import Material, Point2D, Polygon2D, RoofPlane
from ui.drawing_canvas import DrawingCanvas


def _make_canvas(qtbot, outline: Polygon2D, *, holes: list[Polygon2D] | None = None) -> DrawingCanvas:
    canvas = DrawingCanvas()
    canvas.resize(640, 420)
    canvas.set_roof_plane(RoofPlane(id="plane-1", name="1", outline=outline, holes=list(holes or [])))
    qtbot.addWidget(canvas)
    canvas.show()
    qtbot.waitExposed(canvas)
    return canvas


def _point_on_canvas(canvas: DrawingCanvas, point: Point2D) -> QPoint:
    mapper = CanvasMapper(canvas.roof_plane.outline.bounds(), canvas.rect())
    return mapper.map_point(point).toPoint()


def _material(**overrides) -> Material:
    payload = {
        "id": "PD510",
        "nazwa": "PD510",
        "type": "dachówkowa",
        "effective_width_cm": 50,
        "min_sheet_length_cm": 10,
        "max_sheet_length_cm": 500,
        "top_margin_cm": 0,
        "bottom_margin_cm": 0,
        "module_length_cm": 25,
    }
    payload.update(overrides)
    return Material(**payload)


def _apply_layout(canvas: DrawingCanvas, plane: RoofPlane, material: Material) -> None:
    result = generate_layout(plane, material)
    plane.auto_sheet_placements = list(result.placements)
    plane.layout_bands = [band.to_dict() for band in result.bands]
    plane.selected_material_id = material.id
    canvas.set_roof_plane(plane)
    canvas.set_material(material)
    canvas.repaint()


def test_canvas_selects_vertex_handle_on_mouse_press(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    canvas = _make_canvas(qtbot, outline)

    vertex = _point_on_canvas(canvas, outline.points[0])
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, vertex)

    assert canvas._active_vertex_index == 0
    assert canvas._dragging_vertex_index == 0


def test_canvas_dragging_vertex_updates_preview_geometry_live(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    canvas = _make_canvas(qtbot, outline)

    start = _point_on_canvas(canvas, outline.points[1])
    target_domain = Point2D(260, 30)
    target = _point_on_canvas(canvas, target_domain)

    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    QTest.mouseMove(canvas, target)

    preview = canvas.display_outline()
    assert preview is not None
    assert preview.points[1].x == pytest.approx(target_domain.x, abs=1.5)
    assert preview.points[1].y == pytest.approx(target_domain.y, abs=1.5)


def test_canvas_dragging_vertex_emits_updated_outline_on_release(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    canvas = _make_canvas(qtbot, outline)

    start = _point_on_canvas(canvas, outline.points[2])
    target_domain = Point2D(240, 180)
    target = _point_on_canvas(canvas, target_domain)

    with qtbot.waitSignal(canvas.outline_edit_committed, timeout=1000) as blocker:
        QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
        QTest.mouseMove(canvas, target)
        QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, target)

    committed_outline = blocker.args[0]
    assert committed_outline.points[2].x == pytest.approx(target_domain.x, abs=1.5)
    assert committed_outline.points[2].y == pytest.approx(target_domain.y, abs=1.5)
    assert canvas._dragging_vertex_index is None


def test_canvas_recomputes_edge_lengths_for_preview_geometry(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    canvas = _make_canvas(qtbot, outline)

    start = _point_on_canvas(canvas, outline.points[1])
    target_domain = Point2D(260, 50)
    target = _point_on_canvas(canvas, target_domain)

    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    QTest.mouseMove(canvas, target)

    lengths = canvas.edge_lengths_cm()
    preview = canvas.display_outline()
    assert preview is not None
    assert lengths[0] == pytest.approx(segment_length(preview.points[0], preview.points[1]), abs=0.01)
    assert lengths[1] == pytest.approx(segment_length(preview.points[1], preview.points[2]), abs=0.01)


def test_canvas_rejects_invalid_geometry_and_restores_original_outline(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    canvas = _make_canvas(qtbot, outline)

    start = _point_on_canvas(canvas, outline.points[2])
    invalid_domain = Point2D(0, 0)
    target = _point_on_canvas(canvas, invalid_domain)

    with qtbot.waitSignal(canvas.outline_edit_rejected, timeout=1000) as blocker:
        QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
        QTest.mouseMove(canvas, target)
        QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, target)

    assert "Polygon" in blocker.args[0]
    assert canvas.display_outline() == canvas.roof_plane.outline
    assert canvas.roof_plane.outline.points == outline.points


def test_canvas_selects_cutout_polygon_before_main_plane(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    hole = Polygon2D.rectangle(80, 60, origin_x=100, origin_y=70)
    canvas = _make_canvas(qtbot, outline, holes=[hole])

    inside_hole = _point_on_canvas(canvas, Point2D(120, 90))
    QTest.mouseClick(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, inside_hole)

    assert canvas.selected_cutout_index() == 0
    assert canvas.selected_geometry_kind() == "cutout_polygon"


def test_canvas_dragging_cutout_vertex_emits_updated_hole(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    hole = Polygon2D.rectangle(80, 60, origin_x=100, origin_y=70)
    canvas = _make_canvas(qtbot, outline, holes=[hole])

    start = _point_on_canvas(canvas, hole.points[1])
    target_domain = Point2D(210, 70)
    target = _point_on_canvas(canvas, target_domain)

    with qtbot.waitSignal(canvas.hole_edit_committed, timeout=1000) as blocker:
        QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
        QTest.mouseMove(canvas, target)
        QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, target)

    assert blocker.args[0] == 0
    committed_hole = blocker.args[1]
    assert committed_hole.points[1].x == pytest.approx(target_domain.x, abs=1.5)
    assert committed_hole.points[1].y == pytest.approx(target_domain.y, abs=1.5)
    assert canvas.selected_geometry_kind() == "cutout_vertex"


def test_canvas_rejects_cutout_vertex_drag_outside_plane(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    hole = Polygon2D.rectangle(80, 60, origin_x=100, origin_y=70)
    canvas = _make_canvas(qtbot, outline, holes=[hole])

    start = _point_on_canvas(canvas, hole.points[0])
    invalid_domain = Point2D(-10, 70)
    target = _point_on_canvas(canvas, invalid_domain)

    with qtbot.waitSignal(canvas.outline_edit_rejected, timeout=1000) as blocker:
        QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
        QTest.mouseMove(canvas, target)
        QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, target)

    assert "Wycinek musi leżeć w całości wewnątrz obrysu" in blocker.args[0]
    assert canvas.display_holes()[0].points == hole.points


def test_canvas_builds_sheet_render_items_for_simple_rectangle(qtbot):
    outline = Polygon2D.rectangle(120, 100)
    plane = RoofPlane(id="plane-1", name="Rect", outline=outline)
    canvas = _make_canvas(qtbot, outline)

    _apply_layout(canvas, plane, _material())

    items = canvas._sheet_render_items()

    assert [(item.band_index, item.final_length_cm, len(item.polygons)) for item in items] == [
        (0, 100.0, 1),
        (1, 100.0, 1),
        (2, 100.0, 1),
    ]
    assert canvas._sheet_label_text(items[0]) == "100 cm"


def test_canvas_render_items_preserve_cutout_exclusions(qtbot):
    outline = Polygon2D.rectangle(90, 100)
    hole = Polygon2D.rectangle(30, 40, origin_x=30, origin_y=30)
    plane = RoofPlane(id="plane-1", name="Hole", outline=outline, holes=[hole])
    canvas = _make_canvas(qtbot, outline, holes=[hole])

    _apply_layout(canvas, plane, _material(effective_width_cm=30, module_length_cm=0))

    items = canvas._sheet_render_items()

    assert [(item.band_index, item.final_length_cm) for item in items] == [
        (0, 100.0),
        (1, 30.0),
        (1, 30.0),
        (2, 100.0),
    ]
    assert all(len(item.polygons) == 1 for item in items)
    assert items[1].polygons[0].bounds().max_y == pytest.approx(30.0)
    assert items[2].polygons[0].bounds().min_y == pytest.approx(70.0)
    image = canvas.grab().toImage()
    hole_color = image.pixelColor(_point_on_canvas(canvas, Point2D(45, 50)))
    covered_color = image.pixelColor(_point_on_canvas(canvas, Point2D(15, 50)))
    assert hole_color == canvas.palette().color(QPalette.ColorRole.Base)
    assert covered_color != hole_color


def test_canvas_renders_skewed_plane_sheets_as_full_rectangles(qtbot):
    outline = Polygon2D(
        [
            Point2D(0, 20),
            Point2D(120, 0),
            Point2D(120, 100),
            Point2D(0, 120),
        ]
    )
    plane = RoofPlane(id="plane-1", name="Skewed", outline=outline)
    canvas = _make_canvas(qtbot, outline)

    _apply_layout(canvas, plane, _material())

    items = canvas._sheet_render_items()

    assert len(items) == 3
    assert all(len(item.polygons) == 1 for item in items)
    # Each rendered polygon spans from y_top to y_bottom (raw coverage),
    # which equals raw_length_cm, not final_length_cm.
    for item, placement in zip(items, plane.auto_sheet_placements):
        bounds = item.polygons[0].bounds()
        assert bounds.min_y == pytest.approx(placement.y_top_cm)
        assert bounds.max_y == pytest.approx(placement.y_bottom_cm)
        polygon_height = bounds.max_y - bounds.min_y
        assert polygon_height == pytest.approx(placement.raw_length_cm)

    # With envelope, Point2D(10, 15) should be within the first sheet's
    # coverage (which extends above y=20 on the left edge).
    assert point_in_polygon(Point2D(10, 15), items[0].polygons[0]) is True


def test_canvas_render_items_follow_layout_direction_change(qtbot):
    outline = Polygon2D.rectangle(120, 100)
    plane = RoofPlane(id="plane-1", name="Direction", outline=outline)
    canvas = _make_canvas(qtbot, outline)
    material = _material()

    _apply_layout(canvas, plane, material)
    left_items = canvas._sheet_render_items()

    plane.generation_settings.layout_origin = "right"
    _apply_layout(canvas, plane, material)
    right_items = canvas._sheet_render_items()

    assert left_items[0].polygons[0].bounds().min_x == pytest.approx(0.0)
    assert right_items[0].polygons[0].bounds().min_x == pytest.approx(70.0)


def test_canvas_updates_render_items_after_geometry_edit_and_relayout(qtbot):
    outline = Polygon2D.rectangle(120, 100)
    plane = RoofPlane(id="plane-1", name="Geom", outline=outline)
    canvas = _make_canvas(qtbot, outline)
    material = _material()

    _apply_layout(canvas, plane, material)
    assert len(canvas._sheet_render_items()) == 3

    plane.outline = Polygon2D.rectangle(180, 100)
    plane.layout_bands.clear()
    plane.auto_sheet_placements.clear()
    canvas.set_roof_plane(plane)
    assert canvas._sheet_render_items() == []

    _apply_layout(canvas, plane, material)
    items = canvas._sheet_render_items()
    assert len(items) == 4
    assert items[-1].polygons[0].bounds().max_x == pytest.approx(180.0)
