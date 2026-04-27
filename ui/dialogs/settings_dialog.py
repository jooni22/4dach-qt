# This Python file uses the following encoding: utf-8
"""ui/dialogs/settings_dialog.py — Modal application settings dialog."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QVBoxLayout,
)

from core.app_settings import AppSettings


class SettingsDialog(QDialog):
    """Modal application settings dialog.

    Usage::

        dlg = SettingsDialog(current_settings, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_settings = dlg.build_settings()
    """

    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ustawienia aplikacji")
        self.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumWidth(420)
        self._settings = settings
        self._build_ui()
        self._load_values(settings)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        # --- Sekcja: Wycinki ---
        grp_cutouts = QGroupBox("Wycinki")
        form = QFormLayout(grp_cutouts)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)

        self._spin_top_extra = QDoubleSpinBox()
        self._spin_top_extra.setRange(0.0, 200.0)
        self._spin_top_extra.setSingleStep(0.5)
        self._spin_top_extra.setDecimals(1)
        self._spin_top_extra.setSuffix(" cm")
        self._spin_top_extra.setToolTip(
            "Dodatkowy zapas materiału dodawany do górnego odcinka arkusza,\n"
            "gdy wycinek (otwór) nie przykrywa całej szerokości pasa blachy.\n"
            "Wartość 0 oznacza brak zapasu."
        )
        lbl = QLabel("Zapas górnego odcinka\ndla częściowo przykrytego arkusza:")
        lbl.setWordWrap(True)
        form.addRow(lbl, self._spin_top_extra)

        root.addWidget(grp_cutouts)

        # --- Przyciski ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load_values(self, settings: AppSettings) -> None:
        self._spin_top_extra.setValue(settings.partial_cutout_top_extra_cm)

    def get_values(self) -> dict:
        """Return current dialog values as a dict matching AppSettings fields."""
        return {
            "partial_cutout_top_extra_cm": self._spin_top_extra.value(),
        }

    def build_settings(self) -> AppSettings:
        """Build and return a new AppSettings from current dialog values."""
        return AppSettings.from_dict(self.get_values())
