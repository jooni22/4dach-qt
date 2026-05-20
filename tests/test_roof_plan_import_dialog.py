from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest

from core.models import Point2D
from ui.dialogs.roof_plan_import_dialog import RoofPlanImportCanvas, RoofPlanImportWidget


def _image_path(tmp_path):
    path = tmp_path / "rzut.png"
    image = QImage(240, 180, QImage.Format.Format_RGB32)
    image.fill(Qt.GlobalColor.white)
    assert image.save(str(path))
    return path


def test_roof_plan_import_canvas_stores_crop_drag_in_image_coordinates(qtbot, tmp_path):
    canvas = RoofPlanImportCanvas(_image_path(tmp_path), None)
    qtbot.addWidget(canvas)
    canvas.resize(520, 360)
    canvas.show()
    qtbot.waitExposed(canvas)

    start = canvas._image_to_canvas_point(Point2D(10, 20)).toPoint()
    end = canvas._image_to_canvas_point(Point2D(110, 80)).toPoint()

    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    QTest.mouseMove(canvas, end)
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, end)

    crop = canvas.crop_rect()
    assert crop.left() == pytest.approx(10, abs=0.75)
    assert crop.top() == pytest.approx(20, abs=0.75)
    assert crop.width() == pytest.approx(100, abs=1.0)
    assert crop.height() == pytest.approx(60, abs=1.0)
    roundtrip = canvas._canvas_to_image_rect(canvas._image_to_canvas_rect(crop))
    assert roundtrip.left() == pytest.approx(crop.left())
    assert roundtrip.top() == pytest.approx(crop.top())
    assert roundtrip.width() == pytest.approx(crop.width())
    assert roundtrip.height() == pytest.approx(crop.height())


def test_roof_plan_import_canvas_resize_keeps_image_coordinates_stable(qtbot, tmp_path):
    canvas = RoofPlanImportCanvas(_image_path(tmp_path), None)
    qtbot.addWidget(canvas)
    image_point = Point2D(120, 90)

    canvas.resize(520, 360)
    first_canvas_point = canvas._image_to_canvas_point(image_point)
    first_roundtrip = canvas._canvas_to_image_point(first_canvas_point)
    canvas.resize(820, 500)
    second_canvas_point = canvas._image_to_canvas_point(image_point)
    second_roundtrip = canvas._canvas_to_image_point(second_canvas_point)

    assert second_canvas_point != first_canvas_point
    assert first_roundtrip == image_point
    assert second_roundtrip == image_point


def test_roof_plan_import_widget_closes_sketch_inline_and_handles_undo_and_escape(qtbot, tmp_path):
    widget = RoofPlanImportWidget(_image_path(tmp_path), {}, None)
    qtbot.addWidget(widget)
    canvas = widget.canvas

    canvas.add_sketch_point(Point2D(0, 0))
    canvas.add_sketch_point(Point2D(100, 0))
    canvas.add_sketch_point(Point2D(100, 100))
    qtbot.keyClick(canvas, Qt.Key.Key_Z, modifier=Qt.KeyboardModifier.ControlModifier)

    assert canvas.draft_points() == [Point2D(0, 0), Point2D(100, 0)]

    canvas.add_sketch_point(Point2D(100, 100))
    canvas.close_active_sketch()

    assert len(widget.imported_drafts()) == 1
    assert len(canvas._drafts) == 1
    assert widget.dimension_row_count() == 1
    assert canvas.draft_points() == []

    canvas.add_sketch_point(Point2D(10, 10))
    qtbot.keyClick(canvas, Qt.Key.Key_Escape)

    assert canvas.draft_points() == []


def test_roof_plan_import_requires_reference_dimensions_before_import(qtbot, tmp_path):
    widget = RoofPlanImportWidget(_image_path(tmp_path), {}, None)
    qtbot.addWidget(widget)

    widget.add_import_draft([Point2D(0, 0), Point2D(100, 0), Point2D(100, 80), Point2D(0, 80)])

    assert widget.import_button.isEnabled() is False

    widget.dimension_spin_for_draft(0).setValue(250)

    assert widget.import_button.isEnabled() is True


def test_roof_plan_import_render_controls_update_canvas_state(qtbot, tmp_path):
    widget = RoofPlanImportWidget(_image_path(tmp_path), {}, None)
    qtbot.addWidget(widget)

    widget.image_opacity_slider.setValue(35)
    widget.line_opacity_slider.setValue(55)
    widget.show_image_toggle.setChecked(False)

    assert widget.canvas.image_opacity == 0.35
    assert widget.canvas.line_opacity == 0.55
    assert widget.canvas.show_image is False


def test_roof_plan_import_widget_zoom_controls_change_canvas_mode(qtbot, tmp_path):
    widget = RoofPlanImportWidget(_image_path(tmp_path), {}, None)
    qtbot.addWidget(widget)

    assert widget.canvas.zoom_mode() == "fit"

    widget.zoom_100_button.click()
    assert widget.canvas.zoom_mode() == "manual"
    assert widget.canvas.zoom_factor() == pytest.approx(1.0)

    widget.zoom_in_button.click()
    assert widget.canvas.zoom_factor() > 1.0

    widget.fit_button.click()
    assert widget.canvas.zoom_mode() == "fit"
