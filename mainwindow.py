# This Python file uses the following encoding: utf-8
import sys

from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtGui import QAction, QColor, QFont, QKeySequence, QMouseEvent, QPainter, QPalette, QPen, QPolygonF
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
from core.geometry import build_rectangle_outline, build_trapezoid_outline, build_triangle_outline
from core.models import Point2D, Polygon2D, SheetPlacement
from core.project_state import ProjectState
from core.reporting import build_report, build_report_html


class DrawingCanvas(QWidget):
    def __init__(self, parent=None, show_demo=True):
        super().__init__(parent)
        self.show_demo = show_demo
        self.user_points = []
        self.preview_point = None
        self.roof_plane = None
        self.setMouseTracking(True)
        self.setAutoFillBackground(True)
        self.setMinimumSize(640, 420)

    def set_roof_plane(self, roof_plane):
        self.roof_plane = roof_plane
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.user_points.append(event.position())
            self.update()
            return

        if event.button() == Qt.MouseButton.RightButton:
            self.user_points.clear()
            self.preview_point = None
            self.update()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        self.preview_point = event.position()
        self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.preview_point = None
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), self.palette().color(QPalette.ColorRole.Base))

        frame_color = self.palette().color(QPalette.ColorRole.Mid)
        painter.setPen(QPen(frame_color, 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        if self.roof_plane is not None:
            self._draw_roof_plane(painter)
        elif self.show_demo:
            self._draw_demo_shape(painter)

        self._draw_user_path(painter)
        painter.end()
        super().paintEvent(event)

    def _draw_demo_shape(self, painter: QPainter):
        line_color = self.palette().color(QPalette.ColorRole.Text)
        accent_color = QColor("#a84d42") if self.palette().color(QPalette.ColorRole.Base).lightness() > 128 else QColor("#ff9d7a")

        area = self.rect().adjusted(60, 50, -50, -60)
        points = [
            QPointF(area.left() + area.width() * 0.02, area.top() + area.height() * 0.15),
            QPointF(area.left() + area.width() * 0.02, area.top() + area.height() * 0.72),
            QPointF(area.left() + area.width() * 0.92, area.top() + area.height() * 0.93),
            QPointF(area.left() + area.width() * 0.40, area.top() + area.height() * 0.45),
        ]

        painter.setPen(QPen(line_color, 1.4))
        painter.drawLine(points[0], points[1])
        painter.drawLine(points[0], points[2])
        painter.drawLine(points[1], points[2])

        painter.setBrush(line_color)
        for point in points[:3]:
            painter.drawRect(int(point.x()) - 2, int(point.y()) - 2, 4, 4)

        painter.setPen(QPen(accent_color, 1.4))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(int(points[1].x()) - 7, int(points[1].y()) - 7, 14, 14)

        painter.setPen(QPen(line_color, 1))
        painter.drawText(int(points[0].x()) + 2, int((points[0].y() + points[1].y()) / 2), "300")
        painter.drawText(int((points[0].x() + points[3].x()) / 2), int((points[0].y() + points[3].y()) / 2) - 8, "43°")
        painter.drawText(int((points[3].x() + points[2].x()) / 2), int((points[3].y() + points[2].y()) / 2), "67°")
        painter.drawText(int((points[1].x() + points[2].x()) / 2), int((points[1].y() + points[2].y()) / 2) + 12, "1057")

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

    def _draw_roof_plane(self, painter: QPainter):
        plane = self.roof_plane
        if plane is None:
            return

        bounds = plane.outline.bounds()
        available = self.rect().adjusted(40, 30, -40, -30)
        width = max(bounds.width, 1.0)
        height = max(bounds.height, 1.0)
        scale = min(available.width() / width, available.height() / height)
        scale = scale if scale > 0 else 1.0

        offset_x = available.left() + (available.width() - width * scale) / 2.0
        offset_y = available.top() + (available.height() - height * scale) / 2.0

        def map_point(point):
            return QPointF(
                offset_x + (point.x - bounds.min_x) * scale,
                offset_y + (point.y - bounds.min_y) * scale,
            )

        outline_polygon = QPolygonF([map_point(point) for point in plane.outline.points])
        fill_color = self.palette().color(QPalette.ColorRole.AlternateBase)
        outline_color = self.palette().color(QPalette.ColorRole.Highlight)
        text_color = self.palette().color(QPalette.ColorRole.Text)
        hole_color = QColor(outline_color)
        hole_color.setAlpha(180)

        painter.setPen(QPen(outline_color, 2))
        painter.setBrush(fill_color)
        painter.drawPolygon(outline_polygon)

        painter.setPen(QPen(hole_color, 1.5, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for hole in plane.holes:
            painter.drawPolygon(QPolygonF([map_point(point) for point in hole.points]))

        painter.setPen(text_color)
        label = f"Połać {plane.name}"
        if plane.selected_material_id:
            label += f" | Blacha: {plane.selected_material_id}"
        painter.drawText(available.left(), available.top() - 8, label)


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
                    ("Dowolny", None, None),
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

    def _add_toolbar_action(self, toolbar: QToolBar, icon_kind: str, text: str):
        action = QAction(text, self)
        action.setToolTip(text)
        action.setStatusTip(text)
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
            ("new_document", "Nowy projekt"),
            ("open_folder", "Otwórz projekt"),
            ("save_floppy", "Zapisz projekt"),
            ("roof_outline", "Rysowanie krawędzi połaci"),
            ("base_point_toggle", "Pokaż/ukryj punkt bazowy"),
            ("undo", "Cofnij"),
            ("plus", "Dodaj / Plus"),
            ("minus", "Odejmij / Minus"),
            ("module_count", "Włącz/wyłącz pokazywanie ilości modułów"),
            ("zoom_out", "Oddal / Pomniejsz"),
            ("fit_view", "Pokaż wszystko / Dopasuj do ekranu"),
            ("broom", "Wyczyść / Usuń wszystko"),
        ]

        for index, (icon_kind, text) in enumerate(icon_actions):
            self._add_toolbar_action(toolbar, icon_kind, text)
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
            ("overlay_sheet", "Nakładanie blachy na powierzchnie"),
            ("grid", "Siatka"),
            ("select_properties", "Właściwości / Wybierz"),
            ("from_right", "Od prawej"),
            ("from_base", "Od bazy"),
        ]

        for icon_kind, text in trailing_actions:
            self._add_toolbar_action(toolbar, icon_kind, text)

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

        self.secondary_canvas = DrawingCanvas(self.workspace_tabs, show_demo=False)
        self.secondary_canvas.hide()

        self.report_tab = QWidget(self.workspace_tabs)
        second_layout = QVBoxLayout(self.report_tab)
        second_layout.setContentsMargins(0, 0, 0, 0)
        self.report_view = QTextBrowser(self.report_tab)
        self.report_view.setObjectName("report_view")
        self.report_view.setOpenExternalLinks(False)
        second_layout.addWidget(self.report_view)

        self.primary_canvas = DrawingCanvas(self.workspace_tabs, show_demo=True)
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
        canvas = DrawingCanvas(tab, show_demo=False)
        canvas.set_roof_plane(plane)
        layout.addWidget(canvas)
        tab.setProperty("plane_id", plane.id)
        self._plane_tab_canvases[plane.id] = canvas
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
                self.workspace_tabs.addTab(tab, plane.name)
                if plane.id == self.project_state.active_plane_id:
                    self.primary_canvas = canvas
        else:
            placeholder_tab = QWidget(self.workspace_tabs)
            placeholder_layout = QVBoxLayout(placeholder_tab)
            placeholder_layout.setContentsMargins(0, 0, 0, 0)
            self.primary_canvas = DrawingCanvas(placeholder_tab, show_demo=True)
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
                    dirty_message = (
                        f"<p><strong>Stan layoutu:</strong> wynik jest nieaktualny "
                        f"({active_plane.layout_dirty_reason}).</p>"
                    )
                content = (
                    "<html><body>"
                    f"<h1>Raport 4Dach - {active_plane.name}</h1>"
                    "<p>Raport nie został jeszcze wygenerowany dla aktywnej połaci.</p>"
                    f"{dirty_message}"
                    "<p>Użyj akcji <strong>Plik -> Drukuj raport</strong>, aby przeliczyć layout, BOM i ostrzeżenia.</p>"
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
        message = (
            f"Aktywne arkusze: {len(active_sheets)}\n"
            f"Ręczne arkusze: {manual_count}\n"
            f"Ukryte auto-arkusze: {removed_count}\n"
            f"Stan layoutu: {plane.layout_dirty_reason or 'aktualny'}"
        )
        QMessageBox.information(self, f"Aktywne arkusze - {plane.name}", message)
        self.statusBar().showMessage(f"Pokazano podsumowanie arkuszy połaci {plane.name}", 3000)

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

    def _generate_report_preview(self, variant: str):
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
        self._refresh_report_view(html)
        self.workspace_tabs.setCurrentIndex(self._report_tab_index())
        return True

    def _open_standard_report_preview(self):
        if self._generate_report_preview("standard"):
            self.statusBar().showMessage("Wygenerowano raport dla aktywnej połaci", 4000)

    def _open_continuous_report_preview(self):
        if self._generate_report_preview("continuous"):
            self.statusBar().showMessage("Wygenerowano raport ciągły dla aktywnej połaci", 4000)

    def _open_short_report_preview(self):
        if self._generate_report_preview("short"):
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())
