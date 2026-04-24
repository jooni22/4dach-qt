from __future__ import annotations

import pytest

from core.geometry import build_rectangle_outline
from core.project_state import ProjectState

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QInputDialog, QMenu, QMessageBox

from mainwindow import MainWindow


def test_mainwindow_exposes_expected_ui_contract(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    menu_titles = [action.text() for action in window.menuBar().actions()]
    sheets_menu = window.menuBar().actions()[-1].menu()
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
