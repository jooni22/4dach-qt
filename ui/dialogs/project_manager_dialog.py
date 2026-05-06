"""Project manager dialog for opening and reserving project files."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from core.project_state import ProjectState


class Mode(Enum):
    STARTUP = "startup"
    OPEN = "open"
    SAVE_AS = "save_as"
    NEW = "new"


@dataclass(frozen=True, slots=True)
class ProjectMeta:
    path: Path
    name: str
    address: str
    contact_name: str
    phone: str
    notes: str
    modified_at: datetime
    roof_plane_count: int
    net_area_m2: float


def _parse_modified_at(raw: object, fallback: float) -> datetime:
    if isinstance(raw, str):
        try:
            parsed = datetime.fromisoformat(raw)
            if parsed.tzinfo is None:
                return parsed.astimezone()
            return parsed
        except ValueError:
            pass
    return datetime.fromtimestamp(fallback).astimezone()


def scan_projects_dir(projects_dir: Path | str) -> list[ProjectMeta]:
    root = Path(projects_dir)
    if not root.is_dir():
        return []

    projects: list[ProjectMeta] = []
    for path in root.glob("*.4dach"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            stat = path.stat()
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        meta = payload.get("project_meta")
        meta = meta if isinstance(meta, dict) else {}
        try:
            project_state = ProjectState.from_config(payload)
        except (KeyError, TypeError, ValueError):
            project_state = ProjectState()
        net_area_cm2 = sum(plane.net_area_cm2 for plane in project_state.roof_planes)
        projects.append(
            ProjectMeta(
                path=path,
                name=str(meta.get("name") or path.stem),
                address=str(meta.get("address") or ""),
                contact_name=str(meta.get("contact_name") or ""),
                phone=str(meta.get("phone") or ""),
                notes=str(meta.get("notes") or ""),
                modified_at=_parse_modified_at(meta.get("modified_at"), stat.st_mtime),
                roof_plane_count=len(project_state.roof_planes),
                net_area_m2=net_area_cm2 / 10000.0,
            )
        )
    return sorted(projects, key=lambda project: project.modified_at, reverse=True)


class ProjectManagerDialog(QDialog):
    def __init__(
        self,
        *,
        mode: Mode,
        projects_dir: Path | str,
        default_name: str = "Nowy projekt",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.mode = mode
        self._projects_dir = Path(projects_dir)
        self._selected_path: Path | None = None
        self._startup_action: str | None = None
        self.setWindowTitle(self._title_for_mode(mode))
        self.setMinimumWidth(560)
        self._build_ui(default_name)
        self._reload_projects()

    def _project_path_for_name(self, name: str) -> Path:
        return self._projects_dir / f"{name}.4dach"

    def _resolve_unique_project_name(self, name: str) -> str:
        candidate = name.strip()
        if not candidate:
            return candidate
        if not self._project_path_for_name(candidate).exists():
            return candidate

        index = 2
        while True:
            next_candidate = f"{candidate} {index}"
            if not self._project_path_for_name(next_candidate).exists():
                return next_candidate
            index += 1

    def _title_for_mode(self, mode: Mode) -> str:
        return {
            Mode.STARTUP: "Projekty 4Dach",
            Mode.OPEN: "Otwórz projekt",
            Mode.SAVE_AS: "Zapisz projekt jako",
            Mode.NEW: "Nowy projekt",
        }[mode]

    def _build_ui(self, default_name: str) -> None:
        root = QVBoxLayout(self)

        dir_row = QHBoxLayout()
        self._dir_label = QLabel(str(self._projects_dir))
        self._change_dir_button = QPushButton("Zmień...")
        self._change_dir_button.clicked.connect(self._change_projects_dir)
        dir_row.addWidget(QLabel("Katalog projektów:"))
        dir_row.addWidget(self._dir_label, 1)
        dir_row.addWidget(self._change_dir_button)
        root.addLayout(dir_row)

        self._project_list = QListWidget(self)
        self._project_list.itemDoubleClicked.connect(lambda _item: self.accept())
        root.addWidget(self._project_list)

        self._name_edit = QLineEdit(default_name, self)
        if self.mode in {Mode.NEW, Mode.SAVE_AS}:
            form = QFormLayout()
            self._address_edit = QLineEdit(self)
            self._contact_name_edit = QLineEdit(self)
            self._phone_edit = QLineEdit(self)
            self._notes_edit = QTextEdit(self)
            self._notes_edit.setFixedHeight(80)
            form.addRow("Nazwa projektu:", self._name_edit)
            form.addRow("Adres:", self._address_edit)
            form.addRow("Imię nazwisko:", self._contact_name_edit)
            form.addRow("Telefon:", self._phone_edit)
            form.addRow("Notatki:", self._notes_edit)
            root.addLayout(form)
        else:
            self._name_edit.hide()
            self._address_edit = QLineEdit(self)
            self._contact_name_edit = QLineEdit(self)
            self._phone_edit = QLineEdit(self)
            self._notes_edit = QTextEdit(self)
            self._address_edit.hide()
            self._contact_name_edit.hide()
            self._phone_edit.hide()
            self._notes_edit.hide()

        self._button_box = QDialogButtonBox(self)
        if self.mode == Mode.STARTUP:
            self._open_button = self._button_box.addButton(
                "Otwórz",
                QDialogButtonBox.ButtonRole.AcceptRole,
            )
            self._new_button = self._button_box.addButton(
                "Nowy",
                QDialogButtonBox.ButtonRole.ActionRole,
            )
            self._new_button.clicked.connect(self._accept_new_from_startup)
        else:
            ok_text = "Otwórz" if self.mode == Mode.OPEN else "Zapisz"
            self._button_box.addButton(ok_text, QDialogButtonBox.ButtonRole.AcceptRole)
        self._button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        root.addWidget(self._button_box)

    def _reload_projects(self) -> None:
        self._project_list.clear()
        for project in scan_projects_dir(self._projects_dir):
            item = QListWidgetItem(self._project_item_text(project))
            item.setData(Qt.ItemDataRole.UserRole, project.path)
            self._project_list.addItem(item)
        if self._project_list.count():
            self._project_list.setCurrentRow(0)

    def _project_item_text(self, project: ProjectMeta) -> str:
        lines = [project.name]
        details = [value for value in (project.address, project.contact_name, project.phone) if value]
        if details:
            lines.append(" | ".join(details))
        if project.notes:
            lines.append(project.notes)
        lines.append(
            f"Połacie: {project.roof_plane_count} | "
            f"Powierzchnia netto: {project.net_area_m2:.2f} m²"
        )
        return "\n".join(lines)

    def _change_projects_dir(self) -> None:
        target = QFileDialog.getExistingDirectory(
            self,
            "Wybierz katalog projektów",
            str(self._projects_dir),
        )
        if not target:
            return
        self._projects_dir = Path(target)
        self._dir_label.setText(str(self._projects_dir))
        self._reload_projects()

    def _accept_new_from_startup(self) -> None:
        self._startup_action = "new"
        super().accept()

    def projects_dir(self) -> Path:
        return self._projects_dir

    def startup_action(self) -> str | None:
        return self._startup_action

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
        if self.mode in {Mode.NEW, Mode.SAVE_AS}:
            project_name = self.project_name()
            if not project_name:
                QMessageBox.warning(self, "Brak nazwy projektu", "Nazwa projektu jest wymagana.")
                return
            project_name = self._resolve_unique_project_name(project_name)
            self._name_edit.setText(project_name)
            self._selected_path = self._project_path_for_name(project_name)
            super().accept()
            return

        item = self._project_list.currentItem()
        if item is None:
            return
        self._selected_path = Path(item.data(Qt.ItemDataRole.UserRole))
        self._startup_action = "open"
        super().accept()
