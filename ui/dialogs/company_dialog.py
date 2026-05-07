"""company_dialog.py — DaneFirmyDialog for editing company data."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from ui.dialogs.button_text import localize_button_box


class DaneFirmyDialog(QDialog):
    def __init__(self, config_data: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Dane firmy")
        self.config_data = config_data
        self._setup_ui()
        self._load_values()

    def _setup_ui(self) -> None:
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

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        localize_button_box(button_box)
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    def _load_values(self) -> None:
        data = self.config_data.get("company_data", {})
        self.nazwa_edit.setText(data.get("name", ""))
        self.nip_edit.setText(data.get("nip", ""))
        self.adres_edit.setPlainText(data.get("address", ""))
        self.www_edit.setText(data.get("website", ""))
        self.logo_edit.setText(data.get("logo", ""))

    def get_values(self) -> dict:
        return {
            "name": self.nazwa_edit.text(),
            "nip": self.nip_edit.text(),
            "address": self.adres_edit.toPlainText(),
            "website": self.www_edit.text(),
            "logo": self.logo_edit.text(),
        }
