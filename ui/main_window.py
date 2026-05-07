"""Main application window coordinating project, workspace, and report flows."""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
import warnings
from collections import deque
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QRectF, QSettings, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app_icons import build_icon
from core.geometry import (
    build_add_polac_cutout,
    build_add_polac_outline,
    flip_polygon_in_bounds,
    make_rectangle,
    make_trapezoid,
    make_triangle,
)
from core.models import Point2D, Polygon2D, SheetPlacement
from core.project_state import ProjectState
from core.reporting import build_project_report, build_project_report_html
from core.rounding import ceil_cm
from persistence import load_config, save_config
from project_files import project_config_path, project_dir_from_config_path, project_report_path
from ui.dialogs import (
    AddPolacDialog,
    BlachyDialog,
    CutoutRectangleDialog,
    DaneFirmyDialog,
    ProjectDetailsDialog,
    ProstokatDialog,
    TrapezDialog,
    TrojkatDialog,
)
from ui.dialogs.button_text import (
    show_critical,
    show_information,
    show_question,
    show_warning,
)
from ui.dialogs.project_manager_dialog import Mode, ProjectManagerDialog
from ui.drawing_canvas import CommittedOutlineEdit, DrawingCanvas
from ui.main_window_dialogs import (
    build_centered_hole,
    dialog_accepted,
    remember_shape_config,
)
from ui.main_window_refresh import (
    PostStateChangeRefresh,
    apply_post_state_change_refresh,
    refresh_active_plane_facets,
)
from ui.report_view import ReportController
from ui.theme_manager import ThemeManager
from ui.workspace import WorkspaceController
from user_preferences import UserPreferences


def _localized_question(
    parent,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton,
    default_button: QMessageBox.StandardButton,
) -> QMessageBox.StandardButton:
    return show_question(parent, title, text, buttons, default_button)


def _show_warning(parent, title: str, msg: str) -> None:
    show_warning(parent, title, msg)


@dataclass(slots=True)
class _HistoryEntry:
    label: str
    before_snapshot: dict
    after_snapshot: dict


