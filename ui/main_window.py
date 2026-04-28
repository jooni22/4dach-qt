# This Python file uses the following encoding: utf-8
"""ui/main_window.py — slim MainWindow (~150 lines) that mounts controllers."""
from __future__ import annotations
import copy
import json
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
import tempfile

from PySide6.QtCore import QSettings, QRectF, QSize, Qt, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QInputDialog, QMainWindow,
    QFileDialog, QMenu, QMessageBox, QSizePolicy, QToolButton, QVBoxLayout, QWidget, QLabel,
)
from PySide6.QtGui import QDesktopServices

from app_icons import build_icon
from persistence import load_config, save_config
from core.models import Point2D, Polygon2D, SheetPlacement
from core.project_state import ProjectState
from core.reporting import build_project_report, build_project_report_html
from core.geometry import make_rectangle, make_trapezoid, make_triangle

from ui.theme_manager import ThemeManager
from ui.drawing_canvas import DrawingCanvas
from ui.workspace import WorkspaceController
from ui.report_view import ReportController
from ui.dialogs import BlachyDialog, DaneFirmyDialog, ProstokatDialog, TrapezDialog, TrojkatDialog


def _show_warning(parent, title: str, msg: str) -> None:
    from PySide6.QtWidgets import QMessageBox
    QMessageBox.warning(parent, title, msg)


@dataclass(slots=True)
class _HistoryEntry:
    label: str
    before_snapshot: dict
    after_snapshot: dict


