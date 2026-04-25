from __future__ import annotations

import pytest

from core.geometry import build_rectangle_outline
from core.models import Material, Point2D, Polygon2D
from core.project_state import ProjectState

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QDialogButtonBox, QInputDialog, QMenu, QMessageBox
from PySide6.QtWidgets import QDialog
from PySide6.QtCore import QPointF

from mainwindow import MainWindow
from ui.dialogs.material_dialog import BlachyDialog


@pytest.fixture(autouse=True)
def _disable_mainwindow_disk_writes(monkeypatch):
    monkeypatch.setattr("ui.main_window.save_config", lambda *args, **kwargs: True)


@pytest.fixture(autouse=True)
def _default_question_response(monkeypatch):
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.Discard),
    )


def test_mainwindow_exposes_expected_ui_contract(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    actions = window.menuBar().actions()
    menu_titles = [action.text() for action in actions]
    sheets_menu = actions[-1].menu()
    assert isinstance(sheets_menu, QMenu)
    sheets_actions = [action.text() for action in sheets_menu.actions() if not action.isSeparator()]

    assert menu_titles == ["Plik", "Kształt", "Wycinki", "Katalog", "Arkusze"]
    assert window.workspace_tabs.count() >= 2
    assert window.variant_combo.count() >= 1
    assert window.variant_combo.currentText() == "PD510"
    assert window.project_state.available_material_ids() == ["PD510"]
    assert "Przelicz aktywną połać" in sheets_actions


def test_mainwindow_refreshes_active_plane_on_primary_canvas(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)

    plane = window.project_state.add_roof_plane(build_rectangle_outline(320, 180), selected_material_id="PD510")
    window._refresh_canvas_from_state()

    assert window.primary_canvas.roof_plane is not None
    assert window.primary_canvas.roof_plane.id == plane.id
    assert window.workspace_tabs.tabText(window.workspace_tabs.currentIndex()) == plane.name


def test_mainwindow_creates_plane_tabs_and_switches_active_plane(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)

    first_plane = window.project_state.add_roof_plane(build_rectangle_outline(320, 180), selected_material_id="PD510")
    second_plane = window.project_state.add_roof_plane(build_rectangle_outline(210, 140), selected_material_id="PD510")
    window._refresh_canvas_from_state()

    assert window.workspace_tabs.count() == 3
    assert window.workspace_tabs.tabText(0) == first_plane.name
    assert window.workspace_tabs.tabText(1) == second_plane.name
    assert window.workspace_tabs.tabText(2) == "Raport"
    assert window.project_state.active_plane_id == second_plane.id
    assert window.primary_canvas.roof_plane is not None
    assert window.primary_canvas.roof_plane.id == second_plane.id

    window.workspace_tabs.setCurrentIndex(0)

    assert window.project_state.active_plane_id == first_plane.id
    assert window.primary_canvas.roof_plane is not None
    assert window.primary_canvas.roof_plane.id == first_plane.id


def test_mainwindow_adds_renames_and_deletes_roof_plane_tabs(qtbot, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    window._refresh_canvas_from_state()

    base_count = len(window.project_state.roof_planes)
    window._add_new_roof_plane()

    assert len(window.project_state.roof_planes) == base_count + 1
    added_plane = window.project_state.active_roof_plane()
    assert added_plane is not None
    assert added_plane.outline is None
    assert window.workspace_tabs.tabText(window.workspace_tabs.currentIndex()) == f"{added_plane.name} *"

    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *args, **kwargs: ("Garaż", True)))
    window._rename_active_roof_plane()

    assert added_plane.name == "Garaż"
    assert window.workspace_tabs.tabText(window.workspace_tabs.currentIndex()) == "Garaż *"

    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.Yes),
    )
    window._delete_active_roof_plane()

    assert len(window.project_state.roof_planes) == base_count


