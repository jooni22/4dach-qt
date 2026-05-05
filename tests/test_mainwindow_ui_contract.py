from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from core.app_settings import AppSettings
from core.geometry import build_rectangle_outline
from core.models import Material, Point2D, Polygon2D
from core.project_state import ProjectState

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
)

from mainwindow import MainWindow
from ui.dialogs.material_dialog import BlachyDialog, DaneBlachyDialog
from ui.dialogs.settings_dialog import SettingsDialog
from ui.drawing_canvas import CommittedOutlineEdit


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
    shape_menu = actions[1].menu()
    cutout_menu = actions[2].menu()
    sheets_menu = actions[4].menu()  # "Arkusze" is at index 4, "Ustawienia" is at index 5
    assert isinstance(shape_menu, QMenu)
    assert isinstance(cutout_menu, QMenu)
    assert isinstance(sheets_menu, QMenu)
    shape_actions = [action.text() for action in shape_menu.actions() if not action.isSeparator()]
    cutout_actions = [action.text() for action in cutout_menu.actions() if not action.isSeparator()]
    sheets_actions = [action.text() for action in sheets_menu.actions() if not action.isSeparator()]

    assert menu_titles == ["Plik", "Kształt", "Wycinki", "Katalog", "Arkusze", "Ustawienia"]
    assert shape_actions == ["Kreator połaci...", "Dowolny"]
    assert cutout_actions == ["Dodaj prostokątny wycinek...", "Rysuj wycinek"]
    assert window.workspace_tabs.count() >= 2
    assert window.variant_combo.count() >= 1
    assert window.variant_combo.currentText() == "PD510"
    assert window.project_state.available_material_ids() == ["PD510"]
    assert "Przelicz aktywną połać" in sheets_actions
    file_actions = [action.text() for action in actions[0].menu().actions() if not action.isSeparator()]
    assert file_actions[:4] == ["Nowy projekt", "Wczytaj projekt...", "Zapisz", "Zapisz jako..."]
    assert "Drukuj raport" in file_actions
    assert "Drukuj raport ciągły" not in file_actions
    assert "Drukuj raport skrócony" not in file_actions
    assert window._tb_ctrl.action_new_surface.text() == "Nowa połać"
    assert window._tb_ctrl.action_duplicate_surface.text() == "Duplikuj połać"
    assert window._tb_ctrl.action_overlay_sheet.isCheckable() is True
    assert window._tb_ctrl.action_overlay_sheet.isChecked() is False
    assert window._mode_label.text() == "Mode: IDLE"


