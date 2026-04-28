# This Python file uses the following encoding: utf-8
"""ui/dialogs/settings_dialog.py — Modal application settings dialog."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)

from core.app_settings import (
    AppSettings,
    LIVE_ANGLE_MODE_ABSOLUTE,
    LIVE_ANGLE_MODE_RELATIVE_TO_PREV,
    SHIFT_DRAG_BEHAVIOR_FREE_MOVE,
    SHIFT_DRAG_BEHAVIOR_ORTHOGONAL_LOCK,
)


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

        grp_grid = QGroupBox("Siatka i przyciąganie")
        grid_form = QFormLayout(grp_grid)
        grid_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)

        self._spin_grid_size = QDoubleSpinBox()
        self._spin_grid_size.setRange(1.0, 1000.0)
        self._spin_grid_size.setSingleStep(1.0)
        self._spin_grid_size.setDecimals(1)
        self._spin_grid_size.setSuffix(" cm")
        self._spin_grid_size.setToolTip(
            "Rozmiar oczka siatki używanego do rysowania siatki roboczej\n"
            "oraz przyciągania punktów podczas przeciągania geometrii."
        )
        grid_label = QLabel("Rozmiar oczka siatki:")
        grid_label.setWordWrap(True)
        grid_form.addRow(grid_label, self._spin_grid_size)

        self._combo_shift_behavior = QComboBox()
        self._combo_shift_behavior.addItem("Shift: swobodny ruch bez przyciągania", SHIFT_DRAG_BEHAVIOR_FREE_MOVE)
        self._combo_shift_behavior.addItem("Shift: blokada osi X/Y co 1 cm", SHIFT_DRAG_BEHAVIOR_ORTHOGONAL_LOCK)
        self._combo_shift_behavior.setToolTip(
            "Określa działanie klawisza Shift podczas przeciągania punktów,\n"
            "wycinków i punktu bazowego."
        )
        shift_label = QLabel("Zachowanie klawisza Shift:")
        shift_label.setWordWrap(True)
        grid_form.addRow(shift_label, self._combo_shift_behavior)

        self._check_axis_overlay = QCheckBox("Pokaż wskaźnik osi X/Y")
        self._check_axis_overlay.setToolTip("Pokazuje mały wskaźnik osi podczas rysowania odręcznego.")
        grid_form.addRow("Orientacja:", self._check_axis_overlay)

        self._spin_grid_major = QSpinBox()
        self._spin_grid_major.setRange(1, 10000)
        self._spin_grid_major.setSingleStep(10)
        self._spin_grid_major.setSuffix(" cm")
        self._spin_grid_major.setToolTip("Odstęp głównych linii siatki roboczej.")
        grid_form.addRow("Główna siatka:", self._spin_grid_major)

        self._spin_grid_minor = QSpinBox()
        self._spin_grid_minor.setRange(1, 10000)
        self._spin_grid_minor.setSingleStep(1)
        self._spin_grid_minor.setSuffix(" cm")
        self._spin_grid_minor.setToolTip("Odstęp pomocniczych linii siatki roboczej.")
        grid_form.addRow("Pomocnicza siatka:", self._spin_grid_minor)

        self._check_crosshair = QCheckBox("Pokaż krzyżyk kursora")
        self._check_crosshair.setToolTip("Pokazuje subtelny krzyżyk kierunkowy podczas rysowania i edycji.")
        grid_form.addRow("Kursor:", self._check_crosshair)

        root.addWidget(grp_grid)

        grp_live_drawing = QGroupBox("Rysowanie na żywo")
        live_form = QFormLayout(grp_live_drawing)
        live_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)

        self._combo_live_angle_mode = QComboBox()
        self._combo_live_angle_mode.addItem("Kąt bezwzględny od osi X", LIVE_ANGLE_MODE_ABSOLUTE)
        self._combo_live_angle_mode.addItem("Kąt względem poprzedniej krawędzi", LIVE_ANGLE_MODE_RELATIVE_TO_PREV)
        live_form.addRow("Tryb kąta:", self._combo_live_angle_mode)

        self._check_show_decimal_cm = QCheckBox("Pokazuj długości z dokładnością do 0.1 cm")
        live_form.addRow("Precyzja długości:", self._check_show_decimal_cm)

        self._check_show_angle_arc = QCheckBox("Pokaż łuk kąta przy aktywnym wierzchołku")
        live_form.addRow("Łuk kąta:", self._check_show_angle_arc)

        self._check_show_guide_lines = QCheckBox("Pokaż subtelne linie pomocnicze aktywnego segmentu")
        live_form.addRow("Linie pomocnicze:", self._check_show_guide_lines)

        self._check_close_on_rmb = QCheckBox("Zamykaj wielokąt prawym przyciskiem myszy")
        live_form.addRow("Zamykanie:", self._check_close_on_rmb)

        root.addWidget(grp_live_drawing)

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
        self._spin_grid_size.setValue(settings.grid_size_cm)
        index = self._combo_shift_behavior.findData(settings.shift_drag_behavior)
        self._combo_shift_behavior.setCurrentIndex(max(0, index))
        self._check_axis_overlay.setChecked(settings.show_axis_overlay)
        self._spin_grid_major.setValue(settings.grid_major_cm)
        self._spin_grid_minor.setValue(settings.grid_minor_cm)
        self._check_crosshair.setChecked(settings.show_crosshair)
        live_angle_index = self._combo_live_angle_mode.findData(settings.live_angle_mode)
        self._combo_live_angle_mode.setCurrentIndex(max(0, live_angle_index))
        self._check_show_decimal_cm.setChecked(settings.show_decimal_cm)
        self._check_show_angle_arc.setChecked(settings.show_angle_arc)
        self._check_show_guide_lines.setChecked(settings.show_guide_lines)
        self._check_close_on_rmb.setChecked(settings.close_on_rmb)

    def get_values(self) -> dict:
        """Return current dialog values as a dict matching AppSettings fields."""
        return {
            "partial_cutout_top_extra_cm": self._spin_top_extra.value(),
            "grid_size_cm": self._spin_grid_size.value(),
            "shift_drag_behavior": self._combo_shift_behavior.currentData(),
            "show_axis_overlay": self._check_axis_overlay.isChecked(),
            "grid_major_cm": self._spin_grid_major.value(),
            "grid_minor_cm": self._spin_grid_minor.value(),
            "show_crosshair": self._check_crosshair.isChecked(),
            "live_angle_mode": self._combo_live_angle_mode.currentData(),
            "show_decimal_cm": self._check_show_decimal_cm.isChecked(),
            "show_angle_arc": self._check_show_angle_arc.isChecked(),
            "show_guide_lines": self._check_show_guide_lines.isChecked(),
            "close_on_rmb": self._check_close_on_rmb.isChecked(),
        }

    def build_settings(self) -> AppSettings:
        """Build and return a new AppSettings from current dialog values."""
        return AppSettings.from_dict(self.get_values())