def test_mainwindow_creates_rectangle_geometry_in_active_tab(qtbot, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    window._refresh_canvas_from_state()

    class FakeRectangleDialog:
        def __init__(self, config_data, parent=None) -> None:
            self._values = {"szerokosc": 420, "wysokosc": 260}

        def exec(self) -> int:
            return QDialog.DialogCode.Accepted

        def get_values(self) -> dict:
            return dict(self._values)

    monkeypatch.setattr("ui.main_window.ProstokatDialog", FakeRectangleDialog)

    window._dlg_prostokat()

    plane = window.project_state.active_roof_plane()
    assert plane is not None
    assert len(window.project_state.roof_planes) == 1
    assert plane.outline is not None
    assert plane.outline.points == build_rectangle_outline(420, 260).points
    assert window.primary_canvas.roof_plane is plane
    assert window.primary_canvas.roof_plane.outline is not None
    assert window.workspace_tabs.tabText(window.workspace_tabs.currentIndex()) == f"{plane.name} *"


def test_mainwindow_keeps_generated_shapes_separate_per_tab_and_persists_geometry(qtbot, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    window._refresh_canvas_from_state()

    rectangle_values = {"szerokosc": 300, "wysokosc": 200}
    trapezoid_values = {"typ": "prostokątny", "podstawa_dolna": 500, "podstawa_gorna": 300, "wysokosc": 240}

    class FakeRectangleDialog:
        def __init__(self, config_data, parent=None) -> None:
            pass

        def exec(self) -> int:
            return QDialog.DialogCode.Accepted

        def get_values(self) -> dict:
            return dict(rectangle_values)

    class FakeTrapezoidDialog:
        def __init__(self, config_data, parent=None) -> None:
            pass

        def exec(self) -> int:
            return QDialog.DialogCode.Accepted

        def get_values(self) -> dict:
            return dict(trapezoid_values)

    monkeypatch.setattr("ui.main_window.ProstokatDialog", FakeRectangleDialog)
    monkeypatch.setattr("ui.main_window.TrapezDialog", FakeTrapezoidDialog)

    window._dlg_prostokat()
    first_plane = window.project_state.active_roof_plane()
    assert first_plane is not None

    window._add_new_roof_plane()
    second_plane = window.project_state.active_roof_plane()
    assert second_plane is not None
    assert second_plane.id != first_plane.id

    window._dlg_trapez()

    assert first_plane.outline is not None
    assert first_plane.outline.points == build_rectangle_outline(300, 200).points
    assert second_plane.outline is not None
    assert second_plane.outline.points != first_plane.outline.points
    assert window._workspace.canvas_for_plane(first_plane.id).roof_plane.outline.points == first_plane.outline.points
    assert window._workspace.canvas_for_plane(second_plane.id).roof_plane.outline.points == second_plane.outline.points

    payload = {"blachy": [material.to_dict() for material in window.project_state.materials]}
    window.project_state.apply_to_config(payload)
    reloaded = ProjectState.from_config(payload)

    assert len(reloaded.roof_planes) == 2
    assert reloaded.roof_planes[0].outline is not None
    assert reloaded.roof_planes[0].outline.points == first_plane.outline.points
    assert reloaded.roof_planes[1].outline is not None
    assert reloaded.roof_planes[1].outline.points == second_plane.outline.points


def test_mainwindow_generates_project_report_for_all_roof_planes(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    window.project_state.add_roof_plane(build_rectangle_outline(320, 180), name="Front", selected_material_id="PD510")
    window.project_state.add_roof_plane(build_rectangle_outline(210, 140), name="Back", selected_material_id="PD510")
    window._refresh_canvas_from_state()

    assert window._gen_report("standard") is True
    assert "Raport projektu 4Dach" in window._latest_report_html
    assert "Front" in window._latest_report_html
    assert "Back" in window._latest_report_html
    assert "Zbiorcze zestawienie materiałów" in window._latest_report_html
    assert window._latest_report_plane_id is None
    assert window.workspace_tabs.currentIndex() == window._workspace.report_tab_index()


def test_mainwindow_commits_canvas_outline_edits_to_project_state(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    plane = window.project_state.add_roof_plane(build_rectangle_outline(320, 180), selected_material_id="PD510")
    window._refresh_canvas_from_state()

    updated_outline = Polygon2D(
        [
            Point2D(0, 0),
            Point2D(320, 0),
            Point2D(280, 210),
            Point2D(0, 180),
        ]
    )
    canvas = window._workspace.canvas_for_plane(plane.id)

    canvas.outline_edit_committed.emit(updated_outline)

    assert plane.outline == updated_outline
    assert plane.layout_dirty_reason is None
    assert len(plane.layout_bands) > 0


def test_mainwindow_rolls_back_invalid_canvas_outline_edit(qtbot, monkeypatch):
    messages: list[str] = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *args: messages.append(args[2])))

    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    plane = window.project_state.add_roof_plane(build_rectangle_outline(320, 180), selected_material_id="PD510")
    window.project_state.add_hole_to_plane(Polygon2D.rectangle(60, 60, origin_x=30, origin_y=40), plane.id)
    original_outline = plane.outline
    window._refresh_canvas_from_state()

    invalid_outline = Polygon2D(
        [
            Point2D(80, 0),
            Point2D(320, 0),
            Point2D(320, 180),
            Point2D(0, 180),
        ]
    )
    canvas = window._workspace.canvas_for_plane(plane.id)

    canvas.outline_edit_committed.emit(invalid_outline)

    assert plane.outline == original_outline
    assert messages
    assert "Wycinek musi leżeć w całości wewnątrz obrysu" in messages[-1]


def test_mainwindow_commits_canvas_cutout_edits_to_project_state(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    plane = window.project_state.add_roof_plane(build_rectangle_outline(320, 180), selected_material_id="PD510")
    window.project_state.add_hole_to_plane(Polygon2D.rectangle(60, 50, origin_x=40, origin_y=30), plane.id)
    window._refresh_canvas_from_state()

    updated_hole = Polygon2D.rectangle(80, 50, origin_x=40, origin_y=30)
    canvas = window._workspace.canvas_for_plane(plane.id)

    canvas.hole_edit_committed.emit(0, updated_hole)

    assert plane.holes[0] == updated_hole
    assert plane.layout_dirty_reason is None
    assert len(plane.layout_bands) > 0


def test_mainwindow_material_catalog_edit_updates_project_state_and_dependent_workspace(qtbot, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(
        materials=[
            Material(
                id="PD510",
                nazwa="PD510",
                type="dachówkowa",
                effective_width_cm=51,
                module_length_cm=25,
                bottom_margin_cm=10,
                top_margin_cm=80,
                min_sheet_length_cm=20,
            ),
            Material(
                id="T20",
                nazwa="T20",
                type="trapezowa",
                effective_width_cm=110,
                module_length_cm=0,
                bottom_margin_cm=0,
                top_margin_cm=0,
                min_sheet_length_cm=20,
            ),
        ]
    )
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    dependent_plane = window.project_state.add_roof_plane(build_rectangle_outline(320, 180), selected_material_id="PD510")
    other_plane = window.project_state.add_roof_plane(build_rectangle_outline(210, 140), selected_material_id="T20")
    window.project_state.generate_layout_for_plane(dependent_plane.id)
    window.project_state.generate_layout_for_plane(other_plane.id)
    window.project_state.set_active_plane(dependent_plane.id)
    window._refresh_canvas_from_state()

    updated_materials = [
        Material(
            id="PD510",
            nazwa="PD510 Plus",
            type="dachówkowa",
            effective_width_cm=53,
            module_length_cm=30,
            bottom_margin_cm=12,
            top_margin_cm=82,
            min_sheet_length_cm=25,
        ),
        window.project_state.material_by_id("T20"),
    ]

    class FakeMaterialsDialog:
        def __init__(self, materials, parent=None) -> None:
            self._materials = materials

        def exec(self) -> int:
            return QDialog.DialogCode.Accepted

        def get_values(self):
            return list(updated_materials)

    monkeypatch.setattr("ui.main_window.BlachyDialog", FakeMaterialsDialog)

    window._dlg_blachy()

    active_canvas = window._workspace.canvas_for_plane(dependent_plane.id)
    assert window.project_state.material_by_id("PD510").nazwa == "PD510 Plus"
    assert dependent_plane.layout_dirty_reason is None
    assert other_plane.layout_dirty_reason is None
    assert active_canvas is not None
    assert active_canvas._material is not None
    assert active_canvas._material.id == "PD510"
    assert active_canvas._material.module_length_cm == 30


def test_mainwindow_connects_initial_canvas_edit_signals_on_startup(qtbot, monkeypatch):
    config = {
        "company_data": {"name": "Test"},
        "blachy": [
            {
                "id": "PD510",
                "nazwa": "PD510",
                "type": "dachówkowa",
                "effective_width_cm": 51,
                "module_length_cm": 25,
                "bottom_margin_cm": 10,
                "top_margin_cm": 80,
                "min_sheet_length_cm": 20,
            }
        ],
        "project_state": {
            "active_plane_id": "plane-1",
            "roof_planes": [
                {
                    "id": "plane-1",
                    "name": "Front",
                    "selected_material_id": "PD510",
                    "generation_settings": {"layout_origin": "left", "base_line_y_cm": 180},
                    "auto_sheet_placements": [],
                    "layout_bands": [],
                    "manual_sheet_placements": [],
                    "manually_removed_auto_sheet_ids": [],
                    "layout_revision": 0,
                    "layout_dirty_reason": None,
                    "outline": [
                        {"x": 0, "y": 0},
                        {"x": 320, "y": 0},
                        {"x": 320, "y": 180},
                        {"x": 0, "y": 180},
                    ],
                    "holes": [],
                }
            ],
        },
    }
    monkeypatch.setattr("ui.main_window.load_config", lambda: config)

    window = MainWindow()
    qtbot.addWidget(window)

    canvas = window._workspace.canvas_for_plane("plane-1")
    updated_outline = Polygon2D(
        [
            Point2D(0, 0),
            Point2D(320, 0),
            Point2D(300, 180),
            Point2D(0, 180),
        ]
    )

    assert canvas is not None

    canvas.outline_edit_committed.emit(updated_outline)

    assert window.project_state.roof_plane_by_id("plane-1").outline == updated_outline


def test_mainwindow_freehand_outline_uses_canvas_mapper_instead_of_raw_pixels(qtbot):
    first = MainWindow()
    qtbot.addWidget(first)
    first_canvas = first._workspace.primary_canvas
    first_canvas.resize(640, 420)
    first_canvas.polygon_closed.connect(first._on_polygon_closed)
    first._on_polygon_closed(
        [
            QPointF(110, 80),
            QPointF(530, 80),
            QPointF(530, 340),
            QPointF(110, 340),
        ]
    )

    second = MainWindow()
    qtbot.addWidget(second)
    second_canvas = second._workspace.primary_canvas
    second_canvas.resize(960, 630)
    second_canvas.polygon_closed.connect(second._on_polygon_closed)
    second._on_polygon_closed(
        [
            QPointF(165, 120),
            QPointF(795, 120),
            QPointF(795, 510),
            QPointF(165, 510),
        ]
    )

    first_outline = first.project_state.active_roof_plane().outline
    second_outline = second.project_state.active_roof_plane().outline

    assert first_outline is not None
    assert second_outline is not None
    assert first_outline.points == second_outline.points


def test_mainwindow_open_project_resets_cached_report_and_company_title(qtbot, monkeypatch):
    initial_config = {
        "company_data": {"name": "Firma A"},
        "blachy": [
            {
                "id": "PD510",
                "nazwa": "PD510",
                "type": "dachówkowa",
                "effective_width_cm": 51,
                "module_length_cm": 25,
                "bottom_margin_cm": 10,
                "top_margin_cm": 80,
                "min_sheet_length_cm": 20,
            }
        ],
    }
    reopened_config = {
        "company_data": {"name": "Firma B"},
        "blachy": initial_config["blachy"],
    }
    loads = iter([initial_config, reopened_config])
    monkeypatch.setattr("ui.main_window.load_config", lambda: next(loads))

    window = MainWindow()
    qtbot.addWidget(window)
    window._latest_report_html = "<html>stary raport</html>"
    window._latest_report_plane_id = "plane-123"

    window._open_project()

    assert window._latest_report_html == ""
    assert window._latest_report_plane_id is None
    assert window.windowTitle() == "4Dach — Firma B"


def test_mainwindow_marks_project_dirty_until_explicit_save(qtbot, monkeypatch):
    saved_payloads: list[dict] = []

    def _save_config(config_data, parent=None):
        saved_payloads.append(config_data)
        return True

    monkeypatch.setattr("ui.main_window.save_config", _save_config)

    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    plane = window.project_state.add_roof_plane(build_rectangle_outline(320, 180), selected_material_id="PD510")
    window._mark_saved_state()
    window._refresh_canvas_from_state()

    updated_outline = Polygon2D(
        [
            Point2D(0, 0),
            Point2D(320, 0),
            Point2D(300, 200),
            Point2D(0, 180),
        ]
    )
    canvas = window._workspace.canvas_for_plane(plane.id)

    assert canvas is not None
    assert window._has_unsaved_changes is False

    canvas.outline_edit_committed.emit(updated_outline)

    assert window._has_unsaved_changes is True
    assert window._plane_has_unsaved_changes(plane.id) is True
    assert saved_payloads == []

    assert window._save_project() is True

    assert window._has_unsaved_changes is False
    assert window._plane_has_unsaved_changes(plane.id) is False
    assert saved_payloads


def test_mainwindow_unsaved_close_confirmation_can_cancel_or_discard(qtbot, monkeypatch):
    responses = iter(
        [
            QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Discard,
        ]
    )
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *args, **kwargs: next(responses)))

    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    plane = window.project_state.add_roof_plane(build_rectangle_outline(320, 180), selected_material_id="PD510")
    window._mark_saved_state()
    window._refresh_canvas_from_state()

    canvas = window._workspace.canvas_for_plane(plane.id)
    assert canvas is not None

    canvas.outline_edit_committed.emit(
        Polygon2D(
            [
                Point2D(0, 0),
                Point2D(320, 0),
                Point2D(290, 190),
                Point2D(0, 180),
            ]
        )
    )
    assert window._has_unsaved_changes is True

    assert window._confirm_discard_unsaved_changes(context="zamknięciem programu") is False
    assert window._confirm_discard_unsaved_changes(context="zamknięciem programu") is True
    window._mark_saved_state()


def test_mainwindow_undo_redo_restores_outline_and_material(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(
        materials=[
            Material(
                id="PD510",
                nazwa="PD510",
                type="dachówkowa",
                effective_width_cm=51,
                module_length_cm=25,
                bottom_margin_cm=10,
                top_margin_cm=80,
                min_sheet_length_cm=20,
            ),
            Material(
                id="T20",
                nazwa="T20",
                type="trapezowa",
                effective_width_cm=110,
                module_length_cm=0,
                bottom_margin_cm=0,
                top_margin_cm=0,
                min_sheet_length_cm=20,
            ),
        ]
    )
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    plane = window.project_state.add_roof_plane(build_rectangle_outline(320, 180), selected_material_id="PD510")
    plane_id = plane.id
    original_outline = plane.outline
    window._mark_saved_state()
    window._refresh_canvas_from_state()

    canvas = window._workspace.canvas_for_plane(plane.id)
    updated_outline = Polygon2D(
        [
            Point2D(0, 0),
            Point2D(320, 0),
            Point2D(280, 210),
            Point2D(0, 180),
        ]
    )
    assert canvas is not None

    canvas.outline_edit_committed.emit(updated_outline)
    window._on_material_changed("T20")

    current_plane = window.project_state.roof_plane_by_id(plane_id)
    assert current_plane.outline == updated_outline
    assert current_plane.selected_material_id == "T20"

    window._undo()
    current_plane = window.project_state.roof_plane_by_id(plane_id)
    assert current_plane.selected_material_id == "PD510"
    assert current_plane.outline == updated_outline

    window._undo()
    current_plane = window.project_state.roof_plane_by_id(plane_id)
    assert current_plane.outline == original_outline

    window._redo()
    current_plane = window.project_state.roof_plane_by_id(plane_id)
    assert current_plane.outline == updated_outline

    window._redo()
    current_plane = window.project_state.roof_plane_by_id(plane_id)
    assert current_plane.selected_material_id == "T20"


def test_mainwindow_report_generation_recalculates_only_dirty_planes(qtbot, monkeypatch):
    recalculated: list[str] = []
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.Yes),
    )

    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    first_plane = window.project_state.add_roof_plane(build_rectangle_outline(320, 180), name="Front", selected_material_id="PD510")
    second_plane = window.project_state.add_roof_plane(build_rectangle_outline(210, 140), name="Back", selected_material_id="PD510")
    first_plane.layout_dirty_reason = "geometry_changed"
    second_plane.layout_dirty_reason = None
    window._refresh_canvas_from_state()

    def _generate_layout_for_plane(plane_id):
        recalculated.append(plane_id)
        plane = window.project_state.roof_plane_by_id(plane_id)
        plane.layout_dirty_reason = None
        return object()

    monkeypatch.setattr(ProjectState, "generate_layout_for_plane", lambda self, plane_id: _generate_layout_for_plane(plane_id))
    monkeypatch.setattr("ui.main_window.build_project_report", lambda state: object())
    monkeypatch.setattr("ui.main_window.build_project_report_html", lambda *args, **kwargs: "<html>ok</html>")

    assert window._gen_report("standard") is True
    assert recalculated == [first_plane.id]


def test_blachy_dialog_exposes_save_button(qtbot):
    dialog = BlachyDialog([], None)
    qtbot.addWidget(dialog)

    button_box = dialog.findChild(QDialogButtonBox)
    assert button_box is not None
    assert button_box.standardButtons() & QDialogButtonBox.StandardButton.Save


def test_mainwindow_triangle_dialog_shows_validation_error_without_mutating_state(qtbot, monkeypatch):
    messages: list[str] = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *args: messages.append(args[2])))

    window = MainWindow()
    qtbot.addWidget(window)
    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    window._refresh_canvas_from_state()

    class FakeTriangleDialog:
        def __init__(self, config_data, parent=None) -> None:
            pass

        def exec(self) -> int:
            return QDialog.DialogCode.Accepted

        def get_values(self) -> dict:
            return {
                "typ": "dowolny",
                "podstawa": 300,
                "wysokosc": 180,
                "ramie_enabled": True,
                "ramie": 100,
            }

    monkeypatch.setattr("ui.main_window.TrojkatDialog", FakeTriangleDialog)

    window._dlg_trojkat()

    assert not window.project_state.roof_planes
    assert messages
