from __future__ import annotations

import pytest

from core.geometry import build_rectangle_outline
from core.models import Point2D, Polygon2D
from core.project_state import ProjectState

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QInputDialog, QMenu, QMessageBox
from PySide6.QtWidgets import QDialog

from mainwindow import MainWindow


@pytest.fixture(autouse=True)
def _disable_mainwindow_disk_writes(monkeypatch):
    monkeypatch.setattr("ui.main_window.save_config", lambda *args, **kwargs: True)


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
    assert window.workspace_tabs.tabText(window.workspace_tabs.currentIndex()) == added_plane.name

    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *args, **kwargs: ("Garaż", True)))
    window._rename_active_roof_plane()

    assert added_plane.name == "Garaż"
    assert window.workspace_tabs.tabText(window.workspace_tabs.currentIndex()) == "Garaż"

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
    assert window.workspace_tabs.tabText(window.workspace_tabs.currentIndex()) == plane.name


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
    assert plane.layout_dirty_reason == "geometry_changed"


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
