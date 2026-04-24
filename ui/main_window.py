# This Python file uses the following encoding: utf-8
"""ui/main_window.py — slim MainWindow (~150 lines) that mounts controllers."""
from __future__ import annotations
import sys
from pathlib import Path
import tempfile

from PySide6.QtCore import QSettings, QSize, Qt, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QInputDialog, QMainWindow,
    QMenu, QMessageBox, QSizePolicy, QToolButton, QVBoxLayout, QWidget,
)
from PySide6.QtGui import QDesktopServices

from app_icons import build_icon
from persistence import load_config, save_config
from core.models import Point2D, Polygon2D, SheetPlacement
from core.project_state import ProjectState
from core.reporting import build_report, build_report_html
from core.geometry import make_rectangle, make_trapezoid, make_triangle

from ui.theme_manager import ThemeManager
from ui.workspace import WorkspaceController
from ui.report_view import ReportController
from ui.dialogs import BlachyDialog, DaneFirmyDialog, ProstokatDialog, TrapezDialog, TrojkatDialog


def _show_warning(parent, title: str, msg: str) -> None:
    from PySide6.QtWidgets import QMessageBox
    QMessageBox.warning(parent, title, msg)


class MainWindow(QMainWindow):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._config = load_config()
        self.project_state = ProjectState.from_config(self._config)
        self._theme_mgr = ThemeManager()
        self._latest_report_html = ""
        self._latest_report_plane_id: str | None = None

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
        self._workspace.sync()
        self.primary_canvas = self._workspace.primary_canvas
        self._refresh_report()

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
        self.setWindowTitle(f"4Dach — {company}")

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
        plik.addAction(act("Nowa połać", "Ctrl+N", self._add_new_roof_plane))
        plik.addAction(act("Zmień nazwę połaci...", "F2", self._rename_active_roof_plane))
        plik.addAction(act("Usuń połać...", "Ctrl+W", self._delete_active_roof_plane))
        plik.addSeparator()
        plik.addAction(act("Otwórz...", "Ctrl+O"))
        plik.addAction(act("Zapisz", "Ctrl+S"))
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
        wyc.addAction(act("Dodaj wycinek", None, self._dlg_add_hole))
        wyc.addAction(act("Usuń wycinek", None, self._dlg_del_hole))
        wyc.addAction(act("Przesuń wycinek", None, self._dlg_move_hole))

        kat = mb.addMenu("Katalog")
        kat.addAction(act("Blachy...", None, self._dlg_blachy))
        kat.addAction(act("Dane firmy...", None, self._dlg_firma))

        ark = mb.addMenu("Arkusze")
        ark.addAction(act("Dodaj arkusz", "Insert", self._dlg_add_sheet))
        ark.addAction(act("Usuń arkusz", "Delete", self._dlg_del_sheet))
        ark.addAction(act("Podgląd arkuszy", "Ctrl+A", self._dlg_sheet_preview))
        ark.addAction(act("Aktywne arkusze", None, self._dlg_active_sheets))
        ark.addAction(act("Przelicz aktywną połać", "F5", self._recalculate))
        ark.addSeparator()
        ark.addAction(act("Zmień rodzaj blachy", None, self._dlg_change_material))

    def _build_toolbar(self) -> None:
        from ui.toolbar import ToolbarController
        self._tb_ctrl = ToolbarController(self)
        self._tb_ctrl.variant_combo.currentTextChanged.connect(self._on_material_changed)
        self._tb_ctrl.action_grid.triggered.connect(self._on_grid_toggled)
        self._tb_ctrl.action_module_count.triggered.connect(self._on_module_count_toggled)
        self._tb_ctrl.action_from_right.triggered.connect(self._on_from_right_toggled)
        self._tb_ctrl.action_from_base.triggered.connect(self._on_from_base_toggled)
        self._tb_ctrl.action_overlay_sheet.triggered.connect(self._recalculate)
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
    def _persist(self) -> None:
        self.project_state.apply_to_config(self._config)
        save_config(self._config, self)

    def _refresh_canvas(self) -> None:
        plane = self.project_state.active_roof_plane()
        self._workspace.sync()
        self.primary_canvas = self._workspace.primary_canvas
        self.workspace_tabs = self._workspace.tabs
        if plane:
            canvas = self._workspace.canvas_for_plane(plane.id) or self._workspace.primary_canvas
            canvas.set_roof_plane(plane)
            canvas.set_material(self.project_state.material_by_id(plane.selected_material_id))
        self._refresh_report()

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

    def _active_or_warn(self):
        plane = self.project_state.active_roof_plane()
        if plane is None:
            QMessageBox.information(self, "Brak połaci", "Brak aktywnej połaci")
        return plane

    def _edit(self, fn, msg: str) -> bool:
        try:
            fn()
        except (ValueError, IndexError) as e:
            QMessageBox.warning(self, "Błąd edycji", str(e))
            return False
        self._latest_report_html = ""
        self._persist()
        self._refresh_canvas()
        self.statusBar().showMessage(msg, 4000)
        return True

    # ------------------------------------------------------------------
    def _dirty_label(self, reason) -> str:
        return {"geometry_changed": "nieaktualny po zmianie geometrii",
                "material_changed": "nieaktualny po zmianie materiału",
                "manual_override": "zmieniony ręczną korektą"}.get(reason, f"nieaktualny ({reason})")

    def _dirty_hint(self, reason) -> str:
        return "Użyj Arkusze → Przelicz aktywną połać, aby odświeżyć."

    def _tab_title_for_plane(self, plane) -> str:
        return plane.name + (" *" if plane.layout_dirty_reason else "")

    def _set_active_plane_geometry(self, outline: Polygon2D, message: str) -> bool:
        plane = self.project_state.active_roof_plane()
        selected_material_id = self._tb_ctrl.variant_combo.currentText() or None
        if plane is None:
            return self._edit(
                lambda: self.project_state.add_roof_plane(outline, selected_material_id=selected_material_id),
                message,
            )
        return self._edit(lambda: self.project_state.set_roof_plane_outline(outline, plane.id), message)

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
            self._persist()
            self._refresh_material_combo()
            self._refresh_report()
            self.statusBar().showMessage(f"Aktywna połać: {plane.name}", 2500)

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
        rename_action = menu.addAction("Zmień nazwę połaci...")
        delete_action = menu.addAction("Usuń połać...")
        selected = menu.exec(self._workspace.tabs.tabBar().mapToGlobal(pos))
        if selected == rename_action:
            self._rename_roof_plane_by_id(plane_id)
        elif selected == delete_action:
            self._delete_roof_plane_by_id(plane_id)

    def _on_material_changed(self, text: str) -> None:
        if self.project_state.set_active_material_for_plane(text):
            self._latest_report_html = ""
            self._persist()
            self._refresh_canvas()
        self.statusBar().showMessage(f"Aktywna blacha: {text}", 2500)

    def _on_grid_toggled(self, checked: bool) -> None:
        self._workspace.toggle_grid(checked)

    def _on_module_count_toggled(self, checked: bool) -> None:
        self._workspace.toggle_module_count(checked)

    def _on_from_right_toggled(self, checked: bool) -> None:
        plane = self._active_or_warn()
        if plane is None:
            return
        if plane.outline is None:
            QMessageBox.information(self, "Brak obrysu", "Aktywna połać nie ma jeszcze obrysu")
            return
        origin = "right" if checked else "left"
        if plane.generation_settings.layout_origin != origin:
            plane.generation_settings.layout_origin = origin
            plane.layout_dirty_reason = "geometry_changed"
            self._persist()
            self._refresh_canvas()

    def _on_from_base_toggled(self, checked: bool) -> None:
        plane = self._active_or_warn()
        if plane is None:
            return
        if plane.outline is None:
            QMessageBox.information(self, "Brak obrysu", "Aktywna połać nie ma jeszcze obrysu")
            return
        plane.generation_settings.base_line_y_cm = plane.outline.bounds().max_y if checked else None
        plane.layout_dirty_reason = "geometry_changed"
        self._persist()
        self._refresh_canvas()

    # ------------------------------------------------------------------
    # Polygon drawing
    def _start_draw_outline(self) -> None:
        canvas = self._workspace.primary_canvas
        if canvas is None:
            return
        try:
            canvas.polygon_closed.disconnect(self._on_polygon_closed)
        except (RuntimeError, TypeError):
            pass
        canvas.set_mode(canvas.MODE_DRAW_OUTLINE)
        canvas.polygon_closed.connect(self._on_polygon_closed)
        self.statusBar().showMessage("Kliknij, aby dodać wierzchołki. Enter lub klik na pkt 1 = zamknij. Esc = anuluj.", 0)

    def _on_polygon_closed(self, pixel_points: list) -> None:
        canvas = self._workspace.primary_canvas
        try:
            canvas.polygon_closed.disconnect(self._on_polygon_closed)
        except RuntimeError:
            pass
        canvas.set_mode(canvas.MODE_VIEW)

        if len(pixel_points) < 3:
            self.statusBar().showMessage("Za mało punktów — minimum 3.", 4000)
            return

        from PySide6.QtCore import QRectF

        rect = QRectF(canvas.rect())
        if rect.isEmpty():
            self.statusBar().showMessage("Nie udało się odczytać obszaru rysowania.", 4000)
            return

        min_x = min(point.x() for point in pixel_points)
        min_y = min(point.y() for point in pixel_points)
        domain_pts = [Point2D(point.x() - min_x, point.y() - min_y) for point in pixel_points]

        outline = Polygon2D(domain_pts)
        self._set_active_plane_geometry(outline, "Ustawiono obrys z odręcznego rysowania")

    # ------------------------------------------------------------------
    # Report generation
    def _gen_report(self, variant: str, open_external: bool = False) -> bool:
        plane = self._active_or_warn()
        if plane is None:
            return False
        material_id = plane.selected_material_id or self.project_state.active_material_id()
        material = self.project_state.material_by_id(material_id)
        if material is None:
            QMessageBox.warning(self, "Brak materiału", "Brak aktywnego materiału dla połaci")
            return False
        try:
            layout = self.project_state.generate_layout_for_plane(plane.id)
            report = build_report(self.project_state, layout, material_id, plane.id)
            html = build_report_html(self.project_state, report, material_id, plane.id,
                                     title_suffix={"continuous": "ciągły", "short": "skrócony"}.get(variant, ""),
                                     include_bom=(variant != "short"))
        except ValueError as e:
            QMessageBox.warning(self, "Błąd raportu", str(e))
            return False
        self._latest_report_html = html
        self._latest_report_plane_id = plane.id
        self._persist()
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
        if self._gen_report("standard"):
            self.statusBar().showMessage("Przeliczono aktywną połać", 4000)

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
            self._config.setdefault("ksztalty", {})["trojkat"] = v
            side = v["ramie"] if v.get("ramie_enabled") else None
            outline = make_triangle(v["typ"], v["podstawa"], v["wysokosc"], side)
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
        w, ok = QInputDialog.getDouble(self, "Dodaj wycinek", "Szerokość [cm]:", 50.0, 1.0)
        if not ok:
            return
        h, ok = QInputDialog.getDouble(self, "Dodaj wycinek", "Wysokość [cm]:", 50.0, 1.0)
        if not ok:
            return
        ox, ok = QInputDialog.getDouble(self, "Dodaj wycinek", "Lewy górny X [cm]:", 0.0)
        if not ok:
            return
        oy, ok = QInputDialog.getDouble(self, "Dodaj wycinek", "Lewy górny Y [cm]:", 0.0)
        if not ok:
            return
        hole = Polygon2D.rectangle(w, h, ox, oy)
        self._edit(lambda: self.project_state.add_hole_to_plane(hole, plane.id), f"Dodano wycinek do {plane.name}")

    def _dlg_del_hole(self) -> None:
        plane = self._active_or_warn()
        if plane is None or not plane.holes:
            QMessageBox.information(self, "Brak wycinków", "Aktywna połać nie ma wycinków")
            return
        idx, ok = QInputDialog.getInt(self, "Usuń wycinek", f"Indeks 0-{len(plane.holes)-1}:", 0, 0, len(plane.holes)-1)
        if ok:
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
        if ok and self.project_state.set_active_material_for_plane(sel, plane.id):
            self._latest_report_html = ""
            self._persist()
            self._refresh_canvas()

    # ------------------------------------------------------------------
    # Catalogue dialogs
    def _dlg_blachy(self) -> None:
        dlg = BlachyDialog(self._config, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._config["blachy"] = dlg.get_values()
            self._latest_report_html = ""
            self._persist()
            save_config(self._config, self)
            self.project_state = ProjectState.from_config(self._config)
            self._workspace.bind_project_state(self.project_state, self.project_state.material_by_id)
            self._refresh_material_combo()
            self._refresh_canvas()

    def _dlg_firma(self) -> None:
        dlg = DaneFirmyDialog(self._config, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            v = dlg.get_values()
            self._config["company_data"] = v
            self.project_state.company_data = self.project_state.company_data.from_dict(v)
            self._latest_report_html = ""
            self._persist()
            company = v.get("name", "") or "4Dach"
            self.setWindowTitle(f"4Dach — {company}")

    # ------------------------------------------------------------------
    def closeEvent(self, event: QCloseEvent) -> None:
        settings = QSettings()
        settings.setValue("geometry", self.saveGeometry())
        event.accept()
