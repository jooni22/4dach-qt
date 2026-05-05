from __future__ import annotations

import copy

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QScrollArea, QSlider, QToolButton

from ui.dialogs.add_polac_catalog import SHAPE_CATALOG, SHAPE_ORDER
from ui.dialogs.add_polac_dialog import AddPolacDialog, _PolygonPreviewWidget


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
        },
    }


def test_add_polac_dialog_exposes_full_catalog_and_legacy_seed(qtbot):
    dialog = AddPolacDialog(_legacy_shape_config())
    qtbot.addWidget(dialog)

    assert tuple(dialog.shape_buttons) == (
        "prostokat",
        "trojkat",
        "trapez_row",
        "trapez_prl",
        "trapez_l",
        "trapez6",
        "trapez7",
        "pieciokat",
        "pieciokat2",
    )
    assert [button.text() for button in dialog.shape_buttons.values()] == [
        "Prostokąt",
        "Trójkąt",
        "Trapez\nrównoram.",
        "Równoległobok\nprawy",
        "Równoległobok\nlewy",
        "Trapez\nprawy",
        "Trapez\nlewy",
        "Pięciokąt",
        "Sześciokąt",
    ]
    assert "Połać 10" not in {button.text() for button in dialog.shape_buttons.values()}
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


def test_add_polac_catalog_uses_user_dimension_labels_without_extra_shapes():
    assert SHAPE_ORDER == (
        "prostokat",
        "trojkat",
        "trapez_row",
        "trapez_prl",
        "trapez_l",
        "trapez6",
        "trapez7",
        "pieciokat",
        "pieciokat2",
    )
    assert [shape.label for shape in SHAPE_CATALOG] == [
        "Prostokąt",
        "Trójkąt",
        "Trapez\nrównoram.",
        "Równoległobok\nprawy",
        "Równoległobok\nlewy",
        "Trapez\nprawy",
        "Trapez\nlewy",
        "Pięciokąt",
        "Sześciokąt",
    ]

    labels_by_key = {
        shape.key: tuple(field.label for field in shape.fields) for shape in SHAPE_CATALOG
    }
    assert labels_by_key["prostokat"] == ("A - szerokość:", "H - wysokość:")
    assert labels_by_key["trojkat"] == ("A - podstawa:", "H - wysokość:")
    assert labels_by_key["trapez_row"] == (
        "A - podstawa dolna:",
        "B - podstawa górna:",
        "H - wysokość:",
    )
    assert labels_by_key["trapez_prl"] == (
        "A - podstawa:",
        "E - przesunięcie:",
        "H - wysokość:",
    )
    assert labels_by_key["trapez_l"] == (
        "A - podstawa:",
        "E - przesunięcie:",
        "H - wysokość:",
    )
    assert labels_by_key["trapez6"] == (
        "A - podstawa dolna:",
        "B - podstawa górna:",
        "H - wysokość:",
    )
    assert labels_by_key["trapez7"] == (
        "A - podstawa dolna:",
        "B - podstawa górna:",
        "H - wysokość:",
    )
    assert labels_by_key["pieciokat"] == ("A - szerokość:", "H - wysokość:")
    assert labels_by_key["pieciokat2"] == ("A - szerokość:", "H - wysokość:")


def test_add_polac_dialog_rebuilds_representative_shape_and_cutout_forms(qtbot):
    dialog = AddPolacDialog(_legacy_shape_config())
    qtbot.addWidget(dialog)

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
    assert dialog.cutout_form_fields["H1"].value() == 60
    assert dialog.cutout_form_fields["H"].value() == 60


