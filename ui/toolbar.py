# This Python file uses the following encoding: utf-8
"""toolbar.py — ToolbarController builds and manages the main QToolBar.

Responsibilities:
- Creating toolbar actions with consistent icon + tooltip + callback wiring
- Exposing named action references (self.action_grid, self.action_from_right, …)
- Refreshing icon colours when the theme changes
"""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QColor, QFont
from PySide6.QtWidgets import QComboBox, QMainWindow, QToolBar, QToolButton

from app_icons import build_icon


class ToolbarController:
    """Builds the main application toolbar and exposes key actions."""

    def __init__(self, main_window: QMainWindow) -> None:
        self._win = main_window
        self._toolbar_actions: list[tuple[QAction, str]] = []  # (action, icon_kind)
        self.toolbar = self._create_toolbar()
        self._build_actions()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def refresh_icons(self, foreground: QColor, accent: QColor, muted: QColor) -> None:
        """Re-render all toolbar icons for the current theme colours."""
        for action, icon_kind in self._toolbar_actions:
            icon_color = self._icon_color_for_kind(icon_kind, foreground, accent, muted)
            action.setIcon(build_icon(icon_kind, icon_color, 18))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_toolbar(self) -> QToolBar:
        tb = QToolBar("Pasek główny", self._win)
        tb.setObjectName("main_toolbar")
        tb.setMovable(False)
        tb.setFloatable(False)
        tb.setIconSize(QSize(18, 18))
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        tb.setStyleSheet(
            "QToolBar { spacing: 2px; padding: 1px; }"
            "QToolButton { padding: 1px; margin: 0px; }"
        )
        self._win.addToolBar(tb)
        return tb

    def _add_action(
        self,
        icon_kind: str,
        text: str,
        checkable: bool = False,
        callback=None,
    ) -> QAction:
        action = QAction(text, self._win)
        action.setToolTip(text)
        action.setStatusTip(text)
        action.setCheckable(checkable)
        if callback:
            action.triggered.connect(callback)
        # Always connect statusbar fallback (shows a message; harmless second slot)
        action.triggered.connect(
            lambda checked=False, msg=text: self._win.statusBar().showMessage(msg, 2500)
        )
        self.toolbar.addAction(action)
        self._toolbar_actions.append((action, icon_kind))
        return action

    def _icon_color_for_kind(self, kind: str, fg: QColor, accent: QColor, muted: QColor) -> QColor:
        if kind in {"base_point_toggle", "sun", "moon"}:
            return accent
        if kind in {"module_count", "grid", "broom"}:
            return muted
        return fg

    def _build_actions(self) -> None:
        tb = self.toolbar
        sep_after = {2, 4, 7, 11}

        icon_rows: list[tuple[str, str, bool, object]] = [
            ("new_document",   "Nowy projekt",                                False, None),
            ("open_folder",    "Otwórz projekt",                              False, None),
            ("save_floppy",    "Zapisz projekt",                              False, None),
            ("roof_outline",   "Rysowanie krawędzi połaci",                   False, None),
            ("base_point_toggle", "Pokaż/ukryj punkt bazowy",                 False, None),
            ("undo",           "Cofnij",                                       False, None),
            ("plus",           "Dodaj / Plus",                                False, None),
            ("minus",          "Odejmij / Minus",                             False, None),
            ("module_count",   "Włącz/wyłącz pokazywanie ilości modułów",     False, None),
            ("zoom_out",       "Oddal / Pomniejsz",                           False, None),
            ("fit_view",       "Pokaż wszystko / Dopasuj do ekranu",          False, None),
            ("broom",          "Wyczyść / Usuń wszystko",                     False, None),
        ]

        for index, (icon_kind, text, checkable, callback) in enumerate(icon_rows):
            action = self._add_action(icon_kind, text, checkable=checkable, callback=callback)
            if index in sep_after:
                tb.addSeparator()

        # Named action references that controllers need
        self.action_module_count = self._toolbar_actions[8][0]

        # Material selector button + combo
        self.material_button = QToolButton(self._win)
        self.material_button.setObjectName("material_button")
        self.material_button.setText("A")
        self.material_button.setToolTip("Wybór aktywnej blachy")
        self.material_button.setStatusTip("Wybór aktywnej blachy")
        self.material_button.setAutoRaise(True)
        self.material_button.setFixedSize(22, 20)
        bold_font = QFont(self._win.font())
        bold_font.setBold(True)
        self.material_button.setFont(bold_font)
        self.material_button.clicked.connect(
            lambda: self._win.statusBar().showMessage("Wybór aktywnej blachy", 2500)
        )
        tb.addWidget(self.material_button)

        self.variant_combo = QComboBox(self._win)
        self.variant_combo.setObjectName("variant_combo")
        self.variant_combo.setEditable(True)
        self.variant_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.variant_combo.setFixedWidth(146)
        line_edit = self.variant_combo.lineEdit()
        if line_edit is not None:
            line_edit.setReadOnly(True)
        self.variant_combo.setToolTip("Wybór aktywnej blachy")
        tb.addWidget(self.variant_combo)
        tb.addSeparator()

        # Trailing toggle actions
        trailing: list[tuple[str, str, bool, object]] = [
            ("overlay_sheet",    "Nakładanie blachy na powierzchnie", False, None),
            ("grid",             "Siatka",                             False, None),
            ("select_properties","Właściwości / Wybierz",             False, None),
            ("from_right",       "Od prawej",                          True,  None),
            ("from_base",        "Od bazy",                            True,  None),
        ]
        for icon_kind, text, checkable, callback in trailing:
            action = self._add_action(icon_kind, text, checkable=checkable, callback=callback)

        # Named references for trailing actions
        trailing_actions = [t[0] for t in self._toolbar_actions[-5:]]
        self.action_overlay_sheet   = trailing_actions[0]
        self.action_grid            = trailing_actions[1]
        self.action_select_props    = trailing_actions[2]
        self.action_from_right      = trailing_actions[3]
        self.action_from_base       = trailing_actions[4]
