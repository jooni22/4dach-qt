"""Project details dialog used for create, save-as, and metadata editing."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
)


class ProjectDetailsDialog(QDialog):
    def __init__(
        self,
        *,
        projects_dir: Path | str,
        default_name: str = "Nowy projekt",
        initial_meta: dict | None = None,
        project_path: Path | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._projects_dir = Path(projects_dir)
        self._project_path = project_path
        self._selected_path: Path | None = project_path
        self.setWindowTitle("Dane projektu")
        self.setMinimumWidth(480)
        self._build_ui(default_name, initial_meta or {})

    def _build_ui(self, default_name: str, initial_meta: dict) -> None:
        root = QVBoxLayout(self)

        self._name_edit = QLineEdit(str(initial_meta.get("name") or default_name), self)
        self._address_edit = QLineEdit(str(initial_meta.get("address") or ""), self)
        self._contact_name_edit = QLineEdit(str(initial_meta.get("contact_name") or ""), self)
        self._phone_edit = QLineEdit(str(initial_meta.get("phone") or ""), self)
        self._notes_edit = QTextEdit(self)
        self._notes_edit.setPlainText(str(initial_meta.get("notes") or ""))
        self._notes_edit.setFixedHeight(100)

        form = QFormLayout()
        form.addRow("Nazwa projektu:", self._name_edit)
        form.addRow("Adres:", self._address_edit)
        form.addRow("Osoba kontaktowa:", self._contact_name_edit)
        form.addRow("Telefon:", self._phone_edit)
        form.addRow("Notatki:", self._notes_edit)
        root.addLayout(form)

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        root.addWidget(self._button_box)

    def _project_path_for_name(self, name: str) -> Path:
        return self._projects_dir / f"{name}.4dach"

    def _resolve_unique_project_name(self, name: str) -> str:
        candidate = name.strip()
        if not candidate:
            return candidate

        candidate_path = self._project_path_for_name(candidate)
        if self._project_path is not None and candidate_path == self._project_path:
            return candidate
        if not candidate_path.exists():
            return candidate

        index = 2
        while True:
            next_candidate = f"{candidate} {index}"
            next_path = self._project_path_for_name(next_candidate)
            if self._project_path is not None and next_path == self._project_path:
                return next_candidate
            if not next_path.exists():
                return next_candidate
            index += 1

    def projects_dir(self) -> Path:
        return self._projects_dir

    def project_name(self) -> str:
        return self._name_edit.text().strip()

    def project_meta(self) -> dict:
        return {
            "name": self.project_name(),
            "address": self._address_edit.text().strip(),
            "contact_name": self._contact_name_edit.text().strip(),
            "phone": self._phone_edit.text().strip(),
            "notes": self._notes_edit.toPlainText().strip(),
        }

    def selected_path(self) -> Path | None:
        return self._selected_path

    def accept(self) -> None:
        project_name = self.project_name()
        if not project_name:
            QMessageBox.warning(self, "Brak nazwy projektu", "Nazwa projektu jest wymagana.")
            return
        if self._project_path is not None:
            self._selected_path = self._project_path
            super().accept()
            return
        project_name = self._resolve_unique_project_name(project_name)
        self._name_edit.setText(project_name)
        self._selected_path = self._project_path_for_name(project_name)
        super().accept()
