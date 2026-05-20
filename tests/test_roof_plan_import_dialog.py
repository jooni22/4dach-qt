from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QPushButton

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
    assert canvas._mode == RoofPlanImportCanvas.MODE_DRAW
    roundtrip = canvas._canvas_to_image_rect(canvas._image_to_canvas_rect(crop))
    assert roundtrip.left() == pytest.approx(crop.left())
    assert roundtrip.top() == pytest.approx(crop.top())
    assert roundtrip.width() == pytest.approx(crop.width())
    assert roundtrip.height() == pytest.approx(crop.height())


def test_roof_plan_import_canvas_maps_points_through_active_crop(qtbot, tmp_path):
    canvas = RoofPlanImportCanvas(_image_path(tmp_path), None)
    qtbot.addWidget(canvas)
    canvas.resize(640, 420)
    canvas.set_crop_rect(QRectF(40, 30, 120, 60))

    image_point = Point2D(100, 75)
    canvas_point = canvas._image_to_canvas_point(image_point)
    crop_on_canvas = canvas._image_to_canvas_rect(canvas.crop_rect())
    target = canvas._image_target_rect()

    assert canvas._canvas_to_image_point(canvas_point) == image_point
    assert crop_on_canvas.left() == pytest.approx(target.left())
    assert crop_on_canvas.top() == pytest.approx(target.top())
    assert crop_on_canvas.width() == pytest.approx(target.width())
    assert crop_on_canvas.height() == pytest.approx(target.height())


def test_roof_plan_import_canvas_keeps_full_image_source_during_crop_drag(qtbot, tmp_path):
    canvas = RoofPlanImportCanvas(_image_path(tmp_path), None)
    qtbot.addWidget(canvas)
    canvas.resize(520, 360)
    canvas.show()
    qtbot.waitExposed(canvas)

    start = canvas._image_to_canvas_point(Point2D(10, 20)).toPoint()
    end = canvas._image_to_canvas_point(Point2D(130, 110)).toPoint()

    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    QTest.mouseMove(canvas, end)

    assert canvas.has_crop() is True
    assert canvas._drag_start is not None
    assert canvas._image_source_rect() == QRectF(0, 0, 240, 180)

    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, end)

    assert canvas._drag_start is None
    assert canvas._image_source_rect() == canvas.crop_rect()


def test_roof_plan_import_widget_crop_button_resets_previous_crop(qtbot, tmp_path):
    widget = RoofPlanImportWidget(_image_path(tmp_path), {}, None)
    qtbot.addWidget(widget)
    widget.canvas.set_crop_rect(QRectF(40, 30, 120, 90))
    widget.canvas.set_mode(RoofPlanImportCanvas.MODE_DRAW)

    widget.crop_mode_button.click()

    assert widget.canvas.has_crop() is False
    assert widget.canvas._mode == RoofPlanImportCanvas.MODE_CROP


def test_roof_plan_import_widget_mode_buttons_are_exclusive(qtbot, tmp_path):
    widget = RoofPlanImportWidget(_image_path(tmp_path), {}, None)
    qtbot.addWidget(widget)

    assert widget.draw_mode_button.isChecked() is True
    assert widget.crop_mode_button.isChecked() is False
    assert widget.canvas._mode == RoofPlanImportCanvas.MODE_DRAW

    widget.crop_mode_button.click()

    assert widget.crop_mode_button.isChecked() is True
    assert widget.draw_mode_button.isChecked() is False
    assert widget.canvas._mode == RoofPlanImportCanvas.MODE_CROP

    widget.draw_mode_button.click()

    assert widget.draw_mode_button.isChecked() is True
    assert widget.crop_mode_button.isChecked() is False
    assert widget.canvas._mode == RoofPlanImportCanvas.MODE_DRAW


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


def test_roof_plan_import_widget_undo_button_removes_active_sketch_point(qtbot, tmp_path):
    widget = RoofPlanImportWidget(_image_path(tmp_path), {}, None)
    qtbot.addWidget(widget)

    assert widget.undo_button.isEnabled() is False

    widget.canvas.add_sketch_point(Point2D(0, 0))

    assert widget.undo_button.isEnabled() is True

    widget.undo_button.click()

    assert widget.canvas.draft_points() == []
    assert widget.undo_button.isEnabled() is False


def test_roof_plan_import_requires_reference_dimensions_before_import(qtbot, tmp_path):
    widget = RoofPlanImportWidget(_image_path(tmp_path), {}, None)
    qtbot.addWidget(widget)

    widget.add_import_draft([Point2D(0, 0), Point2D(100, 0), Point2D(100, 80), Point2D(0, 80)])

    assert widget.import_button.isEnabled() is False

    widget.dimension_spin_for_draft(0).setValue(250)

    assert widget.import_button.isEnabled() is True


