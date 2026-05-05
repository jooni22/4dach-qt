from __future__ import annotations

import copy

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QToolButton

from core.geometry import validate_hole_polygon
from core.models import Point2D
from ui.dialogs.add_polac_dialog import AddPolacDialog


def _legacy_shape_config() -> dict:
    return {
        "ksztalty": {
            "prostokat": {"szerokosc": 410, "wysokosc": 210},
            "trojkat": {
                "typ": "dowolny",
                "podstawa": 365,
                "wysokosc": 220,
                "ramie": 280,
                "ramie_enabled": True,
            },
            "trapez": {
                "typ": "prostokątny",
                "podstawa_dolna": 520,
                "podstawa_gorna": 340,
                "wysokosc": 260,
            },
        }
    }


def _dialog_cache_config() -> dict:
    return {
        "ksztalty": _legacy_shape_config()["ksztalty"],
        "add_polac_dialog": {
            "last_shape": "trapez_prl",
            "last_cutout": "lukarna3",
            "flip_h": True,
            "flip_v": False,
            "shapes": {
                "prostokat": {"A": 410, "B": 210},
                "trojkat": {"A": 365, "B": 220},
                "trapez_row": {"A": 520, "B": 260, "C": 340},
                "trapez_prl": {"A": 640, "B": 280, "C": 260},
                "trapez_l": {"A": 610, "B": 240, "C": 310},
                "trapez6": {"A": 580, "B": 250, "C": 290},
                "trapez7": {"A": 530, "B": 230, "C": 300},
                "pieciokat": {"A": 720, "B": 320},
                "pieciokat2": {"A": 700, "B": 330},
            },
            "cutouts": {
                "lukarna1": {"A": 90, "H1": 55},
                "lukarna2": {"A": 120, "H": 70},
                "lukarna3": {"A": 160, "H1": 45, "H": 110},
            },
            "cutout_positions": {
                "lukarna1": {"x": 0.5, "y": 0.5},
                "lukarna2": {"x": 0.62, "y": 0.38},
                "lukarna3": {"x": 0.32, "y": 0.43},
            },
        },
    }


def test_add_polac_dialog_exposes_full_catalog_and_legacy_seed(qtbot):
    dialog = AddPolacDialog(_legacy_shape_config())
    qtbot.addWidget(dialog)

    assert dialog.shape_buttons["prostokat"].text() == "Prostokąt"
    assert dialog.shape_buttons["trapez_prl"].text() == "Trapez prawy"
    assert dialog.shape_preview.minimumHeight() >= 300
    assert isinstance(dialog.flip_h_button, QToolButton)
    assert dialog.flip_h_button.isCheckable() is True
    assert isinstance(dialog.flip_v_button, QToolButton)
    assert dialog.flip_v_button.isCheckable() is True

    assert set(dialog.shape_buttons) == {
        "prostokat",
        "trojkat",
        "trapez_row",
        "trapez_prl",
        "trapez_l",
        "trapez6",
        "trapez7",
        "pieciokat",
        "pieciokat2",
    }
    assert dialog.selected_shape_key == "prostokat"
    assert set(dialog.shape_form_fields) == {"A", "B"}
    assert dialog.shape_form_fields["A"].value() == 410
    assert dialog.shape_form_fields["B"].value() == 210

    qtbot.mouseClick(dialog.shape_buttons["trojkat"], Qt.MouseButton.LeftButton)
    assert dialog.shape_form_fields["A"].value() == 365
    assert dialog.shape_form_fields["B"].value() == 220

    qtbot.mouseClick(dialog.shape_buttons["trapez_row"], Qt.MouseButton.LeftButton)
    assert set(dialog.shape_form_fields) == {"A", "B", "C"}
    assert dialog.shape_form_fields["A"].value() == 520
    assert dialog.shape_form_fields["B"].value() == 260
    assert dialog.shape_form_fields["C"].value() == 340

    qtbot.mouseClick(dialog.next_button, Qt.MouseButton.LeftButton)
    assert dialog.step_stack.currentWidget() is dialog.cutout_step
    assert set(dialog.cutout_buttons) == {"none", "lukarna1", "lukarna2", "lukarna3"}


