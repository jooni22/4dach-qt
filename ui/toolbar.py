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
        self._actions_by_kind: dict[str, QAction] = {}
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
            "QToolButton { padding: 1px; margin: 0px; border: 1px solid transparent; border-radius: 4px; }"
            "QToolButton:checked { background: rgba(90, 150, 255, 0.22); border-color: rgba(90, 150, 255, 0.75); }"
            "QToolButton:pressed { background: rgba(90, 150, 255, 0.30); border-color: rgba(90, 150, 255, 0.85); }"
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
        self._actions_by_kind[icon_kind] = action
        return action

    def _action(self, kind: str) -> QAction:
        return self._actions_by_kind[kind]

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
            ("base_point_toggle", "Ustaw punkt zerowy",                       True,  None),
            ("undo",           "Cofnij",                                       False, None),
            ("plus",           "Nowa połać",                                  False, None),
            ("duplicate_surface", "Duplikuj połać",                           False, None),
            ("trash",          "Usuń zaznaczone (Del)",                       False, None),
        ]

        for index, (icon_kind, text, checkable, callback) in enumerate(icon_rows):
            action = self._add_action(icon_kind, text, checkable=checkable, callback=callback)
            if index in sep_after:
                tb.addSeparator()

        # Named action references that controllers need
        self.action_new_project = self._action("new_document")
        self.action_open_project = self._action("open_folder")
        self.action_save_project = self._action("save_floppy")
        self.action_draw_outline = self._action("roof_outline")
        self.action_draw_outline.setCheckable(True)
        self.action_base_point_toggle = self._action("base_point_toggle")
        self.action_undo = self._action("undo")
        self.action_new_surface = self._action("plus")
        self.action_duplicate_surface = self._action("duplicate_surface")
        self.action_trash = self._action("trash")

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
            ("overlay_sheet",    "Pokaż arkusze",                    True,  None),
            ("grid",             "Pokaż siatkę",                     True,  None),
            ("from_left",        "Układaj od lewej",                  True,  None),
            ("from_right",       "Od prawej",                          True,  None),
        ]
        for icon_kind, text, checkable, callback in trailing:
            self._add_action(icon_kind, text, checkable=checkable, callback=callback)

        # Named references for trailing actions
        self.action_overlay_sheet = self._action("overlay_sheet")
        self.action_grid = self._action("grid")
        self.action_from_left = self._action("from_left")
        self.action_from_right = self._action("from_right")