def test_add_polac_dialog_places_parameters_below_preview_and_keeps_library_scroll_space(
    qtbot,
):
    dialog = AddPolacDialog(_legacy_shape_config())
    qtbot.addWidget(dialog)

    shape_layout = dialog.shape_step.layout()
    shape_workspace = shape_layout.itemAt(1).layout()

    assert isinstance(dialog.shape_library_scroll, QScrollArea)
    assert dialog.shape_library_scroll.widgetResizable() is True
    assert dialog.shape_library_scroll.widget().layout().contentsMargins().right() == 18
    assert shape_workspace.itemAt(0).layout().itemAt(1).widget() is dialog.shape_preview
    assert shape_workspace.itemAt(1).widget() is dialog.shape_parameters_panel
    assert dialog.shape_form_host.parent() is dialog.shape_parameters_panel
    assert any(
        group.title() == "Narzędzia"
        for group in dialog.shape_parameters_panel.findChildren(QGroupBox)
    )
    assert _PolygonPreviewWidget.PREVIEW_MARGIN == 32.0

    qtbot.mouseClick(dialog.next_button, Qt.MouseButton.LeftButton)

    cutout_layout = dialog.cutout_step.layout()
    cutout_workspace = cutout_layout.itemAt(1).layout()

    assert isinstance(dialog.cutout_library_scroll, QScrollArea)
    assert dialog.cutout_library_scroll.widgetResizable() is True
    assert dialog.cutout_library_scroll.widget().layout().contentsMargins().right() == 18
    assert cutout_workspace.itemAt(0).layout().itemAt(1).widget() is dialog.cutout_preview
    assert cutout_workspace.itemAt(1).widget() is dialog.cutout_parameters_panel
    assert dialog.cutout_form_host.parent() is dialog.cutout_parameters_panel


def test_add_polac_dialog_cutout_position_sliders_update_preview_geometry(qtbot):
    dialog = AddPolacDialog(_legacy_shape_config())
    qtbot.addWidget(dialog)

    qtbot.mouseClick(dialog.next_button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(dialog.cutout_buttons["lukarna1"], Qt.MouseButton.LeftButton)

    assert set(dialog.cutout_form_fields) == {"A", "H1"}
    assert set(dialog.cutout_position_sliders) == {"X", "Y"}
    assert isinstance(dialog.cutout_position_sliders["X"], QSlider)
    assert isinstance(dialog.cutout_position_sliders["Y"], QSlider)
    assert dialog.cutout_position_sliders["X"].value() == 50
    assert dialog.cutout_position_sliders["Y"].value() == 50

    dialog.cutout_position_sliders["X"].setValue(25)
    dialog.cutout_position_sliders["Y"].setValue(75)

    cutout = dialog._current_cutout()

    assert cutout is not None
    assert cutout.points[0].x == pytest.approx(82.5)
    assert cutout.points[0].y == pytest.approx(112.5)


def test_add_polac_dialog_hydrates_from_add_polac_dialog_cache(qtbot):
    dialog = AddPolacDialog(_dialog_cache_config())
    qtbot.addWidget(dialog)

    assert dialog.selected_shape_key == "trapez_prl"
    assert isinstance(dialog.flip_h_button, QToolButton)
    assert isinstance(dialog.flip_v_button, QToolButton)
    assert dialog.flip_h_button.isCheckable() is True
    assert dialog.flip_v_button.isCheckable() is True
    assert dialog.flip_h_button.text() == "Odbij poziomo"
    assert dialog.flip_v_button.text() == "Odbij pionowo"
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
    dialog.accept()

    result = dialog.get_result()

    assert result is not None
    assert result.shape_key == "pieciokat2"
    assert result.shape_values == {"A": 640, "B": 280}
    assert result.cutout_kind == "lukarna3"
    assert result.cutout_values == {"A": 140, "H1": 50, "H": 90, "X": 50, "Y": 50}
    assert result.flip_h is True
    assert result.flip_v is True

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
            "lukarna1": {"A": 80, "H1": 60, "X": 50, "Y": 50},
            "lukarna2": {"A": 80, "H": 60, "X": 50, "Y": 50},
            "lukarna3": {"A": 140, "H1": 50, "H": 90, "X": 50, "Y": 50},
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
