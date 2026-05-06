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

from project_files import (
    project_config_path,
    project_dir_from_config_path,
    resolve_unique_project_dir,
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
        self._current_project_dir = project_dir_from_config_path(project_path) if project_path is not None else None
        self._selected_path: Path | None = project_path
        self._initial_project_name = str((initial_meta or {}).get("name") or default_name).strip()
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
        project_dir = resolve_unique_project_dir(
            self._projects_dir,
            name,
            current_dir=self._current_project_dir,
        )
        return project_config_path(project_dir)

    def _resolve_selected_project_path(self, name: str) -> Path:
        candidate = name.strip()
        if self._project_path is not None and candidate == self._initial_project_name:
            return self._project_path
        return self._project_path_for_name(candidate)

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
        self._selected_path = self._resolve_selected_project_path(project_name)
        super().accept()