def test_roof_plan_import_reference_edge_combo_updates_highlight(qtbot, tmp_path):
    widget = RoofPlanImportWidget(_image_path(tmp_path), {}, None)
    qtbot.addWidget(widget)
    widget.add_import_draft([Point2D(0, 0), Point2D(100, 0), Point2D(100, 80), Point2D(0, 80)])

    edge_combo = widget._dimension_rows[0][0]
    assert edge_combo.toolTip() == "Automatycznie wybrano najdłuższą krawędź – możesz zmienić"

    edge_combo.setCurrentIndex(1)

    assert widget._drafts[0].reference_edge_index == 1
    assert widget.canvas._highlighted == (0, 1)


def test_roof_plan_import_highlight_tracks_last_draft_and_delete(qtbot, tmp_path):
    widget = RoofPlanImportWidget(_image_path(tmp_path), {}, None)
    qtbot.addWidget(widget)

    widget.add_import_draft([Point2D(0, 0), Point2D(100, 0), Point2D(100, 80), Point2D(0, 80)])
    widget.add_import_draft([Point2D(10, 10), Point2D(160, 10), Point2D(160, 90), Point2D(10, 90)])

    assert widget.canvas._highlighted == (1, widget._drafts[1].reference_edge_index)

    delete_buttons = []
    for layout_index in range(widget._dimensions_layout.count()):
        item = widget._dimensions_layout.itemAt(layout_index)
        row_widget = item.widget()
        if row_widget is None:
            continue
        delete_buttons.extend(
            button for button in row_widget.findChildren(QPushButton) if button.text() == "Usuń"
        )

    delete_buttons[1].click()

    assert widget.canvas._highlighted == (0, widget._drafts[0].reference_edge_index)

    delete_buttons = []
    for layout_index in range(widget._dimensions_layout.count()):
        item = widget._dimensions_layout.itemAt(layout_index)
        row_widget = item.widget()
        if row_widget is None:
            continue
        delete_buttons.extend(
            button for button in row_widget.findChildren(QPushButton) if button.text() == "Usuń"
        )

    delete_buttons[0].click()

    assert widget.canvas._highlighted is None


def test_roof_plan_import_widget_delete_button_removes_closed_draft(qtbot, tmp_path):
    widget = RoofPlanImportWidget(_image_path(tmp_path), {}, None)
    qtbot.addWidget(widget)

    widget.add_import_draft([Point2D(0, 0), Point2D(100, 0), Point2D(100, 80), Point2D(0, 80)])
    widget.add_import_draft([Point2D(10, 10), Point2D(160, 10), Point2D(160, 90), Point2D(10, 90)])
    widget.dimension_spin_for_draft(0).setValue(250)
    widget.dimension_spin_for_draft(1).setValue(375)

    delete_buttons = []
    for layout_index in range(widget._dimensions_layout.count()):
        item = widget._dimensions_layout.itemAt(layout_index)
        row_widget = item.widget()
        if row_widget is None:
            continue
        delete_buttons.extend(
            button for button in row_widget.findChildren(QPushButton) if button.text() == "Usuń"
        )

    assert len(delete_buttons) == 2

    delete_buttons[0].click()

    assert widget.imported_drafts() == [
        [Point2D(10, 10), Point2D(160, 10), Point2D(160, 90), Point2D(10, 90)]
    ]
    assert widget.canvas._drafts == widget.imported_drafts()
    assert widget.dimension_row_count() == 1
    assert widget.dimension_spin_for_draft(0).value() == pytest.approx(375)


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


def test_roof_plan_import_canvas_manual_zoom_can_pan_and_reset(qtbot, tmp_path):
    widget = RoofPlanImportWidget(_image_path(tmp_path), {}, None)
    qtbot.addWidget(widget)
    canvas = widget.canvas
    canvas.resize(520, 360)
    canvas.set_zoom_factor(2.0)
    before = canvas._image_target_rect()

    start = before.center().toPoint()
    end = (before.center() + QPointF(24, 18)).toPoint()
    QTest.mousePress(canvas, Qt.MouseButton.MiddleButton, Qt.KeyboardModifier.NoModifier, start)
    QTest.mouseMove(canvas, end)
    QTest.mouseRelease(
        canvas,
        Qt.MouseButton.MiddleButton,
        Qt.KeyboardModifier.NoModifier,
        end,
    )

    assert canvas._pan_offset != QPointF(0, 0)
    assert canvas._image_target_rect().topLeft() != before.topLeft()

    widget.fit_button.click()

    assert canvas._pan_offset == QPointF(0, 0)

    canvas.set_zoom_factor(2.0)
    before = canvas._image_target_rect()
    start = before.center().toPoint()
    end = (before.center() + QPointF(24, 18)).toPoint()
    QTest.mousePress(canvas, Qt.MouseButton.MiddleButton, Qt.KeyboardModifier.NoModifier, start)
    QTest.mouseMove(canvas, end)
    QTest.mouseRelease(
        canvas,
        Qt.MouseButton.MiddleButton,
        Qt.KeyboardModifier.NoModifier,
        end,
    )

    assert canvas._pan_offset != QPointF(0, 0)

    widget.zoom_100_button.click()

    assert canvas._pan_offset == QPointF(0, 0)
