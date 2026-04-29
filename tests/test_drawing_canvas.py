from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QMouseEvent, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from core.app_settings import AppSettings
from core.geometry import segment_length
from core.layout_engine import generate_layout
from core.models import Material, Point2D, Polygon2D, RoofPlane
from ui.drawing_canvas import AXIS_WIDGET_PADDING_PX, DrawingCanvas


def _make_canvas(qtbot, outline: Polygon2D, *, holes: list[Polygon2D] | None = None) -> DrawingCanvas:
    canvas = DrawingCanvas()
    canvas.resize(640, 420)
    canvas.set_roof_plane(RoofPlane(id="plane-1", name="1", outline=outline, holes=list(holes or [])))
    qtbot.addWidget(canvas)
    canvas.show()
    qtbot.waitExposed(canvas)
    return canvas


def _point_on_canvas(canvas: DrawingCanvas, point: Point2D) -> QPoint:
    mapper = canvas._canvas_mapper()
    return mapper.map_point(point).toPoint()


def _overlay_point(canvas: DrawingCanvas) -> Point2D | None:
    overlay = canvas._edit_overlay
    if overlay is None:
        return None
    return overlay.domain_point


def _send_mouse_move(
    canvas: DrawingCanvas,
    point: QPoint | QPointF,
    *,
    buttons: Qt.MouseButton = Qt.MouseButton.NoButton,
    modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
) -> None:
    pos = QPointF(point)
    event = QMouseEvent(QEvent.Type.MouseMove, pos, pos, Qt.MouseButton.NoButton, buttons, modifiers)
    QApplication.sendEvent(canvas, event)


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


def test_canvas_allows_cutout_vertex_drag_outside_plane(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    hole = Polygon2D.rectangle(80, 60, origin_x=100, origin_y=70)
    canvas = _make_canvas(qtbot, outline, holes=[hole])

    start = _point_on_canvas(canvas, hole.points[0])
    invalid_domain = Point2D(-10, 70)
    target = _point_on_canvas(canvas, invalid_domain)

    with qtbot.waitSignal(canvas.hole_edit_committed, timeout=1000) as blocker:
        QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
        QTest.mouseMove(canvas, target)
        QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, target)

    assert blocker.args[0] == 0
    assert blocker.args[1].points[0].x == pytest.approx(invalid_domain.x, abs=1.5)
    assert blocker.args[1].points[0].y == pytest.approx(invalid_domain.y, abs=1.5)