def test_mainwindow_toolbar_hides_removed_actions_after_cleanup(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    assert hasattr(window._tb_ctrl, "action_new_surface") is True
    assert hasattr(window._tb_ctrl, "action_duplicate_surface") is True
    assert hasattr(window._tb_ctrl, "action_overlay_sheet") is True
    assert hasattr(window._tb_ctrl, "action_grid") is True
    assert hasattr(window._tb_ctrl, "action_snap_to_grid") is True
    assert hasattr(window._tb_ctrl, "action_base_point_toggle") is True
    assert hasattr(window._tb_ctrl, "action_from_left") is True
    assert hasattr(window._tb_ctrl, "action_from_right") is True

    assert hasattr(window._tb_ctrl, "action_module_count") is False
    assert hasattr(window._tb_ctrl, "action_select_props") is False
    assert hasattr(window._tb_ctrl, "action_from_base") is False
    assert hasattr(window._tb_ctrl, "material_button") is False


def test_settings_dialog_exposes_only_supported_controls_after_cleanup(qtbot):
    dialog = SettingsDialog(AppSettings())
    qtbot.addWidget(dialog)

    assert hasattr(dialog, "_spin_top_extra") is True
    assert hasattr(dialog, "_spin_grid_size") is True
    assert hasattr(dialog, "_spin_grid_major") is True
    assert hasattr(dialog, "_spin_grid_minor") is True
    assert hasattr(dialog, "_check_crosshair") is True
    assert hasattr(dialog, "_check_snap_to_grid") is True
    assert hasattr(dialog, "_check_snap_to_axis") is True
    assert hasattr(dialog, "_check_snap_to_45deg") is True
    assert hasattr(dialog, "_check_snap_to_3060deg") is True
    assert hasattr(dialog, "_check_snap_to_points") is True
    assert hasattr(dialog, "_check_show_inferences") is True
    assert hasattr(dialog, "_combo_live_angle_mode") is True
    assert hasattr(dialog, "_check_show_guide_lines") is True
    assert hasattr(dialog, "_combo_edge_drag_mode") is False
    assert hasattr(dialog, "_check_show_edge_length_labels") is True
    assert hasattr(dialog, "_check_show_vertex_angle_labels") is True
    assert hasattr(dialog, "_check_label_always_visible") is True
    assert hasattr(dialog, "_button_restore_defaults") is True
    assert dialog._button_restore_defaults.text() == "Domyślne"

    assert hasattr(dialog, "_combo_shift_behavior") is False
    assert hasattr(dialog, "_check_show_grid") is False
    assert hasattr(dialog, "_check_axis_overlay") is False
    assert hasattr(dialog, "_check_show_decimal_cm") is False
    assert hasattr(dialog, "_check_show_angle_arc") is False
    assert hasattr(dialog, "_spin_ui_element_scale") is False
    assert hasattr(dialog, "_check_show_xy_references") is False
    assert hasattr(dialog, "_check_close_on_rmb") is False
    assert hasattr(dialog, "_spin_undo_stack_depth") is False


def test_settings_dialog_build_settings_keeps_fixed_defaults(qtbot):
    dialog = SettingsDialog(AppSettings())
    qtbot.addWidget(dialog)

    settings = dialog.build_settings()

    assert settings.shift_drag_behavior == "orthogonal_lock"
    assert settings.show_axis_overlay is True
    assert settings.show_xy_references_during_draw is True
    assert settings.show_decimal_cm is False
    assert settings.show_angle_arc is True
    assert settings.close_on_rmb is True
    assert settings.ui_element_scale == pytest.approx(1.0)
    assert settings.undo_stack_depth == 20


def test_settings_dialog_restore_defaults_reloads_new_code_defaults_without_accepting(qtbot):
    dialog = SettingsDialog(AppSettings())
    qtbot.addWidget(dialog)

    dialog._check_crosshair.setChecked(True)
    dialog._check_snap_to_3060deg.setChecked(False)
    dialog._check_label_always_visible.setChecked(False)

    dialog._button_restore_defaults.click()

    settings = dialog.build_settings()
    assert dialog.result() == 0
    assert settings.show_crosshair is False
    assert settings.snap_to_3060deg is True
    assert settings.label_always_visible is True


def test_dane_blachy_dialog_exposes_only_trapez_minimal_fields_after_cleanup(qtbot):
    dialog = DaneBlachyDialog(None)
    qtbot.addWidget(dialog)

    assert hasattr(dialog, "id_edit") is True
    assert hasattr(dialog, "nazwa_edit") is True
    assert hasattr(dialog, "szerokosc_efektywna_spin") is True
    assert hasattr(dialog, "min_dlugosc_spin") is True
    assert hasattr(dialog, "max_dlugosc_spin") is True

    assert hasattr(dialog, "radio_dachowkowa") is False
    assert hasattr(dialog, "radio_trapezowa") is False
    assert hasattr(dialog, "zapas_dolny_spin") is False
    assert hasattr(dialog, "zapas_gorny_spin") is False
    assert hasattr(dialog, "dlugosc_modulu_spin") is False
    assert hasattr(dialog, "cena_zl_spin") is False
    assert hasattr(dialog, "cena_gr_spin") is False


def test_blachy_dialog_hides_legacy_material_detail_labels_after_cleanup(qtbot):
    dialog = BlachyDialog([], None)
    qtbot.addWidget(dialog)

    label_texts = {label.text() for label in dialog.findChildren(QLabel)}

    assert "Id:" in label_texts
    assert "Nazwa:" in label_texts
    assert "Szerokość efektywna arkusza:" in label_texts
    assert "Min. długość arkusza:" in label_texts
    assert "Maks. długość arkusza:" in label_texts

    assert "Zapas górny:" not in label_texts
    assert "Zapas dolny:" not in label_texts
    assert "Długość modułu:" not in label_texts
    assert "Cena za m2:" not in label_texts


def test_mainwindow_mode_indicator_tracks_draw_and_idle_transitions(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window._start_draw_outline()
    assert window._mode_label.text() == "Mode: DRAW_PLANE"

    window.primary_canvas.set_mode(window.primary_canvas.MODE_IDLE)
    assert window._mode_label.text() == "Mode: IDLE"


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

    assert window.workspace_tabs.count() == 2
    assert window.workspace_tabs.tabText(0) == first_plane.name
    assert window.workspace_tabs.tabText(1) == second_plane.name
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


def test_mainwindow_duplicates_active_roof_plane_with_geometry_and_cutouts(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    plane = window.project_state.add_roof_plane(build_rectangle_outline(320, 180), name="Front", selected_material_id="PD510")
    window.project_state.add_hole_to_plane(Polygon2D.rectangle(60, 50, origin_x=40, origin_y=30), plane.id)
    window.project_state.generate_layout_for_plane(plane.id)
    window._refresh_canvas_from_state()

    window._duplicate_active_roof_plane()

    assert len(window.project_state.roof_planes) == 2
    duplicate = window.project_state.active_roof_plane()
    assert duplicate is not None
    assert duplicate.id != plane.id
    assert duplicate.outline is not plane.outline
    assert duplicate.outline == plane.outline
    assert duplicate.holes[0] is not plane.holes[0]
    assert duplicate.holes == plane.holes
    assert duplicate.layout_bands == plane.layout_bands
    assert duplicate.auto_sheet_placements == plane.auto_sheet_placements
    assert window._workspace.plane_id_for_tab_index(window.workspace_tabs.currentIndex()) == duplicate.id


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


def test_mainwindow_wizard_updates_active_empty_plane_without_creating_new_tab(qtbot, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    empty_plane = window.project_state.add_empty_roof_plane(selected_material_id="PD510")
    window._refresh_canvas_from_state()

    class FakeWizardDialog:
        def __init__(self, config_data, parent=None) -> None:
            self._result = SimpleNamespace(
                shape_key="trapez_prl",
                shape_values={"A": 400, "B": 220, "C": 260},
                cutout_kind="none",
                cutout_values={},
                flip_h=False,
                flip_v=False,
            )

        def exec(self) -> int:
            return QDialog.DialogCode.Accepted

        def get_result(self):
            return self._result

    monkeypatch.setattr("ui.main_window.AddPolacDialog", FakeWizardDialog)

    window._dlg_add_polac()

    plane = window.project_state.active_roof_plane()
    expected_outline = Polygon2D(
        [
            Point2D(140, 0),
            Point2D(400, 0),
            Point2D(400, 220),
            Point2D(0, 220),
        ]
    )
    assert plane is not None
    assert plane.id == empty_plane.id
    assert len(window.project_state.roof_planes) == 1
    assert plane.outline is not None
    assert plane.outline.points == expected_outline.points
    assert window.workspace_tabs.count() == 1
    assert window._workspace.plane_id_for_tab_index(window.workspace_tabs.currentIndex()) == empty_plane.id


def test_mainwindow_wizard_creates_new_plane_when_none_exists(qtbot, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    window._refresh_canvas_from_state()

    class FakeWizardDialog:
        def __init__(self, config_data, parent=None) -> None:
            self._result = SimpleNamespace(
                shape_key="prostokat",
                shape_values={"A": 420, "B": 260},
                cutout_kind="none",
                cutout_values={},
                flip_h=False,
                flip_v=False,
            )

        def exec(self) -> int:
            return QDialog.DialogCode.Accepted

        def get_result(self):
            return self._result

    monkeypatch.setattr("ui.main_window.AddPolacDialog", FakeWizardDialog)

    window._dlg_add_polac()

    plane = window.project_state.active_roof_plane()
    assert plane is not None
    assert len(window.project_state.roof_planes) == 1
    assert plane.outline is not None
    assert plane.outline.points == build_rectangle_outline(420, 260).points
    assert window._workspace.plane_id_for_tab_index(window.workspace_tabs.currentIndex()) == plane.id


def test_mainwindow_wizard_commits_outline_and_cutout_as_single_undo_entry(qtbot, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    plane = window.project_state.add_empty_roof_plane(selected_material_id="PD510")
    window._refresh_canvas_from_state()

    class FakeWizardDialog:
        def __init__(self, config_data, parent=None) -> None:
            self._result = SimpleNamespace(
                shape_key="prostokat",
                shape_values={"A": 500, "B": 300},
                cutout_kind="lukarna3",
                cutout_values={"A": 140, "H1": 50, "H": 90},
                flip_h=False,
                flip_v=False,
            )

        def exec(self) -> int:
            return QDialog.DialogCode.Accepted

        def get_result(self):
            return self._result

    monkeypatch.setattr("ui.main_window.AddPolacDialog", FakeWizardDialog)

    window._dlg_add_polac()

    updated_plane = window.project_state.roof_plane_by_id(plane.id)
    expected_hole = Polygon2D(
        [
            Point2D(250, 105),
            Point2D(320, 155),
            Point2D(320, 195),
            Point2D(180, 195),
            Point2D(180, 155),
        ]
    )

    assert updated_plane is not None
    assert updated_plane.outline is not None
    assert updated_plane.outline.points == build_rectangle_outline(500, 300).points
    assert updated_plane.holes == [expected_hole]
    assert len(window._undo_stack) == 1

    window._undo()
    reverted_plane = window.project_state.roof_plane_by_id(plane.id)

    assert reverted_plane is not None
    assert reverted_plane.outline is None
    assert reverted_plane.holes == []

    window._redo()
    redone_plane = window.project_state.roof_plane_by_id(plane.id)

    assert redone_plane is not None
    assert redone_plane.outline is not None
    assert redone_plane.outline.points == build_rectangle_outline(500, 300).points
    assert redone_plane.holes == [expected_hole]


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
    assert window.workspace_tabs.currentIndex() == 1


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


def test_mainwindow_commits_whole_plane_move_outline_and_holes_to_project_state(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    plane = window.project_state.add_roof_plane(build_rectangle_outline(320, 180), selected_material_id="PD510")
    original_hole = Polygon2D.rectangle(60, 50, origin_x=40, origin_y=30)
    window.project_state.add_hole_to_plane(original_hole, plane.id)
    window._refresh_canvas_from_state()

    moved_outline = Polygon2D(
        [
            Point2D(30, 20),
            Point2D(350, 20),
            Point2D(350, 200),
            Point2D(30, 200),
        ]
    )
    moved_hole = Polygon2D.rectangle(60, 50, origin_x=70, origin_y=50)
    canvas = window._workspace.canvas_for_plane(plane.id)

    canvas.outline_edit_committed.emit(
        CommittedOutlineEdit(
            outline=moved_outline,
            holes=[moved_hole],
            operation="plane_move",
        )
    )

    assert plane.outline == moved_outline
    assert plane.holes == [moved_hole]
    assert plane.layout_dirty_reason is None
    assert len(plane.layout_bands) > 0


def test_mainwindow_allows_canvas_outline_edit_even_when_cutout_moves_outside_outline(qtbot, monkeypatch):
    messages: list[str] = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *args: messages.append(args[2])))

    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    plane = window.project_state.add_roof_plane(build_rectangle_outline(320, 180), selected_material_id="PD510")
    window.project_state.add_hole_to_plane(Polygon2D.rectangle(60, 60, origin_x=30, origin_y=40), plane.id)
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

    assert plane.outline == invalid_outline
    assert messages == []


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


def test_mainwindow_preserves_cutout_selection_after_canvas_edit_commit(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    plane = window.project_state.add_roof_plane(build_rectangle_outline(320, 180), selected_material_id="PD510")
    window.project_state.add_hole_to_plane(Polygon2D.rectangle(60, 50, origin_x=40, origin_y=30), plane.id)
    window._refresh_canvas_from_state()

    canvas = window._workspace.canvas_for_plane(plane.id)
    assert canvas is not None
    canvas._selected_hole_index = 0
    canvas._active_hole_vertex_index = 1

    updated_hole = Polygon2D.rectangle(80, 50, origin_x=40, origin_y=30)
    canvas.hole_edit_committed.emit(0, updated_hole)

    refreshed_canvas = window._workspace.canvas_for_plane(plane.id)
    assert refreshed_canvas is not None
    assert refreshed_canvas.selected_geometry_kind() == "cutout_vertex"
    assert refreshed_canvas.selected_cutout_index() == 0


def test_mainwindow_toolbar_origin_toggle_enables_origin_edit_mode(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    window.project_state.add_roof_plane(build_rectangle_outline(320, 180), selected_material_id="PD510")
    window._refresh_canvas_from_state()

    window._tb_ctrl.action_base_point_toggle.trigger()

    assert window.primary_canvas is not None
    assert window.primary_canvas._origin_edit_enabled is True
    assert window._tb_ctrl.action_base_point_toggle.isChecked() is True
    assert "QToolButton:checked" in window._tb_ctrl.toolbar.styleSheet()


def test_mainwindow_settings_dialog_updates_grid_size_on_project_state_and_canvas(qtbot, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    plane = window.project_state.add_roof_plane(build_rectangle_outline(320, 180), selected_material_id="PD510")
    window._refresh_canvas_from_state()

    class FakeSettingsDialog:
        def __init__(self, settings, parent=None) -> None:
            self._settings = settings

        def exec(self) -> int:
            return QDialog.DialogCode.Accepted

        def build_settings(self):
            return AppSettings(
                partial_cutout_top_extra_cm=self._settings.partial_cutout_top_extra_cm,
                grid_size_cm=25.0,
                shift_drag_behavior="orthogonal_lock",
                show_grid=False,
                grid_major_cm=50,
                grid_minor_cm=5,
                show_crosshair=False,
                live_angle_mode="relative_to_prev",
                show_decimal_cm=False,
                show_angle_arc=True,
                show_guide_lines=False,
                close_on_rmb=True,
                snap_to_grid=False,
                snap_to_axis=False,
                snap_to_45deg=False,
                snap_to_3060deg=True,
                snap_to_points=False,
                show_inferences=False,
                ui_element_scale=1.0,
                undo_stack_depth=20,
            )

    monkeypatch.setattr("ui.dialogs.settings_dialog.SettingsDialog", FakeSettingsDialog)

    window._dlg_settings()

    canvas = window._workspace.canvas_for_plane(plane.id)
    assert window.project_state.app_settings.grid_size_cm == pytest.approx(25.0)
    assert window.project_state.app_settings.shift_drag_behavior == "orthogonal_lock"
    assert window.project_state.app_settings.show_grid is False
    assert window.project_state.app_settings.show_axis_overlay is True
    assert window.project_state.app_settings.grid_major_cm == 50
    assert window.project_state.app_settings.grid_minor_cm == 5
    assert window.project_state.app_settings.show_crosshair is False
    assert window.project_state.app_settings.show_xy_references_during_draw is True
    assert window.project_state.app_settings.live_angle_mode == "relative_to_prev"
    assert window.project_state.app_settings.show_decimal_cm is False
    assert window.project_state.app_settings.show_angle_arc is True
    assert window.project_state.app_settings.show_guide_lines is False
    assert window.project_state.app_settings.close_on_rmb is True
    assert window.project_state.app_settings.snap_to_grid is False
    assert window.project_state.app_settings.snap_to_axis is False
    assert window.project_state.app_settings.snap_to_45deg is False
    assert window.project_state.app_settings.snap_to_3060deg is True
    assert window.project_state.app_settings.snap_to_points is False
    assert window.project_state.app_settings.show_inferences is False
    assert window.project_state.app_settings.ui_element_scale == pytest.approx(1.0)
    assert window.project_state.app_settings.undo_stack_depth == 20
    assert canvas is not None
    assert canvas._edit_overlay_grid_step_cm(canvas._canvas_mapper()) == pytest.approx(25.0)
    assert canvas._app_settings.live_angle_mode == "relative_to_prev"
    assert canvas._app_settings.close_on_rmb is True
    assert canvas._app_settings.shift_drag_behavior == "orthogonal_lock"
    assert canvas._show_grid is False
    assert canvas._app_settings.show_axis_overlay is True
    assert canvas._app_settings.grid_major_cm == 50
    assert canvas._app_settings.grid_minor_cm == 5
    assert canvas._app_settings.show_crosshair is False
    assert canvas._app_settings.show_xy_references_during_draw is True
    assert canvas.snap_to_grid_enabled() is False
    assert window._tb_ctrl.action_grid.isChecked() is False
    assert window._tb_ctrl.action_snap_to_grid.isChecked() is False


def test_mainwindow_uses_code_defaults_when_config_payload_is_empty(qtbot, monkeypatch):
    monkeypatch.setattr("ui.main_window.load_config", lambda: {})

    window = MainWindow()
    qtbot.addWidget(window)

    settings = window.project_state.app_settings
    assert settings.partial_cutout_top_extra_cm == 15
    assert settings.grid_size_cm == 10
    assert settings.show_decimal_cm is False


def test_mainwindow_toolbar_grid_toggle_updates_canvas_grid_visibility_only(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    plane = window.project_state.add_roof_plane(build_rectangle_outline(320, 180), selected_material_id="PD510")
    window._refresh_canvas_from_state()

    canvas = window._workspace.canvas_for_plane(plane.id)
    assert canvas is not None
    assert window._tb_ctrl.action_grid.text() == "Pokaż siatkę"
    assert window._tb_ctrl.action_grid.isCheckable() is True
    assert window._tb_ctrl.action_grid.isChecked() is True
    assert window._tb_ctrl.action_snap_to_grid.text() == "Snap to Grid"
    assert window._tb_ctrl.action_snap_to_grid.isCheckable() is True
    assert window._tb_ctrl.action_snap_to_grid.isChecked() is True
    assert canvas._show_grid is True
    assert canvas.snap_to_grid_enabled() is True

    window._tb_ctrl.action_grid.trigger()

    assert window._tb_ctrl.action_grid.isChecked() is False
    assert window._tb_ctrl.action_snap_to_grid.isChecked() is True
    assert canvas._show_grid is False
    assert canvas.snap_to_grid_enabled() is True
    assert canvas._app_settings.show_axis_overlay is True
    assert window.project_state.app_settings.show_grid is False
    assert window.project_state.app_settings.snap_to_grid is True


def test_mainwindow_cutout_menu_exposes_only_add_and_draw_actions(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    actions = window.menuBar().actions()
    cutouts_menu = actions[2].menu()

    assert isinstance(cutouts_menu, QMenu)
    cutout_actions = [action.text() for action in cutouts_menu.actions() if not action.isSeparator()]
    assert cutout_actions == ["Dodaj prostokątny wycinek...", "Rysuj wycinek"]


def test_mainwindow_toolbar_sheet_toggle_switches_wireframe_mode_without_recalc(qtbot, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    plane = window.project_state.add_roof_plane(build_rectangle_outline(320, 180), selected_material_id="PD510")
    window.project_state.generate_layout_for_plane(plane.id)
    window._refresh_canvas_from_state()

    calls: list[str] = []
    original_generate_layout = ProjectState.generate_layout_for_plane

    def _tracked_generate_layout(self, plane_id=None):
        calls.append(plane_id or "active")
        return original_generate_layout(self, plane_id)

    monkeypatch.setattr(ProjectState, "generate_layout_for_plane", _tracked_generate_layout)

    canvas = window._workspace.canvas_for_plane(plane.id)
    assert canvas is not None
    assert window._tb_ctrl.action_overlay_sheet.isChecked() is False
    assert window._sheets_visible is False
    assert canvas._show_sheet_placements is False

    window._tb_ctrl.action_overlay_sheet.trigger()

    assert window._tb_ctrl.action_overlay_sheet.isChecked() is True
    assert window._sheets_visible is True
    assert canvas._show_sheet_placements is True
    assert calls == []


def test_mainwindow_layout_direction_uses_explicit_left_and_right_actions(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    plane = window.project_state.add_roof_plane(build_rectangle_outline(320, 180), selected_material_id="PD510")
    window._refresh_canvas_from_state()

    assert window._tb_ctrl.action_from_left.isChecked() is True
    assert window._tb_ctrl.action_from_right.isChecked() is False

    window._tb_ctrl.action_from_right.trigger()

    assert plane.generation_settings.layout_origin == "right"
    assert window._tb_ctrl.action_from_left.isChecked() is False
    assert window._tb_ctrl.action_from_right.isChecked() is True

    window._tb_ctrl.action_from_left.trigger()

    assert plane.generation_settings.layout_origin == "left"
    assert window._tb_ctrl.action_from_left.isChecked() is True
    assert window._tb_ctrl.action_from_right.isChecked() is False


def test_mainwindow_commits_canvas_origin_edit_to_project_state(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    plane = window.project_state.add_roof_plane(build_rectangle_outline(320, 180), selected_material_id="PD510")
    window._refresh_canvas_from_state()

    canvas = window._workspace.canvas_for_plane(plane.id)
    assert canvas is not None

    canvas.origin_edit_committed.emit(Point2D(35.0, 170.0))

    assert plane.generation_settings.origin_x_cm == pytest.approx(35.0)
    assert plane.generation_settings.origin_y_cm == pytest.approx(170.0)


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


def test_mainwindow_freehand_outline_keeps_global_canvas_position_instead_of_bbox_normalization(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    canvas = window._workspace.primary_canvas
    canvas.resize(640, 420)
    canvas.polygon_closed.connect(window._on_polygon_closed)

    window._on_polygon_closed(
        [
            QPointF(110, 80),
            QPointF(310, 80),
            QPointF(310, 240),
            QPointF(110, 240),
        ]
    )
    first_outline = window.project_state.active_roof_plane().outline

    canvas.polygon_closed.connect(window._on_polygon_closed)
    window._on_polygon_closed(
        [
            QPointF(160, 80),
            QPointF(360, 80),
            QPointF(360, 240),
            QPointF(160, 240),
        ]
    )
    second_outline = window.project_state.active_roof_plane().outline

    assert first_outline is not None
    assert second_outline is not None
    assert second_outline.points[0].x >= first_outline.points[0].x
    assert second_outline.points[1].x >= first_outline.points[1].x
    assert second_outline.points[0].y == pytest.approx(first_outline.points[0].y, abs=0.1)
    assert second_outline.points[2].y == pytest.approx(first_outline.points[2].y, abs=0.1)


def test_mainwindow_freehand_outline_uses_same_grid_snap_as_canvas(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.project_state.app_settings.grid_size_cm = 25.0
    window.project_state.app_settings.snap_to_grid = True
    window.project_state.delete_roof_plane(window.project_state.active_roof_plane().id)
    window._refresh_canvas_from_state()
    canvas = window._workspace.primary_canvas
    canvas.resize(640, 420)
    canvas.set_app_settings(window.project_state.app_settings)
    canvas.set_mode(canvas.MODE_DRAW_OUTLINE)
    mapper = canvas._free_draw_mapper()
    point = mapper.map_point(Point2D(270.0, 43.0))
    snapped_point = canvas._domain_to_pixel_point(canvas._pixel_to_domain_point(point, mapper), mapper)

    canvas.polygon_closed.connect(window._on_polygon_closed)
    window._on_polygon_closed(
        [
            snapped_point,
            canvas._domain_to_pixel_point(canvas._pixel_to_domain_point(mapper.map_point(Point2D(320.0, 43.0)), mapper), mapper),
            canvas._domain_to_pixel_point(canvas._pixel_to_domain_point(mapper.map_point(Point2D(350.0, 100.0)), mapper), mapper),
        ]
    )

    outline = window.project_state.active_roof_plane().outline
    assert outline is not None
    assert outline.points[0].x == pytest.approx(275.0, abs=0.1)
    assert outline.points[0].y == pytest.approx(50.0, abs=0.1)


def test_mainwindow_freehand_outline_does_not_resnap_with_different_origin(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.project_state.delete_roof_plane(window.project_state.active_roof_plane().id)
    window.project_state.app_settings.grid_size_cm = 25.0
    window.project_state.app_settings.snap_to_grid = True
    window._refresh_canvas_from_state()
    canvas = window._workspace.primary_canvas
    canvas.resize(640, 420)
    canvas.set_app_settings(window.project_state.app_settings)
    canvas.set_mode(canvas.MODE_DRAW_OUTLINE)
    mapper = canvas._free_draw_mapper()
    clicked_point = mapper.map_point(Point2D(270.0, 43.0))
    snapped_point = canvas._domain_to_pixel_point(canvas._pixel_to_domain_point(clicked_point, mapper), mapper)

    canvas.polygon_closed.connect(window._on_polygon_closed)
    window._on_polygon_closed(
        [
            snapped_point,
            canvas._domain_to_pixel_point(canvas._pixel_to_domain_point(mapper.map_point(Point2D(320.0, 43.0)), mapper), mapper),
            canvas._domain_to_pixel_point(canvas._pixel_to_domain_point(mapper.map_point(Point2D(350.0, 100.0)), mapper), mapper),
        ]
    )

    outline = window.project_state.active_roof_plane().outline
    assert outline is not None
    assert outline.points[0].x == pytest.approx(275.0, abs=0.1)
    assert outline.points[0].y == pytest.approx(50.0, abs=0.1)


def test_mainwindow_tab_switch_refreshes_status_report_material_and_origin_mode(qtbot):
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
    first_plane = window.project_state.add_roof_plane(build_rectangle_outline(320, 180), name="Front", selected_material_id="PD510")
    second_plane = window.project_state.add_roof_plane(build_rectangle_outline(210, 140), name="Back", selected_material_id="T20")
    second_plane.generation_settings.layout_origin = "right"
    window._refresh_canvas_from_state()
    window._tb_ctrl.action_base_point_toggle.trigger()

    assert window.project_state.active_plane_id == second_plane.id
    assert "Back" in window._status_label.text()

    window.workspace_tabs.setCurrentIndex(0)

    first_canvas = window._workspace.canvas_for_plane(first_plane.id)
    second_canvas = window._workspace.canvas_for_plane(second_plane.id)

    assert window.project_state.active_plane_id == first_plane.id
    assert window.variant_combo.currentText() == "PD510"
    assert "Front" in window._status_label.text()
    assert "Blacha: PD510" in window._status_label.text()
    assert "od lewej" in window._status_label.text()
    assert "Front" in window._workspace.report_view.toPlainText()
    assert first_canvas is not None
    assert second_canvas is not None
    assert first_canvas._origin_edit_enabled is True
    assert second_canvas._origin_edit_enabled is False


def test_mainwindow_toolbar_grid_toggle_does_not_rebuild_workspace(qtbot, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    plane = window.project_state.add_roof_plane(build_rectangle_outline(320, 180), selected_material_id="PD510")
    window._refresh_canvas_from_state()

    calls: list[str] = []
    monkeypatch.setattr(window._workspace, "sync", lambda: calls.append("sync"))

    canvas = window._workspace.canvas_for_plane(plane.id)
    assert canvas is not None
    assert canvas._show_grid is True

    window._tb_ctrl.action_grid.trigger()

    assert calls == []
    assert canvas._show_grid is False


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
    monkeypatch.setattr("ui.main_window.load_config", lambda *args, **kwargs: next(loads))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *args, **kwargs: ("/tmp/reopened.json", "JSON (*.json)")))

    window = MainWindow()
    qtbot.addWidget(window)
    window._latest_report_html = "<html>stary raport</html>"
    window._latest_report_plane_id = "plane-123"

    window._open_project()

    assert window._latest_report_html == ""
    assert window._latest_report_plane_id is None
    assert window.windowTitle() == "4Dach — Firma B"
    assert window._project_file_path == Path("/tmp/reopened.json")


def test_mainwindow_marks_project_dirty_until_explicit_save(qtbot, monkeypatch):
    saved_payloads: list[dict] = []

    def _save_config(config_data, parent=None, path=None):
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


def test_mainwindow_new_project_clears_roof_planes_and_detaches_save_path(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    window.project_state.add_roof_plane(build_rectangle_outline(320, 180), selected_material_id="PD510")
    window._project_file_path = Path("/tmp/existing.json")
    window._refresh_canvas_from_state()

    window._new_project()

    assert window.project_state.roof_planes == []
    assert window.project_state.active_plane_id is None
    assert window._project_file_path is None


def test_mainwindow_save_as_updates_target_path(qtbot, monkeypatch):
    saved_paths: list[Path | None] = []

    def _save_config(config_data, parent=None, path=None):
        saved_paths.append(path)
        return True

    monkeypatch.setattr("ui.main_window.save_config", _save_config)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *args, **kwargs: ("/tmp/exported-project.json", "JSON (*.json)")))

    window = MainWindow()
    qtbot.addWidget(window)
    window._project_file_path = None

    assert window._save_project_as() is True
    assert window._project_file_path == Path("/tmp/exported-project.json")
    assert saved_paths == [Path("/tmp/exported-project.json")]


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


def test_mainwindow_settings_dialog_does_not_overwrite_manual_override_on_planes(qtbot, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    plane = window.project_state.add_roof_plane(build_rectangle_outline(320, 180), selected_material_id="PD510")
    window.project_state.generate_layout_for_plane(plane.id)
    window._refresh_canvas_from_state()

    assert len(plane.auto_sheet_placements) > 0
    removed_auto_id = plane.auto_sheet_placements[0].id
    window.project_state.remove_sheet_placement(removed_auto_id, plane.id)
    assert plane.layout_dirty_reason == "manual_override"
    original_removed_ids = list(plane.manually_removed_auto_sheet_ids)
    assert removed_auto_id in original_removed_ids

    class FakeSettingsDialog:
        def __init__(self, settings, parent=None) -> None:
            self._settings = settings

        def exec(self) -> int:
            return QDialog.DialogCode.Accepted

        def build_settings(self):
            return AppSettings(
                partial_cutout_top_extra_cm=self._settings.partial_cutout_top_extra_cm,
                grid_size_cm=25.0,
                shift_drag_behavior="orthogonal_lock",
            )

    monkeypatch.setattr("ui.dialogs.settings_dialog.SettingsDialog", FakeSettingsDialog)

    window._dlg_settings()

    assert plane.layout_dirty_reason == "manual_override"
    assert list(plane.manually_removed_auto_sheet_ids) == original_removed_ids


def test_post_state_change_refresh_contract_orders_cache_materials_canvas_and_dirty_state():
    from ui.main_window_refresh import PostStateChangeRefresh, apply_post_state_change_refresh

    calls: list[str] = []

    class FakeWindow:
        def _invalidate_cached_report(self) -> None:
            calls.append("invalidate_report")

        def _refresh_material_combo(self) -> None:
            calls.append("refresh_materials")

        def _refresh_canvas(self) -> None:
            calls.append("refresh_canvas")

        def _mark_saved_state(self) -> None:
            calls.append("mark_saved")

        def _refresh_dirty_state(self) -> None:
            calls.append("refresh_dirty")

    apply_post_state_change_refresh(
        FakeWindow(),
        PostStateChangeRefresh(
            invalidate_report_cache=True,
            refresh_materials=True,
            dirty_state_mode="refresh",
        ),
    )

    assert calls == [
        "invalidate_report",
        "refresh_materials",
        "refresh_canvas",
        "refresh_dirty",
    ]


def test_build_centered_hole_prefers_space_after_existing_cutouts():
    from ui.main_window_dialogs import build_centered_hole

    plane = type(
        "PlaneStub",
        (),
        {
            "outline": build_rectangle_outline(320, 180),
            "holes": [Polygon2D.rectangle(60, 40, origin_x=40, origin_y=20)],
        },
    )()

    hole = build_centered_hole(plane, 50, 30)

    assert hole.bounds().min_x == pytest.approx(110.0)
    assert hole.bounds().min_y == pytest.approx(75.0)


def test_cutout_rectangle_dialog_uses_dedicated_config_values(qtbot):
    from ui.dialogs.shape_dialogs import CutoutRectangleDialog

    dialog = CutoutRectangleDialog(
        {
            "ksztalty": {"prostokat": {"szerokosc": 1500, "wysokosc": 1300}},
            "wycinki": {"prostokat": {"szerokosc": 90, "wysokosc": 70}},
        }
    )
    qtbot.addWidget(dialog)

    assert dialog.get_values() == {"szerokosc": 90, "wysokosc": 70}


def test_mainwindow_add_hole_uses_dedicated_cutout_rectangle_config(qtbot, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)

    window.project_state = ProjectState(materials=window.project_state.materials)
    window._workspace.bind_project_state(window.project_state, window.project_state.material_by_id)
    window.project_state.add_empty_roof_plane(selected_material_id="PD510")
    window._refresh_canvas_from_state()

    plane = window.project_state.active_roof_plane()
    assert plane is not None
    window.project_state.set_roof_plane_outline(build_rectangle_outline(500, 400), plane.id)
    window._refresh_canvas_from_state()
    window._config.setdefault("ksztalty", {})["prostokat"] = {"szerokosc": 1500, "wysokosc": 1300}

    class FakeCutoutRectangleDialog:
        def __init__(self, config_data, parent=None) -> None:
            self._values = {"szerokosc": 90, "wysokosc": 70}

        def setWindowTitle(self, _title: str) -> None:
            return None

        def exec(self) -> int:
            return QDialog.DialogCode.Accepted

        def get_values(self) -> dict:
            return dict(self._values)

    monkeypatch.setattr("ui.main_window.CutoutRectangleDialog", FakeCutoutRectangleDialog)

    window._dlg_add_hole()

    updated_plane = window.project_state.active_roof_plane()
    assert updated_plane is not None
    assert window._config["ksztalty"]["prostokat"] == {"szerokosc": 1500, "wysokosc": 1300}
    assert window._config["wycinki"]["prostokat"] == {"szerokosc": 90, "wysokosc": 70}
    assert len(updated_plane.holes) == 1
    assert updated_plane.holes[0].bounds().width == pytest.approx(90.0)
    assert updated_plane.holes[0].bounds().height == pytest.approx(70.0)
