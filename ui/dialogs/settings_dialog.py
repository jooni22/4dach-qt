"""ui/dialogs/settings_dialog.py — Modal application settings dialog."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)

from core.app_settings import (
    EDGE_DRAG_MODE_INSERT_VERTEX,
    EDGE_DRAG_MODE_MOVE_VERTICES,
    LIVE_ANGLE_MODE_ABSOLUTE,
    LIVE_ANGLE_MODE_RELATIVE_TO_PREV,
    AppSettings,
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

        self._spin_top_extra = QSpinBox()
        self._spin_top_extra.setRange(0, 200)
        self._spin_top_extra.setSingleStep(1)
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

        self._spin_grid_size = QSpinBox()
        self._spin_grid_size.setRange(1, 1000)
        self._spin_grid_size.setSingleStep(1)
        self._spin_grid_size.setSuffix(" cm")
        self._spin_grid_size.setToolTip(
            "Rozmiar oczka siatki używanego do rysowania siatki roboczej\n"
            "oraz przyciągania punktów podczas przeciągania geometrii."
        )
        grid_label = QLabel("Rozmiar oczka siatki:")
        grid_label.setWordWrap(True)
        grid_form.addRow(grid_label, self._spin_grid_size)

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

        self._check_snap_to_grid = QCheckBox("Przyciągaj do siatki")
        grid_form.addRow("Snap:", self._check_snap_to_grid)

        self._check_snap_to_axis = QCheckBox("Przyciągaj do osi 0°/90°")
        grid_form.addRow("Osie:", self._check_snap_to_axis)

        self._check_snap_to_45deg = QCheckBox("Przyciągaj do 45°")
        grid_form.addRow("Kąty:", self._check_snap_to_45deg)

        self._check_snap_to_3060deg = QCheckBox("Przyciągaj do 30°/60°")
        grid_form.addRow("Kąty 30/60:", self._check_snap_to_3060deg)

        self._check_snap_to_points = QCheckBox("Przyciągaj do punktów charakterystycznych")
        grid_form.addRow("Punkty:", self._check_snap_to_points)

        self._check_show_inferences = QCheckBox("Pokaż linie inferencji CAD")
        grid_form.addRow("Inferencje:", self._check_show_inferences)

        root.addWidget(grp_grid)

        grp_live_drawing = QGroupBox("Rysowanie na żywo")
        live_form = QFormLayout(grp_live_drawing)
        live_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)

        self._combo_live_angle_mode = QComboBox()
        self._combo_live_angle_mode.addItem("Kąt bezwzględny od osi X", LIVE_ANGLE_MODE_ABSOLUTE)
        self._combo_live_angle_mode.addItem("Kąt względem poprzedniej krawędzi", LIVE_ANGLE_MODE_RELATIVE_TO_PREV)
        live_form.addRow("Tryb kąta:", self._combo_live_angle_mode)

        self._check_show_guide_lines = QCheckBox("Pokaż subtelne linie pomocnicze aktywnego segmentu")
        live_form.addRow("Linie pomocnicze:", self._check_show_guide_lines)

        root.addWidget(grp_live_drawing)

        grp_post_draw = QGroupBox("Edycja po rysowaniu")
        post_form = QFormLayout(grp_post_draw)
        post_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)

        self._combo_edge_drag_mode = QComboBox()
        self._combo_edge_drag_mode.addItem("Przeciąganie krawędzi przesuwa oba końce", EDGE_DRAG_MODE_MOVE_VERTICES)
        self._combo_edge_drag_mode.addItem("Przeciąganie krawędzi wstawia nowy wierzchołek", EDGE_DRAG_MODE_INSERT_VERTEX)
        post_form.addRow("Środek krawędzi:", self._combo_edge_drag_mode)

        self._check_show_edge_length_labels = QCheckBox("Pokaż etykiety długości krawędzi")
        post_form.addRow("Długości:", self._check_show_edge_length_labels)

        self._check_show_vertex_angle_labels = QCheckBox("Pokaż etykiety kątów wierzchołków")
        post_form.addRow("Kąty:", self._check_show_vertex_angle_labels)

        self._check_label_always_visible = QCheckBox("Pokazuj etykiety także bez zaznaczenia")
        post_form.addRow("Widoczność:", self._check_label_always_visible)

        root.addWidget(grp_post_draw)

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
        self._spin_grid_major.setValue(settings.grid_major_cm)
        self._spin_grid_minor.setValue(settings.grid_minor_cm)
        self._check_crosshair.setChecked(settings.show_crosshair)
        live_angle_index = self._combo_live_angle_mode.findData(settings.live_angle_mode)
        self._combo_live_angle_mode.setCurrentIndex(max(0, live_angle_index))
        self._check_show_guide_lines.setChecked(settings.show_guide_lines)
        self._check_snap_to_grid.setChecked(settings.snap_to_grid)
        self._check_snap_to_axis.setChecked(settings.snap_to_axis)
        self._check_snap_to_45deg.setChecked(settings.snap_to_45deg)
        self._check_snap_to_3060deg.setChecked(settings.snap_to_3060deg)
        self._check_snap_to_points.setChecked(settings.snap_to_points)
        self._check_show_inferences.setChecked(settings.show_inferences)
        edge_drag_mode_index = self._combo_edge_drag_mode.findData(settings.edge_drag_mode)
        self._combo_edge_drag_mode.setCurrentIndex(max(0, edge_drag_mode_index))
        self._check_show_edge_length_labels.setChecked(settings.show_edge_length_labels)
        self._check_show_vertex_angle_labels.setChecked(settings.show_vertex_angle_labels)
        self._check_label_always_visible.setChecked(settings.label_always_visible)

    def get_values(self) -> dict:
        """Return current dialog values as a dict matching AppSettings fields."""
        return {
            "partial_cutout_top_extra_cm": self._spin_top_extra.value(),
            "grid_size_cm": self._spin_grid_size.value(),
            "grid_major_cm": self._spin_grid_major.value(),
            "grid_minor_cm": self._spin_grid_minor.value(),
            "show_crosshair": self._check_crosshair.isChecked(),
            "live_angle_mode": self._combo_live_angle_mode.currentData(),
            "show_guide_lines": self._check_show_guide_lines.isChecked(),
            "snap_to_grid": self._check_snap_to_grid.isChecked(),
            "snap_to_axis": self._check_snap_to_axis.isChecked(),
            "snap_to_45deg": self._check_snap_to_45deg.isChecked(),
            "snap_to_3060deg": self._check_snap_to_3060deg.isChecked(),
            "snap_to_points": self._check_snap_to_points.isChecked(),
            "show_inferences": self._check_show_inferences.isChecked(),
            "edge_drag_mode": self._combo_edge_drag_mode.currentData(),
            "show_edge_length_labels": self._check_show_edge_length_labels.isChecked(),
            "show_vertex_angle_labels": self._check_show_vertex_angle_labels.isChecked(),
            "label_always_visible": self._check_label_always_visible.isChecked(),
        }

    def build_settings(self) -> AppSettings:
        """Build and return a new AppSettings from current dialog values."""
        return AppSettings.from_dict(self.get_values())
