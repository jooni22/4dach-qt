from __future__ import annotations

import pytest

from core.geometry import build_rectangle_outline

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QMenu

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
    assert window.workspace_tabs.count() == 2
    assert window.variant_combo.count() >= 1
    assert window.variant_combo.currentText() == "PD510"
    assert window.project_state.available_material_ids() == ["PD510"]
    assert "Przelicz aktywną połać" in sheets_actions


def test_mainwindow_refreshes_active_plane_on_primary_canvas(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    plane = window.project_state.add_roof_plane(build_rectangle_outline(320, 180), selected_material_id="PD510")
    window._refresh_canvas_from_state()

    assert window.primary_canvas.roof_plane is not None
    assert window.primary_canvas.roof_plane.id == plane.id
    assert window.workspace_tabs.tabText(0) == plane.name
    assert window.secondary_canvas.roof_plane is None


def test_mainwindow_creates_plane_tabs_and_switches_active_plane(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

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