def test_add_polac_dialog_rebuilds_representative_shape_and_cutout_forms(qtbot):
    dialog = AddPolacDialog(_legacy_shape_config())
    qtbot.addWidget(dialog)
    dialog.show()

    qtbot.mouseClick(dialog.shape_buttons["trapez_prl"], Qt.MouseButton.LeftButton)
    assert set(dialog.shape_form_fields) == {"A", "B", "C"}
    assert dialog.shape_form_fields["A"].value() == 800
    assert dialog.shape_form_fields["B"].value() == 300
    assert dialog.shape_form_fields["C"].value() == 500

    qtbot.mouseClick(dialog.shape_buttons["trapez6"], Qt.MouseButton.LeftButton)
    assert set(dialog.shape_form_fields) == {"A", "B", "C"}
    assert dialog.shape_form_fields["A"].value() == 800
    assert dialog.shape_form_fields["B"].value() == 300
    assert dialog.shape_form_fields["C"].value() == 500

    qtbot.mouseClick(dialog.shape_buttons["pieciokat2"], Qt.MouseButton.LeftButton)
    assert set(dialog.shape_form_fields) == {"A", "B"}
    assert dialog.shape_form_fields["A"].value() == 800
    assert dialog.shape_form_fields["B"].value() == 300

    qtbot.mouseClick(dialog.next_button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(dialog.cutout_buttons["lukarna3"], Qt.MouseButton.LeftButton)
    assert dialog.selected_cutout_kind == "lukarna3"
    assert set(dialog.cutout_form_fields) == {"A", "H1", "H"}
    assert dialog.cutout_form_fields["A"].value() == 80
    assert dialog.cutout_form_fields["H1"].value() < dialog.cutout_form_fields["H"].value()
    assert dialog.cutout_form_fields["H"].value() == 60


def test_add_polac_dialog_hydrates_from_add_polac_dialog_cache(qtbot):
    dialog = AddPolacDialog(_dialog_cache_config())
    qtbot.addWidget(dialog)

    assert dialog.selected_shape_key == "trapez_prl"
    assert dialog.flip_h_button.isChecked() is True
    assert dialog.flip_v_button.isChecked() is False
    assert dialog.shape_form_fields["A"].value() == 640
    assert dialog.shape_form_fields["B"].value() == 280
    assert dialog.shape_form_fields["C"].value() == 260

    qtbot.mouseClick(dialog.next_button, Qt.MouseButton.LeftButton)

    assert dialog.selected_cutout_kind == "lukarna3"
    assert dialog.cutout_form_fields["A"].value() == 160
    assert dialog.cutout_form_fields["H1"].value() == 45
    assert dialog.cutout_form_fields["H"].value() == 110
    assert dialog._cutout_positions["lukarna3"] == {"x": pytest.approx(0.32), "y": pytest.approx(0.43)}


def test_add_polac_dialog_links_field_focus_to_preview_badge_and_blocks_invalid_shape_values(qtbot):
    dialog = AddPolacDialog(_legacy_shape_config())
    qtbot.addWidget(dialog)
    dialog.show()

    qtbot.mouseClick(dialog.shape_buttons["trapez_row"], Qt.MouseButton.LeftButton)
    qtbot.mouseClick(dialog.shape_form_fields["C"], Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: dialog.shape_preview.active_dimension_key == "C")

    previous_points = [(point.x, point.y) for point in dialog.shape_preview.outline_polygon.points]
    dialog.shape_form_fields["A"].setValue(300)

    assert dialog.shape_form_fields["A"].value() == 300
    assert "Podstawa górna" in dialog.shape_validation_label.text()
    assert dialog.next_button.isEnabled() is False
    assert [(point.x, point.y) for point in dialog.shape_preview.outline_polygon.points] == previous_points


def test_add_polac_dialog_dragging_cutout_clamps_and_persists_position(qtbot):
    dialog = AddPolacDialog(_legacy_shape_config())
    qtbot.addWidget(dialog)
    dialog.show()

    dialog.shape_form_fields["A"].setValue(420)
    dialog.shape_form_fields["B"].setValue(260)
    qtbot.mouseClick(dialog.next_button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(dialog.cutout_buttons["lukarna1"], Qt.MouseButton.LeftButton)

    cutout = dialog._current_cutout()
    assert cutout is not None
    center = cutout.bounds()
    start = dialog.cutout_preview.domain_to_view(
        Point2D(center.min_x + center.width / 2.0, center.min_y + center.height / 2.0)
    ).toPoint()
    target = QPoint(dialog.cutout_preview.width() - 12, dialog.cutout_preview.height() - 12)

    qtbot.mousePress(dialog.cutout_preview, Qt.MouseButton.LeftButton, pos=start)
    qtbot.mouseMove(dialog.cutout_preview, target)
    qtbot.mouseRelease(dialog.cutout_preview, Qt.MouseButton.LeftButton, pos=target)

    position = dialog._cutout_positions["lukarna1"]
    preview_cutout = dialog.cutout_preview.cutout_polygon

    assert position["x"] > 0.5
    assert position["y"] > 0.5
    assert preview_cutout is not None
    assert validate_hole_polygon(dialog.cutout_preview.outline_polygon, preview_cutout) == []


def test_add_polac_dialog_accept_updates_cache_and_result(qtbot):
    config = _legacy_shape_config()
    dialog = AddPolacDialog(config)
    qtbot.addWidget(dialog)

    qtbot.mouseClick(dialog.shape_buttons["pieciokat2"], Qt.MouseButton.LeftButton)
    dialog.shape_form_fields["A"].setValue(640)
    dialog.shape_form_fields["B"].setValue(280)
    dialog.flip_h_button.setChecked(True)
    dialog.flip_v_button.setChecked(True)

    qtbot.mouseClick(dialog.next_button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(dialog.cutout_buttons["lukarna3"], Qt.MouseButton.LeftButton)
    dialog.cutout_form_fields["A"].setValue(140)
    dialog.cutout_form_fields["H1"].setValue(50)
    dialog.cutout_form_fields["H"].setValue(90)
    dialog._cutout_positions["lukarna3"] = {"x": 0.73, "y": 0.41}
    dialog._refresh_cutout_preview()
    dialog.accept()

    result = dialog.get_result()

    assert result is not None
    assert result.shape_key == "pieciokat2"
    assert result.shape_values == {"A": 640, "B": 280}
    assert result.cutout_kind == "lukarna3"
    assert result.cutout_values == {"A": 140, "H1": 50, "H": 90}
    assert result.flip_h is True
    assert result.flip_v is True
    assert result.cutout_position == {"x": pytest.approx(0.73), "y": pytest.approx(0.41)}

    assert config["add_polac_dialog"] == {
        "last_shape": "pieciokat2",
        "last_cutout": "lukarna3",
        "flip_h": True,
        "flip_v": True,
        "shapes": {
            "prostokat": {"A": 410, "B": 210},
            "trojkat": {"A": 365, "B": 220},
            "trapez_row": {"A": 520, "B": 260, "C": 340},
            "trapez_prl": {"A": 800, "B": 300, "C": 500},
            "trapez_l": {"A": 800, "B": 300, "C": 500},
            "trapez6": {"A": 800, "B": 300, "C": 500},
            "trapez7": {"A": 800, "B": 300, "C": 500},
            "pieciokat": {"A": 800, "B": 300},
            "pieciokat2": {"A": 640, "B": 280},
        },
        "cutouts": {
            "lukarna1": {"A": 80, "H1": 60},
            "lukarna2": {"A": 80, "H": 60},
            "lukarna3": {"A": 140, "H1": 50, "H": 90},
        },
        "cutout_positions": {
            "lukarna1": {"x": 0.5, "y": 0.5},
            "lukarna2": {"x": 0.5, "y": 0.5},
            "lukarna3": {"x": 0.73, "y": 0.41},
        },
    }
    assert config["ksztalty"] == _legacy_shape_config()["ksztalty"]


def test_add_polac_dialog_cancel_does_not_update_cache(qtbot):
    config = _legacy_shape_config()
    original = copy.deepcopy(config)
    dialog = AddPolacDialog(config)
    qtbot.addWidget(dialog)

    qtbot.mouseClick(dialog.shape_buttons["trapez_prl"], Qt.MouseButton.LeftButton)
    dialog.shape_form_fields["A"].setValue(999)
    qtbot.mouseClick(dialog.next_button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(dialog.cutout_buttons["lukarna2"], Qt.MouseButton.LeftButton)
    dialog.cutout_form_fields["A"].setValue(123)
    dialog.reject()

    assert dialog.get_result() is None
    assert config == original
