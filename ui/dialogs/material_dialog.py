# This Python file uses the following encoding: utf-8
"""material_dialog.py — BlachyDialog and DaneBlachyDialog for sheet material catalogue."""
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
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
)


class BlachyDialog(QDialog):
    def __init__(self, config_data: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Blachy")
        self.config_data = config_data
        self.blachy_data: list[dict] = list(config_data.get("blachy", []))
        self.selected_blacha_index = 0
        self._setup_ui()
        self._load_blachy_list()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        main_layout = QVBoxLayout()

        self.blachy_list = QListWidget()
        main_layout.addWidget(self.blachy_list)

        self.params_group = QGroupBox("Parametry wybranego elementu")
        params_layout = QFormLayout()

        self.szerokosc_efektywna_label = QLabel()
        params_layout.addRow("Szerokość efektywna arkusza:", self.szerokosc_efektywna_label)
        self.max_dlugosc_label = QLabel()
        params_layout.addRow("Maks. długość arkusza:", self.max_dlugosc_label)
        self.zapas_dolny_label = QLabel()
        params_layout.addRow("Zapas dolny:", self.zapas_dolny_label)
        self.zapas_gorny_label = QLabel()
        params_layout.addRow("Zapas górny:", self.zapas_gorny_label)
        self.min_dlugosc_label = QLabel()
        params_layout.addRow("Min. długość arkusza:", self.min_dlugosc_label)
        self.odleglosc_lat_label = QLabel()
        params_layout.addRow("Odległość między łatami:", self.odleglosc_lat_label)
        self.odleglosc_kontrlat_label = QLabel()
        params_layout.addRow("Odległość między kontrłatami:", self.odleglosc_kontrlat_label)
        self.moduly_list = QListWidget()
        self.moduly_list.setMaximumHeight(60)
        params_layout.addRow("Moduły:", self.moduly_list)
        self.cena_label = QLabel()
        params_layout.addRow("Cena za m2:", self.cena_label)
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

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _connect_signals(self) -> None:
        self.blachy_list.currentRowChanged.connect(self._on_blacha_selected)
        self.dodaj_btn.clicked.connect(self._on_dodaj)
        self.edycja_btn.clicked.connect(self._on_edycja)
        self.usun_btn.clicked.connect(self._on_usun)

    def _load_blachy_list(self) -> None:
        self.blachy_list.clear()
        for blacha in self.blachy_data:
            self.blachy_list.addItem(blacha.get("id", ""))
        if self.blachy_list.count() > 0:
            self.blachy_list.setCurrentRow(0)

    def _on_blacha_selected(self, index: int) -> None:
        if 0 <= index < len(self.blachy_data):
            blacha = self.blachy_data[index]
            self.szerokosc_efektywna_label.setText(f"{blacha.get('szerokosc_efektywna', 0)} cm")
            self.max_dlugosc_label.setText("900 cm")
            self.zapas_dolny_label.setText(f"{blacha.get('zapas_dolny', 0)} cm")
            self.zapas_gorny_label.setText(f"{blacha.get('zapas_gorny', 0)} cm")
            self.min_dlugosc_label.setText(f"{blacha.get('min_dlugosc_arkusza', 0)} cm")
            self.odleglosc_lat_label.setText(f"{blacha.get('odleglosc_miedzy_latami', 0)} cm")
            self.odleglosc_kontrlat_label.setText(f"{blacha.get('odleglosc_miedzy_kontrlatami', 0)} cm")
            self.moduly_list.clear()
            for modul in blacha.get("moduly", []):
                self.moduly_list.addItem(str(modul))
            cena_zl = blacha.get("cena_zl", 0)
            cena_gr = blacha.get("cena_gr", 0)
            self.cena_label.setText(f"{cena_zl},{cena_gr:02d} zł")

    def _on_dodaj(self) -> None:
        dialog = DaneBlachyDialog(self.config_data, None, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.blachy_data.append(dialog.get_values())
            self._load_blachy_list()

    def _on_edycja(self) -> None:
        index = self.blachy_list.currentRow()
        if index >= 0:
            dialog = DaneBlachyDialog(self.config_data, self.blachy_data[index], self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.blachy_data[index] = dialog.get_values()
                self._load_blachy_list()

    def _on_usun(self) -> None:
        index = self.blachy_list.currentRow()
        if index >= 0:
            self.blachy_list.takeItem(index)
            del self.blachy_data[index]

    def get_values(self) -> list[dict]:
        return self.blachy_data


class DaneBlachyDialog(QDialog):
    def __init__(self, config_data: dict, blacha_data: dict | None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Dane blachy")
        self.config_data = config_data
        self.blacha_data = blacha_data
        self._setup_ui()
        self._load_values()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        type_group = QGroupBox("Typ blachy")
        type_layout = QVBoxLayout()
        self.radio_dachowkowa = QRadioButton("dachówkowa")
        self.radio_trapezowa = QRadioButton("trapezowa")
        type_layout.addWidget(self.radio_dachowkowa)
        type_layout.addWidget(self.radio_trapezowa)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        form_layout = QFormLayout()

        self.nazwa_edit = QLineEdit()
        form_layout.addRow("Nazwa:", self.nazwa_edit)

        self.szerokosc_efektywna_spin = QSpinBox()
        self.szerokosc_efektywna_spin.setRange(1, 999)
        self.szerokosc_efektywna_spin.setSuffix(" cm")
        form_layout.addRow("Szerokość efektywna arkusza:", self.szerokosc_efektywna_spin)

        self.dlugosc_modulu_spin = QSpinBox()
        self.dlugosc_modulu_spin.setRange(1, 999)
        self.dlugosc_modulu_spin.setSuffix(" cm")
        form_layout.addRow("Długość modułu:", self.dlugosc_modulu_spin)

        self.zapas_dolny_spin = QSpinBox()
        self.zapas_dolny_spin.setRange(0, 999)
        self.zapas_dolny_spin.setSuffix(" cm")
        form_layout.addRow("Zapas dolny:", self.zapas_dolny_spin)

        self.zapas_gorny_spin = QSpinBox()
        self.zapas_gorny_spin.setRange(0, 999)
        self.zapas_gorny_spin.setSuffix(" cm")
        form_layout.addRow("Zapas górny:", self.zapas_gorny_spin)

        self.min_dlugosc_spin = QSpinBox()
        self.min_dlugosc_spin.setRange(0, 999)
        self.min_dlugosc_spin.setSuffix(" cm")
        form_layout.addRow("Minimalna długość arkusza:", self.min_dlugosc_spin)

        self.odleglosc_lat_spin = QSpinBox()
        self.odleglosc_lat_spin.setRange(0, 999)
        self.odleglosc_lat_spin.setSuffix(" cm")
        form_layout.addRow("Odległość między łatami:", self.odleglosc_lat_spin)

        self.odleglosc_kontrlat_spin = QSpinBox()
        self.odleglosc_kontrlat_spin.setRange(0, 999)
        self.odleglosc_kontrlat_spin.setSuffix(" cm")
        form_layout.addRow("Odległość między kontrłatami:", self.odleglosc_kontrlat_spin)

        layout.addLayout(form_layout)

        moduly_group = QGroupBox("Moduły")
        moduly_layout = QVBoxLayout()
        moduly_top_layout = QVBoxLayout()
        self.moduly_spin = QSpinBox()
        self.moduly_spin.setRange(1, 999)
        moduly_top_layout.addWidget(QLabel("Długość modułu:"))
        moduly_top_layout.addWidget(self.moduly_spin)

        moduly_btn_layout = QHBoxLayout()
        self.moduly_plus_btn = QPushButton("+")
        self.moduly_minus_btn = QPushButton("-")
        moduly_btn_layout.addWidget(self.moduly_plus_btn)
        moduly_btn_layout.addWidget(self.moduly_minus_btn)
        moduly_top_layout.addLayout(moduly_btn_layout)
        moduly_layout.addLayout(moduly_top_layout)

        self.moduly_list = QListWidget()
        self.moduly_list.setMaximumHeight(80)
        moduly_layout.addWidget(self.moduly_list)
        moduly_group.setLayout(moduly_layout)
        layout.addWidget(moduly_group)

        price_group = QGroupBox("Cena")
        price_layout = QVBoxLayout()
        self.radio_m2 = QRadioButton("m2")
        self.radio_mb = QRadioButton("mb")
        price_layout.addWidget(self.radio_m2)
        price_layout.addWidget(self.radio_mb)

        price_value_layout = QHBoxLayout()
        self.cena_zl_spin = QSpinBox()
        self.cena_zl_spin.setRange(0, 99999)
        self.cena_zl_spin.setSuffix(" zł")
        self.cena_gr_spin = QSpinBox()
        self.cena_gr_spin.setRange(0, 99)
        self.cena_gr_spin.setSuffix(" gr")
        price_value_layout.addWidget(self.cena_zl_spin)
        price_value_layout.addWidget(self.cena_gr_spin)
        price_layout.addLayout(price_value_layout)
        price_group.setLayout(price_layout)
        layout.addWidget(price_group)

        self.moduly_plus_btn.clicked.connect(self._on_moduly_plus)
        self.moduly_minus_btn.clicked.connect(self._on_moduly_minus)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    def _on_moduly_plus(self) -> None:
        self.moduly_list.addItem(str(self.moduly_spin.value()))
        self.moduly_list.scrollToBottom()

    def _on_moduly_minus(self) -> None:
        current_row = self.moduly_list.currentRow()
        if current_row >= 0:
            self.moduly_list.takeItem(current_row)

    def _load_values(self) -> None:
        if self.blacha_data:
            typ = self.blacha_data.get("type", "dachówkowa")
            if typ == "dachówkowa":
                self.radio_dachowkowa.setChecked(True)
            else:
                self.radio_trapezowa.setChecked(True)
            self.nazwa_edit.setText(self.blacha_data.get("nazwa", ""))
            self.szerokosc_efektywna_spin.setValue(self.blacha_data.get("szerokosc_efektywna", 51))
            self.dlugosc_modulu_spin.setValue(self.blacha_data.get("dlugosc_modulu", 25))
            self.zapas_dolny_spin.setValue(self.blacha_data.get("zapas_dolny", 10))
            self.zapas_gorny_spin.setValue(self.blacha_data.get("zapas_gorny", 80))
            self.min_dlugosc_spin.setValue(self.blacha_data.get("min_dlugosc_arkusza", 20))
            self.odleglosc_lat_spin.setValue(self.blacha_data.get("odleglosc_miedzy_latami", 10))
            self.odleglosc_kontrlat_spin.setValue(self.blacha_data.get("odleglosc_miedzy_kontrlatami", 0))
            for modul in self.blacha_data.get("moduly", []):
                self.moduly_list.addItem(str(modul))
            cena_za = self.blacha_data.get("cena_za", "m2")
            (self.radio_m2 if cena_za == "m2" else self.radio_mb).setChecked(True)
            self.cena_zl_spin.setValue(self.blacha_data.get("cena_zl", 10))
            self.cena_gr_spin.setValue(self.blacha_data.get("cena_gr", 0))
        else:
            self.radio_dachowkowa.setChecked(True)
            self.radio_m2.setChecked(True)

    def get_values(self) -> dict:
        moduly = [int(self.moduly_list.item(i).text()) for i in range(self.moduly_list.count())]
        return {
            "id": self.nazwa_edit.text() or "Nowa",
            "type": "dachówkowa" if self.radio_dachowkowa.isChecked() else "trapezowa",
            "nazwa": self.nazwa_edit.text(),
            "szerokosc_efektywna": self.szerokosc_efektywna_spin.value(),
            "dlugosc_modulu": self.dlugosc_modulu_spin.value(),
            "zapas_dolny": self.zapas_dolny_spin.value(),
            "zapas_gorny": self.zapas_gorny_spin.value(),
            "min_dlugosc_arkusza": self.min_dlugosc_spin.value(),
            "odleglosc_miedzy_latami": self.odleglosc_lat_spin.value(),
            "odleglosc_miedzy_kontrlatami": self.odleglosc_kontrlat_spin.value(),
            "moduly": moduly,
            "cena_za": "m2" if self.radio_m2.isChecked() else "mb",
            "cena_zl": self.cena_zl_spin.value(),
            "cena_gr": self.cena_gr_spin.value(),
        }