class MainWindow(QMainWindow):
    def __init__(self, parent=None, *, auto_startup: bool = True) -> None:
        super().__init__(parent)
        self._config = load_config()
        self._user_prefs = UserPreferences()
        if not self._user_prefs.storage_ready:
            self._show_user_preferences_storage_error()
        if self._user_prefs.migrate_from_config(self._config):
            self._user_prefs.save()
        self._inject_user_preferences(self._config)
        self.project_state = ProjectState.from_config(self._config)
        self._theme_mgr = ThemeManager()
        self._latest_report_html = ""
        self._latest_report_plane_id: str | None = None
        undo_depth = self.project_state.app_settings.undo_stack_depth
        self._undo_stack: deque[_HistoryEntry] = deque(maxlen=undo_depth)
        self._redo_stack: deque[_HistoryEntry] = deque(maxlen=undo_depth)
        self._saved_snapshot_signature = ""
        self._saved_plane_snapshot_signatures: dict[str, str] = {}
        self._unsaved_plane_ids: set[str] = set()
        self._has_unsaved_changes = False
        self._base_window_title = ""
        self._snap_to_grid_enabled = self.project_state.app_settings.snap_to_grid
        self._sheets_visible = False
        self._project_file_path: Path | None = None
        self._close_after_startup_cancel = False
        self._last_autosave_error: str | None = None

        self._status_label = QLabel("")
        self._mode_label = QLabel("Tryb: bezczynny")
        self.statusBar().addPermanentWidget(self._mode_label)
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
        self._start_autosave_timer()

        settings = QSettings()
        geo = settings.value("geometry")
        if geo:
            self.restoreGeometry(geo)
        else:
            self.resize(1120, 720)

        self.statusBar().showMessage("Lewy przycisk myszy: rysowanie, prawy: wyczyść szkic", 5000)
        if auto_startup:
            self._show_startup_project_manager()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._close_after_startup_cancel:
            self._close_after_startup_cancel = False
            self.close()

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
        plik.addAction(act("Edytuj projekt...", None, self._edit_project_meta))
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
        plik.addSeparator()
        plik.addAction(act("Zakończ", "Ctrl+Q", self.close))

        ksztalt = mb.addMenu("Kształt")
        ksztalt.addAction(act("Kreator połaci...", None, self._dlg_add_polac))

        wyc = mb.addMenu("Wycinki")
        wyc.addAction(act("Dodaj prostokątny wycinek...", None, self._dlg_add_hole))

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
        self._tb_ctrl.action_print_report.triggered.connect(lambda: self._gen_report("standard", True))
        self._tb_ctrl.action_draw_outline.triggered.connect(self._start_draw_outline)
        self._tb_ctrl.action_draw_cutout.triggered.connect(self._start_draw_cutout)
        self._tb_ctrl.action_new_surface.triggered.connect(self._add_new_roof_plane)
        self._tb_ctrl.action_duplicate_surface.triggered.connect(self._duplicate_active_roof_plane)
        self._tb_ctrl.action_undo.triggered.connect(self._undo)
        self._tb_ctrl.action_trash.triggered.connect(self._delete_selected_geometry)
        self._tb_ctrl.action_trash.setEnabled(False)
        self._tb_ctrl.action_grid.triggered.connect(self._on_grid_toggled)
        self._tb_ctrl.action_grid.setChecked(self.project_state.app_settings.show_grid)
        self._tb_ctrl.action_snap_to_grid.triggered.connect(self._on_snap_to_grid_toggled)
        self._tb_ctrl.action_snap_to_grid.setChecked(self.project_state.app_settings.snap_to_grid)
        self._tb_ctrl.action_base_point_toggle.triggered.connect(self._on_origin_mode_toggled)
        self._tb_ctrl.action_from_left.triggered.connect(self._on_from_left_toggled)
        self._tb_ctrl.action_from_right.triggered.connect(self._on_from_right_toggled)
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
        project_meta = self._config.get("project_meta")
        project_name = project_meta.get("name") if isinstance(project_meta, dict) else ""
        self._base_window_title = f"4Dach — {project_name or company or '4Dach'}"
        self._refresh_window_title()

    def _refresh_base_window_title(self) -> None:
        company = self._config.get("company_data", {}).get("name", "") or "4Dach"
        self._set_company_title(company)

    def _refresh_window_title(self) -> None:
        suffix = " *" if self._has_unsaved_changes else ""
        self.setWindowTitle(f"{self._base_window_title}{suffix}")

    def _serialize_current_config(self) -> dict:
        fragment = copy.deepcopy(self.project_state.to_config_fragment())
        fragment.pop("app_settings", None)
        payload = {
            "project_meta": copy.deepcopy(self._config.get("project_meta", {})),
            "materials": fragment.get("materials", {"order": [], "items": {}}),
            "project_state": fragment.get("project_state", {}),
            "blachy": fragment.get("blachy", []),
        }
        return payload

    def _inject_user_preferences(self, payload: dict) -> dict:
        return self._user_prefs.inject_into_config(payload)

    def _state_config_from_project_payload(self, payload: dict) -> dict:
        return self._inject_user_preferences(copy.deepcopy(payload))

    def _project_display_name(self, fallback: str = "Nowy projekt") -> str:
        project_meta = self._config.get("project_meta")
        if isinstance(project_meta, dict) and project_meta.get("name"):
            return str(project_meta["name"])
        if self._project_file_path is not None:
            return project_dir_from_config_path(self._project_file_path).name
        company = self._config.get("company_data", {}).get("name", "")
        return company or fallback

    def _prepare_payload_for_save(self, payload: dict, project_path: Path) -> dict:
        return self._prepare_payload_for_save_with_meta(payload, project_path, None)

    def _prepare_payload_for_save_with_meta(
        self,
        payload: dict,
        project_path: Path,
        project_meta: dict | None,
    ) -> dict:
        now = datetime.now().astimezone().isoformat()
        meta = copy.deepcopy(payload.get("project_meta") or {})
        if isinstance(project_meta, dict):
            meta.update(copy.deepcopy(project_meta))
        fallback_name = project_dir_from_config_path(project_path).name
        name = str(meta.get("name") or fallback_name).strip() or fallback_name
        meta = {
            "name": name,
            "address": str(meta.get("address") or ""),
            "contact_name": str(meta.get("contact_name") or ""),
            "phone": str(meta.get("phone") or ""),
            "notes": str(meta.get("notes") or ""),
            "created_at": str(meta.get("created_at") or now),
            "modified_at": now,
        }
        payload = copy.deepcopy(payload)
        payload["project_meta"] = meta
        return payload

    def _project_meta_from_dialog(self, dialog: ProjectManagerDialog) -> dict:
        provider = getattr(dialog, "project_meta", None)
        if callable(provider):
            meta = provider()
            if isinstance(meta, dict):
                return copy.deepcopy(meta)
        return {"name": dialog.project_name()}

    def _rename_project_directory_if_needed(self, target_project_path: Path) -> tuple[Path, str | None]:
        current_project_path = self._project_file_path
        if current_project_path is None:
            return target_project_path, None
        current_project_dir = project_dir_from_config_path(current_project_path)
        target_project_dir = project_dir_from_config_path(target_project_path)
        if current_project_dir == target_project_dir:
            return current_project_path, None
        try:
            target_project_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(current_project_dir), str(target_project_dir))
        except OSError:
            return current_project_path, "Nazwa projektu została zmieniona, ale nazwa katalogu pozostała bez zmian."
        return project_config_path(target_project_dir), None

    def _ensure_project_file_parent_ready(self, project_path: Path) -> bool:
        parent = project_path.parent
        try:
            parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=parent, delete=True):
                pass
            return True
        except OSError as exc:
            show_critical(
                self,
                "Błąd katalogu projektu",
                f"Nie można przygotować katalogu projektu:\n{parent}\n\n{exc}",
            )
            return False

    def _show_user_preferences_storage_error(self) -> None:
        candidates = "\n".join(str(path) for path in self._user_prefs.storage_candidates)
        show_critical(
            self,
            "Błąd katalogu 4Dach",
            "Nie można utworzyć katalogu danych użytkownika.\n\n"
            f"Sprawdzone ścieżki:\n{candidates}\n\n"
            "Utwórz folder ręcznie i uruchom aplikację ponownie.",
        )

    def _persist_user_preferences(self, *keys: str) -> None:
        values: dict = {}
        for key in keys:
            if key == "app_settings":
                values[key] = self.project_state.app_settings.to_dict()
            elif key in self._config:
                values[key] = copy.deepcopy(self._config[key])
        if values:
            self._user_prefs.update(values)
            self._user_prefs.save()
            for key, value in values.items():
                self._config[key] = copy.deepcopy(value)

    def _persist_projects_dir(self, projects_dir: Path) -> None:
        self._user_prefs.set("projects_dir", str(projects_dir))
        self._user_prefs.save()

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

    def _invalidate_cached_report(self) -> None:
        self._latest_report_html = ""
        self._latest_report_plane_id = None

    def _refresh_ui_after_state_change(
        self,
        *,
        invalidate_report_cache: bool = False,
        refresh_materials: bool = False,
        dirty_state_mode: str = "preserve",
    ) -> None:
        apply_post_state_change_refresh(
            self,
            PostStateChangeRefresh(
                invalidate_report_cache=invalidate_report_cache,
                refresh_materials=refresh_materials,
                dirty_state_mode=dirty_state_mode,
            ),
        )

    def _plane_has_unsaved_changes(self, plane_id: str | None) -> bool:
        return bool(plane_id and plane_id in self._unsaved_plane_ids)

    def _push_history(self, label: str, before_snapshot: dict, after_snapshot: dict) -> None:
        if before_snapshot == after_snapshot:
            return
        self._undo_stack.append(_HistoryEntry(label, before_snapshot, after_snapshot))
        self._redo_stack.clear()

    def _set_undo_stack_depth(self, depth: int) -> None:
        normalized_depth = max(1, int(depth))
        undo_items = list(self._undo_stack)
        redo_items = list(self._redo_stack)
        self._undo_stack = deque(undo_items[-normalized_depth:], maxlen=normalized_depth)
        self._redo_stack = deque(redo_items[-normalized_depth:], maxlen=normalized_depth)

    def _set_mode_indicator(self, mode: str) -> None:
        display = {
            DrawingCanvas.MODE_IDLE: "bezczynny",
            DrawingCanvas.MODE_DRAW_PLANE: "rysowanie połaci",
            DrawingCanvas.MODE_DRAW_CUT: "rysowanie wycinka",
            DrawingCanvas.MODE_EDIT: "edycja",
            DrawingCanvas.MODE_MOVE: "przesuwanie",
            DrawingCanvas.MODE_SELECT_SHEET: "wybór arkusza",
        }.get(mode, str(mode).upper())
        self._mode_label.setText(f"Tryb: {display}")
        if hasattr(self, "_tb_ctrl"):
            self._tb_ctrl.action_draw_outline.blockSignals(True)
            self._tb_ctrl.action_draw_cutout.blockSignals(True)
            self._tb_ctrl.action_draw_outline.setChecked(mode == DrawingCanvas.MODE_DRAW_PLANE)
            self._tb_ctrl.action_draw_cutout.setChecked(mode == DrawingCanvas.MODE_DRAW_CUT)
            self._tb_ctrl.action_draw_outline.blockSignals(False)
            self._tb_ctrl.action_draw_cutout.blockSignals(False)

    def _active_canvas_mode(self) -> str:
        canvas = getattr(self, "primary_canvas", None)
        if canvas is None:
            return DrawingCanvas.MODE_IDLE
        return canvas.mode()

    def _apply_snapshot(self, snapshot: dict) -> None:
        self._config = self._state_config_from_project_payload(snapshot)
        self.project_state = ProjectState.from_config(self._config)
        self._workspace.bind_project_state(self.project_state, self.project_state.material_by_id)
        self._invalidate_cached_report()
        self._refresh_base_window_title()
        self._refresh_ui_after_state_change(
            invalidate_report_cache=True,
            refresh_materials=True,
            dirty_state_mode="refresh",
        )

    def _save_project(self) -> bool:
        if self._project_file_path is None:
            return self._save_project_as()
        payload = self._prepare_payload_for_save(
            self._serialize_current_config(),
            self._project_file_path,
        )
        if not self._ensure_project_file_parent_ready(self._project_file_path):
            return False
        if not save_config(payload, self, path=self._project_file_path):
            return False
        self._config = self._state_config_from_project_payload(payload)
        self._refresh_base_window_title()
        self._mark_saved_state()
        self._last_autosave_error = None
        self.statusBar().showMessage("Zapisano projekt", 3000)
        return True

    def _save_project_as(self) -> bool:
        dialog = ProjectDetailsDialog(
            projects_dir=self._user_prefs.projects_dir,
            default_name=self._project_display_name(),
            initial_meta=copy.deepcopy(self._config.get("project_meta", {})),
            parent=self,
        )
        if not dialog_accepted(dialog):
            return False
        if self._save_project_from_dialog(dialog) is None:
            return False
        self.statusBar().showMessage("Zapisano projekt pod nową nazwą", 3000)
        return True

    def _save_project_from_dialog(self, dialog, *, payload: dict | None = None) -> dict | None:
        self._persist_projects_dir(dialog.projects_dir())
        project_path = dialog.selected_path()
        if project_path is None:
            return None
        payload_to_save = self._prepare_payload_for_save_with_meta(
            self._serialize_current_config() if payload is None else payload,
            project_path,
            self._project_meta_from_dialog(dialog),
        )
        if not self._ensure_project_file_parent_ready(project_path):
            return None
        if not save_config(payload_to_save, self, path=project_path):
            return None
        self._project_file_path = project_path
        self._config = self._state_config_from_project_payload(payload_to_save)
        self._refresh_base_window_title()
        self._mark_saved_state()
        self._last_autosave_error = None
        return payload_to_save

    def _create_new_project(self) -> bool:
        dialog = ProjectDetailsDialog(
            projects_dir=self._user_prefs.projects_dir,
            default_name="Nowy projekt",
            parent=self,
        )
        if not dialog_accepted(dialog):
            return False
        payload = self._serialize_current_config()
        payload.setdefault("project_state", {})["active_plane_id"] = None
        payload["project_state"]["roof_planes"] = {"order": [], "items": {}}
        saved_payload = self._save_project_from_dialog(dialog, payload=payload)
        if saved_payload is None:
            return False
        self._load_project_payload(
            saved_payload,
            project_file_path=self._project_file_path,
            reset_history=True,
        )
        self.statusBar().showMessage("Utworzono nowy projekt", 3000)
        return True

    def _edit_project_meta(self) -> None:
        dialog = ProjectDetailsDialog(
            projects_dir=self._user_prefs.projects_dir,
            default_name=self._project_display_name(),
            initial_meta=copy.deepcopy(self._config.get("project_meta", {})),
            project_path=self._project_file_path,
            parent=self,
        )
        if not dialog_accepted(dialog):
            return
        self._persist_projects_dir(dialog.projects_dir())
        before_snapshot = self._serialize_current_config()
        renamed_project_path = dialog.selected_path() or self._project_file_path
        rename_warning: str | None = None
        if renamed_project_path is not None:
            self._project_file_path, rename_warning = self._rename_project_directory_if_needed(renamed_project_path)
        self._config["project_meta"] = self._prepare_payload_for_save_with_meta(
            {"project_meta": self._config.get("project_meta", {})},
            self._project_file_path or renamed_project_path or project_config_path(Path(self._project_display_name())),
            self._project_meta_from_dialog(dialog),
        )["project_meta"]
        self._refresh_base_window_title()
        after_snapshot = self._serialize_current_config()
        self._push_history("Edycja danych projektu", before_snapshot, after_snapshot)
        self._refresh_dirty_state()
        if rename_warning is not None:
            show_information(self, "Zmieniono nazwę projektu", rename_warning)
        self.statusBar().showMessage("Zaktualizowano dane projektu", 4000)

    def _start_autosave_timer(self) -> None:
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(5 * 60 * 1000)
        self._autosave_timer.timeout.connect(self._autosave_project_if_needed)
        self._autosave_timer.start()

    def _autosave_project_if_needed(self) -> None:
        if self._project_file_path is None or not self._has_unsaved_changes:
            return
        payload = self._prepare_payload_for_save(
            self._serialize_current_config(),
            self._project_file_path,
        )
        if not self._ensure_project_file_parent_ready(self._project_file_path):
            return
        if not save_config(payload, self, path=self._project_file_path):
            error_key = str(self._project_file_path)
            if self._last_autosave_error != error_key:
                self.statusBar().showMessage("Autozapis nie powiódł się", 5000)
                self._last_autosave_error = error_key
            return
        self._config = self._state_config_from_project_payload(payload)
        self._refresh_base_window_title()
        self._mark_saved_state()
        self._last_autosave_error = None
        self.statusBar().showMessage("Autozapisano projekt", 3000)

    def _confirm_discard_unsaved_changes(self, *, context: str) -> bool:
        if not self._has_unsaved_changes:
            return True
        answer = _localized_question(
            self,
            "Niezapisane zmiany",
            f"Projekt ma niezapisane zmiany. Czy chcesz zapisać przed {context}?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if answer == QMessageBox.StandardButton.Save:
            return self._save_project()
        return answer == QMessageBox.StandardButton.Discard

    def _load_project_payload(self, payload: dict, *, project_file_path: Path | None, reset_history: bool) -> None:
        if reset_history:
            self._undo_stack.clear()
            self._redo_stack.clear()
        self._project_file_path = project_file_path
        self._config = self._state_config_from_project_payload(payload)
        self.project_state = ProjectState.from_config(self._config)
        self._set_undo_stack_depth(self.project_state.app_settings.undo_stack_depth)
        self._workspace.bind_project_state(self.project_state, self.project_state.material_by_id)
        self._invalidate_cached_report()
        self._refresh_base_window_title()
        self._refresh_ui_after_state_change(
            invalidate_report_cache=True,
            refresh_materials=True,
            dirty_state_mode="mark_saved",
        )

    def _new_project(self) -> None:
        if not self._confirm_discard_unsaved_changes(context="utworzeniem nowego projektu"):
            return
        self._create_new_project()

    def _open_project(self) -> None:
        if not self._confirm_discard_unsaved_changes(context="otwarciem projektu"):
            return
        dialog = ProjectManagerDialog(
            mode=Mode.OPEN,
            projects_dir=self._user_prefs.projects_dir,
            parent=self,
        )
        if not dialog_accepted(dialog):
            return
        self._persist_projects_dir(dialog.projects_dir())
        project_path = dialog.selected_path()
        if project_path is None:
            return
        self._load_project_payload(load_config(project_path), project_file_path=project_path, reset_history=True)
        self.statusBar().showMessage("Wczytano projekt", 3000)

    def _show_startup_project_manager(self) -> None:
        dialog = ProjectManagerDialog(
            mode=Mode.STARTUP,
            projects_dir=self._user_prefs.projects_dir,
            parent=self,
        )
        if not dialog_accepted(dialog):
            self._close_after_startup_cancel = True
            return
        self._persist_projects_dir(dialog.projects_dir())
        if dialog.startup_action() == "new":
            self._create_new_project()
            return
        project_path = dialog.selected_path()
        if project_path is not None:
            self._load_project_payload(load_config(project_path), project_file_path=project_path, reset_history=True)

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
            show_warning(self, failure_title, str(e))
            return False

        for plane in self.project_state.roof_planes:
            # Fix #7: Skip auto-regeneration for manual_override to preserve user intent
            if plane.layout_dirty_reason and plane.layout_dirty_reason != "manual_override":
                with suppress(Exception):
                    self.project_state.generate_layout_for_plane(plane.id)

        after_snapshot = self._serialize_current_config()
        self._push_history(label, before_snapshot, after_snapshot)
        self._refresh_ui_after_state_change(
            invalidate_report_cache=True,
            refresh_materials=True,
            dirty_state_mode="refresh",
        )
        if after_refresh is not None:
            after_refresh()
        self.statusBar().showMessage(success_message, 4000)
        return True

    def _refresh_canvas(self) -> None:
        plane = self.project_state.active_roof_plane()
        self._workspace.sync()
        self._workspace.set_sheet_visibility(self._sheets_visible)
        self._snap_to_grid_enabled = self.project_state.app_settings.snap_to_grid
        if hasattr(self, "_tb_ctrl"):
            self._tb_ctrl.action_grid.blockSignals(True)
            self._tb_ctrl.action_grid.setChecked(self.project_state.app_settings.show_grid)
            self._tb_ctrl.action_grid.blockSignals(False)
            self._tb_ctrl.action_snap_to_grid.blockSignals(True)
            self._tb_ctrl.action_snap_to_grid.setChecked(self.project_state.app_settings.snap_to_grid)
            self._tb_ctrl.action_snap_to_grid.blockSignals(False)
            self._tb_ctrl.action_overlay_sheet.blockSignals(True)
            self._tb_ctrl.action_overlay_sheet.setChecked(self._sheets_visible)
            self._tb_ctrl.action_overlay_sheet.blockSignals(False)
        self.primary_canvas = self._workspace.primary_canvas
        self.workspace_tabs = self._workspace.tabs
        for candidate in self._workspace.plane_canvases():
            candidate.set_app_settings(self.project_state.app_settings)
            candidate.toggle_grid(self.project_state.app_settings.show_grid)
            candidate.set_snap_to_grid_enabled(self._snap_to_grid_enabled)
            self._connect_canvas_signals(candidate)
        if plane:
            canvas = self._workspace.canvas_for_plane(plane.id) or self._workspace.primary_canvas
            canvas.set_roof_plane(plane)
            canvas.set_material(self.project_state.material_by_id(plane.selected_material_id))
            canvas.set_app_settings(self.project_state.app_settings)
            canvas.toggle_grid(self.project_state.app_settings.show_grid)
            canvas.set_snap_to_grid_enabled(self._snap_to_grid_enabled)
        elif self.primary_canvas is not None:
            self.primary_canvas.set_app_settings(self.project_state.app_settings)
            self.primary_canvas.toggle_grid(self.project_state.app_settings.show_grid)
            self.primary_canvas.set_snap_to_grid_enabled(self._snap_to_grid_enabled)
        self._refresh_active_plane_facets()
        self._refresh_tab_titles()

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
        display_by_id = {material.id: material.display_name for material in self.project_state.materials}
        combo.blockSignals(True)
        combo.clear()
        if ids:
            combo.addItems([display_by_id.get(material_id, material_id) for material_id in ids])
            plane = self.project_state.active_roof_plane()
            preferred = (plane.selected_material_id if plane else None) or ids[0]
            preferred_id = preferred if preferred in ids else ids[0]
            combo.setCurrentText(display_by_id.get(preferred_id, preferred_id))
        combo.blockSignals(False)
        self._sync_layout_direction_actions()

    def _selected_material_id_from_combo(self) -> str | None:
        selected_text = self._tb_ctrl.variant_combo.currentText()
        if not selected_text:
            return None
        return self._material_id_from_display_text(selected_text)

    def _material_id_from_display_text(self, selected_text: str) -> str:
        for material in self.project_state.materials:
            if selected_text == material.display_name or selected_text == material.id:
                return material.id
        return selected_text

    def _active_or_warn(self):
        return self._require_active_plane("Brak połaci", "Brak aktywnej połaci")

    def _active_with_outline_or_warn(self):
        plane = self._require_active_plane("Brak połaci", "Brak aktywnej połaci")
        if plane is None:
            return None
        if plane.outline is None:
            show_information(self, "Brak obrysu", "Aktywna połać nie ma jeszcze obrysu")
            return None
        return plane

    def _active_with_holes_or_warn(self):
        plane = self._require_active_plane("Brak połaci", "Brak aktywnej połaci")
        if plane is None:
            return None
        if not plane.holes:
            show_information(self, "Brak wycinków", "Aktywna połać nie ma wycinków")
            return None
        return plane

    def _connect_canvas_signal(self, signal, slot) -> None:
        with suppress(TypeError):
            signal.connect(slot, Qt.ConnectionType.UniqueConnection)

    def _connect_canvas_signals(self, canvas: DrawingCanvas) -> None:
        self._connect_canvas_signal(canvas.outline_edit_committed, self._on_outline_edit_committed)
        self._connect_canvas_signal(canvas.outline_edit_rejected, self._on_outline_edit_rejected)
        self._connect_canvas_signal(canvas.hole_edit_committed, self._on_hole_edit_committed)
        self._connect_canvas_signal(canvas.origin_edit_committed, self._on_origin_edit_committed)
        self._connect_canvas_signal(canvas.selection_changed, self._on_selection_changed)
        self._connect_canvas_signal(canvas.delete_requested, self._delete_selected_geometry)
        self._connect_canvas_signal(canvas.mode_changed, self._on_canvas_mode_changed)

    def _require_active_plane(self, title: str, message: str):
        plane = self.project_state.active_roof_plane()
        if plane is None:
            show_information(self, title, message)
        return plane

    def _focus_active_plane_tab(self) -> None:
        active_plane = self.project_state.active_roof_plane()
        if active_plane is None:
            return
        index = self._workspace.tab_index_for_plane(active_plane.id)
        if index >= 0:
            self._workspace.tabs.setCurrentIndex(index)

    def _confirm_yes_no(self, title: str, message: str, *, default=QMessageBox.StandardButton.No) -> bool:
        answer = _localized_question(
            self,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            default,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _select_index(self, title: str, upper_bound: int) -> int | None:
        index, ok = QInputDialog.getInt(self, title, f"Indeks 0-{upper_bound}:", 0, 0, upper_bound)
        return index if ok else None

    def _recalculate_plane(self, plane_id: str) -> None:
        self.project_state.generate_layout_for_plane(plane_id)

    def _recalculate_planes_or_warn(self, plane_ids: list[str]) -> bool:
        for plane_id in plane_ids:
            try:
                self._recalculate_plane(plane_id)
            except ValueError as e:
                show_warning(self, "Błąd przeliczania", str(e))
                return False
        return True

    def _manual_sheet_values(self) -> tuple[int, int, int, int, int] | None:
        band, ok = QInputDialog.getInt(self, "Dodaj arkusz", "Numer pasa:", 0, 0, 999)
        if not ok:
            return None
        left_x, ok = QInputDialog.getInt(self, "Dodaj arkusz", "Lewy X [cm]:", 0)
        if not ok:
            return None
        width_cm, ok = QInputDialog.getInt(self, "Dodaj arkusz", "Szerokość [cm]:", 50, 1)
        if not ok:
            return None
        top_y, ok = QInputDialog.getInt(self, "Dodaj arkusz", "Górny Y [cm]:", 0)
        if not ok:
            return None
        length_cm, ok = QInputDialog.getInt(self, "Dodaj arkusz", "Długość końcowa [cm]:", 100, 1)
        if not ok:
            return None
        return band, left_x, width_cm, top_y, length_cm

    def _build_manual_sheet_placement(
        self,
        plane,
        *,
        band_index: int,
        left_x_cm: float,
        width_cm: float,
        top_y_cm: float,
        length_cm: float,
    ) -> SheetPlacement:
        return SheetPlacement(
            id=f"{plane.id}-manual-{plane.layout_revision + len(plane.manual_sheet_placements) + 1}",
            band_index=band_index,
            x_left_cm=left_x_cm,
            x_right_cm=left_x_cm + width_cm,
            y_top_cm=top_y_cm,
            y_bottom_cm=top_y_cm + length_cm,
            raw_length_cm=length_cm,
            final_length_cm=length_cm,
            source="manual",
        )

    def _active_plane_sheets(self, plane) -> list[SheetPlacement]:
        return self.project_state.active_sheet_placements_for_plane(plane.id)

    def _select_material_id(self, plane, material_ids: list[str]) -> str | None:
        current = plane.selected_material_id or material_ids[0]
        display_by_id = {
            material.id: material.display_name
            for material in self.project_state.materials
            if material.id in material_ids
        }
        display_items = [display_by_id.get(material_id, material_id) for material_id in material_ids]
        selected, ok = QInputDialog.getItem(
            self,
            "Zmień materiał",
            "Materiał:",
            display_items,
            material_ids.index(current) if current in material_ids else 0,
            False,
        )
        if not ok:
            return None
        return material_ids[display_items.index(selected)]

    def _sheet_preview_text(self, sheets: list[SheetPlacement]) -> str:
        return "\n".join(
            f"{index}. {sheet.id} | pas {sheet.band_index} | {ceil_cm(sheet.final_length_cm)} cm"
            for index, sheet in enumerate(sheets)
        ) or "Brak"

    def _active_sheet_summary_text(self, plane, sheets: list[SheetPlacement]) -> str:
        return (
            f"Aktywne: {len(sheets)}\n"
            f"Ręczne: {len(plane.manual_sheet_placements)}\n"
            f"Ukryte auto: {len(plane.manually_removed_auto_sheet_ids)}"
        )

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
        self.project_state.set_plane_layout_origin(plane_id, origin)

    def _sync_layout_direction_actions(self) -> None:
        plane = self.project_state.active_roof_plane()
        from_left = plane is None or plane.generation_settings.layout_origin != "right"
        self._tb_ctrl.action_from_left.blockSignals(True)
        self._tb_ctrl.action_from_right.blockSignals(True)
        self._tb_ctrl.action_from_left.setChecked(from_left)
        self._tb_ctrl.action_from_right.setChecked(not from_left)
        self._tb_ctrl.action_from_left.blockSignals(False)
        self._tb_ctrl.action_from_right.blockSignals(False)

    def _set_plane_coordinate_origin(self, plane_id: str, origin: Point2D) -> None:
        self.project_state.set_plane_coordinate_origin(plane_id, origin)

    def _refresh_active_canvas_selection_state(self) -> None:
        if self.primary_canvas:
            is_selected = self.primary_canvas._plane_selected or self.primary_canvas._selected_hole_index is not None
            self._on_selection_changed(is_selected)
            self._set_mode_indicator(self.primary_canvas.mode())
            return
        self._set_mode_indicator(DrawingCanvas.MODE_IDLE)

    def _refresh_active_plane_facets(self) -> None:
        refresh_active_plane_facets(self)

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
        selected_material_id = self._selected_material_id_from_combo()
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
        selected_material_id = self._selected_material_id_from_combo()
        if self._edit(
            lambda: self.project_state.add_empty_roof_plane(selected_material_id=selected_material_id),
            "Dodano nową połacię",
        ):
            self._focus_active_plane_tab()

    def _duplicate_active_roof_plane(self) -> None:
        plane = self._active_or_warn()
        if plane is None:
            return
        if self._edit(
            lambda: self.project_state.duplicate_roof_plane(plane.id),
            f"Zduplikowano połacię {plane.name}",
            label=f"Duplikacja połaci {plane.name}",
        ):
            self._focus_active_plane_tab()

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
        if self._confirm_yes_no("Usuń połać", f"Czy na pewno usunąć połacię „{plane.name}”?"):
            self._edit(lambda: self.project_state.delete_roof_plane(plane.id), f"Usunięto połacię {plane.name}")

    def _delete_active_roof_plane(self) -> None:
        plane = self._active_or_warn()
        if plane is not None:
            self._delete_roof_plane_by_id(plane.id)

    # ------------------------------------------------------------------
    # Signal handlers
    def _on_tab_changed(self, index: int) -> None:
        if index < 0:
            return
        plane_id = self._workspace.plane_id_for_tab_index(index)
        if plane_id is None:
            return
        plane = self.project_state.roof_plane_by_id(plane_id)
        if plane and self.project_state.set_active_plane(plane.id):
            self._workspace.primary_canvas = self._workspace.canvas_for_plane(plane.id) or self._workspace.primary_canvas
            self.primary_canvas = self._workspace.primary_canvas
            self._refresh_material_combo()
            self._refresh_active_plane_facets()
            self.statusBar().showMessage(f"Aktywna połać: {plane.name}", 2500)

    def _on_selection_changed(self, is_selected: bool) -> None:
        if hasattr(self, '_tb_ctrl') and hasattr(self._tb_ctrl, 'action_trash'):
            self._tb_ctrl.action_trash.setEnabled(is_selected)
        if self.primary_canvas is not None and self.primary_canvas.mode() in {DrawingCanvas.MODE_IDLE, DrawingCanvas.MODE_EDIT}:
            if is_selected:
                self._set_mode_indicator(DrawingCanvas.MODE_EDIT)
            else:
                self._set_mode_indicator(DrawingCanvas.MODE_IDLE)

    def _on_canvas_mode_changed(self, mode: str) -> None:
        self._set_mode_indicator(mode)

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
            if self._confirm_yes_no("Usuń połać", "Czy na pewno usunąć wybraną połać?"):
                self._delete_active_roof_plane()

    def _on_tab_close_requested(self, index: int) -> None:
        plane_id = self._workspace.plane_id_for_tab_index(index)
        if plane_id is not None:
            self._delete_roof_plane_by_id(plane_id)

    def _on_tab_bar_double_clicked(self, index: int) -> None:
        if index < 0:
            return
        plane_id = self._workspace.plane_id_for_tab_index(index)
        if plane_id is not None:
            self._rename_roof_plane_by_id(plane_id)

    def _open_tab_context_menu(self, pos) -> None:
        index = self._workspace.tabs.tabBar().tabAt(pos)
        if index < 0:
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
        material_id = self._material_id_from_display_text(text)
        if not material_id:
            return
        if plane.selected_material_id == material_id:
            self.statusBar().showMessage(f"Aktywna blacha: {text}", 2500)
            return
        self._edit(
            lambda: self.project_state.set_active_material_for_plane(material_id, plane.id),
            f"Ustawiono materiał {text}",
            label=f"Zmiana materiału połaci {plane.name}",
        )

    def _on_outline_edit_committed(self, outline: Polygon2D | CommittedOutlineEdit) -> None:
        canvas = self.sender() if isinstance(self.sender(), DrawingCanvas) else self.primary_canvas
        selection_snapshot = canvas.selection_snapshot() if isinstance(canvas, DrawingCanvas) else None
        plane = self.project_state.active_roof_plane()
        plane_id = plane.id if plane is not None else None
        committed_outline = outline.outline if isinstance(outline, CommittedOutlineEdit) else outline
        committed_holes = outline.holes if isinstance(outline, CommittedOutlineEdit) else None
        edit_operation = outline.operation if isinstance(outline, CommittedOutlineEdit) else "outline_edit"
        self._edit(
            lambda: self.project_state.set_roof_plane_geometry(committed_outline, committed_holes, plane_id)
            if committed_holes is not None
            else self.project_state.set_roof_plane_outline(committed_outline, plane_id),
            "Zaktualizowano geometrię połaci",
            label=f"Zmiana geometrii połaci ({edit_operation})",
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
        show_warning(self, "Nieprawidłowa geometria", message)
        self.statusBar().showMessage("Odrzucono zmianę geometrii połaci", 4000)

    def _on_grid_toggled(self, checked: bool) -> None:
        self.project_state.app_settings.show_grid = checked
        self._workspace.toggle_grid(checked)
        self._persist_user_preferences("app_settings")

    def _on_snap_to_grid_toggled(self, checked: bool) -> None:
        self._snap_to_grid_enabled = checked
        self.project_state.app_settings.snap_to_grid = checked
        self._workspace.set_snap_to_grid_enabled(checked)
        self._persist_user_preferences("app_settings")

    def _on_sheet_visibility_toggled(self, checked: bool) -> None:
        self._sheets_visible = checked
        self._workspace.set_sheet_visibility(checked)
        self._refresh_status_bar_info()
        message = "Pokazano arkusze" if checked else "Ukryto arkusze i włączono widok obrysów"
        self.statusBar().showMessage(message, 3000)

    def _on_origin_mode_toggled(self, checked: bool) -> None:
        if checked and self._active_with_outline_or_warn() is None:
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
        plane = self._active_with_outline_or_warn()
        if plane is None:
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

    # ------------------------------------------------------------------
    # Polygon drawing
    def _start_draw_outline(self) -> None:
        self._begin_polygon_capture(mode=DrawingCanvas.MODE_DRAW_PLANE, handler=self._on_polygon_closed)

    def _start_draw_cutout(self) -> None:
        if self._active_with_outline_or_warn() is None:
            return
        self._begin_polygon_capture(mode=DrawingCanvas.MODE_DRAW_CUT, handler=self._on_cutout_closed)

    def _begin_polygon_capture(self, *, mode: str, handler) -> None:
        canvas = self._workspace.primary_canvas
        if canvas is None:
            return
        self._disconnect_canvas_capture_signals(canvas)
        canvas.set_mode(mode)
        self._set_mode_indicator(mode)
        if mode == canvas.MODE_DRAW_CUT:
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
            with suppress(RuntimeError, TypeError):
                canvas.polygon_closed.disconnect(self._on_polygon_closed)
            with suppress(RuntimeError, TypeError):
                canvas.cutout_closed.disconnect(self._on_cutout_closed)

    def _on_polygon_closed(self, pixel_points: list) -> None:
        canvas = self._workspace.primary_canvas
        if canvas is None:
            return

        if len(pixel_points) < 3:
            self._disconnect_canvas_capture_signals(canvas)
            canvas.set_mode(canvas.MODE_IDLE)
            self._set_mode_indicator(canvas.mode())
            self.statusBar().showMessage("Za mało punktów — minimum 3.", 4000)
            return

        mapper = canvas._free_draw_mapper()
        outline = Polygon2D(
            [
                canvas._pixel_to_domain_point(point, mapper)
                for point in pixel_points
            ]
        )
        self._disconnect_canvas_capture_signals(canvas)
        canvas.set_mode(canvas.MODE_IDLE)
        self._set_mode_indicator(canvas.mode())
        self._set_active_plane_geometry(outline, "Ustawiono obrys z odręcznego rysowania")

    def _on_cutout_closed(self, pixel_points: list) -> None:
        canvas = self._workspace.primary_canvas
        plane = self.project_state.active_roof_plane()
        if canvas is None or plane is None:
            return

        if len(pixel_points) < 3:
            self._disconnect_canvas_capture_signals(canvas)
            canvas.set_mode(canvas.MODE_IDLE)
            self._set_mode_indicator(canvas.mode())
            self.statusBar().showMessage("Za mało punktów — minimum 3.", 4000)
            return
        if plane.outline is None:
            self._disconnect_canvas_capture_signals(canvas)
            canvas.set_mode(canvas.MODE_IDLE)
            self._set_mode_indicator(canvas.mode())
            self.statusBar().showMessage("Aktywna połać nie ma jeszcze obrysu.", 4000)
            return

        mapper = DrawingCanvas.build_view_mapper(plane.outline.bounds(), QRectF(canvas.rect()))
        hole = Polygon2D([canvas._pixel_to_domain_point(point, mapper) for point in pixel_points])
        self._disconnect_canvas_capture_signals(canvas)
        canvas.set_mode(canvas.MODE_IDLE)
        self._set_mode_indicator(canvas.mode())
        self._edit(lambda: self.project_state.add_hole_to_plane(hole, plane.id), f"Dodano wycinek do {plane.name}")

    # ------------------------------------------------------------------
    # Report generation
    def _gen_report(self, variant: str, open_external: bool = False) -> bool:
        if not self.project_state.roof_planes:
            show_information(self, "Brak połaci", "Brak połaci do raportu")
            return False
        dirty_plane_ids = [plane.id for plane in self.project_state.roof_planes if plane.layout_dirty_reason]
        if dirty_plane_ids:
            answer = _localized_question(
                self,
                "Nieaktualny layout",
                "Niektóre połacie wymagają przeliczenia. Przeliczyć teraz tylko nieaktualne połacie?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes,
            )
            if answer == QMessageBox.StandardButton.Cancel:
                return False
            if answer == QMessageBox.StandardButton.Yes and not self._recalculate_planes_or_warn(dirty_plane_ids):
                return False
        try:
            report = build_project_report(self.project_state, self._config.get("project_meta"))
            html = build_project_report_html(
                report,
                title_suffix={"continuous": "ciągły", "short": "skrócony"}.get(variant, ""),
                include_aggregated_bom=True,
                include_plane_sheet_tables=(variant != "short"),
                page_break_between_planes=(variant != "continuous"),
            )
        except ValueError as e:
            show_warning(self, "Błąd raportu", str(e))
            return False
        self._latest_report_html = html
        self._latest_report_plane_id = None
        self._refresh_ui_after_state_change(dirty_state_mode="refresh")
        report_path: Path | None = None
        if self._project_file_path is not None:
            report_path = project_report_path(project_dir_from_config_path(self._project_file_path))
            if not self._ensure_project_file_parent_ready(self._project_file_path):
                return False
            try:
                report_path.write_text(html, encoding="utf-8")
            except OSError as exc:
                show_warning(self, "Błąd raportu", f"Nie można zapisać raportu HTML:\n{exc}")
                return False
        if open_external:
            if report_path is None:
                show_information(
                    self,
                    "Zapisz projekt",
                    "Aby otworzyć raport w przeglądarce, najpierw zapisz projekt.",
                )
                return False
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(report_path)))
        else:
            self._report_ctrl.show_html(html)
            active_index = self._workspace.tab_index_for_plane(self.project_state.active_plane_id)
            if active_index >= 0:
                self._workspace.tabs.setCurrentIndex(active_index)
        return True

    def _recalculate(self) -> None:
        plane = self._active_or_warn()
        if plane is None:
            return
        if not self._recalculate_planes_or_warn([plane.id]):
            return
        self._refresh_ui_after_state_change(
            invalidate_report_cache=True,
            dirty_state_mode="refresh",
        )
        self.statusBar().showMessage(f"Przeliczono połać {plane.name}", 4000)

    # ------------------------------------------------------------------
    # Shape dialogs
    def _dlg_add_polac(self) -> None:
        dlg = AddPolacDialog(self._config, self)
        if not dialog_accepted(dlg):
            return
        result = dlg.get_result()
        if result is None:
            return
        self._persist_user_preferences("add_polac_dialog")

        try:
            outline = build_add_polac_outline(result.shape_key, result.shape_values)
            outline = flip_polygon_in_bounds(
                outline,
                horizontal=result.flip_h,
                vertical=result.flip_v,
            )
            cutout = build_add_polac_cutout(result.cutout_kind, result.cutout_values, outline)
        except ValueError as exc:
            show_warning(self, "Błąd edycji", str(exc))
            return

        holes = [] if cutout is None else [cutout]
        plane = self.project_state.active_roof_plane()
        selected_material_id = self._selected_material_id_from_combo()

        def _apply_wizard_geometry() -> None:
            if plane is None:
                created_plane = self.project_state.add_roof_plane(
                    outline,
                    selected_material_id=selected_material_id,
                )
                self.project_state.set_roof_plane_geometry(outline, holes, created_plane.id)
                return
            self.project_state.set_roof_plane_geometry(outline, holes, plane.id)

        if self._edit(
            _apply_wizard_geometry,
            "Ustawiono geometrię połaci z kreatora",
            label="Kreator połaci",
        ):
            self._focus_active_plane_tab()

    def _dlg_prostokat(self) -> None:
        dlg = ProstokatDialog(self._config, self)
        if not dialog_accepted(dlg):
            return
        values = dlg.get_values()
        remember_shape_config(self._config, "prostokat", values)
        self._persist_user_preferences("ksztalty")
        outline = make_rectangle(values["szerokosc"], values["wysokosc"])
        self._set_active_plane_geometry(
            outline,
            f"Ustawiono obrys prostokąta {values['szerokosc']}×{values['wysokosc']} cm",
        )

    def _dlg_trojkat(self) -> None:
        dlg = TrojkatDialog(self._config, self)
        if not dialog_accepted(dlg):
            return
        values = dlg.get_values()
        side = values["ramie"] if values.get("ramie_enabled") else None
        try:
            outline = make_triangle(values["typ"], values["podstawa"], values["wysokosc"], side)
        except ValueError as e:
            show_warning(self, "Błąd edycji", str(e))
            return
        remember_shape_config(self._config, "trojkat", values)
        self._persist_user_preferences("ksztalty")
        self._set_active_plane_geometry(outline, f"Ustawiono obrys trójkąta {values['typ']}")

    def _dlg_trapez(self) -> None:
        dlg = TrapezDialog(self._config, self)
        if not dialog_accepted(dlg):
            return
        values = dlg.get_values()
        remember_shape_config(self._config, "trapez", values)
        self._persist_user_preferences("ksztalty")
        outline = make_trapezoid(
            values["typ"],
            values["podstawa_dolna"],
            values["podstawa_gorna"],
            values["wysokosc"],
        )
        self._set_active_plane_geometry(outline, f"Ustawiono obrys trapezu {values['typ']}")

    # ------------------------------------------------------------------
    # Hole dialogs
    def _dlg_add_hole(self) -> None:
        plane = self._active_or_warn()
        if plane is None:
            return
        dlg = CutoutRectangleDialog(self._config, self)
        dlg.setWindowTitle("Prostokątny wycinek")
        if not dialog_accepted(dlg):
            return
        values = dlg.get_values()
        self._config.setdefault("wycinki", {})["prostokat"] = dict(values)
        self._persist_user_preferences("wycinki")
        hole = build_centered_hole(plane, values["szerokosc"], values["wysokosc"])
        self._edit(lambda: self.project_state.add_hole_to_plane(hole, plane.id), f"Dodano wycinek do {plane.name}")

    def _dlg_del_hole(self) -> None:
        plane = self._active_with_holes_or_warn()
        if plane is None:
            return
        canvas = self._workspace.canvas_for_plane(plane.id) or self._workspace.primary_canvas
        idx = canvas.selected_cutout_index() if canvas is not None else None
        if idx is None:
            idx = self._select_index("Usuń wycinek", len(plane.holes) - 1)
            if idx is None:
                return
        if self._confirm_yes_no("Usuń wycinek", "Czy na pewno usunąć wybrany wycinek?"):
            self._edit(lambda: self.project_state.delete_hole_from_plane(idx, plane.id), f"Usunięto wycinek {idx}")

    def _dlg_move_hole(self) -> None:
        plane = self._active_with_holes_or_warn()
        if plane is None:
            return
        idx = self._select_index("Przesuń wycinek", len(plane.holes) - 1)
        if idx is None:
            return
        dx, ok = QInputDialog.getInt(self, "Przesuń wycinek", "Przesunięcie X [cm]:", 0)
        if not ok:
            return
        dy, ok = QInputDialog.getInt(self, "Przesuń wycinek", "Przesunięcie Y [cm]:", 0)
        if ok:
            self._edit(lambda: self.project_state.move_hole_in_plane(idx, dx, dy, plane.id), f"Przesunięto wycinek {idx}")

    # ------------------------------------------------------------------
    # Sheet dialogs
    def _dlg_add_sheet(self) -> None:
        plane = self._active_or_warn()
        if plane is None:
            return
        values = self._manual_sheet_values()
        if values is None:
            return
        band, left_x, width_cm, top_y, length_cm = values
        placement = self._build_manual_sheet_placement(
            plane,
            band_index=band,
            left_x_cm=left_x,
            width_cm=width_cm,
            top_y_cm=top_y,
            length_cm=length_cm,
        )
        self._edit(
            lambda: self.project_state.add_manual_sheet_placement(placement, plane.id),
            f"Dodano arkusz do {plane.name}",
        )

    def _dlg_del_sheet(self) -> None:
        plane = self._active_or_warn()
        if plane is None:
            return
        sheets = self._active_plane_sheets(plane)
        if not sheets:
            show_information(self, "Brak arkuszy", "Brak arkuszy do usunięcia")
            return
        idx = self._select_index("Usuń arkusz", len(sheets) - 1)
        if idx is not None:
            self._edit(lambda: self.project_state.remove_sheet_placement(sheets[idx].id, plane.id), "Usunięto arkusz")

    def _dlg_sheet_preview(self) -> None:
        plane = self._active_or_warn()
        if plane is None:
            return
        sheets = self._active_plane_sheets(plane)
        show_information(self, f"Arkusze — {plane.name}", self._sheet_preview_text(sheets))

    def _dlg_active_sheets(self) -> None:
        plane = self._active_or_warn()
        if plane is None:
            return
        sheets = self._active_plane_sheets(plane)
        show_information(
            self,
            f"Aktywne arkusze — {plane.name}",
            self._active_sheet_summary_text(plane, sheets),
        )

    def _dlg_change_material(self) -> None:
        plane = self._active_or_warn()
        if plane is None:
            return
        ids = self.project_state.available_material_ids()
        if not ids:
            show_warning(self, "Brak materiałów", "Brak materiałów w katalogu")
            return
        selected_material_id = self._select_material_id(plane, ids)
        if selected_material_id and selected_material_id != plane.selected_material_id:
            self._edit(
                lambda: self.project_state.set_active_material_for_plane(selected_material_id, plane.id),
                f"Ustawiono materiał {selected_material_id}",
                label=f"Zmiana materiału połaci {plane.name}",
            )

    # ------------------------------------------------------------------
    # Catalogue dialogs
    def _dlg_blachy(self) -> None:
        dlg = BlachyDialog(self.project_state.materials, self)
        if not dialog_accepted(dlg):
            return
        self._edit(
            lambda: self.project_state.replace_materials(dlg.get_values()),
            "Zaktualizowano katalog materiałów",
            label="Edycja katalogu materiałów",
        )

    def _dlg_firma(self) -> None:
        dlg = DaneFirmyDialog(self._config, self)
        if not dialog_accepted(dlg):
            return
        values = dlg.get_values()
        self._config["company_data"] = values
        self.project_state.company_data = self.project_state.company_data.from_dict(values)
        self._persist_user_preferences("company_data")
        self._refresh_base_window_title()
        self._refresh_report()
        self.statusBar().showMessage("Zaktualizowano dane firmy", 4000)

    def _dlg_settings(self) -> None:
        from ui.dialogs.settings_dialog import SettingsDialog

        dlg = SettingsDialog(self.project_state.app_settings, parent=self)
        if not dialog_accepted(dlg):
            return
        new_settings = dlg.build_settings()
        self.project_state.app_settings = new_settings
        self._set_undo_stack_depth(new_settings.undo_stack_depth)
        self._snap_to_grid_enabled = new_settings.snap_to_grid
        self._persist_user_preferences("app_settings")
        self._refresh_canvas()
        self.statusBar().showMessage("Zaktualizowano ustawienia aplikacji", 4000)

    # ------------------------------------------------------------------
    def closeEvent(self, event: QCloseEvent) -> None:
        settings = QSettings()
        settings.setValue("geometry", self.saveGeometry())
        if self._confirm_discard_unsaved_changes(context="zamknięciem programu"):
            event.accept()
        else:
            event.ignore()
