from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from core.canvas_mapper import CanvasMapper
from core.geometry import segment_length
from core.models import Point2D, Polygon2D, RoofPlane
from ui.drawing_canvas import DrawingCanvas


def _make_canvas(qtbot, outline: Polygon2D) -> DrawingCanvas:
    canvas = DrawingCanvas()
    canvas.resize(640, 420)
    canvas.set_roof_plane(RoofPlane(id="plane-1", name="1", outline=outline))
    qtbot.addWidget(canvas)
    canvas.show()
    qtbot.waitExposed(canvas)
    return canvas


def _point_on_canvas(canvas: DrawingCanvas, point: Point2D) -> QPoint:
    mapper = CanvasMapper(canvas.roof_plane.outline.bounds(), canvas.rect())
    return mapper.map_point(point).toPoint()


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
