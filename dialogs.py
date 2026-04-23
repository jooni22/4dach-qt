# -*- coding: utf-8 -*-
import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QRadioButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ProstokatDialog(QDialog):
    def __init__(self, config_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Prostokąt")
        self.config_data = config_data
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
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

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    def _load_values(self):
        values = self.config_data.get("ksztalty", {}).get("prostokat", {})
        self.szerokosc_spin.setValue(values.get("szerokosc", 300))
        self.wysokosc_spin.setValue(values.get("wysokosc", 300))

    def get_values(self):
        return {
            "szerokosc": self.szerokosc_spin.value(),
            "wysokosc": self.wysokosc_spin.value(),
        }


class TrojkatDialog(QDialog):
    def __init__(self, config_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Trójkąt")
        self.config_data = config_data
        self._setup_ui()
        self._load_values()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Radio buttons for triangle type
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

        # Form layout for dimensions
        form_layout = QFormLayout()

        self.podstawa_spin = QSpinBox()
        self.podstawa_spin.setRange(1, 9999)
        self.podstawa_spin.setSuffix(" cm")
        form_layout.addRow("Podstawa:", self.podstawa_spin)

        self.wysokosc_spin = QSpinBox()
        self.wysokosc_spin.setRange(1, 9999)
        self.wysokosc_spin.setSuffix(" cm")
        form_layout.addRow("Wysokość:", self.wysokosc_spin)

        # Ramię checkbox with spinbox
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

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    def _connect_signals(self):
        self.radio_rownoramienny.toggled.connect(self._on_type_changed)
        self.ramie_checkbox.toggled.connect(self._on_ramie_toggled)

    def _on_type_changed(self):
        is_rownoramienny = self.radio_rownoramienny.isChecked()
        self.ramie_checkbox.setEnabled(not is_rownoramienny)
        self.ramie_spin.setEnabled(not is_rownoramienny and self.ramie_checkbox.isChecked())

    def _on_ramie_toggled(self, checked):
        self.ramie_spin.setEnabled(checked and not self.radio_rownoramienny.isChecked())

    def _load_values(self):
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

    def get_values(self):
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
    def __init__(self, config_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Trapez")
        self.config_data = config_data
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Radio buttons for trapez type
        type_group = QGroupBox("Typ trapezu")
        type_layout = QVBoxLayout()

        self.radio_rownoramienny = QRadioButton("równoramienny")
        self.radio_prostokatny = QRadioButton("prostokątny")

        type_layout.addWidget(self.radio_rownoramienny)
        type_layout.addWidget(self.radio_prostokatny)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        # Form layout for dimensions
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

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    def _load_values(self):
        values = self.config_data.get("ksztalty", {}).get("trapez", {})
        
        typ = values.get("typ", "równoramienny")
        if typ == "równoramienny":
            self.radio_rownoramienny.setChecked(True)
        else:
            self.radio_prostokatny.setChecked(True)

        self.podstawa_dolna_spin.setValue(values.get("podstawa_dolna", 500))
        self.podstawa_gorna_spin.setValue(values.get("podstawa_gorna", 300))
        self.wysokosc_spin.setValue(values.get("wysokosc", 300))

    def get_values(self):
        typ = "równoramienny" if self.radio_rownoramienny.isChecked() else "prostokątny"

        return {
            "typ": typ,
            "podstawa_dolna": self.podstawa_dolna_spin.value(),
            "podstawa_gorna": self.podstawa_gorna_spin.value(),
            "wysokosc": self.wysokosc_spin.value(),
        }


class DaneFirmyDialog(QDialog):
    def __init__(self, config_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dane firmy")
        self.config_data = config_data
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        self.nazwa_edit = QLineEdit()
        form_layout.addRow("Nazwa firmy:", self.nazwa_edit)

        self.nip_edit = QLineEdit()
        form_layout.addRow("NIP:", self.nip_edit)

        self.adres_edit = QTextEdit()
        self.adres_edit.setMaximumHeight(80)
        form_layout.addRow("Adres:", self.adres_edit)

        self.www_edit = QLineEdit()
        form_layout.addRow("Adres strony WWW:", self.www_edit)

        self.logo_edit = QLineEdit()
        form_layout.addRow("Logo firmy:", self.logo_edit)

        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    def _load_values(self):
        data = self.config_data.get("company_data", {})
        self.nazwa_edit.setText(data.get("name", ""))
        self.nip_edit.setText(data.get("nip", ""))
        self.adres_edit.setPlainText(data.get("address", ""))
        self.www_edit.setText(data.get("website", ""))
        self.logo_edit.setText(data.get("logo", ""))

    def get_values(self):
        return {
            "name": self.nazwa_edit.text(),
            "nip": self.nip_edit.text(),
            "address": self.adres_edit.toPlainText(),
            "website": self.www_edit.text(),
            "logo": self.logo_edit.text(),
        }


class BlachyDialog(QDialog):
    def __init__(self, config_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Blachy")
        self.config_data = config_data
        self.blachy_data = config_data.get("blachy", [])
        self.selected_blacha_index = 0
        self._setup_ui()
        self._load_blachy_list()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Main horizontal layout
        main_layout = QVBoxLayout()

        # List widget for blachy
        self.blachy_list = QListWidget()
        main_layout.addWidget(self.blachy_list)

        # Parameters display
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
        params_layout.addRow("Odległość międzyłatami:", self.odleglosc_lat_label)

        self.odleglosc_kontrlat_label = QLabel()
        params_layout.addRow("Odległość między kontrłatami:", self.odleglosc_kontrlat_label)

        self.moduly_list = QListWidget()
        self.moduly_list.setMaximumHeight(60)
        params_layout.addRow("Moduły:", self.moduly_list)

        self.cena_label = QLabel()
        params_layout.addRow("Cena za m2:", self.cena_label)

        self.params_group.setLayout(params_layout)
        main_layout.addWidget(self.params_group)

        # Action buttons
        action_layout = QVBoxLayout()
        
        from PySide6.QtWidgets import QPushButton, QHBoxLayout
        
        button_layout = QHBoxLayout()
        self.dodaj_btn = QPushButton("+ Dodaj")
        self.edycja_btn = QPushButton("Edycja")
        self.usun_btn = QPushButton("- Usuń")
        
        button_layout.addWidget(self.dodaj_btn)
        button_layout.addWidget(self.edycja_btn)
        button_layout.addWidget(self.usun_btn)
        
        action_layout.addLayout(button_layout)
        main_layout.addLayout(action_layout)

        layout.addLayout(main_layout)

        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _connect_signals(self):
        self.blachy_list.currentRowChanged.connect(self._on_blacha_selected)
        self.dodaj_btn.clicked.connect(self._on_dodaj)
        self.edycja_btn.clicked.connect(self._on_edycja)
        self.usun_btn.clicked.connect(self._on_usun)

    def _load_blachy_list(self):
        self.blachy_list.clear()
        for blacha in self.blachy_data:
            self.blachy_list.addItem(blacha.get("id", ""))
        
        if self.blachy_list.count() > 0:
            self.blachy_list.setCurrentRow(0)

    def _on_blacha_selected(self, index):
        if 0 <= index < len(self.blachy_data):
            blacha = self.blachy_data[index]
            self.szerokosc_efektywna_label.setText(f"{blacha.get('szerokosc_efektywna', 0)} cm")
            self.max_dlugosc_label.setText(f"{900} cm")  # Fixed from spec
            self.zapas_dolny_label.setText(f"{blacha.get('zapas_dolny', 0)} cm")
            self.zapas_gorny_label.setText(f"{blacha.get('zapas_gorny', 0)} cm")
            self.min_dlugosc_label.setText(f"{blacha.get('min_dlugosc_arkusza', 0)} cm")
            self.odleglosc_lat_label.setText(f"{blacha.get('odleglosc_miedzy_latami', 0)} cm")
            self.odleglosc_kontrlat_label.setText(f"{blacha.get('odleglosc_miedzy_kontrlatami', 0)} cm")
            
            self.moduly_list.clear()
            for modul in blacha.get("moduly", []):
                self.moduly_list.addItem(str(modul))
            
            cena_zl = blacha.get('cena_zl', 0)
            cena_gr = blacha.get('cena_gr', 0)
            self.cena_label.setText(f"{cena_zl},{cena_gr:02d} zł")

    def _on_dodaj(self):
        dialog = DaneBlachyDialog(self.config_data, None, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_blacha = dialog.get_values()
            self.blachy_data.append(new_blacha)
            self._load_blachy_list()

    def _on_edycja(self):
        index = self.blachy_list.currentRow()
        if index >= 0:
            blacha = self.blachy_data[index]
            dialog = DaneBlachyDialog(self.config_data, blacha, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                updated_blacha = dialog.get_values()
                self.blachy_data[index] = updated_blacha
                self._load_blachy_list()

    def _on_usun(self):
        index = self.blachy_list.currentRow()
        if index >= 0:
            self.blachy_list.takeItem(index)
            del self.blachy_data[index]

    def get_values(self):
        return self.blachy_data


class DaneBlachyDialog(QDialog):
    def __init__(self, config_data, blacha_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dane blachy")
        self.config_data = config_data
        self.blacha_data = blacha_data
        self.moduly = []
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Radio buttons for blacha type
        type_group = QGroupBox("Typ blachy")
        type_layout = QVBoxLayout()

        self.radio_dachowkowa = QRadioButton("dachówkowa")
        self.radio_trapezowa = QRadioButton("trapezowa")

        type_layout.addWidget(self.radio_dachowkowa)
        type_layout.addWidget(self.radio_trapezowa)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        # Form layout for parameters
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
        form_layout.addRow("Odległość międzyłatami:", self.odleglosc_lat_spin)

        self.odleglosc_kontrlat_spin = QSpinBox()
        self.odleglosc_kontrlat_spin.setRange(0, 999)
        self.odleglosc_kontrlat_spin.setSuffix(" cm")
        form_layout.addRow("Odległość między kontrłatami:", self.odleglosc_kontrlat_spin)

        layout.addLayout(form_layout)

        # Moduly section
        moduly_group = QGroupBox("Moduły")
        moduly_layout = QVBoxLayout()

        moduly_top_layout = QVBoxLayout()
        
        self.moduly_spin = QSpinBox()
        self.moduly_spin.setRange(1, 999)
        moduly_top_layout.addWidget(QLabel("Długość modułu:"))
        moduly_top_layout.addWidget(self.moduly_spin)

        moduly_buttons_layout = QVBoxLayout()
        from PySide6.QtWidgets import QPushButton, QHBoxLayout
        
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

        # Price section
        price_group = QGroupBox("Cena")
        price_layout = QVBoxLayout()

        price_type_layout = QVBoxLayout()
        self.radio_m2 = QRadioButton("m2")
        self.radio_mb = QRadioButton("mb")
        price_type_layout.addWidget(self.radio_m2)
        price_type_layout.addWidget(self.radio_mb)
        price_layout.addLayout(price_type_layout)

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

        # Connect signals
        self.moduly_plus_btn.clicked.connect(self._on_moduly_plus)
        self.moduly_minus_btn.clicked.connect(self._on_moduly_minus)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    def _on_moduly_plus(self):
        value = self.moduly_spin.value()
        self.moduly_list.addItem(str(value))
        self.moduly_list.scrollToBottom()

    def _on_moduly_minus(self):
        current_row = self.moduly_list.currentRow()
        if current_row >= 0:
            self.moduly_list.takeItem(current_row)

    def _load_values(self):
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
            if cena_za == "m2":
                self.radio_m2.setChecked(True)
            else:
                self.radio_mb.setChecked(True)

            self.cena_zl_spin.setValue(self.blacha_data.get("cena_zl", 10))
            self.cena_gr_spin.setValue(self.blacha_data.get("cena_gr", 0))
        else:
            self.radio_dachowkowa.setChecked(True)
            self.radio_m2.setChecked(True)

    def get_values(self):
        moduly = []
        for i in range(self.moduly_list.count()):
            moduly.append(int(self.moduly_list.item(i).text()))

        typ = "dachówkowa" if self.radio_dachowkowa.isChecked() else "trapezowa"
        cena_za = "m2" if self.radio_m2.isChecked() else "mb"

        return {
            "id": self.nazwa_edit.text() or "Nowa",
            "type": typ,
            "nazwa": self.nazwa_edit.text(),
            "szerokosc_efektywna": self.szerokosc_efektywna_spin.value(),
            "dlugosc_modulu": self.dlugosc_modulu_spin.value(),
            "zapas_dolny": self.zapas_dolny_spin.value(),
            "zapas_gorny": self.zapas_gorny_spin.value(),
            "min_dlugosc_arkusza": self.min_dlugosc_spin.value(),
            "odleglosc_miedzy_latami": self.odleglosc_lat_spin.value(),
            "odleglosc_miedzy_kontrlatami": self.odleglosc_kontrlat_spin.value(),
            "moduly": moduly,
            "cena_za": cena_za,
            "cena_zl": self.cena_zl_spin.value(),
            "cena_gr": self.cena_gr_spin.value(),
        }


def show_ostrzezenie_dialog(parent=None):
    """Show warning dialog for clearing active roof surface"""
    from PySide6.QtWidgets import QMessageBox
    
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle("Ostrzeżenie")
    msg_box.setIcon(QMessageBox.Icon.Warning)
    msg_box.setText("Czy na pewno wyczyścić aktywną połać?")
    
    cancel_button = msg_box.addButton("X Anuluj", QMessageBox.ButtonRole.RejectRole)
    ok_button = msg_box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
    
    msg_box.exec()
    
    return msg_box.clickedButton() == ok_button


def load_config():
    """Load configuration from config.json"""
    config_path = Path(__file__).parent / "config.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_config(config_data):
    """Save configuration to config.json"""
    config_path = Path(__file__).parent / "config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)