class MainWindow(QMainWindow):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._config = load_config()
        self.project_state = ProjectState.from_config(self._config)
        self._theme_mgr = ThemeManager()
        self._latest_report_html = ""
        self._latest_report_plane_id: str | None = None
        self._undo_stack: list[_HistoryEntry] = []
        self._redo_stack: list[_HistoryEntry] = []
        self._saved_snapshot_signature = ""
        self._saved_plane_snapshot_signatures: dict[str, str] = {}
        self._unsaved_plane_ids: set[str] = set()
        self._has_unsaved_changes = False
        self._base_window_title = ""
        self._snap_to_grid_enabled = True
        self._sheets_visible = True
        self._project_file_path: Path | None = Path(__file__).resolve().parent.parent / "config.json"

        self._status_label = QLabel("")
        self.statusBar().addPermanentWidget(self._status_label)

        self._build_chrome()
        self._workspace = WorkspaceController(
            self.centralWidget(),
            self.project_state,
            self.project_state.material_by_id,
        )
        layout = QVBoxLayout(self.centralWidget())
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._workspace.tabs)

        self._report_ctrl = ReportController(self._workspace.report_view)
        self._build_menu()
        self._build_toolbar()
        self.workspace_tabs = self._workspace.tabs
        self.variant_combo = self._tb_ctrl.variant_combo
        self._apply_theme()
        self._refresh_canvas()
        self._mark_saved_state()

        settings = QSettings()
        geo = settings.value("geometry")
        if geo:
            self.restoreGeometry(geo)
        else:
            self.resize(1120, 720)

        self.statusBar().showMessage("Lewy przycisk myszy: rysowanie, prawy: wyczyść szkic", 5000)

    # ------------------------------------------------------------------
    def _build_chrome(self) -> None:
        self.menuBar().setNativeMenuBar(False)
        central = QWidget(self)
        central.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCentralWidget(central)

        company = self._config.get("company_data", {}).get("name", "") or "4Dach"
        self._set_company_title(company)

        self._theme_toggle = QToolButton(self)
        self._theme_toggle.setObjectName("theme_toggle")
        self._theme_toggle.setAutoRaise(True)
        self._theme_toggle.setCheckable(True)
        self._theme_toggle.setIconSize(QSize(16, 16))
        self._theme_toggle.clicked.connect(self._on_toggle_theme)
        self.menuBar().setCornerWidget(self._theme_toggle, Qt.Corner.TopRightCorner)

    def _build_menu(self) -> None:
        mb = self.menuBar()
        mb.clear()

        def act(title, shortcut=None, cb=None):
            a = QAction(title, self)
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
            a.setStatusTip(title)
            if cb:
                a.triggered.connect(cb)
            return a

        plik = mb.addMenu("Plik")
        plik.addAction(act("Nowy projekt", "Ctrl+N", self._new_project))
        plik.addAction(act("Wczytaj projekt...", "Ctrl+O", self._open_project))
        plik.addAction(act("Zapisz", "Ctrl+S", self._save_project))
        plik.addAction(act("Zapisz jako...", "Ctrl+Shift+S", self._save_project_as))
        plik.addSeparator()
        plik.addAction(act("Nowa połać", None, self._add_new_roof_plane))
        plik.addAction(act("Duplikuj połać", "Ctrl+D", self._duplicate_active_roof_plane))
        plik.addAction(act("Zmień nazwę połaci...", "F2", self._rename_active_roof_plane))
        plik.addAction(act("Usuń połać...", "Ctrl+W", self._delete_active_roof_plane))
        plik.addSeparator()
        plik.addAction(act("Cofnij", "Ctrl+Z", self._undo))
        plik.addAction(act("Ponów", "Ctrl+Shift+Z", self._redo))
        plik.addSeparator()
        plik.addAction(act("Drukuj raport", "Ctrl+P", lambda: self._gen_report("standard", True)))
        plik.addAction(act("Drukuj raport ciągły", "Shift+Ctrl+P", lambda: self._gen_report("continuous", True)))
        plik.addAction(act("Drukuj raport skrócony", None, lambda: self._gen_report("short", True)))
        plik.addSeparator()
        plik.addAction(act("Zakończ", "Ctrl+Q", self.close))

        ksztalt = mb.addMenu("Kształt")
        ksztalt.addAction(act("Prostokąt...", None, self._dlg_prostokat))
        ksztalt.addAction(act("Trójkąt...", None, self._dlg_trojkat))
        ksztalt.addAction(act("Trapez...", None, self._dlg_trapez))
        ksztalt.addAction(act("Dowolny", None, self._start_draw_outline))

        wyc = mb.addMenu("Wycinki")
        wyc.addAction(act("Dodaj prostokątny wycinek...", None, self._dlg_add_hole))
        wyc.addAction(act("Rysuj wycinek", None, self._start_draw_cutout))
        wyc.addAction(act("Przesuń wycinek...", None, self._dlg_move_hole))
        wyc.addAction(act("Usuń wycinek", None, self._dlg_del_hole))

        kat = mb.addMenu("Katalog")
        kat.addAction(act("Blachy...", None, self._dlg_blachy))
        kat.addAction(act("Dane firmy...", None, self._dlg_firma))

        ark = mb.addMenu("Arkusze")
        # ark.addAction(act("Dodaj arkusz", "Insert", self._dlg_add_sheet))
        # ark.addAction(act("Usuń arkusz", "Delete", self._dlg_del_sheet))
        # ark.addAction(act("Podgląd arkuszy", "Ctrl+A", self._dlg_sheet_preview))
        # ark.addAction(act("Aktywne arkusze", None, self._dlg_active_sheets))
        ark.addAction(act("Przelicz aktywną połać", "F5", self._recalculate))
        ark.addSeparator()
        ark.addAction(act("Zmień rodzaj blachy", None, self._dlg_change_material))

        ust = mb.addMenu("Ustawienia")
        ust.addAction(act("Ustawienia aplikacji\u2026", None, self._dlg_settings))

    def _build_toolbar(self) -> None:
        from ui.toolbar import ToolbarController
        self._tb_ctrl = ToolbarController(self)
        self._tb_ctrl.variant_combo.currentTextChanged.connect(self._on_material_changed)
        self._tb_ctrl.action_new_project.triggered.connect(self._new_project)
        self._tb_ctrl.action_open_project.triggered.connect(self._open_project)
        self._tb_ctrl.action_save_project.triggered.connect(self._save_project)
        self._tb_ctrl.action_new_surface.triggered.connect(self._add_new_roof_plane)
        self._tb_ctrl.action_duplicate_surface.triggered.connect(self._duplicate_active_roof_plane)
        self._tb_ctrl.action_undo.triggered.connect(self._undo)
        self._tb_ctrl.action_trash.triggered.connect(self._delete_selected_geometry)
        self._tb_ctrl.action_trash.setEnabled(False)
        self._tb_ctrl.action_grid.triggered.connect(self._on_grid_toggled)
        self._tb_ctrl.action_grid.setChecked(self._snap_to_grid_enabled)
        self._tb_ctrl.action_module_count.triggered.connect(self._on_module_count_toggled)
        self._tb_ctrl.action_base_point_toggle.triggered.connect(self._on_origin_mode_toggled)
        self._tb_ctrl.action_from_left.triggered.connect(self._on_from_left_toggled)
        self._tb_ctrl.action_from_right.triggered.connect(self._on_from_right_toggled)
        self._tb_ctrl.action_from_base.triggered.connect(self._on_from_base_toggled)
        self._tb_ctrl.action_overlay_sheet.triggered.connect(self._on_sheet_visibility_toggled)
        self._tb_ctrl.action_overlay_sheet.setChecked(self._sheets_visible)
        self._refresh_material_combo()
        self._workspace.tabs.currentChanged.connect(self._on_tab_changed)
        self._workspace.tabs.tabCloseRequested.connect(self._on_tab_close_requested)
        self._workspace.tabs.tabBarDoubleClicked.connect(self._on_tab_bar_double_clicked)
        self._workspace.tabs.customContextMenuRequested.connect(self._open_tab_context_menu)

    # ------------------------------------------------------------------
    def _apply_theme(self) -> None:
        tokens = self._theme_mgr.apply()
        self._tb_ctrl.refresh_icons(tokens.icon_fg, tokens.icon_accent, tokens.icon_muted)
        kind = "sun" if self._theme_mgr.current_theme == "dark" else "moon"
        self._theme_toggle.setIcon(build_icon(kind, tokens.icon_accent, 16))
        self._theme_toggle.setToolTip(tokens.toggle_tip)
        self._theme_toggle.blockSignals(True)
        self._theme_toggle.setChecked(self._theme_mgr.current_theme == "dark")
        self._theme_toggle.blockSignals(False)
        self._workspace.update_all_canvases()
        self.menuBar().setCornerWidget(self._theme_toggle, Qt.Corner.TopRightCorner)

    def _on_toggle_theme(self) -> None:
        self._theme_mgr.toggle()
        self._apply_theme()

    # ------------------------------------------------------------------
    def _set_company_title(self, company: str) -> None:
        self._base_window_title = f"4Dach — {company}"
        self._refresh_window_title()

    def _refresh_window_title(self) -> None:
        suffix = " *" if self._has_unsaved_changes else ""
        self.setWindowTitle(f"{self._base_window_title}{suffix}")

    def _serialize_current_config(self) -> dict:
        payload = copy.deepcopy(self._config)
        self.project_state.apply_to_config(payload)
        return payload

    def _normalized_dirty_payload(self, payload: dict) -> dict:
        normalized = copy.deepcopy(payload)
        normalized.setdefault("project_state", {})["active_plane_id"] = None
        return normalized

    def _snapshot_signature(self, payload: dict) -> str:
        normalized = self._normalized_dirty_payload(payload)
        return json.dumps(normalized, ensure_ascii=False, sort_keys=True)

    def _plane_snapshot_signatures(self, payload: dict) -> dict[str, str]:
        planes = payload.get("project_state", {}).get("roof_planes", [])
        if isinstance(planes, dict):
            items = planes.get("items", {})
            order = planes.get("order", list(items.keys()))
            return {
                plane_id: json.dumps(items[plane_id], ensure_ascii=False, sort_keys=True)
                for plane_id in order
                if plane_id in items
            }
        return {
            plane_payload["id"]: json.dumps(plane_payload, ensure_ascii=False, sort_keys=True)
            for plane_payload in planes
        }

    def _mark_saved_state(self) -> None:
        payload = self._serialize_current_config()
        self._saved_snapshot_signature = self._snapshot_signature(payload)
        self._saved_plane_snapshot_signatures = self._plane_snapshot_signatures(payload)
        self._has_unsaved_changes = False
        self._unsaved_plane_ids.clear()
        self._refresh_dirty_indicators()

    def _refresh_dirty_state(self) -> None:
        payload = self._serialize_current_config()
        self._has_unsaved_changes = self._snapshot_signature(payload) != self._saved_snapshot_signature
        current_plane_signatures = self._plane_snapshot_signatures(payload)
        self._unsaved_plane_ids = {
            plane_id
            for plane_id, signature in current_plane_signatures.items()
            if signature != self._saved_plane_snapshot_signatures.get(plane_id)
        }
        self._unsaved_plane_ids.update(
            plane_id for plane_id in self._saved_plane_snapshot_signatures if plane_id not in current_plane_signatures
        )
        self._refresh_dirty_indicators()

    def _refresh_dirty_indicators(self) -> None:
        self._refresh_window_title()
        self._refresh_tab_titles()

    def _plane_has_unsaved_changes(self, plane_id: str | None) -> bool:
        return bool(plane_id and plane_id in self._unsaved_plane_ids)

    def _push_history(self, label: str, before_snapshot: dict, after_snapshot: dict) -> None:
        if before_snapshot == after_snapshot:
            return
        self._undo_stack.append(_HistoryEntry(label, before_snapshot, after_snapshot))
        self._redo_stack.clear()

    def _apply_snapshot(self, snapshot: dict) -> None:
        self._config = copy.deepcopy(snapshot)
        self.project_state = ProjectState.from_config(self._config)
        self._workspace.bind_project_state(self.project_state, self.project_state.material_by_id)
        self._latest_report_html = ""
        self._latest_report_plane_id = None
        company = self._config.get("company_data", {}).get("name", "") or "4Dach"
        self._set_company_title(company)
        self._refresh_material_combo()
        self._refresh_canvas()
        self._refresh_dirty_state()

    def _save_project(self) -> bool:
        if self._project_file_path is None:
            return self._save_project_as()
        payload = self._serialize_current_config()
        if not save_config(payload, self, path=self._project_file_path):
            return False
        self._config = payload
        self._mark_saved_state()
        self.statusBar().showMessage("Zapisano projekt", 3000)
        return True

    def _save_project_as(self) -> bool:
        target, _ = QFileDialog.getSaveFileName(
            self,
            "Zapisz projekt jako",
            str(self._project_file_path or Path.cwd() / "projekt.json"),
            "JSON (*.json);;Wszystkie pliki (*)",
        )
        if not target:
            return False
        if not target.lower().endswith(".json"):
            target = f"{target}.json"
        payload = self._serialize_current_config()
        project_path = Path(target)
        if not save_config(payload, self, path=project_path):
            return False
        self._project_file_path = project_path
        self._config = payload
        self._mark_saved_state()
        self.statusBar().showMessage("Zapisano projekt pod nową nazwą", 3000)
        return True

    def _confirm_discard_unsaved_changes(self, *, context: str) -> bool:
        if not self._has_unsaved_changes:
            return True
        answer = QMessageBox.question(
            self,
            "Niezapisane zmiany",
            f"Projekt ma niezapisane zmiany. Czy chcesz zapisać przed {context}?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if answer == QMessageBox.StandardButton.Save:
            return self._save_project()
        if answer == QMessageBox.StandardButton.Discard:
            return True
        return False

    def _load_project_payload(self, payload: dict, *, project_file_path: Path | None, reset_history: bool) -> None:
        if reset_history:
            self._undo_stack.clear()
            self._redo_stack.clear()
        self._project_file_path = project_file_path
        self._config = payload
        self.project_state = ProjectState.from_config(self._config)
        self._workspace.bind_project_state(self.project_state, self.project_state.material_by_id)
        self._latest_report_html = ""
        self._latest_report_plane_id = None
        company = self._config.get("company_data", {}).get("name", "") or "4Dach"
        self._set_company_title(company)
        self._refresh_material_combo()
        self._refresh_canvas()
        self._mark_saved_state()

    def _new_project(self) -> None:
        if not self._confirm_discard_unsaved_changes(context="utworzeniem nowego projektu"):
            return
        payload = self._serialize_current_config()
        payload.setdefault("project_state", {})["active_plane_id"] = None
        payload["project_state"]["roof_planes"] = {"order": [], "items": {}}
        self._load_project_payload(payload, project_file_path=None, reset_history=True)
        self.statusBar().showMessage("Utworzono nowy projekt", 3000)

    def _open_project(self) -> None:
        if not self._confirm_discard_unsaved_changes(context="otwarciem projektu"):
            return
        target, _ = QFileDialog.getOpenFileName(
            self,
            "Wczytaj projekt",
            str(self._project_file_path or Path.cwd()),
            "JSON (*.json);;Wszystkie pliki (*)",
        )
        if not target:
            return
        project_path = Path(target)
        self._load_project_payload(load_config(project_path), project_file_path=project_path, reset_history=True)
        self.statusBar().showMessage("Wczytano projekt", 3000)

    def _undo(self) -> None:
        if not self._undo_stack:
            self.statusBar().showMessage("Brak operacji do cofnięcia", 2500)
            return
        entry = self._undo_stack.pop()
        self._redo_stack.append(entry)
        self._apply_snapshot(entry.before_snapshot)
        self.statusBar().showMessage(f"Cofnięto: {entry.label}", 3000)

    def _redo(self) -> None:
        if not self._redo_stack:
            self.statusBar().showMessage("Brak operacji do ponowienia", 2500)
            return
        entry = self._redo_stack.pop()
        self._undo_stack.append(entry)
        self._apply_snapshot(entry.after_snapshot)
        self.statusBar().showMessage(f"Ponowiono: {entry.label}", 3000)

    def _perform_command(
        self,
        label: str,
        fn,
        success_message: str,
        *,
        failure_title: str = "Błąd edycji",
        after_refresh=None,
    ) -> bool:
        before_snapshot = self._serialize_current_config()
        try:
            fn()
        except (ValueError, IndexError) as e:
            QMessageBox.warning(self, failure_title, str(e))
            return False

        for plane in self.project_state.roof_planes:
            # Fix #7: Skip auto-regeneration for manual_override to preserve user intent
            if plane.layout_dirty_reason and plane.layout_dirty_reason != "manual_override":
                try:
                    self.project_state.generate_layout_for_plane(plane.id)
                except Exception:
                    pass

        after_snapshot = self._serialize_current_config()
        self._push_history(label, before_snapshot, after_snapshot)
        self._latest_report_html = ""
        self._latest_report_plane_id = None
        self._refresh_material_combo()
        self._refresh_canvas()
        if after_refresh is not None:
            after_refresh()
        self._refresh_dirty_state()
        self.statusBar().showMessage(success_message, 4000)
        return True

    def _refresh_canvas(self) -> None:
        plane = self.project_state.active_roof_plane()
        self._workspace.sync()
        self._workspace.set_sheet_visibility(self._sheets_visible)
        self.primary_canvas = self._workspace.primary_canvas
        self.workspace_tabs = self._workspace.tabs
        for candidate in self._workspace.plane_canvases():
            candidate.set_app_settings(self.project_state.app_settings)
            candidate.set_snap_to_grid_enabled(self._snap_to_grid_enabled)
            try:
                candidate.outline_edit_committed.connect(
                    self._on_outline_edit_committed,
                    Qt.ConnectionType.UniqueConnection,
                )
            except TypeError:
                pass
            try:
                candidate.outline_edit_rejected.connect(
                    self._on_outline_edit_rejected,
                    Qt.ConnectionType.UniqueConnection,
                )
            except TypeError:
                pass
            try:
                candidate.hole_edit_committed.connect(
                    self._on_hole_edit_committed,
                    Qt.ConnectionType.UniqueConnection,
                )
            except TypeError:
                pass
            try:
                candidate.origin_edit_committed.connect(
                    self._on_origin_edit_committed,
                    Qt.ConnectionType.UniqueConnection,
                )
            except TypeError:
                pass
            try:
                candidate.selection_changed.connect(
                    self._on_selection_changed,
                    Qt.ConnectionType.UniqueConnection,
                )
            except TypeError:
                pass
            try:
                candidate.delete_requested.connect(
                    self._delete_selected_geometry,
                    Qt.ConnectionType.UniqueConnection,
                )
            except TypeError:
                pass
        if plane:
            canvas = self._workspace.canvas_for_plane(plane.id) or self._workspace.primary_canvas
            canvas.set_roof_plane(plane)
            canvas.set_material(self.project_state.material_by_id(plane.selected_material_id))
            canvas.set_app_settings(self.project_state.app_settings)
            canvas.set_snap_to_grid_enabled(self._snap_to_grid_enabled)
        elif self.primary_canvas is not None:
            self.primary_canvas.set_app_settings(self.project_state.app_settings)
            self.primary_canvas.set_snap_to_grid_enabled(self._snap_to_grid_enabled)
        self._apply_origin_edit_mode_to_canvases()
            
        if self.primary_canvas:
            is_selected = self.primary_canvas._plane_selected or self.primary_canvas._selected_hole_index is not None
            self._on_selection_changed(is_selected)

        self._refresh_tab_titles()
        self._refresh_report()
        self._refresh_status_bar_info()

    def _refresh_status_bar_info(self) -> None:
        plane = self.project_state.active_roof_plane()
        if not plane:
            self._status_label.setText("")
            return
            
        label = f"Połać {plane.name}"
        if plane.selected_material_id:
            label += f" | Blacha: {plane.selected_material_id}"
            
        if plane.generation_settings.layout_origin == "right":
            label += " | Układ: <--- od prawej"
        else:
            label += " | Układ: od lewej --->"
        label += " | Arkusze: widoczne" if self._sheets_visible else " | Arkusze: ukryte"
        self._status_label.setText(label)

    def _refresh_canvas_from_state(self) -> None:
        self._refresh_canvas()

    def _refresh_report(self) -> None:
        plane = self.project_state.active_roof_plane()
        self._report_ctrl.set_cached_or_placeholder(
            plane, self._latest_report_html, self._latest_report_plane_id,
            self._dirty_label, self._dirty_hint,
        )

    def _refresh_material_combo(self) -> None:
        combo = self._tb_ctrl.variant_combo
        ids = self.project_state.available_material_ids()
        combo.blockSignals(True)
        combo.clear()
        if ids:
            combo.addItems(ids)
            plane = self.project_state.active_roof_plane()
            preferred = (plane.selected_material_id if plane else None) or ids[0]
            combo.setCurrentText(preferred if preferred in ids else ids[0])
        combo.blockSignals(False)
        self._sync_layout_direction_actions()

    def _active_or_warn(self):
        plane = self.project_state.active_roof_plane()
        if plane is None:
            QMessageBox.information(self, "Brak połaci", "Brak aktywnej połaci")
        return plane

    def _edit(self, fn, msg: str, *, label: str | None = None, failure_title: str = "Błąd edycji", after_refresh=None) -> bool:
        return self._perform_command(label or msg, fn, msg, failure_title=failure_title, after_refresh=after_refresh)

    # ------------------------------------------------------------------
    def _dirty_label(self, reason) -> str:
        return {"geometry_changed": "nieaktualny po zmianie geometrii",
                "material_changed": "nieaktualny po zmianie materiału",
                "manual_override": "zmieniony ręczną korektą"}.get(reason, f"nieaktualny ({reason})")

    def _dirty_hint(self, reason) -> str:
        return "Użyj Arkusze → Przelicz aktywną połać, aby odświeżyć."

    def _tab_title_for_plane(self, plane) -> str:
        suffixes: list[str] = []
        if self._plane_has_unsaved_changes(plane.id):
            suffixes.append("*")
        if plane.layout_dirty_reason:
            suffixes.append("!")
        return f"{plane.name} {' '.join(suffixes)}".rstrip()

    def _refresh_tab_titles(self) -> None:
        for plane in self.project_state.roof_planes:
            self._workspace.update_tab_title(plane.id, self._tab_title_for_plane(plane))

    def _set_plane_layout_origin(self, plane_id: str, origin: str) -> None:
        plane = self.project_state.roof_plane_by_id(plane_id)
        if plane is None:
            raise ValueError("Nie znaleziono aktywnej połaci")
        plane.generation_settings.layout_origin = origin
        plane.layout_dirty_reason = "geometry_changed"

    def _sync_layout_direction_actions(self) -> None:
        plane = self.project_state.active_roof_plane()
        from_left = plane is None or plane.generation_settings.layout_origin != "right"
        self._tb_ctrl.action_from_left.blockSignals(True)
        self._tb_ctrl.action_from_right.blockSignals(True)
        self._tb_ctrl.action_from_left.setChecked(from_left)
        self._tb_ctrl.action_from_right.setChecked(not from_left)
        self._tb_ctrl.action_from_left.blockSignals(False)
        self._tb_ctrl.action_from_right.blockSignals(False)

    def _set_plane_base_line_mode(self, plane_id: str, enabled: bool) -> None:
        plane = self.project_state.roof_plane_by_id(plane_id)
        if plane is None:
            raise ValueError("Nie znaleziono aktywnej połaci")
        if plane.outline is None:
            raise ValueError("Aktywna połać nie ma jeszcze obrysu")
        plane.generation_settings.base_line_y_cm = plane.outline.bounds().max_y if enabled else None
        plane.layout_dirty_reason = "geometry_changed"

    def _set_plane_coordinate_origin(self, plane_id: str, origin: Point2D) -> None:
        plane = self.project_state.roof_plane_by_id(plane_id)
        if plane is None:
            raise ValueError("Nie znaleziono aktywnej połaci")
        if plane.outline is None:
            raise ValueError("Aktywna połać nie ma jeszcze obrysu")
        plane.generation_settings.origin_x_cm = origin.x
        plane.generation_settings.origin_y_cm = origin.y

    def _apply_origin_edit_mode_to_canvases(self) -> None:
        enabled = bool(
            hasattr(self, "_tb_ctrl")
            and hasattr(self._tb_ctrl, "action_base_point_toggle")
            and self._tb_ctrl.action_base_point_toggle.isChecked()
        )
        active_plane = self.project_state.active_roof_plane()
        active_plane_id = active_plane.id if active_plane is not None else None
        for plane in self.project_state.roof_planes:
            canvas = self._workspace.canvas_for_plane(plane.id)
            if canvas is not None:
                canvas.set_origin_edit_enabled(enabled and plane.id == active_plane_id)
        if self._workspace.primary_canvas is not None and active_plane_id is None:
            self._workspace.primary_canvas.set_origin_edit_enabled(False)

    def _restore_canvas_selection(self, plane_id: str | None, selection_snapshot) -> None:
        canvas = self._workspace.canvas_for_plane(plane_id) if plane_id is not None else self.primary_canvas
        if canvas is None:
            return
        canvas.restore_selection(selection_snapshot)

    def _set_active_plane_geometry(self, outline: Polygon2D, message: str) -> bool:
        plane = self.project_state.active_roof_plane()
        selected_material_id = self._tb_ctrl.variant_combo.currentText() or None
        if plane is None:
            return self._edit(
                lambda: self.project_state.add_roof_plane(outline, selected_material_id=selected_material_id),
                message,
            )
        return self._edit(lambda: self.project_state.set_roof_plane_outline(outline, plane.id), message)

    def _commit_active_plane_geometry_edit(self, outline: Polygon2D, message: str) -> bool:
        success = self._set_active_plane_geometry(outline, message)
        if not success:
            self._refresh_canvas()
        return success

    def _add_new_roof_plane(self) -> None:
        selected_material_id = self._tb_ctrl.variant_combo.currentText() or None
        if self._edit(
            lambda: self.project_state.add_empty_roof_plane(selected_material_id=selected_material_id),
            "Dodano nową połacię",
        ):
            active_plane = self.project_state.active_roof_plane()
            if active_plane is not None:
                index = self._workspace.tab_index_for_plane(active_plane.id)
                if index >= 0:
                    self._workspace.tabs.setCurrentIndex(index)

    def _duplicate_active_roof_plane(self) -> None:
        plane = self._active_or_warn()
        if plane is None:
            return
        if self._edit(
            lambda: self.project_state.duplicate_roof_plane(plane.id),
            f"Zduplikowano połacię {plane.name}",
            label=f"Duplikacja połaci {plane.name}",
        ):
            duplicated_plane = self.project_state.active_roof_plane()
            if duplicated_plane is not None:
                index = self._workspace.tab_index_for_plane(duplicated_plane.id)
                if index >= 0:
                    self._workspace.tabs.setCurrentIndex(index)

    def _rename_roof_plane_by_id(self, plane_id: str) -> None:
        plane = self.project_state.roof_plane_by_id(plane_id)
        if plane is None:
            return
        name, ok = QInputDialog.getText(self, "Zmień nazwę połaci", "Nazwa:", text=plane.name)
        if ok:
            self._edit(lambda: self.project_state.rename_roof_plane(plane.id, name), f"Zmieniono nazwę połaci na {name.strip()}")

    def _rename_active_roof_plane(self) -> None:
        plane = self._active_or_warn()
        if plane is not None:
            self._rename_roof_plane_by_id(plane.id)

    def _delete_roof_plane_by_id(self, plane_id: str) -> None:
        plane = self.project_state.roof_plane_by_id(plane_id)
        if plane is None:
            return
        answer = QMessageBox.question(
            self,
            "Usuń połać",
            f"Czy na pewno usunąć połacię „{plane.name}”?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._edit(lambda: self.project_state.delete_roof_plane(plane.id), f"Usunięto połacię {plane.name}")

    def _delete_active_roof_plane(self) -> None:
        plane = self._active_or_warn()
        if plane is not None:
            self._delete_roof_plane_by_id(plane.id)

    # ------------------------------------------------------------------
    # Signal handlers
    def _on_tab_changed(self, index: int) -> None:
        if index < 0 or self._workspace.is_report_tab_index(index):
            return
        plane_id = self._workspace.plane_id_for_tab_index(index)
        if plane_id is None:
            return
        plane = self.project_state.roof_plane_by_id(plane_id)
        if plane and self.project_state.set_active_plane(plane.id):
            self._workspace.primary_canvas = self._workspace.canvas_for_plane(plane.id) or self._workspace.primary_canvas
            self.primary_canvas = self._workspace.primary_canvas
            self._refresh_material_combo()
            self._refresh_report()
            self._apply_origin_edit_mode_to_canvases()
            
            if self.primary_canvas:
                is_selected = self.primary_canvas._plane_selected or self.primary_canvas._selected_hole_index is not None
                self._on_selection_changed(is_selected)
                
            self.statusBar().showMessage(f"Aktywna połać: {plane.name}", 2500)

    def _on_selection_changed(self, is_selected: bool) -> None:
        if hasattr(self, '_tb_ctrl') and hasattr(self._tb_ctrl, 'action_trash'):
            self._tb_ctrl.action_trash.setEnabled(is_selected)

    def _delete_selected_geometry(self) -> None:
        canvas = self.primary_canvas
        if canvas is None:
            return
        kind = canvas.selected_geometry_kind()
        if kind in {"cutout_polygon", "cutout_vertex"}:
            idx = canvas.selected_cutout_index()
            if idx is not None:
                self._dlg_del_hole()
        elif kind in {"main_polygon", "main_polygon_vertex"}:
            answer = QMessageBox.question(
                self,
                "Usuń połać",
                "Czy na pewno usunąć wybraną połać?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self._delete_active_roof_plane()

    def _on_tab_close_requested(self, index: int) -> None:
        if self._workspace.is_report_tab_index(index):
            return
        plane_id = self._workspace.plane_id_for_tab_index(index)
        if plane_id is not None:
            self._delete_roof_plane_by_id(plane_id)

    def _on_tab_bar_double_clicked(self, index: int) -> None:
        if index < 0 or self._workspace.is_report_tab_index(index):
            return
        plane_id = self._workspace.plane_id_for_tab_index(index)
        if plane_id is not None:
            self._rename_roof_plane_by_id(plane_id)

    def _open_tab_context_menu(self, pos) -> None:
        index = self._workspace.tabs.tabBar().tabAt(pos)
        if index < 0 or self._workspace.is_report_tab_index(index):
            return
        plane_id = self._workspace.plane_id_for_tab_index(index)
        if plane_id is None:
            return

        menu = QMenu(self)
        duplicate_action = menu.addAction("Duplikuj połać")
        rename_action = menu.addAction("Zmień nazwę połaci...")
        delete_action = menu.addAction("Usuń połać...")
        selected = menu.exec(self._workspace.tabs.tabBar().mapToGlobal(pos))
        if selected == duplicate_action:
            self._edit(
                lambda: self.project_state.duplicate_roof_plane(plane_id),
                "Zduplikowano połacię",
                label=f"Duplikacja połaci {plane_id}",
            )
        elif selected == rename_action:
            self._rename_roof_plane_by_id(plane_id)
        elif selected == delete_action:
            self._delete_roof_plane_by_id(plane_id)

    def _on_material_changed(self, text: str) -> None:
        plane = self.project_state.active_roof_plane()
        if plane is None:
            return
        if plane.selected_material_id == text:
            self.statusBar().showMessage(f"Aktywna blacha: {text}", 2500)
            return
        self._edit(
            lambda: self.project_state.set_active_material_for_plane(text, plane.id),
            f"Ustawiono materiał {text}",
            label=f"Zmiana materiału połaci {plane.name}",
        )

    def _on_outline_edit_committed(self, outline: Polygon2D) -> None:
        canvas = self.sender() if isinstance(self.sender(), DrawingCanvas) else self.primary_canvas
        selection_snapshot = canvas.selection_snapshot() if isinstance(canvas, DrawingCanvas) else None
        plane = self.project_state.active_roof_plane()
        plane_id = plane.id if plane is not None else None
        self._edit(
            lambda: self.project_state.set_roof_plane_outline(outline, plane_id),
            "Zaktualizowano geometrię połaci",
            after_refresh=lambda: self._restore_canvas_selection(plane_id, selection_snapshot),
        )

    def _on_hole_edit_committed(self, hole_index: int, hole: Polygon2D) -> None:
        canvas = self.sender() if isinstance(self.sender(), DrawingCanvas) else self.primary_canvas
        selection_snapshot = canvas.selection_snapshot() if isinstance(canvas, DrawingCanvas) else None
        plane = self.project_state.active_roof_plane()
        plane_id = plane.id if plane is not None else None
        self._edit(
            lambda: self.project_state.set_hole_polygon(hole_index, hole, plane_id),
            f"Zaktualizowano wycinek {hole_index}",
            after_refresh=lambda: self._restore_canvas_selection(plane_id, selection_snapshot),
        )

    def _on_origin_edit_committed(self, origin: Point2D) -> None:
        plane = self.project_state.active_roof_plane()
        if plane is None:
            return
        self._edit(
            lambda: self._set_plane_coordinate_origin(plane.id, origin),
            f"Ustawiono punkt zerowy dla połaci {plane.name}",
            label=f"Zmiana punktu zerowego {plane.name}",
        )

    def _on_outline_edit_rejected(self, message: str) -> None:
        QMessageBox.warning(self, "Nieprawidłowa geometria", message)
        self.statusBar().showMessage("Odrzucono zmianę geometrii połaci", 4000)

    def _on_grid_toggled(self, checked: bool) -> None:
        self._snap_to_grid_enabled = checked
        self._workspace.set_snap_to_grid_enabled(checked)

    def _on_sheet_visibility_toggled(self, checked: bool) -> None:
        self._sheets_visible = checked
        self._workspace.set_sheet_visibility(checked)
        self._refresh_status_bar_info()
        message = "Pokazano arkusze" if checked else "Ukryto arkusze i włączono widok obrysów"
        self.statusBar().showMessage(message, 3000)

    def _on_module_count_toggled(self, checked: bool) -> None:
        self._workspace.toggle_module_count(checked)

    def _on_origin_mode_toggled(self, checked: bool) -> None:
        plane = self.project_state.active_roof_plane()
        if checked and (plane is None or plane.outline is None):
            QMessageBox.information(self, "Brak obrysu", "Aktywna połać nie ma jeszcze obrysu")
            self._tb_ctrl.action_base_point_toggle.blockSignals(True)
            self._tb_ctrl.action_base_point_toggle.setChecked(False)
            self._tb_ctrl.action_base_point_toggle.blockSignals(False)
            checked = False
        self._apply_origin_edit_mode_to_canvases()
        if checked:
            self.statusBar().showMessage("Przeciągnij punkt zerowy po połaci, aby ustawić nowe (0,0).", 4000)
        else:
            self.statusBar().showMessage("Wyłączono ustawianie punktu zerowego.", 2500)

    def _on_from_left_toggled(self, checked: bool) -> None:
        if not checked:
            self._sync_layout_direction_actions()
            return
        self._set_active_layout_origin("left")

    def _on_from_right_toggled(self, checked: bool) -> None:
        if not checked:
            self._sync_layout_direction_actions()
            return
        self._set_active_layout_origin("right")

    def _set_active_layout_origin(self, origin: str) -> None:
        plane = self._active_or_warn()
        if plane is None:
            self._sync_layout_direction_actions()
            return
        if plane.outline is None:
            QMessageBox.information(self, "Brak obrysu", "Aktywna połać nie ma jeszcze obrysu")
            self._sync_layout_direction_actions()
            return
        if plane.generation_settings.layout_origin == origin:
            self._sync_layout_direction_actions()
            return
        self._edit(
            lambda: self._set_plane_layout_origin(plane.id, origin),
            f"Ustawiono kierunek układania dla {plane.name}",
            label=f"Zmiana kierunku układania {plane.name}",
        )

    def _on_from_base_toggled(self, checked: bool) -> None:
        plane = self._active_or_warn()
        if plane is None:
            return
        if plane.outline is None:
            QMessageBox.information(self, "Brak obrysu", "Aktywna połać nie ma jeszcze obrysu")
            return
        self._edit(
            lambda: self._set_plane_base_line_mode(plane.id, checked),
            f"Zmieniono bazę układania dla {plane.name}",
            label=f"Zmiana bazy układania {plane.name}",
        )

    # ------------------------------------------------------------------
    # Polygon drawing
    def _start_draw_outline(self) -> None:
        self._begin_polygon_capture(mode=DrawingCanvas.MODE_DRAW_OUTLINE, handler=self._on_polygon_closed)

    def _start_draw_cutout(self) -> None:
        plane = self._active_or_warn()
        if plane is None:
            return
        if plane.outline is None:
            QMessageBox.information(self, "Brak obrysu", "Aktywna połać nie ma jeszcze obrysu")
            return
        self._begin_polygon_capture(mode=DrawingCanvas.MODE_DRAW_CUTOUT, handler=self._on_cutout_closed)

    def _begin_polygon_capture(self, *, mode: str, handler) -> None:
        canvas = self._workspace.primary_canvas
        if canvas is None:
            return
        self._disconnect_canvas_capture_signals(canvas)
        canvas.set_mode(mode)
        if mode == canvas.MODE_DRAW_CUTOUT:
            canvas.cutout_closed.connect(handler)
            self.statusBar().showMessage("Rysuj wycinek wewnątrz połaci. Enter lub klik na pkt 1 = zamknij. Esc = anuluj.", 0)
        else:
            canvas.polygon_closed.connect(handler)
            self.statusBar().showMessage("Kliknij, aby dodać wierzchołki. Enter lub klik na pkt 1 = zamknij. Esc = anuluj.", 0)

    def _disconnect_canvas_capture_signals(self, canvas: DrawingCanvas | None) -> None:
        if canvas is None:
            return
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            try:
                canvas.polygon_closed.disconnect(self._on_polygon_closed)
            except (RuntimeError, TypeError):
                pass
            try:
                canvas.cutout_closed.disconnect(self._on_cutout_closed)
            except (RuntimeError, TypeError):
                pass

    def _on_polygon_closed(self, pixel_points: list) -> None:
        canvas = self._workspace.primary_canvas
        self._disconnect_canvas_capture_signals(canvas)
        canvas.set_mode(canvas.MODE_VIEW)

        if len(pixel_points) < 3:
            self.statusBar().showMessage("Za mało punktów — minimum 3.", 4000)
            return

        mapper = canvas._free_draw_mapper()
        outline = Polygon2D(
            [
                mapper.unmap_point(point)
                for point in pixel_points
            ]
        )
        self._set_active_plane_geometry(outline, "Ustawiono obrys z odręcznego rysowania")

    def _on_cutout_closed(self, pixel_points: list) -> None:
        canvas = self._workspace.primary_canvas
        plane = self.project_state.active_roof_plane()
        if canvas is None or plane is None:
            return
        self._disconnect_canvas_capture_signals(canvas)
        canvas.set_mode(canvas.MODE_VIEW)

        if len(pixel_points) < 3:
            self.statusBar().showMessage("Za mało punktów — minimum 3.", 4000)
            return
        if plane.outline is None:
            self.statusBar().showMessage("Aktywna połać nie ma jeszcze obrysu.", 4000)
            return

        mapper = DrawingCanvas.build_view_mapper(plane.outline.bounds(), QRectF(canvas.rect()))
        hole = Polygon2D([mapper.unmap_point(point) for point in pixel_points])
        self._edit(lambda: self.project_state.add_hole_to_plane(hole, plane.id), f"Dodano wycinek do {plane.name}")

    # ------------------------------------------------------------------
    # Report generation
    def _gen_report(self, variant: str, open_external: bool = False) -> bool:
        if not self.project_state.roof_planes:
            QMessageBox.information(self, "Brak połaci", "Brak połaci do raportu")
            return False
        dirty_plane_ids = [plane.id for plane in self.project_state.roof_planes if plane.layout_dirty_reason]
        if dirty_plane_ids:
            answer = QMessageBox.question(
                self,
                "Nieaktualny layout",
                "Niektóre połacie wymagają przeliczenia. Przeliczyć teraz tylko nieaktualne połacie?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes,
            )
            if answer == QMessageBox.StandardButton.Cancel:
                return False
            if answer == QMessageBox.StandardButton.Yes:
                for plane_id in dirty_plane_ids:
                    try:
                        self.project_state.generate_layout_for_plane(plane_id)
                    except ValueError as e:
                        QMessageBox.warning(self, "Błąd przeliczania", str(e))
                        return False
        try:
            report = build_project_report(self.project_state)
            html = build_project_report_html(
                report,
                title_suffix={"continuous": "ciągły", "short": "skrócony"}.get(variant, ""),
                include_aggregated_bom=True,
                include_plane_sheet_tables=(variant != "short"),
                page_break_between_planes=(variant != "continuous"),
            )
        except ValueError as e:
            QMessageBox.warning(self, "Błąd raportu", str(e))
            return False
        self._latest_report_html = html
        self._latest_report_plane_id = None
        self._refresh_dirty_state()
        self._refresh_canvas()
        if open_external:
            suffix = {"continuous": "_ciagly", "short": "_skrocony"}.get(variant, "")
            p = Path(tempfile.gettempdir()) / f"raport-dach{suffix}.html"
            p.write_text(html, encoding="utf-8")
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))
        else:
            self._report_ctrl.show_html(html)
            self._workspace.tabs.setCurrentIndex(self._workspace.report_tab_index())
        return True

    def _recalculate(self) -> None:
        plane = self._active_or_warn()
        if plane is None:
            return
        try:
            self.project_state.generate_layout_for_plane(plane.id)
        except ValueError as e:
            QMessageBox.warning(self, "Błąd przeliczania", str(e))
            return
        self._latest_report_html = ""
        self._latest_report_plane_id = None
        self._refresh_dirty_state()
        self._refresh_canvas()
        self.statusBar().showMessage(f"Przeliczono połać {plane.name}", 4000)

    # ------------------------------------------------------------------
    # Shape dialogs
    def _dlg_prostokat(self) -> None:
        dlg = ProstokatDialog(self._config, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            v = dlg.get_values()
            self._config.setdefault("ksztalty", {})["prostokat"] = v
            outline = make_rectangle(v["szerokosc"], v["wysokosc"])
            self._set_active_plane_geometry(outline, f"Ustawiono obrys prostokąta {v['szerokosc']}×{v['wysokosc']} cm")

    def _dlg_trojkat(self) -> None:
        dlg = TrojkatDialog(self._config, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            v = dlg.get_values()
            side = v["ramie"] if v.get("ramie_enabled") else None
            try:
                outline = make_triangle(v["typ"], v["podstawa"], v["wysokosc"], side)
            except ValueError as e:
                QMessageBox.warning(self, "Błąd edycji", str(e))
                return
            self._config.setdefault("ksztalty", {})["trojkat"] = v
            self._set_active_plane_geometry(outline, f"Ustawiono obrys trójkąta {v['typ']}")

    def _dlg_trapez(self) -> None:
        dlg = TrapezDialog(self._config, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            v = dlg.get_values()
            self._config.setdefault("ksztalty", {})["trapez"] = v
            outline = make_trapezoid(v["typ"], v["podstawa_dolna"], v["podstawa_gorna"], v["wysokosc"])
            self._set_active_plane_geometry(outline, f"Ustawiono obrys trapezu {v['typ']}")

    # ------------------------------------------------------------------
    # Hole dialogs
    def _dlg_add_hole(self) -> None:
        plane = self._active_or_warn()
        if plane is None:
            return
        from ui.dialogs.shape_dialogs import ProstokatDialog
        dlg = ProstokatDialog(self._config, self)
        dlg.setWindowTitle("Prostokątny wycinek")
        if dlg.exec() == QDialog.DialogCode.Accepted:
            v = dlg.get_values()
            w = v["szerokosc"]
            h = v["wysokosc"]
            if plane.outline:
                pts = plane.outline.points
                center_x = sum(p.x for p in pts) / len(pts)
                center_y = sum(p.y for p in pts) / len(pts)
                ox = center_x - w / 2.0
                oy = center_y - h / 2.0
                if plane.holes:
                    max_x = max(hole.bounds().max_x for hole in plane.holes)
                    ox = max_x + 10.0
            else:
                ox = 0.0
                oy = 0.0

            hole = Polygon2D.rectangle(w, h, ox, oy)
            self._edit(lambda: self.project_state.add_hole_to_plane(hole, plane.id), f"Dodano wycinek do {plane.name}")

    def _dlg_del_hole(self) -> None:
        plane = self._active_or_warn()
        if plane is None or not plane.holes:
            QMessageBox.information(self, "Brak wycinków", "Aktywna połać nie ma wycinków")
            return
        canvas = self._workspace.canvas_for_plane(plane.id) or self._workspace.primary_canvas
        idx = canvas.selected_cutout_index() if canvas is not None else None
        if idx is None:
            idx, ok = QInputDialog.getInt(self, "Usuń wycinek", f"Indeks 0-{len(plane.holes)-1}:", 0, 0, len(plane.holes)-1)
            if not ok:
                return
        answer = QMessageBox.question(
            self,
            "Usuń wycinek",
            "Czy na pewno usunąć wybrany wycinek?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._edit(lambda: self.project_state.delete_hole_from_plane(idx, plane.id), f"Usunięto wycinek {idx}")

    def _dlg_move_hole(self) -> None:
        plane = self._active_or_warn()
        if plane is None or not plane.holes:
            QMessageBox.information(self, "Brak wycinków", "Aktywna połać nie ma wycinków")
            return
        idx, ok = QInputDialog.getInt(self, "Przesuń wycinek", f"Indeks 0-{len(plane.holes)-1}:", 0, 0, len(plane.holes)-1)
        if not ok:
            return
        dx, ok = QInputDialog.getDouble(self, "Przesuń wycinek", "Przesunięcie X [cm]:")
        if not ok:
            return
        dy, ok = QInputDialog.getDouble(self, "Przesuń wycinek", "Przesunięcie Y [cm]:")
        if ok:
            self._edit(lambda: self.project_state.move_hole_in_plane(idx, dx, dy, plane.id), f"Przesunięto wycinek {idx}")

    # ------------------------------------------------------------------
    # Sheet dialogs
    def _dlg_add_sheet(self) -> None:
        plane = self._active_or_warn()
        if plane is None:
            return
        band, ok = QInputDialog.getInt(self, "Dodaj arkusz", "Numer pasa:", 0, 0, 999)
        if not ok:
            return
        xl, ok = QInputDialog.getDouble(self, "Dodaj arkusz", "Lewy X [cm]:", 0.0)
        if not ok:
            return
        width, ok = QInputDialog.getDouble(self, "Dodaj arkusz", "Szerokość [cm]:", 50.0, 0.01)
        if not ok:
            return
        yt, ok = QInputDialog.getDouble(self, "Dodaj arkusz", "Górny Y [cm]:", 0.0)
        if not ok:
            return
        length, ok = QInputDialog.getDouble(self, "Dodaj arkusz", "Długość końcowa [cm]:", 100.0, 0.01)
        if not ok:
            return
        s = SheetPlacement(
            id=f"{plane.id}-manual-{plane.layout_revision + len(plane.manual_sheet_placements) + 1}",
            band_index=band, x_left_cm=xl, x_right_cm=xl+width, y_top_cm=yt, y_bottom_cm=yt+length,
            raw_length_cm=length, final_length_cm=length, source="manual",
        )
        self._edit(lambda: self.project_state.add_manual_sheet_placement(s, plane.id), f"Dodano arkusz do {plane.name}")

    def _dlg_del_sheet(self) -> None:
        plane = self._active_or_warn()
        if plane is None:
            return
        sheets = self.project_state.active_sheet_placements_for_plane(plane.id)
        if not sheets:
            QMessageBox.information(self, "Brak arkuszy", "Brak arkuszy do usunięcia")
            return
        idx, ok = QInputDialog.getInt(self, "Usuń arkusz", f"Indeks 0-{len(sheets)-1}:", 0, 0, len(sheets)-1)
        if ok:
            self._edit(lambda: self.project_state.remove_sheet_placement(sheets[idx].id, plane.id), "Usunięto arkusz")

    def _dlg_sheet_preview(self) -> None:
        plane = self._active_or_warn()
        if plane is None:
            return
        sheets = self.project_state.active_sheet_placements_for_plane(plane.id)
        lines = "\n".join(f"{i}. {s.id} | pas {s.band_index} | {s.final_length_cm:.1f} cm" for i, s in enumerate(sheets)) or "Brak"
        QMessageBox.information(self, f"Arkusze — {plane.name}", lines)

    def _dlg_active_sheets(self) -> None:
        plane = self._active_or_warn()
        if plane is None:
            return
        sheets = self.project_state.active_sheet_placements_for_plane(plane.id)
        QMessageBox.information(self, f"Aktywne arkusze — {plane.name}",
            f"Aktywne: {len(sheets)}\nRęczne: {len(plane.manual_sheet_placements)}\nUkryte auto: {len(plane.manually_removed_auto_sheet_ids)}")

    def _dlg_change_material(self) -> None:
        plane = self._active_or_warn()
        if plane is None:
            return
        ids = self.project_state.available_material_ids()
        if not ids:
            QMessageBox.warning(self, "Brak materiałów", "Brak materiałów w katalogu")
            return
        current = plane.selected_material_id or ids[0]
        sel, ok = QInputDialog.getItem(self, "Zmień materiał", "Materiał:", ids,
                                       ids.index(current) if current in ids else 0, False)
        if ok and sel != current:
            self._edit(
                lambda: self.project_state.set_active_material_for_plane(sel, plane.id),
                f"Ustawiono materiał {sel}",
                label=f"Zmiana materiału połaci {plane.name}",
            )

    # ------------------------------------------------------------------
    # Catalogue dialogs
    def _dlg_blachy(self) -> None:
        dlg = BlachyDialog(self.project_state.materials, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._edit(
                lambda: self.project_state.replace_materials(dlg.get_values()),
                "Zaktualizowano katalog materiałów",
                label="Edycja katalogu materiałów",
            )

    def _dlg_firma(self) -> None:
        dlg = DaneFirmyDialog(self._config, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            v = dlg.get_values()
            def _apply_company_data() -> None:
                self._config["company_data"] = v
                self.project_state.company_data = self.project_state.company_data.from_dict(v)
                company = v.get("name", "") or "4Dach"
                self._set_company_title(company)

            self._edit(_apply_company_data, "Zaktualizowano dane firmy", label="Edycja danych firmy")

    def _dlg_settings(self) -> None:
        from ui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self.project_state.app_settings, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_settings = dlg.build_settings()
            def _apply_settings() -> None:
                self.project_state.app_settings = new_settings
                for plane in self.project_state.roof_planes:
                    if plane.outline is not None:
                        plane.layout_dirty_reason = "settings_changed"
            self._edit(_apply_settings, "Zaktualizowano ustawienia aplikacji",
                       label="Zmiana ustawień aplikacji")

    # ------------------------------------------------------------------
    def closeEvent(self, event: QCloseEvent) -> None:
        settings = QSettings()
        settings.setValue("geometry", self.saveGeometry())
        if self._confirm_discard_unsaved_changes(context="zamknięciem programu"):
            event.accept()
        else:
            event.ignore()
