"""material_dialog.py — dialogs for editing the project material registry."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from core.models import Material


class BlachyDialog(QDialog):
    def __init__(self, materials: list[Material], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Blachy")
        self._materials = [Material.from_dict(material.to_dict()) for material in materials]
        self._setup_ui()
        self._load_blachy_list()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        main_layout = QVBoxLayout()

        self.blachy_list = QListWidget()
        main_layout.addWidget(self.blachy_list)

        self.params_group = QGroupBox("Parametry wybranego materiału")
        params_layout = QFormLayout()

        self.id_label = QLabel()
        params_layout.addRow("Id:", self.id_label)
        self.nazwa_label = QLabel()
        params_layout.addRow("Nazwa:", self.nazwa_label)
        self.szerokosc_efektywna_label = QLabel()
        params_layout.addRow("Szerokość efektywna arkusza:", self.szerokosc_efektywna_label)
        self.min_dlugosc_label = QLabel()
        params_layout.addRow("Min. długość arkusza:", self.min_dlugosc_label)
        self.max_dlugosc_label = QLabel()
        params_layout.addRow("Maks. długość arkusza:", self.max_dlugosc_label)
        self.params_group.setLayout(params_layout)
        main_layout.addWidget(self.params_group)

        button_layout = QHBoxLayout()
        self.dodaj_btn = QPushButton("+ Dodaj")
        self.edycja_btn = QPushButton("Edycja")
        self.usun_btn = QPushButton("- Usuń")
        button_layout.addWidget(self.dodaj_btn)
        button_layout.addWidget(self.edycja_btn)
        button_layout.addWidget(self.usun_btn)
        main_layout.addLayout(button_layout)

        layout.addLayout(main_layout)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _connect_signals(self) -> None:
        self.blachy_list.currentRowChanged.connect(self._on_blacha_selected)
        self.dodaj_btn.clicked.connect(self._on_dodaj)
        self.edycja_btn.clicked.connect(self._on_edycja)
        self.usun_btn.clicked.connect(self._on_usun)

    def _load_blachy_list(self) -> None:
        current_row = self.blachy_list.currentRow()
        self.blachy_list.clear()
        for material in self._materials:
            self.blachy_list.addItem(f"{material.id} — {material.display_name}")
        if self.blachy_list.count() > 0:
            self.blachy_list.setCurrentRow(min(max(current_row, 0), self.blachy_list.count() - 1))
        else:
            self._clear_details()

    def _clear_details(self) -> None:
        for label in (
            self.id_label,
            self.nazwa_label,
            self.szerokosc_efektywna_label,
            self.min_dlugosc_label,
            self.max_dlugosc_label,
        ):
            label.setText("-")

    def _on_blacha_selected(self, index: int) -> None:
        if 0 <= index < len(self._materials):
            material = self._materials[index]
            self.id_label.setText(material.id)
            self.nazwa_label.setText(material.display_name)
            self.szerokosc_efektywna_label.setText(f"{material.effective_width_cm:g} cm")
            self.min_dlugosc_label.setText(f"{material.min_sheet_length_cm:g} cm")
            self.max_dlugosc_label.setText(f"{material.max_sheet_length_cm:g} cm")
        else:
            self._clear_details()

    def _save_material_from_dialog(self, dialog: DaneBlachyDialog, existing_index: int | None = None) -> None:
        material = dialog.get_values()
        duplicate_index = next(
            (index for index, candidate in enumerate(self._materials) if candidate.id == material.id and index != existing_index),
            None,
        )
        if duplicate_index is not None:
            QMessageBox.warning(self, "Duplikat", "Materiał o podanym identyfikatorze już istnieje")
            return
        if existing_index is None:
            self._materials.append(material)
        else:
            self._materials[existing_index] = material
        self._load_blachy_list()
        target_index = existing_index if existing_index is not None else len(self._materials) - 1
        self.blachy_list.setCurrentRow(target_index)

    def _on_dodaj(self) -> None:
        dialog = DaneBlachyDialog(None, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._save_material_from_dialog(dialog)

    def _on_edycja(self) -> None:
        index = self.blachy_list.currentRow()
        if index >= 0:
            dialog = DaneBlachyDialog(self._materials[index], self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._save_material_from_dialog(dialog, index)

    def _on_usun(self) -> None:
        index = self.blachy_list.currentRow()
        if index >= 0:
            del self._materials[index]
            self._load_blachy_list()

    def get_values(self) -> list[Material]:
        return [Material.from_dict(material.to_dict()) for material in self._materials]


class DaneBlachyDialog(QDialog):
    def __init__(self, material_data: Material | None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Dane blachy")
        self.material_data = material_data
        self._setup_ui()
        self._load_values()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        self.id_edit = QLineEdit()
        form_layout.addRow("Id:", self.id_edit)

        self.nazwa_edit = QLineEdit()
        form_layout.addRow("Nazwa:", self.nazwa_edit)

        self.szerokosc_efektywna_spin = QSpinBox()
        self.szerokosc_efektywna_spin.setRange(1, 9999)
        self.szerokosc_efektywna_spin.setSuffix(" cm")
        form_layout.addRow("Szerokość efektywna arkusza:", self.szerokosc_efektywna_spin)

        self.min_dlugosc_spin = QSpinBox()
        self.min_dlugosc_spin.setRange(0, 9999)
        self.min_dlugosc_spin.setSuffix(" cm")
        form_layout.addRow("Minimalna długość arkusza:", self.min_dlugosc_spin)

        self.max_dlugosc_spin = QSpinBox()
        self.max_dlugosc_spin.setRange(0, 9999)
        self.max_dlugosc_spin.setValue(900)
        self.max_dlugosc_spin.setSuffix(" cm")
        form_layout.addRow("Maksymalna długość arkusza:", self.max_dlugosc_spin)

        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self._accept_if_valid)
        layout.addWidget(button_box)

    def _load_values(self) -> None:
        material = self.material_data
        if material is None:
            return

        self.id_edit.setText(material.id)
        self.nazwa_edit.setText(material.display_name)
        self.szerokosc_efektywna_spin.setValue(round(material.effective_width_cm))
        self.min_dlugosc_spin.setValue(round(material.min_sheet_length_cm))
        self.max_dlugosc_spin.setValue(round(material.max_sheet_length_cm))

    def _accept_if_valid(self) -> None:
        if not self.id_edit.text().strip():
            QMessageBox.warning(self, "Brak id", "Id materiału nie może być puste")
            return
        if not self.nazwa_edit.text().strip():
            QMessageBox.warning(self, "Brak nazwy", "Nazwa materiału nie może być pusta")
            return
        if self.max_dlugosc_spin.value() < self.min_dlugosc_spin.value():
            QMessageBox.warning(
                self,
                "Nieprawidłowy zakres",
                "Maksymalna długość arkusza nie może być mniejsza od minimalnej",
            )
            return
        self.accept()

    def get_values(self) -> Material:
        return Material(
            id=self.id_edit.text().strip(),
            display_name=self.nazwa_edit.text().strip(),
            type="trapezowa",
            effective_width_cm=self.szerokosc_efektywna_spin.value(),
            min_sheet_length_cm=self.min_dlugosc_spin.value(),
            max_sheet_length_cm=self.max_dlugosc_spin.value(),
        )