def test_canvas_axis_indicator_origin_is_pinned_to_canvas_corner(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    canvas = _make_canvas(qtbot, outline)

    axis_origin = canvas._axis_indicator_origin()
    canvas_rect = QRectF(canvas.rect())

    assert axis_origin.x() == pytest.approx(AXIS_WIDGET_PADDING_PX)
    assert axis_origin.y() == pytest.approx(canvas_rect.bottom() - AXIS_WIDGET_PADDING_PX)


def test_canvas_hovering_outline_vertex_sets_edit_overlay(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    canvas = _make_canvas(qtbot, outline)

    vertex = _point_on_canvas(canvas, outline.points[0])
    _send_mouse_move(canvas, vertex)

    assert canvas._edit_overlay is not None
    assert canvas._edit_overlay.mode == "hover"
    assert canvas._edit_overlay.target_kind == "outline_vertex"
    assert canvas._edit_overlay.vertex_index == 0
    assert _overlay_point(canvas).x == pytest.approx(outline.points[0].x, abs=0.1)
    assert _overlay_point(canvas).y == pytest.approx(outline.points[0].y, abs=0.1)


def test_canvas_hovering_outside_handles_clears_edit_overlay(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    canvas = _make_canvas(qtbot, outline)

    _send_mouse_move(canvas, _point_on_canvas(canvas, outline.points[0]))
    assert canvas._edit_overlay is not None

    _send_mouse_move(canvas, _point_on_canvas(canvas, Point2D(150, 100)))

    assert canvas._edit_overlay is None


def test_canvas_dragging_outline_vertex_switches_edit_overlay_to_drag(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    canvas = _make_canvas(qtbot, outline)

    start = _point_on_canvas(canvas, outline.points[1])
    _send_mouse_move(canvas, start)
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)

    assert canvas._edit_overlay is not None
    assert canvas._edit_overlay.mode == "drag"
    assert canvas._edit_overlay.target_kind == "outline_vertex"
    assert canvas._edit_overlay.vertex_index == 1


def test_canvas_dragging_hole_center_updates_edit_overlay_domain_point(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    hole = Polygon2D.rectangle(80, 60, origin_x=100, origin_y=70)
    canvas = _make_canvas(qtbot, outline, holes=[hole])

    hole_center = Point2D(140, 100)
    target_domain = Point2D(170, 120)
    start = _point_on_canvas(canvas, hole_center)
    target = _point_on_canvas(canvas, target_domain)

    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    _send_mouse_move(canvas, target, buttons=Qt.MouseButton.LeftButton)

    assert canvas._edit_overlay is not None
    assert canvas._edit_overlay.mode == "drag"
    assert canvas._edit_overlay.target_kind == "hole_center"
    assert _overlay_point(canvas).x == pytest.approx(target_domain.x, abs=1.5)
    assert _overlay_point(canvas).y == pytest.approx(target_domain.y, abs=1.5)


def test_canvas_dragging_hole_center_exposes_coordinate_labels_for_all_cutout_vertices(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    hole = Polygon2D.rectangle(80, 60, origin_x=100, origin_y=70)
    canvas = _make_canvas(qtbot, outline, holes=[hole])

    hole_center = Point2D(140, 100)
    target_domain = Point2D(170, 120)
    start = _point_on_canvas(canvas, hole_center)
    target = _point_on_canvas(canvas, target_domain)

    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    _send_mouse_move(canvas, target, buttons=Qt.MouseButton.LeftButton)

    labels = canvas._coordinate_overlay_labels()

    assert [label.kind for label in labels] == ["active", "vertex", "vertex", "vertex", "vertex"]
    assert labels[0].domain_point.x == pytest.approx(target_domain.x, abs=1.5)
    assert labels[0].domain_point.y == pytest.approx(target_domain.y, abs=1.5)

    preview_hole = canvas.display_holes()[0]
    assert [label.domain_point for label in labels[1:]] == preview_hole.points


def test_canvas_origin_defaults_to_outline_bottom_left_corner(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    canvas = _make_canvas(qtbot, outline)

    assert canvas._origin_point() == Point2D(0.0, 200.0)


def test_canvas_coordinate_label_text_uses_origin_relative_coordinates(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    plane = RoofPlane(id="plane-1", name="1", outline=outline)
    plane.generation_settings.origin_x_cm = 25.0
    plane.generation_settings.origin_y_cm = 180.0
    canvas = DrawingCanvas()
    canvas.resize(640, 420)
    canvas.set_roof_plane(plane)
    qtbot.addWidget(canvas)
    canvas.show()
    qtbot.waitExposed(canvas)

    assert canvas._coordinate_label_text(Point2D(450.24, 120.54)) == "X: 425.2 | Y: 59.5"


def test_canvas_dragging_origin_emits_committed_origin_point(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    canvas = _make_canvas(qtbot, outline)

    canvas.set_origin_edit_enabled(True)
    start = _point_on_canvas(canvas, canvas._origin_point())
    target_domain = Point2D(80, 150)
    target = _point_on_canvas(canvas, target_domain)

    with qtbot.waitSignal(canvas.origin_edit_committed, timeout=1000) as blocker:
        QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
        _send_mouse_move(canvas, target, buttons=Qt.MouseButton.LeftButton)
        QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, target)

    committed_origin = blocker.args[0]
    assert committed_origin.x == pytest.approx(target_domain.x, abs=1.5)
    assert committed_origin.y == pytest.approx(target_domain.y, abs=1.5)


def test_canvas_dragging_origin_forces_grid_visibility_only_during_drag(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    canvas = _make_canvas(qtbot, outline)
    canvas.set_origin_edit_enabled(True)

    assert canvas._show_grid is False
    assert canvas._grid_visible() is False

    start = _point_on_canvas(canvas, canvas._origin_point())
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)

    assert canvas._dragging_origin is True
    assert canvas._grid_visible() is True

    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)

    assert canvas._dragging_origin is False
    assert canvas._grid_visible() is False


def test_canvas_dragging_origin_projects_to_nearest_boundary_when_cursor_leaves_shape(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    canvas = _make_canvas(qtbot, outline)
    canvas.set_origin_edit_enabled(True)

    start = _point_on_canvas(canvas, canvas._origin_point())
    outside_target = _point_on_canvas(canvas, Point2D(350.0, 120.0))

    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    _send_mouse_move(canvas, outside_target, buttons=Qt.MouseButton.LeftButton)

    assert canvas._origin_point().x == pytest.approx(300.0, abs=1.5)
    assert canvas._origin_point().y == pytest.approx(120.0, abs=1.5)


def test_canvas_dragging_origin_label_uses_previous_origin_as_reference(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    plane = RoofPlane(id="plane-1", name="1", outline=outline)
    plane.generation_settings.origin_x_cm = 25.0
    plane.generation_settings.origin_y_cm = 180.0
    canvas = DrawingCanvas()
    canvas.resize(640, 420)
    canvas.set_roof_plane(plane)
    qtbot.addWidget(canvas)
    canvas.show()
    qtbot.waitExposed(canvas)
    canvas.set_snap_to_grid_enabled(False)
    canvas.set_origin_edit_enabled(True)

    start = _point_on_canvas(canvas, canvas._origin_point())
    target = _point_on_canvas(canvas, Point2D(80.0, 150.0))

    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    _send_mouse_move(canvas, target, buttons=Qt.MouseButton.LeftButton)

    assert canvas._origin_drag_label_text() == "X: 55.0 | Y: 30.0"


def test_canvas_draws_origin_marker_after_edit_handles(qtbot, monkeypatch):
    outline = Polygon2D.rectangle(300, 200)
    canvas = _make_canvas(qtbot, outline)
    canvas.set_origin_edit_enabled(True)
    canvas._plane_selected = True
    calls: list[str] = []

    monkeypatch.setattr(canvas, "_draw_sheet_placements", lambda *args, **kwargs: None)
    monkeypatch.setattr(canvas, "_draw_axis_indicator", lambda *args, **kwargs: None)
    monkeypatch.setattr(canvas, "_draw_edit_overlay", lambda *args, **kwargs: calls.append("overlay"))
    monkeypatch.setattr(canvas, "_draw_vertex_handles", lambda *args, **kwargs: calls.append("vertex"))
    monkeypatch.setattr(canvas, "_draw_midpoint_handles", lambda *args, **kwargs: calls.append("midpoint"))
    monkeypatch.setattr(canvas, "_draw_origin_marker", lambda *args, **kwargs: calls.append("origin"))

    canvas.grab()
    QApplication.processEvents()

    assert "origin" in calls
    assert "vertex" in calls
    assert "overlay" in calls
    assert calls[-1] == "origin"


def test_canvas_dragging_vertex_snaps_to_configured_grid_size(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    canvas = _make_canvas(qtbot, outline)
    canvas.set_app_settings(AppSettings(grid_size_cm=25.0))

    start = _point_on_canvas(canvas, outline.points[1])
    target = _point_on_canvas(canvas, Point2D(263, 43))

    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    _send_mouse_move(canvas, target, buttons=Qt.MouseButton.LeftButton)

    preview = canvas.display_outline()
    assert preview is not None
    assert preview.points[1].x == pytest.approx(275.0, abs=1.5)
    assert preview.points[1].y == pytest.approx(50.0, abs=1.5)


def test_canvas_global_snap_toggle_disables_vertex_snapping(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    canvas = _make_canvas(qtbot, outline)
    canvas.set_app_settings(AppSettings(grid_size_cm=25.0))
    canvas.set_snap_to_grid_enabled(False)

    start = _point_on_canvas(canvas, outline.points[1])
    target_domain = Point2D(263, 43)
    target = _point_on_canvas(canvas, target_domain)

    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    _send_mouse_move(canvas, target, buttons=Qt.MouseButton.LeftButton)

    preview = canvas.display_outline()
    assert preview is not None
    assert preview.points[1].x == pytest.approx(target_domain.x, abs=1.5)
    assert preview.points[1].y == pytest.approx(target_domain.y, abs=1.5)


def test_canvas_shift_temporarily_bypasses_vertex_snapping(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    canvas = _make_canvas(qtbot, outline)
    canvas.set_app_settings(AppSettings(grid_size_cm=25.0))

    start = _point_on_canvas(canvas, outline.points[1])
    target_domain = Point2D(263, 43)
    target = _point_on_canvas(canvas, target_domain)

    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    _send_mouse_move(
        canvas,
        target,
        buttons=Qt.MouseButton.LeftButton,
        modifiers=Qt.KeyboardModifier.ShiftModifier,
    )

    preview = canvas.display_outline()
    assert preview is not None
    assert preview.points[1].x == pytest.approx(target_domain.x, abs=1.5)
    assert preview.points[1].y == pytest.approx(target_domain.y, abs=1.5)


def test_canvas_ctrl_uses_ten_times_finer_snap_step(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    canvas = _make_canvas(qtbot, outline)
    canvas.set_app_settings(AppSettings(grid_size_cm=25.0))

    start = _point_on_canvas(canvas, outline.points[1])
    target = _point_on_canvas(canvas, Point2D(263, 43))

    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    _send_mouse_move(
        canvas,
        target,
        buttons=Qt.MouseButton.LeftButton,
        modifiers=Qt.KeyboardModifier.ControlModifier,
    )

    preview = canvas.display_outline()
    assert preview is not None
    assert preview.points[1].x == pytest.approx(262.5, abs=1.5)
    assert preview.points[1].y == pytest.approx(42.5, abs=1.5)


def test_canvas_dragging_hole_center_snaps_a_vertex_instead_of_the_center(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    hole = Polygon2D.rectangle(80, 60, origin_x=100, origin_y=70)
    canvas = _make_canvas(qtbot, outline, holes=[hole])
    canvas.set_app_settings(AppSettings(grid_size_cm=25.0))

    hole_center = Point2D(140, 100)
    target_domain = Point2D(171, 121)
    start = _point_on_canvas(canvas, hole_center)
    target = _point_on_canvas(canvas, target_domain)

    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    _send_mouse_move(canvas, target, buttons=Qt.MouseButton.LeftButton)

    preview_hole = canvas.display_holes()[0]
    preview_center = canvas._hole_center_point(preview_hole)
    origin = canvas._origin_point()

    snapped_vertices = [
        point
        for point in preview_hole.points
        if abs((point.x - origin.x) / 25.0 - round((point.x - origin.x) / 25.0)) < 1e-6
        and abs((origin.y - point.y) / 25.0 - round((origin.y - point.y) / 25.0)) < 1e-6
    ]

    assert snapped_vertices
    assert abs(preview_center.x - 175.0) > 1.5 or abs(preview_center.y - 125.0) > 1.5


def test_canvas_edit_overlay_uses_configured_grid_size(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    canvas = _make_canvas(qtbot, outline)
    canvas.set_app_settings(AppSettings(grid_size_cm=5.0))

    mapper = canvas._canvas_mapper()

    assert canvas._edit_overlay_grid_step_cm(mapper) == pytest.approx(5.0)


def test_canvas_coordinate_label_text_uses_single_decimal_without_unit(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    canvas = _make_canvas(qtbot, outline)

    assert canvas._coordinate_label_text(Point2D(450.24, 120.54)) == "X: 450.2 | Y: 79.5"


def test_canvas_mouse_release_clears_edit_overlay_after_drag(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    canvas = _make_canvas(qtbot, outline)

    start = _point_on_canvas(canvas, outline.points[1])
    target = _point_on_canvas(canvas, Point2D(260, 30))

    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    _send_mouse_move(canvas, target, buttons=Qt.MouseButton.LeftButton)
    assert canvas._edit_overlay is not None

    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, target)

    assert canvas._edit_overlay is None


def test_canvas_escape_clears_edit_overlay_during_drag(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    canvas = _make_canvas(qtbot, outline)

    start = _point_on_canvas(canvas, outline.points[1])
    target = _point_on_canvas(canvas, Point2D(260, 30))

    canvas.setFocus()
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    _send_mouse_move(canvas, target, buttons=Qt.MouseButton.LeftButton)
    assert canvas._edit_overlay is not None

    QTest.keyClick(canvas, Qt.Key.Key_Escape)

    assert canvas._edit_overlay is None


def test_canvas_manual_grid_toggle_remains_independent_from_edit_overlay(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    canvas = _make_canvas(qtbot, outline)

    canvas.toggle_grid(True)
    _send_mouse_move(canvas, _point_on_canvas(canvas, outline.points[0]))

    assert canvas._show_grid is True
    assert canvas._edit_overlay is not None

    canvas.toggle_grid(False)

    assert canvas._show_grid is False
    assert canvas._edit_overlay is not None


def test_canvas_uses_extra_horizontal_view_margin(qtbot):
    outline = Polygon2D.rectangle(300, 200)
    canvas = _make_canvas(qtbot, outline)

    mapper = canvas._canvas_mapper()
    mapped_bounds = mapper.map_rect(0.0, 300.0, 0.0, 200.0)

    assert mapped_bounds.left() >= 79.9
    assert canvas.rect().width() - mapped_bounds.right() >= 79.0


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
    assert canvas._sheet_label_text(items[0]) == "100"


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
    image = canvas.grab().toImage()
    hole_color = image.pixelColor(_point_on_canvas(canvas, Point2D(40, 45)))
    covered_color = image.pixelColor(_point_on_canvas(canvas, Point2D(15, 50)))
    assert covered_color != hole_color


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


def test_canvas_partial_cutout_top_sheet_uses_final_length_for_visual_height(qtbot):
    outline = Polygon2D.rectangle(1000, 1000)
    hole = Polygon2D.rectangle(300, 300, origin_x=0, origin_y=300)
    plane = RoofPlane(id="plane-1", name="PartialVisual", outline=outline, holes=[hole])
    canvas = _make_canvas(qtbot, outline, holes=[hole])

    _apply_layout(canvas, plane, _material(effective_width_cm=510, max_sheet_length_cm=1000, module_length_cm=0))

    items = canvas._sheet_render_items()
    top_item = next(item for item in items if item.split_reason == "partial_cutout_top")
    polygon_bounds = top_item.polygons[0].bounds()

    assert top_item.raw_length_cm == pytest.approx(300.0)
    assert top_item.final_length_cm == pytest.approx(315.0)
    assert polygon_bounds.min_y == pytest.approx(-15.0)
    assert polygon_bounds.max_y == pytest.approx(300.0)
    assert polygon_bounds.height == pytest.approx(315.0)

    protruding_point = canvas._canvas_mapper().map_point(Point2D(100, -10))
    assert canvas._hit_test_sheet(QPointF(protruding_point)) == top_item.placement_id


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
