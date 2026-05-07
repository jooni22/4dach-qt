"""theme_manager.py — centralised Qt palette and stylesheet management.

ThemeManager owns the light/dark palette definitions, the global stylesheet
template, and the icon-colour helpers.  It persists the current theme via
``QSettings`` so the user's preference is restored between sessions.
"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


@dataclass(frozen=True)
class _ThemeTokens:
    """All colour values needed to build palette + stylesheet."""
    menu_bg: str
    menu_hover: str
    menu_text: str
    border: str
    tab_selected: str
    tab_hover: str
    toolbar_bg: str
    button_hover: str
    canvas_border: str
    input_bg: str
    pressed_bg: str
    disabled_text: str
    toggle_tip: str
    icon_fg: QColor
    icon_accent: QColor
    icon_muted: QColor
    palette: QPalette


def _build_dark_tokens() -> _ThemeTokens:
    palette = QPalette()
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
    return _ThemeTokens(
        menu_bg="#2d323c", menu_hover="#454d59", menu_text="#f0f0f0",
        border="#555d69", tab_selected="#171a20", tab_hover="#39414d",
        toolbar_bg="#2a2f38", button_hover="#454d59", canvas_border="#555d69",
        input_bg="#171a20", pressed_bg="#536071", disabled_text="#7d8794",
        toggle_tip="Przełącz na tryb jasny",
        icon_fg=QColor("#f1efe7"), icon_accent=QColor("#8dc7ff"), icon_muted=QColor("#aeb7c4"),
        palette=palette,
    )


def _build_light_tokens() -> _ThemeTokens:
    palette = QPalette()
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
    return _ThemeTokens(
        menu_bg="#e3e0d4", menu_hover="#d0d0d0", menu_text="#1c1a16",
        border="#9e9e97", tab_selected="#fffdf4", tab_hover="#d7d3c7",
        toolbar_bg="#dedccf", button_hover="#d4d1c6", canvas_border="#9e9e97",
        input_bg="#fffdf4", pressed_bg="#cbc7bb", disabled_text="#8d8a80",
        toggle_tip="Przełącz na tryb ciemny",
        icon_fg=QColor("#49453b"), icon_accent=QColor("#c74d3d"), icon_muted=QColor("#777367"),
        palette=palette,
    )


def _build_stylesheet(t: _ThemeTokens) -> str:
    return (
        "QMainWindow { background: palette(window); }"
        f"QMenuBar {{ spacing: 4px; background: {t.menu_bg}; color: {t.menu_text}; border-bottom: 1px solid {t.border}; }}"
        "QMenuBar::item { padding: 3px 8px; background: transparent; }"
        f"QMenuBar::item:selected {{ background: {t.menu_hover}; color: {t.menu_text}; }}"
        f"QMenu {{ background: {t.menu_bg}; color: {t.menu_text}; border: 1px solid {t.border}; }}"
        f"QMenu::item:selected {{ background: {t.menu_hover}; color: {t.menu_text}; }}"
        f"QPushButton {{ color: {t.menu_text}; background: palette(button); border: 1px solid {t.border}; padding: 3px 10px; min-height: 20px; }}"
        f"QPushButton:hover {{ background: {t.button_hover}; }}"
        f"QPushButton:pressed {{ background: {t.pressed_bg}; }}"
        f"QPushButton:disabled {{ color: {t.disabled_text}; background: {t.toolbar_bg}; border: 1px solid {t.border}; }}"
        f"QToolBar {{ background: {t.toolbar_bg}; border-top: 1px solid {t.border}; border-bottom: 1px solid {t.border}; spacing: 2px; padding: 1px; }}"
        f"QToolBar::separator {{ width: 1px; margin: 2px 3px; background: {t.border}; }}"
        f"QToolButton {{ color: {t.menu_text}; padding: 1px; margin: 0px; border: 1px solid transparent; background: transparent; }}"
        f"QToolButton:hover {{ background: {t.button_hover}; border: 1px solid {t.border}; }}"
        f"QToolButton:pressed {{ background: {t.pressed_bg}; border: 1px solid {t.border}; }}"
        f"QToolButton:disabled {{ color: {t.disabled_text}; }}"
        f"QLineEdit, QComboBox {{ background: {t.input_bg}; color: {t.menu_text}; border: 1px solid {t.border}; padding: 1px 3px; selection-background-color: {t.button_hover}; selection-color: {t.menu_text}; }}"
        f"QComboBox::editable {{ background: {t.input_bg}; }}"
        f"QComboBox QLineEdit {{ background: {t.input_bg}; color: {t.menu_text}; border: none; padding: 0px; }}"
        f"QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 18px; border-left: 1px solid {t.border}; background: {t.button_hover}; }}"
        "QComboBox::down-arrow { width: 8px; height: 8px; }"
        f"QComboBox QAbstractItemView {{ background: {t.input_bg}; color: {t.menu_text}; border: 1px solid {t.border}; selection-background-color: {t.button_hover}; selection-color: {t.menu_text}; }}"
        f"QTabWidget::pane {{ border-top: 1px solid {t.border}; background: palette(base); }}"
        f"QTabBar::tab {{ color: {t.menu_text}; background: {t.toolbar_bg}; border: 1px solid {t.border}; border-bottom: none; padding: 1px 5px; min-width: 14px; margin-right: 1px; }}"
        f"QTabBar::tab:selected {{ background: {t.tab_selected}; color: {t.menu_text}; }}"
        f"QTabBar::tab:hover {{ background: {t.tab_hover}; }}"
        f"QStatusBar {{ color: {t.menu_text}; border-top: 1px solid {t.border}; }}"
        f"DrawingCanvas {{ border: 1px solid {t.canvas_border}; background: palette(base); }}"
        f"QToolButton#theme_toggle {{ border: none; padding: 0 8px; background: transparent; }}"
        f"QToolButton#theme_toggle:hover {{ background: {t.menu_hover}; border: none; }}"
    )


class ThemeManager:
    """Manages application theme (light/dark) with QSettings persistence."""

    _SETTINGS_KEY = "theme"

    def __init__(self) -> None:
        self._settings = QSettings()
        self._theme: str = self._settings.value(self._SETTINGS_KEY, "light")
        if self._theme not in ("light", "dark"):
            self._theme = "light"

    @property
    def current_theme(self) -> str:
        return self._theme

    @property
    def tokens(self) -> _ThemeTokens:
        return _build_dark_tokens() if self._theme == "dark" else _build_light_tokens()

    def toggle(self) -> None:
        self._theme = "dark" if self._theme == "light" else "light"
        self._settings.setValue(self._SETTINGS_KEY, self._theme)

    def set_theme(self, name: str) -> None:
        if name in ("light", "dark"):
            self._theme = name
            self._settings.setValue(self._SETTINGS_KEY, name)

    def apply(self) -> _ThemeTokens:
        """Apply palette + stylesheet to the running QApplication. Returns tokens."""
        app = QApplication.instance()
        if not app:
            raise RuntimeError("QApplication must exist before applying theme")
        t = self.tokens
        app.setPalette(t.palette)
        app.setStyleSheet(_build_stylesheet(t))
        return t
