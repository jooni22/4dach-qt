# This Python file uses the following encoding: utf-8
import sys

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QUrl, Signal
from PySide6.QtGui import QAction, QColor, QFont, QKeyEvent, QKeySequence, QMouseEvent, QPainter, QPalette, QPen, QPolygonF
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QTabWidget,
    QTextBrowser,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QDesktopServices

from app_icons import build_icon

# Important:
# You need to run the following command to generate the ui_form.py file
#     pyside6-uic form.ui -o ui_form.py, or
#     pyside2-uic form.ui -o ui_form.py
from ui_form import Ui_MainWindow

from dialogs import (
    BlachyDialog,
    DaneFirmyDialog,
    ProstokatDialog,
    TrapezDialog,
    TrojkatDialog,
    load_config,
    save_config,
    show_ostrzezenie_dialog,
)
from core.canvas_mapper import CanvasMapper
from core.geometry import build_rectangle_outline, build_trapezoid_outline, build_triangle_outline
from core.models import Point2D, Polygon2D, SheetPlacement
from core.project_state import ProjectState
from core.reporting import build_report, build_report_html


class DrawingCanvas(QWidget):
    MODE_VIEW = "view"
    MODE_DRAW_OUTLINE = "draw_outline"
    MODE_SELECT_SHEET = "select_sheet"
    MODE_MOVE_VERTEX = "move_vertex"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_points: list[QPointF] = []
        self.preview_point: QPointF | None = None
        self.roof_plane = None
        self._mode = self.MODE_VIEW
        self._selected_sheet_id: str | None = None
        self._show_grid = False
        self._show_module_count = False
        self._material = None
        # Zoom / pan
        self._zoom = 1.0
        self._pan_x = 0.0
        self._pan_y = 0.0
        self._dragging_vertex_index: int | None = None
        self._drag_start_point: QPointF | None = None
        # Undo/redo for user_points
        self._user_points_history: list[list[QPointF]] = []
        self._user_points_redo: list[list[QPointF]] = []
        self.setMouseTracking(True)
        self.setAutoFillBackground(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(640, 420)

    def toggle_grid(self, enabled: bool | None = None):
        self._show_grid = not self._show_grid if enabled is None else enabled
        self.update()

    def toggle_module_count(self, enabled: bool | None = None):
        self._show_module_count = not self._show_module_count if enabled is None else enabled
        self.update()

    def set_mode(self, mode: str):
        self._mode = mode
        if mode == self.MODE_DRAW_OUTLINE:
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif mode == self.MODE_SELECT_SHEET:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        elif mode == self.MODE_MOVE_VERTEX:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def set_roof_plane(self, roof_plane):
        self.roof_plane = roof_plane
        self.update()

    def set_material(self, material):
        self._material = material
        self.update()

    def _save_user_points_undo(self):
        self._user_points_history.append([QPointF(p.x(), p.y()) for p in self.user_points])
        self._user_points_redo.clear()

    def undo_user_points(self) -> bool:
        if not self._user_points_history:
            return False
        self._user_points_redo.append([QPointF(p.x(), p.y()) for p in self.user_points])
        self.user_points = self._user_points_history.pop()
        self.update()
        return True

    def redo_user_points(self) -> bool:
        if not self._user_points_redo:
            return False
        self._user_points_history.append([QPointF(p.x(), p.y()) for p in self.user_points])
        self.user_points = self._user_points_redo.pop()
        self.update()
        return True

    def zoom_in(self):
        self._zoom = min(self._zoom * 1.2, 10.0)
        self.update()

    def zoom_out(self):
        self._zoom = max(self._zoom / 1.2, 0.1)
        self.update()

    def fit_view(self):
        self._zoom = 1.0
        self._pan_x = 0.0
        self._pan_y = 0.0
        self.update()

    def _effective_mapper(self) -> CanvasMapper | None:
        if self.roof_plane is None:
            return None
        bounds = self.roof_plane.outline.bounds()
        rect = QRectF(self.rect())
        mapper = CanvasMapper(bounds, rect)
        mapper.scale *= self._zoom
        mapper.offset_x += self._pan_x
        mapper.offset_y += self._pan_y
        return mapper

    def _hit_test_sheet(self, pos) -> str | None:
        if self.roof_plane is None:
            return None
        mapper = self._effective_mapper()
        if mapper is None:
            return None
        px = pos.x()
        py = pos.y()
        for sheet in self.roof_plane.manual_sheet_placements + self.roof_plane.auto_sheet_placements:
            rect = mapper.map_rect(sheet.x_left_cm, sheet.x_right_cm, sheet.y_top_cm, sheet.y_bottom_cm)
            if rect.contains(px, py):
                return sheet.id
        return None

    def _hit_test_vertex(self, pos) -> int | None:
        if self.roof_plane is None:
            return None
        mapper = self._effective_mapper()
        if mapper is None:
            return None
        for index, point in enumerate(self.roof_plane.outline.points):
            mp = mapper.map_point(point)
            if abs(mp.x() - pos.x()) <= 8 and abs(mp.y() - pos.y()) <= 8:
                return index
        return None

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._mode == self.MODE_DRAW_OUTLINE:
                self._save_user_points_undo()
                self.user_points.append(event.position())
                self.update()
                return
            if self._mode == self.MODE_SELECT_SHEET:
                sheet_id = self._hit_test_sheet(event.position())
                if sheet_id != self._selected_sheet_id:
                    self._selected_sheet_id = sheet_id
                    self.update()
                return
            if self._mode == self.MODE_MOVE_VERTEX:
                vertex_index = self._hit_test_vertex(event.position())
                if vertex_index is not None:
                    self._dragging_vertex_index = vertex_index
                    self._drag_start_point = event.position()
                    self.setCursor(Qt.CursorShape.ClosedHandCursor)
                return

        if event.button() == Qt.MouseButton.RightButton:
            if self._mode == self.MODE_DRAW_OUTLINE:
                self._save_user_points_undo()
                self.user_points.clear()
                self.preview_point = None
                self.update()
                return
            if self._mode == self.MODE_SELECT_SHEET:
                self._selected_sheet_id = None
                self.update()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._mode == self.MODE_DRAW_OUTLINE:
            self.preview_point = event.position()
            self.update()
        elif self._mode == self.MODE_MOVE_VERTEX and self._dragging_vertex_index is not None and self._drag_start_point is not None and self.roof_plane is not None:
            mapper = self._effective_mapper()
            if mapper is not None:
                delta_px = event.position() - self._drag_start_point
                # Live preview not implemented for simplicity; just redraw
                pass
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._mode == self.MODE_MOVE_VERTEX and self._dragging_vertex_index is not None and self._drag_start_point is not None and self.roof_plane is not None:
            mapper = self._effective_mapper()
            if mapper is not None:
                delta_px = event.position() - self._drag_start_point
                delta_cm = Point2D(
                    mapper.unmap_length(delta_px.x()),
                    mapper.unmap_length(delta_px.y()),
                )
                self.vertex_moved.emit(self._dragging_vertex_index, delta_cm.x, delta_cm.y)
            self._dragging_vertex_index = None
            self._drag_start_point = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        if self._mode == self.MODE_DRAW_OUTLINE:
            self.preview_point = None
            self.update()
        super().leaveEvent(event)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()
        event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), self.palette().color(QPalette.ColorRole.Base))

        frame_color = self.palette().color(QPalette.ColorRole.Mid)
        painter.setPen(QPen(frame_color, 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        if self.roof_plane is not None:
            if self._show_grid:
                self._draw_grid(painter)
            self._draw_roof_plane(painter)

        if self._mode == self.MODE_DRAW_OUTLINE:
            self._draw_user_path(painter)

        if self._selected_sheet_id and self._mode == self.MODE_SELECT_SHEET:
            self._draw_selected_sheet_highlight(painter)

        painter.end()
        super().paintEvent(event)

    def _draw_grid(self, painter: QPainter):
        grid_color = self.palette().color(QPalette.ColorRole.Mid)
        grid_color.setAlpha(60)
        painter.setPen(QPen(grid_color, 0.5))
        w = self.width()
        h = self.height()
        step = 50
        for x in range(0, w, step):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, step):
            painter.drawLine(0, y, w, y)

    def _draw_user_path(self, painter: QPainter):
        if not self.user_points:
            return

        accent = self.palette().color(QPalette.ColorRole.Highlight)
        painter.setPen(QPen(accent, 2.0))

        for index in range(len(self.user_points) - 1):
            painter.drawLine(self.user_points[index], self.user_points[index + 1])

        if self.preview_point is not None:
            painter.drawLine(self.user_points[-1], self.preview_point)

        painter.setBrush(accent)
        for point in self.user_points:
            painter.drawEllipse(int(point.x()) - 3, int(point.y()) - 3, 6, 6)

    vertex_moved = Signal(int, float, float)
    outline_finalized = Signal(object)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if self._mode == self.MODE_DRAW_OUTLINE and len(self.user_points) >= 3:
            self._finalize_outline()
            return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        if isinstance(event, QKeyEvent) and self._mode == self.MODE_DRAW_OUTLINE:
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                if len(self.user_points) >= 3:
                    self._finalize_outline()
                event.accept()
                return
            if event.key() == Qt.Key.Key_Escape:
                self._save_user_points_undo()
                self.user_points.clear()
                self.preview_point = None
                self.update()
                event.accept()
                return
        super().keyPressEvent(event)

    def _finalize_outline(self):
        if len(self.user_points) < 3:
            return
        points = [Point2D(p.x(), p.y()) for p in self.user_points]
        self.user_points.clear()
        self.preview_point = None
        self._user_points_history.clear()
        self._user_points_redo.clear()
        self.outline_finalized.emit(points)
        self.update()

    def _draw_roof_plane(self, painter: QPainter):
        plane = self.roof_plane
        if plane is None:
            return

        mapper = self._effective_mapper()
        if mapper is None:
            return

        outline_polygon = QPolygonF([mapper.map_point(point) for point in plane.outline.points])
        fill_color = self.palette().color(QPalette.ColorRole.AlternateBase)
        outline_color = self.palette().color(QPalette.ColorRole.Highlight)
        text_color = self.palette().color(QPalette.ColorRole.Text)
        hole_color = QColor(outline_color)
        hole_color.setAlpha(180)

        painter.setPen(QPen(outline_color, 2))
        painter.setBrush(fill_color)
        painter.drawPolygon(outline_polygon)

        # Vertex handles
        painter.setPen(QPen(outline_color, 1))
        painter.setBrush(outline_color)
        for point in plane.outline.points:
            mp = mapper.map_point(point)
            painter.drawRect(int(mp.x()) - 3, int(mp.y()) - 3, 6, 6)

        painter.setPen(QPen(hole_color, 1.5, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for hole in plane.holes:
            painter.drawPolygon(QPolygonF([mapper.map_point(point) for point in hole.points]))

        # Draw sheet placements
        self._draw_sheet_placements(painter, plane, mapper, text_color)

        painter.setPen(text_color)
        label = f"Połać {plane.name}"
        if plane.selected_material_id:
            label += f" | Blacha: {plane.selected_material_id}"
        painter.drawText(self.rect().adjusted(40, 30, -40, -30).left(), self.rect().adjusted(40, 30, -40, -30).top() - 8, label)

    def _draw_sheet_placements(self, painter: QPainter, plane, mapper: CanvasMapper, text_color: QColor):
        if not plane.auto_sheet_placements and not plane.manual_sheet_placements:
            return

        auto_color = QColor("#6aa7ff" if self.palette().color(QPalette.ColorRole.Base).lightness() > 128 else "#8dc7ff")
        manual_color = QColor("#ff9d7a" if self.palette().color(QPalette.ColorRole.Base).lightness() > 128 else "#ff7a5c")
        auto_color.setAlpha(120)
        manual_color.setAlpha(140)

        all_sheets = list(plane.auto_sheet_placements) + list(plane.manual_sheet_placements)
        for sheet in all_sheets:
            color = manual_color if sheet.source == "manual" else auto_color
            rect = mapper.map_rect(sheet.x_left_cm, sheet.x_right_cm, sheet.y_top_cm, sheet.y_bottom_cm)
            painter.setPen(QPen(color.darker(150), 1))
            painter.setBrush(color)
            painter.drawRect(rect)

            # Module lines for modular materials
            if hasattr(self, '_material') and self._material and self._material.module_length_cm > 0:
                mod_len_px = mapper.map_length(self._material.module_length_cm)
                if mod_len_px > 4:
                    mod_pen = QPen(text_color)
                    mod_pen.setStyle(Qt.PenStyle.DotLine)
                    mod_pen.setWidthF(0.5)
                    painter.setPen(mod_pen)
                    y_start = rect.y()
                    y_end = rect.y() + rect.height()
                    x_left = rect.x()
                    x_right = rect.x() + rect.width()
                    mod_y = y_start + mod_len_px
                    while mod_y < y_end - 1:
                        painter.drawLine(QPointF(x_left, mod_y), QPointF(x_right, mod_y))
                        mod_y += mod_len_px

            # Label with length or module count
            if self._show_module_count and hasattr(self, '_material') and self._material and self._material.module_length_cm > 0:
                modules = max(1, int(round(sheet.final_length_cm / self._material.module_length_cm)))
                label_text = f"{modules}"
            else:
                label_text = f"{sheet.final_length_cm:.0f}"
            painter.setPen(text_color)
            font = painter.font()
            font.setPointSize(max(7, int(min(rect.width(), rect.height()) / 8)))
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label_text)
            font.setPointSize(font.pointSize() + 2)
            painter.setFont(font)

    def _draw_selected_sheet_highlight(self, painter: QPainter):
        if self.roof_plane is None or self._selected_sheet_id is None:
            return
        mapper = self._effective_mapper()
        if mapper is None:
            return
        all_sheets = list(self.roof_plane.auto_sheet_placements) + list(self.roof_plane.manual_sheet_placements)
        for sheet in all_sheets:
            if sheet.id == self._selected_sheet_id:
                rect = mapper.map_rect(sheet.x_left_cm, sheet.x_right_cm, sheet.y_top_cm, sheet.y_bottom_cm)
                painter.setPen(QPen(QColor("#ff3333"), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(rect.adjusted(-2, -2, 2, 2))
                break


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self._actions = []
        self._toolbar_actions = []
        self._theme = "light"
        self._config = load_config()
        self.project_state = ProjectState.from_config(self._config)
        self._latest_layout_result = None
        self._latest_report = None
        self._latest_report_html = ""
        self._latest_report_plane_id = None
        self._plane_tab_canvases: dict[str, DrawingCanvas] = {}
        self.ui.setupUi(self)
        self.setWindowTitle("4Dach wersja 1.0 Super Dach sp.j. instalacja 3, plik: testmarcin (zmieniony)")
        self.resize(1120, 720)
        self._setup_window_style()
        self._build_main_menu()
        self._build_top_toolbar()
        self._setup_central_area()
        self._apply_theme()
        self._refresh_canvas_from_state()
        self.statusBar().showMessage("Lewy przycisk myszy: rysowanie, prawy: wyczyść szkic", 5000)

    def _setup_window_style(self):
        self.menuBar().setNativeMenuBar(False)
        self.theme_toggle = QToolButton(self)
        self.theme_toggle.setObjectName("theme_toggle")
        self.theme_toggle.setAutoRaise(True)
        self.theme_toggle.setCheckable(True)
        self.theme_toggle.setIconSize(QSize(16, 16))
        self.theme_toggle.clicked.connect(self._toggle_theme)
        self.menuBar().setCornerWidget(self.theme_toggle, Qt.Corner.TopRightCorner)

    def _create_menu_action(self, title: str, shortcut: str | None = None):
        action = QAction(title, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.setStatusTip(title)
        action.triggered.connect(lambda checked=False, text=title: self.statusBar().showMessage(text, 2500))
        self._actions.append(action)
        return action

    def _build_main_menu(self):
        self.menuBar().clear()

        menu_structure = [
            (
                "Plik",
                [
                    ("Nowy dach", "Ctrl+N", None),
                    ("Otwórz...", "Ctrl+O", None),
                    ("Zapisz", "Ctrl+S", None),
                    ("Zapisz jako...", "Shift+Ctrl+S", None),
                    None,
                    ("Drukuj raport", "Ctrl+P", self._open_standard_report_preview),
                    ("Drukuj raport ciągły", "Shift+Ctrl+P", self._open_continuous_report_preview),
                    ("Drukuj raport skrócony", None, self._open_short_report_preview),
                    None,
                    ("Zakończ", "Ctrl+Q", None),
                ],
            ),
            (
                "Kształt",
                [
                    ("Prostokąt...", None, self._open_prostokat_dialog),
                    ("Trójkąt...", None, self._open_trojkat_dialog),
                    ("Trapez...", None, self._open_trapez_dialog),
                    ("Dowolny", None, self._on_draw_freeform_outline),
                None,
                ("Przesuń punkty obrysu", None, self._on_toggle_move_vertex),
                ],
            ),
            (
                "Wycinki",
                [
                    ("Dodaj wycinek", None, self._open_add_hole_dialog),
                    ("Usuń wycinek", None, self._open_delete_hole_dialog),
                    ("Przesuń wycinek", None, self._open_move_hole_dialog),
                    ("Skopiuj wycinek", None, None),
                    ("Wklej wycinek", None, None),
                ],
            ),
            (
                "Katalog",
                [
                    ("Blachy...", None, self._open_blachy_dialog),
                    ("Dane firmy...", None, self._open_dane_firmy_dialog),
                ],
            ),
            (
                "Arkusze",
                [
                    ("Dodaj arkusz", "Insert", self._open_add_sheet_dialog),
                    ("Usuń arkusz", "Delete", self._open_remove_sheet_dialog),
                    ("Podgląd arkuszy", "Ctrl+A", self._open_sheet_preview_dialog),
                    ("Aktywne arkusze", None, self._open_active_sheets_dialog),
                    ("Przelicz aktywną połać", "F5", self._open_recalculate_active_plane),
                    None,
                    ("Zmień rodzaj blachy", None, self._open_change_material_dialog),
                ],
            ),
        ]

        for menu_title, entries in menu_structure:
            menu = self.menuBar().addMenu(menu_title)
            for entry in entries:
                if entry is None:
                    menu.addSeparator()
                    continue

                title, shortcut, callback = entry
                action = self._create_menu_action(title, shortcut)
                if callback:
                    action.triggered.connect(callback)
                menu.addAction(action)

    def _add_toolbar_action(self, toolbar: QToolBar, icon_kind: str, text: str, checkable: bool = False, callback=None):
        action = QAction(text, self)
        action.setToolTip(text)
        action.setStatusTip(text)
        action.setCheckable(checkable)
        if callback:
            action.triggered.connect(callback)
        else:
            action.triggered.connect(lambda checked=False, value=text: self.statusBar().showMessage(value, 2500))
        toolbar.addAction(action)
        self._actions.append(action)
        self._toolbar_actions.append((action, icon_kind))
        return action

    def _icon_color_for_kind(self, kind: str, foreground: QColor, accent: QColor, muted: QColor) -> QColor:
        if kind in {"base_point_toggle", "sun", "moon"}:
            return accent
        if kind in {"module_count", "grid", "broom"}:
            return muted
        return foreground

    def _refresh_theme_icons(self, foreground: QColor, accent: QColor, muted: QColor):
        for action, icon_kind in self._toolbar_actions:
            icon_color = self._icon_color_for_kind(icon_kind, foreground, accent, muted)
            action.setIcon(build_icon(icon_kind, icon_color, 18))

        toggle_kind = "sun" if self._theme == "dark" else "moon"
        toggle_color = self._icon_color_for_kind(toggle_kind, foreground, accent, muted)
        self.theme_toggle.setIcon(build_icon(toggle_kind, toggle_color, 16))
        self.theme_toggle.setText("")

    def _build_top_toolbar(self):
        toolbar = QToolBar("Pasek główny", self)
        toolbar.setObjectName("main_toolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setIconSize(QSize(18, 18))
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        toolbar.setStyleSheet(
            "QToolBar { spacing: 2px; padding: 1px; }"
            "QToolButton { padding: 1px; margin: 0px; }"
        )
        self.addToolBar(toolbar)
        self.main_toolbar = toolbar
        self._toolbar_actions.clear()

        icon_actions = [
            ("new_document", "Nowy projekt", None),
            ("open_folder", "Otwórz projekt", None),
            ("save_floppy", "Zapisz projekt", None),
            ("roof_outline", "Rysowanie krawędzi połaci", self._on_toggle_draw_outline),
            ("base_point_toggle", "Pokaż/ukryj punkt bazowy", None),
            ("undo", "Cofnij", self._on_undo_canvas),
            ("plus", "Dodaj / Plus", self._on_zoom_in),
            ("minus", "Odejmij / Minus", self._on_zoom_out),
            ("module_count", "Włącz/wyłącz pokazywanie ilości modułów", self._on_module_count_toggled),
            ("zoom_out", "Oddal / Pomniejsz", self._on_zoom_out),
            ("fit_view", "Pokaż wszystko / Dopasuj do ekranu", self._on_fit_view),
            ("broom", "Wyczyść / Usuń wszystko", None),
        ]

        for index, (icon_kind, text, callback) in enumerate(icon_actions):
            checkable = icon_kind == "roof_outline"
            action = self._add_toolbar_action(toolbar, icon_kind, text, checkable=checkable)
            if callback:
                action.triggered.connect(callback)
            if index in {2, 4, 7, 11}:
                toolbar.addSeparator()

        self.material_button = QToolButton(self)
        self.material_button.setObjectName("material_button")
        self.material_button.setText("A")
        self.material_button.setToolTip("Wybór aktywnej blachy")
        self.material_button.setStatusTip("Wybór aktywnej blachy")
        self.material_button.setAutoRaise(True)
        self.material_button.setFixedSize(22, 20)
        material_font = QFont(self.font())
        material_font.setBold(True)
        self.material_button.setFont(material_font)
        self.material_button.clicked.connect(lambda checked=False: self.statusBar().showMessage("Wybór aktywnej blachy", 2500))
        toolbar.addWidget(self.material_button)

        variant_combo = QComboBox(self)
        variant_combo.setObjectName("variant_combo")
        variant_combo.setEditable(True)
        variant_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        variant_combo.setFixedWidth(146)
        self.variant_combo = variant_combo
        self._refresh_material_combo()
        try:
            line_edit = variant_combo.lineEdit()
            if line_edit is not None:
                line_edit.setReadOnly(True)
        except AttributeError:
            pass
        variant_combo.setToolTip("Wybór aktywnej blachy")
        variant_combo.currentTextChanged.connect(self._on_material_changed)
        toolbar.addWidget(variant_combo)
        toolbar.addSeparator()

        trailing_actions = [
            ("overlay_sheet", "Nakładanie blachy na powierzchnie", False, self._open_recalculate_active_plane),
            ("grid", "Siatka", False, self._on_grid_toggled),
            ("select_properties", "Właściwości / Wybierz", False, None),
            ("from_right", "Od prawej", True, self._on_from_right_toggled),
            ("from_base", "Od bazy", True, self._on_from_base_toggled),
        ]

        for icon_kind, text, checkable, callback in trailing_actions:
            action = self._add_toolbar_action(toolbar, icon_kind, text, checkable=checkable, callback=callback)

    def _on_from_right_toggled(self, checked: bool):
        plane = self.project_state.active_roof_plane()
        if plane is None:
            self.statusBar().showMessage("Brak aktywnej połaci", 3000)
            return
        origin = "right" if checked else "left"
        if plane.generation_settings.layout_origin != origin:
            plane.generation_settings.layout_origin = origin
            plane.layout_dirty_reason = "geometry_changed"
            self._persist_project_state()
            self._refresh_canvas_from_state()
            self.statusBar().showMessage(f"Kierunek pasów: {'od prawej' if checked else 'od lewej'}", 3000)

    def _on_from_base_toggled(self, checked: bool):
        plane = self.project_state.active_roof_plane()
        if plane is None:
            self.statusBar().showMessage("Brak aktywnej połaci", 3000)
            return
        plane.generation_settings.base_line_y_cm = plane.outline.bounds().max_y if checked else None
        plane.layout_dirty_reason = "geometry_changed"
        self._persist_project_state()
        self._refresh_canvas_from_state()
        self.statusBar().showMessage(f"Linia bazowa: {'auto' if checked else 'wyłączona'}", 3000)

    def _on_grid_toggled(self, checked: bool):
        self.primary_canvas.toggle_grid(checked)
        self.secondary_canvas.toggle_grid(checked)
        for canvas in self._plane_tab_canvases.values():
            canvas.toggle_grid(checked)
        self.statusBar().showMessage(f"Siatka: {'włączona' if checked else 'wyłączona'}", 3000)

    def _on_module_count_toggled(self, checked: bool):
        self.primary_canvas.toggle_module_count(checked)
        self.secondary_canvas.toggle_module_count(checked)
        for canvas in self._plane_tab_canvases.values():
            canvas.toggle_module_count(checked)
        self.statusBar().showMessage(f"Ilość modułów: {'włączona' if checked else 'wyłączona'}", 3000)

    def _setup_central_area(self):
        central = QWidget(self)
        central.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.workspace_tabs = QTabWidget(central)
        self.workspace_tabs.setObjectName("workspace_tabs")
        self.workspace_tabs.setDocumentMode(True)
        self.workspace_tabs.setTabsClosable(False)
        self.workspace_tabs.currentChanged.connect(self._on_workspace_tab_changed)

        self.secondary_canvas = DrawingCanvas(self.workspace_tabs)
        self.secondary_canvas.hide()
        self._connect_canvas_signals(self.secondary_canvas)

        self.report_tab = QWidget(self.workspace_tabs)
        second_layout = QVBoxLayout(self.report_tab)
        second_layout.setContentsMargins(0, 0, 0, 0)
        self.report_view = QTextBrowser(self.report_tab)
        self.report_view.setObjectName("report_view")
        self.report_view.setOpenExternalLinks(False)
        second_layout.addWidget(self.report_view)

        self.primary_canvas = DrawingCanvas(self.workspace_tabs)
        self._connect_canvas_signals(self.primary_canvas)
        self._plane_tab_canvases = {}
        self.workspace_tabs.addTab(self.report_tab, "Raport")
        layout.addWidget(self.workspace_tabs)
        self.setCentralWidget(central)
        self._sync_workspace_tabs_with_state()
        self._refresh_report_view()

    def _toggle_theme(self):
        self._theme = "dark" if self._theme == "light" else "light"
        self._apply_theme()

    def _apply_theme(self):
        app = QApplication.instance()
        if not app or not isinstance(app, QApplication):
            return
        palette = QPalette()

        if self._theme == "dark":
            palette.setColor(QPalette.ColorRole.Window, QColor("#20242b"))
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#f0f0f0"))
            palette.setColor(QPalette.ColorRole.Base, QColor("#171a20"))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#262b33"))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#2d323c"))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#f0f0f0"))
            palette.setColor(QPalette.ColorRole.Text, QColor("#f0f0f0"))
            palette.setColor(QPalette.ColorRole.Button, QColor("#2d323c"))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor("#f0f0f0"))
            palette.setColor(QPalette.ColorRole.Highlight, QColor("#6aa7ff"))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
            menu_bg = "#2d323c"
            menu_hover = "#454d59"
            border = "#555d69"
            tab_selected = "#171a20"
            tab_hover = "#39414d"
            toolbar_bg = "#2a2f38"
            button_hover = "#454d59"
            canvas_border = "#555d69"
            toggle_tip = "Przełącz na light mode"
            menu_text = "#f0f0f0"
            icon_fg = QColor("#f1efe7")
            icon_accent = QColor("#8dc7ff")
            icon_muted = QColor("#aeb7c4")
            input_bg = "#171a20"
            pressed_bg = "#536071"
            disabled_text = "#7d8794"
        else:
            palette.setColor(QPalette.ColorRole.Window, QColor("#d6d5cb"))
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#111111"))
            palette.setColor(QPalette.ColorRole.Base, QColor("#fffdf4"))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#efede2"))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#fffdf4"))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#111111"))
            palette.setColor(QPalette.ColorRole.Text, QColor("#111111"))
            palette.setColor(QPalette.ColorRole.Button, QColor("#e4e1d6"))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor("#111111"))
            palette.setColor(QPalette.ColorRole.Highlight, QColor("#c74d3d"))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
            menu_bg = "#e3e0d4"
            menu_hover = "#d0d0d0"
            border = "#9e9e97"
            tab_selected = "#fffdf4"
            tab_hover = "#d7d3c7"
            toolbar_bg = "#dedccf"
            button_hover = "#d4d1c6"
            canvas_border = "#9e9e97"
            toggle_tip = "Przełącz na night mode"
            menu_text = "#1c1a16"
            icon_fg = QColor("#49453b")
            icon_accent = QColor("#c74d3d")
            icon_muted = QColor("#777367")
            input_bg = "#fffdf4"
            pressed_bg = "#cbc7bb"
            disabled_text = "#8d8a80"

        app.setPalette(palette)
        app.setStyleSheet(
            "QMainWindow { background: palette(window); }"
            f"QMenuBar {{ spacing: 4px; background: {menu_bg}; color: {menu_text}; border-bottom: 1px solid {border}; }}"
            "QMenuBar::item { padding: 3px 8px; background: transparent; }"
            f"QMenuBar::item:selected {{ background: {menu_hover}; color: {menu_text}; }}"
            f"QMenu {{ background: {menu_bg}; color: {menu_text}; border: 1px solid {border}; }}"
            f"QMenu::item:selected {{ background: {menu_hover}; color: {menu_text}; }}"
            f"QToolBar {{ background: {toolbar_bg}; border-top: 1px solid {border}; border-bottom: 1px solid {border}; spacing: 2px; padding: 1px; }}"
            f"QToolBar::separator {{ width: 1px; margin: 2px 3px; background: {border}; }}"
            f"QToolButton {{ color: {menu_text}; padding: 1px; margin: 0px; border: 1px solid transparent; background: transparent; }}"
            f"QToolButton:hover {{ background: {button_hover}; border: 1px solid {border}; }}"
            f"QToolButton:pressed {{ background: {pressed_bg}; border: 1px solid {border}; }}"
            f"QToolButton:disabled {{ color: {disabled_text}; }}"
            f"QLineEdit, QComboBox {{ background: {input_bg}; color: {menu_text}; border: 1px solid {border}; padding: 1px 3px; selection-background-color: {button_hover}; selection-color: {menu_text}; }}"
            f"QComboBox::editable {{ background: {input_bg}; }}"
            f"QComboBox QLineEdit {{ background: {input_bg}; color: {menu_text}; border: none; padding: 0px; }}"
            f"QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 18px; border-left: 1px solid {border}; background: {button_hover}; }}"
            "QComboBox::down-arrow { width: 8px; height: 8px; }"
            f"QComboBox QAbstractItemView {{ background: {input_bg}; color: {menu_text}; border: 1px solid {border}; selection-background-color: {button_hover}; selection-color: {menu_text}; }}"
            f"QTabWidget::pane {{ border-top: 1px solid {border}; background: palette(base); }}"
            f"QTabBar::tab {{ color: {menu_text}; background: {toolbar_bg}; border: 1px solid {border}; border-bottom: none; padding: 1px 5px; min-width: 14px; margin-right: 1px; }}"
            f"QTabBar::tab:selected {{ background: {tab_selected}; color: {menu_text}; }}"
            f"QTabBar::tab:hover {{ background: {tab_hover}; }}"
            f"QStatusBar {{ color: {menu_text}; border-top: 1px solid {border}; }}"
            f"DrawingCanvas {{ border: 1px solid {canvas_border}; background: palette(base); }}"
            f"QToolButton#material_button {{ color: {menu_text}; border: 1px solid {border}; background: {input_bg}; padding: 0px; margin-left: 2px; margin-right: 0px; }}"
            f"QToolButton#material_button:hover {{ background: {button_hover}; border: 1px solid {border}; }}"
            f"QToolButton#theme_toggle {{ border: none; padding: 0 8px; background: transparent; }}"
            f"QToolButton#theme_toggle:hover {{ background: {menu_hover}; border: none; }}"
        )

        self._refresh_theme_icons(icon_fg, icon_accent, icon_muted)
        self.theme_toggle.blockSignals(True)
        self.theme_toggle.setChecked(self._theme == "dark")
        self.theme_toggle.setToolTip(toggle_tip)
        self.theme_toggle.blockSignals(False)
        self.theme_toggle.update()
        self.menuBar().setCornerWidget(self.theme_toggle, Qt.Corner.TopRightCorner)
        self.primary_canvas.update()
        self.secondary_canvas.update()
        for canvas in self._plane_tab_canvases.values():
            canvas.update()

    def _reload_project_state(self):
        self.project_state = ProjectState.from_config(self._config)
        self._clear_generated_report()
        if hasattr(self, "variant_combo"):
            self._refresh_material_combo()
        self._refresh_canvas_from_state()

    def _refresh_material_combo(self):
        material_ids = self.project_state.available_material_ids()
        current_text = self.variant_combo.currentText() if self.variant_combo.count() else ""
        active_plane = self.project_state.active_roof_plane()
        self.variant_combo.blockSignals(True)
        self.variant_combo.clear()
        if material_ids:
            self.variant_combo.addItems(material_ids)
            preferred_material = active_plane.selected_material_id if active_plane is not None else None
            target_material = preferred_material or current_text or material_ids[0]
            if target_material not in material_ids:
                target_material = material_ids[0]
            self.variant_combo.setCurrentText(target_material)
        self.variant_combo.blockSignals(False)

    def _report_tab_index(self) -> int:
        return self.workspace_tabs.count() - 1

    def _active_plane_tab_index(self) -> int:
        active_plane_id = self.project_state.active_plane_id
        if active_plane_id is None:
            return 0
        plane_ids = [plane.id for plane in self.project_state.roof_planes]
        try:
            return plane_ids.index(active_plane_id)
        except ValueError:
            return 0

    def _build_plane_tab(self, plane):
        tab = QWidget(self.workspace_tabs)
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        canvas = DrawingCanvas(tab)
        canvas.set_roof_plane(plane)
        material = self.project_state.material_by_id(plane.selected_material_id) if plane else None
        canvas.set_material(material)
        layout.addWidget(canvas)
        tab.setProperty("plane_id", plane.id)
        self._plane_tab_canvases[plane.id] = canvas
        self._connect_canvas_signals(canvas)
        return tab, canvas

    def _sync_workspace_tabs_with_state(self):
        self.workspace_tabs.blockSignals(True)
        self.workspace_tabs.clear()
        self._plane_tab_canvases = {}

        if self.project_state.roof_planes:
            if self.project_state.active_roof_plane() is None:
                self.project_state.set_active_plane(self.project_state.roof_planes[0].id)
            for plane in self.project_state.roof_planes:
                tab, canvas = self._build_plane_tab(plane)
                tab_name = plane.name
                if plane.layout_dirty_reason:
                    tab_name += " *"
                self.workspace_tabs.addTab(tab, tab_name)
                if plane.id == self.project_state.active_plane_id:
                    self.primary_canvas = canvas
        else:
            placeholder_tab = QWidget(self.workspace_tabs)
            placeholder_layout = QVBoxLayout(placeholder_tab)
            placeholder_layout.setContentsMargins(0, 0, 0, 0)
            self.primary_canvas = DrawingCanvas(placeholder_tab)
            placeholder_layout.addWidget(self.primary_canvas)
            self.workspace_tabs.addTab(placeholder_tab, "1")

        self.workspace_tabs.addTab(self.report_tab, "Raport")

        if self.project_state.roof_planes:
            self.workspace_tabs.setCurrentIndex(self._active_plane_tab_index())
        else:
            self.workspace_tabs.setCurrentIndex(0)

        self.workspace_tabs.blockSignals(False)

    def _on_workspace_tab_changed(self, index: int):
        if index < 0 or index == self._report_tab_index():
            return

        if index >= len(self.project_state.roof_planes):
            return

        plane = self.project_state.roof_planes[index]
        if not self.project_state.set_active_plane(plane.id):
            return

        self.primary_canvas = self._plane_tab_canvases.get(plane.id, self.primary_canvas)
        self._persist_project_state()
        if hasattr(self, "variant_combo"):
            self._refresh_material_combo()
        self._refresh_report_view()
        self.statusBar().showMessage(f"Aktywna połać: {plane.name}", 2500)

    def _refresh_canvas_from_state(self):
        active_plane = self.project_state.active_roof_plane()
        self._sync_workspace_tabs_with_state()
        self.primary_canvas.set_roof_plane(active_plane)
        material = self.project_state.material_by_id(active_plane.selected_material_id) if active_plane else None
        self.primary_canvas.set_material(material)
        self.secondary_canvas.set_roof_plane(None)
        if active_plane is not None:
            self.workspace_tabs.setCurrentIndex(self._active_plane_tab_index())
        self.workspace_tabs.setTabText(self._report_tab_index(), "Raport")
        self._refresh_report_view()

    def _persist_project_state(self):
        self.project_state.apply_to_config(self._config)
        save_config(self._config)

    def _apply_project_edit(self, callback, success_message: str):
        try:
            callback()
        except (ValueError, IndexError) as error:
            QMessageBox.warning(self, "Błąd edycji", str(error))
            self.statusBar().showMessage(str(error), 4000)
            return False

        self._clear_generated_report()
        self._persist_project_state()
        self._refresh_canvas_from_state()
        self.statusBar().showMessage(success_message, 4000)
        return True

    def _active_plane_or_warn(self):
        plane = self.project_state.active_roof_plane()
        if plane is None:
            message = "Brak aktywnej połaci"
            QMessageBox.information(self, "Brak połaci", message)
            self.statusBar().showMessage(message, 3000)
            return None
        return plane

    def _ask_int(self, title: str, label: str, value: int, minimum: int, maximum: int):
        return QInputDialog.getInt(self, title, label, value, minimum, maximum)

    def _ask_float(self, title: str, label: str, value: float = 0.0, minimum: float = -9999.0, maximum: float = 9999.0):
        return QInputDialog.getDouble(self, title, label, value, minimum, maximum, 2)

    def _on_material_changed(self, text: str):
        if self.project_state.set_active_material_for_plane(text):
            self._clear_generated_report()
            self._persist_project_state()
            self._refresh_canvas_from_state()
        self.statusBar().showMessage(f"Aktywna blacha: {text}", 2500)

    def _add_roof_plane(self, outline, shape_name: str, detail: str):
        plane = self.project_state.add_roof_plane(outline, selected_material_id=self.variant_combo.currentText() or None)
        self._clear_generated_report()
        self._persist_project_state()
        self._refresh_canvas_from_state()
        self.statusBar().showMessage(f"{shape_name}: dodano połać {plane.name} ({detail})", 4000)

    def _clear_generated_report(self):
        self._latest_layout_result = None
        self._latest_report = None
        self._latest_report_html = ""
        self._latest_report_plane_id = None
        if hasattr(self, "report_view"):
            self._refresh_report_view()

    def _layout_dirty_reason_label(self, reason: str | None) -> str:
        labels = {
            None: "aktualny",
            "geometry_changed": "nieaktualny po zmianie geometrii",
            "material_changed": "nieaktualny po zmianie materiału",
            "manual_override": "zmieniony ręczną korektą arkuszy",
        }
        return labels.get(reason, f"nieaktualny ({reason})")

    def _layout_dirty_reason_hint(self, reason: str | None) -> str:
        hints = {
            "geometry_changed": "Użyj akcji Arkusze -> Przelicz aktywną połać, aby odświeżyć layout i raport po zmianie geometrii.",
            "material_changed": "Użyj akcji Arkusze -> Przelicz aktywną połać, aby przeliczyć układ dla nowego materiału.",
            "manual_override": "Jeśli chcesz odtworzyć automatyczny układ po ręcznych korektach, użyj akcji Arkusze -> Przelicz aktywną połać.",
        }
        if reason is None:
            return "Użyj akcji Plik -> Drukuj raport lub Arkusze -> Przelicz aktywną połać, aby wygenerować aktualny wynik."
        return hints.get(reason, "Użyj akcji Plik -> Drukuj raport lub Arkusze -> Przelicz aktywną połać, aby wygenerować aktualny wynik.")

    def _refresh_report_view(self, html: str | None = None):
        active_plane = self.project_state.active_roof_plane()
        content = html if html is not None else ""
        if not content and active_plane is not None and self._latest_report_plane_id == active_plane.id and self._latest_report_html:
            content = self._latest_report_html
        if not content:
            if active_plane is None:
                content = (
                    "<html><body>"
                    "<h1>Raport 4Dach</h1>"
                    "<p>Dodaj połać, aby wygenerować pierwszy raport.</p>"
                    "</body></html>"
                )
            else:
                dirty_message = ""
                if active_plane.layout_dirty_reason:
                    reason_label = self._layout_dirty_reason_label(active_plane.layout_dirty_reason)
                    reason_hint = self._layout_dirty_reason_hint(active_plane.layout_dirty_reason)
                    dirty_message = (
                        f"<p><strong>Stan layoutu:</strong> {reason_label}.</p>"
                        f"<p>{reason_hint}</p>"
                    )
                content = (
                    "<html><body>"
                    f"<h1>Raport 4Dach - {active_plane.name}</h1>"
                    "<p>Raport nie został jeszcze wygenerowany dla aktywnej połaci.</p>"
                    f"{dirty_message}"
                    "<p>Użyj akcji <strong>Plik -> Drukuj raport</strong> lub <strong>Arkusze -> Przelicz aktywną połać</strong>, aby przeliczyć layout, BOM i ostrzeżenia.</p>"
                    "</body></html>"
                )
        self.report_view.setHtml(content)

    def _sheet_lines(self, plane) -> list[str]:
        active_sheets = self.project_state.active_sheet_placements_for_plane(plane.id)
        if not active_sheets:
            return ["Brak aktywnych arkuszy"]

        return [
            (
                f"{index}. {sheet.id} | źródło: {sheet.source} | pas: {sheet.band_index} | "
                f"X: {sheet.x_left_cm:.2f}-{sheet.x_right_cm:.2f} cm | "
                f"Y: {sheet.y_top_cm:.2f}-{sheet.y_bottom_cm:.2f} cm | "
                f"długość: {sheet.final_length_cm:.2f} cm"
            )
            for index, sheet in enumerate(active_sheets)
        ]

    def _open_add_sheet_dialog(self):
        plane = self._active_plane_or_warn()
        if plane is None:
            return

        band_index, accepted = self._ask_int("Dodaj arkusz", "Numer pasa:", 0, 0, 999)
        if not accepted:
            return
        x_left, accepted = self._ask_float("Dodaj arkusz", "Lewy X [cm]:", 0.0)
        if not accepted:
            return
        width, accepted = self._ask_float("Dodaj arkusz", "Szerokość [cm]:", 50.0, 0.01)
        if not accepted:
            return
        y_top, accepted = self._ask_float("Dodaj arkusz", "Górny Y [cm]:", 0.0)
        if not accepted:
            return
        length, accepted = self._ask_float("Dodaj arkusz", "Długość końcowa [cm]:", 100.0, 0.01)
        if not accepted:
            return

        placement = SheetPlacement(
            id=f"{plane.id}-manual-{plane.layout_revision + len(plane.manual_sheet_placements) + 1}",
            band_index=band_index,
            x_left_cm=x_left,
            x_right_cm=x_left + width,
            y_top_cm=y_top,
            y_bottom_cm=y_top + length,
            raw_length_cm=length,
            final_length_cm=length,
            source="manual",
        )
        self._apply_project_edit(
            lambda: self.project_state.add_manual_sheet_placement(placement, plane.id),
            f"Dodano ręczny arkusz do połaci {plane.name}",
        )

    def _open_remove_sheet_dialog(self):
        plane = self._active_plane_or_warn()
        if plane is None:
            return

        active_sheets = self.project_state.active_sheet_placements_for_plane(plane.id)
        if not active_sheets:
            QMessageBox.information(self, "Brak arkuszy", "Aktywna połać nie ma arkuszy do usunięcia")
            self.statusBar().showMessage("Aktywna połać nie ma arkuszy do usunięcia", 3000)
            return

        sheet_index, accepted = self._ask_int(
            "Usuń arkusz",
            f"Indeks arkusza 0-{len(active_sheets) - 1}:",
            0,
            0,
            len(active_sheets) - 1,
        )
        if not accepted:
            return

        sheet = active_sheets[sheet_index]
        self._apply_project_edit(
            lambda: self.project_state.remove_sheet_placement(sheet.id, plane.id),
            f"Usunięto arkusz {sheet.id} z połaci {plane.name}",
        )

    def _open_sheet_preview_dialog(self):
        plane = self._active_plane_or_warn()
        if plane is None:
            return

        details = "\n".join(self._sheet_lines(plane))
        QMessageBox.information(self, f"Podgląd arkuszy - {plane.name}", details)
        self.statusBar().showMessage(f"Pokazano podgląd arkuszy połaci {plane.name}", 3000)

    def _open_active_sheets_dialog(self):
        plane = self._active_plane_or_warn()
        if plane is None:
            return

        active_sheets = self.project_state.active_sheet_placements_for_plane(plane.id)
        manual_count = len(plane.manual_sheet_placements)
        removed_count = len(plane.manually_removed_auto_sheet_ids)
        layout_status = self._layout_dirty_reason_label(plane.layout_dirty_reason)
        hint = self._layout_dirty_reason_hint(plane.layout_dirty_reason) if plane.layout_dirty_reason else ""
        message = (
            f"Aktywne arkusze: {len(active_sheets)}\n"
            f"Ręczne arkusze: {manual_count}\n"
            f"Ukryte auto-arkusze: {removed_count}\n"
            f"Stan layoutu: {layout_status}"
        )
        if hint:
            message = f"{message}\n\n{hint}"
        QMessageBox.information(self, f"Aktywne arkusze - {plane.name}", message)
        self.statusBar().showMessage(f"Pokazano podsumowanie arkuszy połaci {plane.name}", 3000)

    def _open_recalculate_active_plane(self):
        if self._generate_report_preview("standard"):
            self.statusBar().showMessage("Przeliczono aktywną połać i odświeżono raport", 4000)

    def _open_change_material_dialog(self):
        plane = self._active_plane_or_warn()
        if plane is None:
            return

        material_ids = self.project_state.available_material_ids()
        if not material_ids:
            QMessageBox.warning(self, "Brak materiałów", "Brak dostępnych materiałów w katalogu")
            self.statusBar().showMessage("Brak dostępnych materiałów w katalogu", 3000)
            return

        current_material = plane.selected_material_id or self.project_state.active_material_id() or material_ids[0]
        selected_material, accepted = QInputDialog.getItem(
            self,
            "Zmień rodzaj blachy",
            "Materiał:",
            material_ids,
            material_ids.index(current_material) if current_material in material_ids else 0,
            False,
        )
        if not accepted:
            return

        if self.project_state.set_active_material_for_plane(selected_material, plane.id):
            self.variant_combo.blockSignals(True)
            self.variant_combo.setCurrentText(selected_material)
            self.variant_combo.blockSignals(False)
            self._clear_generated_report()
            self._persist_project_state()
            self._refresh_canvas_from_state()
            self.statusBar().showMessage(f"Zmieniono materiał połaci {plane.name} na {selected_material}", 4000)

    def _build_report_html_for_variant(self, variant: str, material_id: str, plane_id: str, report):
        if variant == "continuous":
            return build_report_html(
                self.project_state,
                report,
                material_id,
                plane_id,
                title_suffix="ciągły",
            )
        if variant == "short":
            return build_report_html(
                self.project_state,
                report,
                material_id,
                plane_id,
                include_bom=False,
                title_suffix="skrócony",
            )
        return build_report_html(self.project_state, report, material_id, plane_id)

    def _generate_report_preview(self, variant: str, open_external: bool = False):
        plane = self._active_plane_or_warn()
        if plane is None:
            return False

        material_id = plane.selected_material_id or self.project_state.active_material_id()
        material = self.project_state.material_by_id(material_id)
        if material is None or material_id is None:
            message = "Brak aktywnego materiału dla połaci"
            QMessageBox.warning(self, "Brak materiału", message)
            self.statusBar().showMessage(message, 4000)
            return False

        try:
            layout_result = self.project_state.generate_layout_for_plane(plane.id)
            report = build_report(self.project_state, layout_result, material_id, plane.id)
            html = self._build_report_html_for_variant(variant, material_id, plane.id, report)
        except ValueError as error:
            QMessageBox.warning(self, "Błąd raportu", str(error))
            self.statusBar().showMessage(str(error), 4000)
            return False

        self._latest_layout_result = layout_result
        self._latest_report = report
        self._latest_report_html = html
        self._latest_report_plane_id = plane.id
        self._persist_project_state()
        self._refresh_canvas_from_state()
        if open_external:
            from pathlib import Path
            import tempfile
            suffix = "_ciagly" if variant == "continuous" else "_skrocony" if variant == "short" else ""
            temp_path = Path(tempfile.gettempdir()) / f"raport-dach{suffix}.html"
            temp_path.write_text(html, encoding="utf-8")
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(temp_path)))
        else:
            self._refresh_report_view(html)
            self.workspace_tabs.setCurrentIndex(self._report_tab_index())
        return True

    def _open_standard_report_preview(self):
        if self._generate_report_preview("standard", open_external=True):
            self.statusBar().showMessage("Wygenerowano raport dla aktywnej połaci", 4000)

    def _open_continuous_report_preview(self):
        if self._generate_report_preview("continuous", open_external=True):
            self.statusBar().showMessage("Wygenerowano raport ciągły dla aktywnej połaci", 4000)

    def _open_short_report_preview(self):
        if self._generate_report_preview("short", open_external=True):
            self.statusBar().showMessage("Wygenerowano raport skrócony dla aktywnej połaci", 4000)

    def _open_prostokat_dialog(self):
        dialog = ProstokatDialog(self._config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.get_values()
            self._config["ksztalty"]["prostokat"] = values
            outline = build_rectangle_outline(values["szerokosc"], values["wysokosc"])
            self._add_roof_plane(outline, "Prostokąt", f"{values['szerokosc']} x {values['wysokosc']} cm")

    def _open_trojkat_dialog(self):
        dialog = TrojkatDialog(self._config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.get_values()
            self._config["ksztalty"]["trojkat"] = values
            side_length = values["ramie"] if values.get("ramie_enabled") else None
            outline = build_triangle_outline(values["typ"], values["podstawa"], values["wysokosc"], side_length)
            self._add_roof_plane(outline, "Trójkąt", f"{values['typ']}, podstawa: {values['podstawa']} cm")

    def _open_trapez_dialog(self):
        dialog = TrapezDialog(self._config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.get_values()
            self._config["ksztalty"]["trapez"] = values
            outline = build_trapezoid_outline(values["typ"], values["podstawa_dolna"], values["podstawa_gorna"], values["wysokosc"])
            self._add_roof_plane(outline, "Trapez", f"{values['typ']}, podstawa dolna: {values['podstawa_dolna']} cm")

    def _open_add_hole_dialog(self):
        plane = self._active_plane_or_warn()
        if plane is None:
            return

        width, accepted = self._ask_float("Dodaj wycinek", "Szerokość wycinka [cm]:", 50.0, 1.0)
        if not accepted:
            return
        height, accepted = self._ask_float("Dodaj wycinek", "Wysokość wycinka [cm]:", 50.0, 1.0)
        if not accepted:
            return
        origin_x, accepted = self._ask_float("Dodaj wycinek", "Lewy górny X [cm]:", 0.0, -9999.0)
        if not accepted:
            return
        origin_y, accepted = self._ask_float("Dodaj wycinek", "Lewy górny Y [cm]:", 0.0, -9999.0)
        if not accepted:
            return

        hole = Polygon2D.rectangle(width, height, origin_x=origin_x, origin_y=origin_y)
        self._apply_project_edit(
            lambda: self.project_state.add_hole_to_plane(hole, plane.id),
            f"Dodano wycinek do połaci {plane.name}",
        )

    def _open_delete_hole_dialog(self):
        plane = self._active_plane_or_warn()
        if plane is None:
            return
        if not plane.holes:
            QMessageBox.information(self, "Brak wycinków", "Aktywna połać nie ma wycinków do usunięcia")
            self.statusBar().showMessage("Aktywna połać nie ma wycinków do usunięcia", 3000)
            return

        hole_index, accepted = self._ask_int(
            "Usuń wycinek",
            f"Indeks wycinka 0-{len(plane.holes) - 1}:",
            len(plane.holes) - 1,
            0,
            len(plane.holes) - 1,
        )
        if not accepted:
            return

        self._apply_project_edit(
            lambda: self.project_state.delete_hole_from_plane(hole_index, plane.id),
            f"Usunięto wycinek {hole_index} z połaci {plane.name}",
        )

    def _open_move_hole_dialog(self):
        plane = self._active_plane_or_warn()
        if plane is None:
            return
        if not plane.holes:
            QMessageBox.information(self, "Brak wycinków", "Aktywna połać nie ma wycinków do przesunięcia")
            self.statusBar().showMessage("Aktywna połać nie ma wycinków do przesunięcia", 3000)
            return

        hole_index, accepted = self._ask_int(
            "Przesuń wycinek",
            f"Indeks wycinka 0-{len(plane.holes) - 1}:",
            0,
            0,
            len(plane.holes) - 1,
        )
        if not accepted:
            return
        dx, accepted = self._ask_float("Przesuń wycinek", "Przesunięcie X [cm]:")
        if not accepted:
            return
        dy, accepted = self._ask_float("Przesuń wycinek", "Przesunięcie Y [cm]:")
        if not accepted:
            return

        self._apply_project_edit(
            lambda: self.project_state.move_hole_in_plane(hole_index, dx, dy, plane.id),
            f"Przesunięto wycinek {hole_index} połaci {plane.name}",
        )

    def _open_dane_firmy_dialog(self):
        dialog = DaneFirmyDialog(self._config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.get_values()
            self._config["company_data"] = values
            self.project_state.company_data = self.project_state.company_data.from_dict(values)
            self._clear_generated_report()
            self._persist_project_state()
            self._reload_project_state()
            self.statusBar().showMessage(f"Dane firmy zapisane: {values['name']}", 3000)

    def _open_blachy_dialog(self):
        dialog = BlachyDialog(self._config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.get_values()
            self._config["blachy"] = values
            self._clear_generated_report()
            self._persist_project_state()
            save_config(self._config)
            self._reload_project_state()
            self.statusBar().showMessage(f"Lista blach zaktualizowana: {len(values)} pozycji", 3000)

    def _show_ostrzezenie_dialog(self):
        result = show_ostrzezenie_dialog(self)
        if result:
            self.statusBar().showMessage("Aktywna połać wyczyszczona", 3000)
        else:
            self.statusBar().showMessage("Anulowano czyszczenie", 3000)

    def _on_draw_freeform_outline(self):
        self.primary_canvas.set_mode(DrawingCanvas.MODE_DRAW_OUTLINE)
        self.statusBar().showMessage("Rysowanie obrysu: LPM dodaje punkt, Enter zamyka, PPM czyści, Cofnij usuwa ostatni punkt", 5000)

    def _on_toggle_draw_outline(self, checked: bool):
        mode = DrawingCanvas.MODE_DRAW_OUTLINE if checked else DrawingCanvas.MODE_VIEW
        self.primary_canvas.set_mode(mode)
        for canvas in self._plane_tab_canvases.values():
            canvas.set_mode(mode)
        self.statusBar().showMessage("Rysowanie obrysu" if checked else "Widok", 3000)

    def _on_toggle_move_vertex(self):
        self.primary_canvas.set_mode(DrawingCanvas.MODE_MOVE_VERTEX)
        for canvas in self._plane_tab_canvases.values():
            canvas.set_mode(DrawingCanvas.MODE_MOVE_VERTEX)
        self.statusBar().showMessage("Przesuwanie punktów obrysu: przeciągnij punkt", 4000)

    def _on_undo_canvas(self):
        if self.primary_canvas._mode == DrawingCanvas.MODE_DRAW_OUTLINE:
            if self.primary_canvas.undo_user_points():
                self.statusBar().showMessage("Cofnięto ostatni punkt", 2000)
            else:
                self.statusBar().showMessage("Brak punktów do cofnięcia", 2000)
        else:
            self.statusBar().showMessage("Cofnij działa tylko w trybie rysowania", 2000)

    def _on_zoom_in(self):
        self.primary_canvas.zoom_in()
        self.statusBar().showMessage("Przybliżenie", 1500)

    def _on_zoom_out(self):
        self.primary_canvas.zoom_out()
        self.statusBar().showMessage("Oddalenie", 1500)

    def _on_fit_view(self):
        self.primary_canvas.fit_view()
        for canvas in self._plane_tab_canvases.values():
            canvas.fit_view()
        self.statusBar().showMessage("Dopasowano widok", 1500)

    def _on_canvas_vertex_moved(self, canvas: DrawingCanvas, vertex_index: int, dx_cm: float, dy_cm: float):
        plane_id = canvas.roof_plane.id if canvas.roof_plane else None
        if plane_id is None:
            return
        try:
            self.project_state.move_roof_plane_point(vertex_index, dx_cm, dy_cm, plane_id)
            self._clear_generated_report()
            self._persist_project_state()
            self._refresh_canvas_from_state()
            self.statusBar().showMessage(f"Przesunięto punkt {vertex_index}", 3000)
        except (ValueError, IndexError) as error:
            QMessageBox.warning(self, "Błąd edycji", str(error))
            self.statusBar().showMessage(str(error), 4000)

    def _connect_canvas_signals(self, canvas: DrawingCanvas):
        canvas.vertex_moved.connect(lambda index, dx, dy: self._on_canvas_vertex_moved(canvas, index, dx, dy))
        canvas.outline_finalized.connect(self._on_canvas_outline_finalized)

    def _on_canvas_outline_finalized(self, points: list):
        try:
            outline = Polygon2D(points)
            self._add_roof_plane(outline, "Dowolny", f"{len(points)} punktów")
            self.primary_canvas.set_mode(DrawingCanvas.MODE_VIEW)
            for canvas in self._plane_tab_canvases.values():
                canvas.set_mode(DrawingCanvas.MODE_VIEW)
            for action, _ in self._toolbar_actions:
                if action.toolTip() == "Rysowanie krawędzi połaci":
                    action.setChecked(False)
            self.statusBar().showMessage("Dodano połać z rysowanego obrysu", 4000)
        except ValueError as error:
            QMessageBox.warning(self, "Błąd obrysu", str(error))
            self.statusBar().showMessage(str(error), 4000)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())
