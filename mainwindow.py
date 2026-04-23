# This Python file uses the following encoding: utf-8
import sys

from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtGui import QAction, QColor, QFont, QKeySequence, QMouseEvent, QPainter, QPalette, QPen
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QMainWindow,
    QSizePolicy,
    QTabWidget,
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


class DrawingCanvas(QWidget):
    def __init__(self, parent=None, show_demo=True):
        super().__init__(parent)
        self.show_demo = show_demo
        self.user_points = []
        self.preview_point = None
        self.setMouseTracking(True)
        self.setAutoFillBackground(True)
        self.setMinimumSize(640, 420)

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

        if self.show_demo:
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


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self._actions = []
        self._toolbar_actions = []
        self._theme = "light"
        self.ui.setupUi(self)
        self.setWindowTitle("4Dach wersja 1.0 Super Dach sp.j. instalacja 3, plik: testmarcin (zmieniony)")
        self.resize(1120, 720)
        self._setup_window_style()
        self._build_main_menu()
        self._build_top_toolbar()
        self._setup_central_area()
        self._apply_theme()
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
                    ("Nowy dach", "Ctrl+N"),
                    ("Otwórz...", "Ctrl+O"),
                    ("Zapisz", "Ctrl+S"),
                    ("Zapisz jako...", "Shift+Ctrl+S"),
                    None,
                    ("Drukuj raport", "Ctrl+P"),
                    ("Drukuj raport ciągły", "Shift+Ctrl+P"),
                    ("Drukuj raport skrócony", None),
                    None,
                    ("Zakończ", "Ctrl+Q"),
                ],
            ),
            (
                "Kształt",
                [
                    ("Prostokąt...", None),
                    ("Trójkąt...", None),
                    ("Trapez...", None),
                    ("Dowolny", None),
                    None,
                    ("Przesuń", None),
                    ("Przesuń punkt", None),
                    None,
                    ("Odwróć w pionie", None),
                    ("Odwróć w poziomie", None),
                    ("Obracanie...", None),
                    None,
                    ("Wyrównaj punkt w poziomie", "Ctrl+W"),
                    ("Wyrównaj punkt w pionie", "Ctrl+E"),
                ],
            ),
            (
                "Wycinki",
                [
                    ("Dodaj wycinek", None),
                    ("Usuń wycinek", None),
                    ("Przesuń wycinek", None),
                    ("Skopiuj wycinek", None),
                    ("Wklej wycinek", None),
                ],
            ),
            (
                "Katalog",
                [
                    ("Blachy...", None),
                    ("Dane firmy...", None),
                ],
            ),
            (
                "Arkusze",
                [
                    ("Dodaj arkusz", "Insert"),
                    ("Usuń arkusz", "Delete"),
                    ("Podgląd arkuszy", "Ctrl+A"),
                    ("Aktywne arkusze", None),
                    None,
                    ("Ustaw linię podziału", None),
                    ("Usuń linię podziału", None),
                    None,
                    ("Zmień rodzaj blachy", None),
                ],
            ),
        ]

        for menu_title, entries in menu_structure:
            menu = self.menuBar().addMenu(menu_title)
            for entry in entries:
                if entry is None:
                    menu.addSeparator()
                    continue

                title, shortcut = entry
                menu.addAction(self._create_menu_action(title, shortcut))

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
        variant_combo.lineEdit().setReadOnly(True)
        variant_combo.setFixedWidth(146)
        variant_combo.addItems(["PD510", "PD610", "PD710"])
        variant_combo.setCurrentText("PD510")
        variant_combo.setToolTip("Wybór aktywnej blachy")
        variant_combo.currentTextChanged.connect(lambda text: self.statusBar().showMessage(f"Aktywna blacha: {text}", 2500))
        self.variant_combo = variant_combo
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

        self.primary_canvas = DrawingCanvas(self.workspace_tabs, show_demo=True)
        self.secondary_canvas = DrawingCanvas(self.workspace_tabs, show_demo=False)

        first_tab = QWidget(self.workspace_tabs)
        first_layout = QVBoxLayout(first_tab)
        first_layout.setContentsMargins(0, 0, 0, 0)
        first_layout.addWidget(self.primary_canvas)

        second_tab = QWidget(self.workspace_tabs)
        second_layout = QVBoxLayout(second_tab)
        second_layout.setContentsMargins(0, 0, 0, 0)
        second_layout.addWidget(self.secondary_canvas)

        self.workspace_tabs.addTab(first_tab, "1")
        self.workspace_tabs.addTab(second_tab, "2")
        layout.addWidget(self.workspace_tabs)
        self.setCentralWidget(central)

    def _toggle_theme(self):
        self._theme = "dark" if self._theme == "light" else "light"
        self._apply_theme()

    def _apply_theme(self):
        app = QApplication.instance()
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())
