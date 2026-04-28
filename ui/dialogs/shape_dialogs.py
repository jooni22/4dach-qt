"""shape_dialogs.py — dialogs for adding roof-plane outlines by shape."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
)


class ProstokatDialog(QDialog):
    def __init__(self, config_data: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Prostokąt")
        self.config_data = config_data
        self._setup_ui()
        self._load_values()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.szerokosc_spin = QSpinBox()
        self.szerokosc_spin.setRange(1, 9999)
        self.szerokosc_spin.setSuffix(" cm")
        form_layout.addRow("Szerokość:", self.szerokosc_spin)

        self.wysokosc_spin = QSpinBox()
        self.wysokosc_spin.setRange(1, 9999)
        self.wysokosc_spin.setSuffix(" cm")
        form_layout.addRow("Wysokość:", self.wysokosc_spin)

        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    def _load_values(self) -> None:
        values = self.config_data.get("ksztalty", {}).get("prostokat", {})
        self.szerokosc_spin.setValue(values.get("szerokosc", 300))
        self.wysokosc_spin.setValue(values.get("wysokosc", 300))

    def get_values(self) -> dict:
        return {
            "szerokosc": self.szerokosc_spin.value(),
            "wysokosc": self.wysokosc_spin.value(),
        }


class TrojkatDialog(QDialog):
    def __init__(self, config_data: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Trójkąt")
        self.config_data = config_data
        self._setup_ui()
        self._load_values()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        type_group = QGroupBox("Typ trójkąta")
        type_layout = QVBoxLayout()
        self.radio_rownoramienny = QRadioButton("równoramienny")
        self.radio_prostokatny = QRadioButton("prostokątny")
        self.radio_dowolny = QRadioButton("dowolny")
        type_layout.addWidget(self.radio_rownoramienny)
        type_layout.addWidget(self.radio_prostokatny)
        type_layout.addWidget(self.radio_dowolny)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        form_layout = QFormLayout()

        self.podstawa_spin = QSpinBox()
        self.podstawa_spin.setRange(1, 9999)
        self.podstawa_spin.setSuffix(" cm")
        form_layout.addRow("Podstawa:", self.podstawa_spin)

        self.wysokosc_spin = QSpinBox()
        self.wysokosc_spin.setRange(1, 9999)
        self.wysokosc_spin.setSuffix(" cm")
        form_layout.addRow("Wysokość:", self.wysokosc_spin)

        self.ramie_checkbox = QCheckBox("Ramię")
        self.ramie_spin = QSpinBox()
        self.ramie_spin.setRange(1, 9999)
        self.ramie_spin.setSuffix(" cm")
        self.ramie_spin.setEnabled(False)
        ramie_layout = QVBoxLayout()
        ramie_layout.addWidget(self.ramie_checkbox)
        ramie_layout.addWidget(self.ramie_spin)
        form_layout.addRow("", ramie_layout)

        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    def _connect_signals(self) -> None:
        self.radio_rownoramienny.toggled.connect(self._on_type_changed)
        self.ramie_checkbox.toggled.connect(self._on_ramie_toggled)

    def _on_type_changed(self) -> None:
        is_rownoramienny = self.radio_rownoramienny.isChecked()
        self.ramie_checkbox.setEnabled(not is_rownoramienny)
        self.ramie_spin.setEnabled(not is_rownoramienny and self.ramie_checkbox.isChecked())

    def _on_ramie_toggled(self, checked: bool) -> None:
        self.ramie_spin.setEnabled(checked and not self.radio_rownoramienny.isChecked())

    def _load_values(self) -> None:
        values = self.config_data.get("ksztalty", {}).get("trojkat", {})
        typ = values.get("typ", "równoramienny")
        if typ == "równoramienny":
            self.radio_rownoramienny.setChecked(True)
        elif typ == "prostokątny":
            self.radio_prostokatny.setChecked(True)
        else:
            self.radio_dowolny.setChecked(True)
        self.podstawa_spin.setValue(values.get("podstawa", 300))
        self.wysokosc_spin.setValue(values.get("wysokosc", 300))
        self.ramie_spin.setValue(values.get("ramie", 400))
        self.ramie_checkbox.setChecked(values.get("ramie_enabled", False))

    def get_values(self) -> dict:
        typ = "równoramienny"
        if self.radio_prostokatny.isChecked():
            typ = "prostokątny"
        elif self.radio_dowolny.isChecked():
            typ = "dowolny"
        return {
            "typ": typ,
            "podstawa": self.podstawa_spin.value(),
            "wysokosc": self.wysokosc_spin.value(),
            "ramie": self.ramie_spin.value(),
            "ramie_enabled": self.ramie_checkbox.isChecked(),
        }


class TrapezDialog(QDialog):
    def __init__(self, config_data: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Trapez")
        self.config_data = config_data
        self._setup_ui()
        self._load_values()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        type_group = QGroupBox("Typ trapezu")
        type_layout = QVBoxLayout()
        self.radio_rownoramienny = QRadioButton("równoramienny")
        self.radio_prostokatny = QRadioButton("prostokątny")
        type_layout.addWidget(self.radio_rownoramienny)
        type_layout.addWidget(self.radio_prostokatny)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        form_layout = QFormLayout()

        self.podstawa_dolna_spin = QSpinBox()
        self.podstawa_dolna_spin.setRange(1, 9999)
        self.podstawa_dolna_spin.setSuffix(" cm")
        form_layout.addRow("Podstawa dolna:", self.podstawa_dolna_spin)

        self.podstawa_gorna_spin = QSpinBox()
        self.podstawa_gorna_spin.setRange(1, 9999)
        self.podstawa_gorna_spin.setSuffix(" cm")
        form_layout.addRow("górna:", self.podstawa_gorna_spin)

        self.wysokosc_spin = QSpinBox()
        self.wysokosc_spin.setRange(1, 9999)
        self.wysokosc_spin.setSuffix(" cm")
        form_layout.addRow("Wysokość:", self.wysokosc_spin)

        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    def _load_values(self) -> None:
        values = self.config_data.get("ksztalty", {}).get("trapez", {})
        typ = values.get("typ", "równoramienny")
        if typ == "równoramienny":
            self.radio_rownoramienny.setChecked(True)
        else:
            self.radio_prostokatny.setChecked(True)
        self.podstawa_dolna_spin.setValue(values.get("podstawa_dolna", 500))
        self.podstawa_gorna_spin.setValue(values.get("podstawa_gorna", 300))
        self.wysokosc_spin.setValue(values.get("wysokosc", 300))

    def get_values(self) -> dict:
        return {
            "typ": "równoramienny" if self.radio_rownoramienny.isChecked() else "prostokątny",
            "podstawa_dolna": self.podstawa_dolna_spin.value(),
            "podstawa_gorna": self.podstawa_gorna_spin.value(),
            "wysokosc": self.wysokosc_spin.value(),
        }
