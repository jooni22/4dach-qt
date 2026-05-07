"""Project manager dialog for opening and reserving project files."""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
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
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.project_state import ProjectState
from project_files import project_config_path, project_report_path, resolve_unique_project_dir


class Mode(Enum):
    STARTUP = "startup"
    OPEN = "open"
    SAVE_AS = "save_as"
    NEW = "new"


@dataclass(frozen=True, slots=True)
class ProjectMeta:
    project_dir: Path
    config_path: Path
    report_path: Path
    has_report: bool
    name: str
    address: str
    contact_name: str
    phone: str
    notes: str
    created_at: datetime
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
    for project_dir in root.iterdir():
        if not project_dir.is_dir():
            continue
        config_path = project_config_path(project_dir)
        report_path = project_report_path(project_dir)
        if not config_path.is_file():
            continue
        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            stat = config_path.stat()
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
                project_dir=project_dir,
                config_path=config_path,
                report_path=report_path,
                has_report=report_path.is_file(),
                name=str(meta.get("name") or project_dir.name),
                address=str(meta.get("address") or ""),
                contact_name=str(meta.get("contact_name") or ""),
                phone=str(meta.get("phone") or ""),
                notes=str(meta.get("notes") or ""),
                created_at=_parse_modified_at(meta.get("created_at"), stat.st_ctime),
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
        current_project_path: Path | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.mode = mode
        self._projects_dir = Path(projects_dir)
        self._current_project_path = current_project_path
        self._selected_path: Path | None = None
        self._startup_action: str | None = None
        self.setWindowTitle(self._title_for_mode(mode))
        self.setMinimumWidth(560)
        self._build_ui(default_name)
        self._reload_projects()

    def _project_path_for_name(self, name: str) -> Path:
        return project_config_path(resolve_unique_project_dir(self._projects_dir, name))

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
            form.addRow("Osoba kontaktowa:", self._contact_name_edit)
            form.addRow("Telefon:", self._phone_edit)
            form.addRow("Notatki:", self._notes_edit)
            root.addLayout(form)
        else:
            self._build_browser_panel(root)
            self._name_edit.hide()
            self._address_edit = QLineEdit(self)
            self._contact_name_edit = QLineEdit(self)
            self._phone_edit = QLineEdit(self)
            self._notes_edit = QTextEdit(self)
            self._address_edit.hide()
            self._contact_name_edit.hide()
            self._phone_edit.hide()
            self._notes_edit.hide()

    def _build_browser_panel(self, root: QVBoxLayout) -> None:
        self._browser_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self._browser_splitter.setChildrenCollapsible(False)

        list_panel = QWidget(self._browser_splitter)
        list_layout = QVBoxLayout(list_panel)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.addWidget(QLabel("Projekty", list_panel))
        list_layout.addWidget(self._project_list)

        details_panel = QWidget(self._browser_splitter)
        details_layout = QVBoxLayout(details_panel)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.addWidget(QLabel("Szczegóły projektu", details_panel))

        details_form = QFormLayout()
        self._details_name_value = QLabel("-", details_panel)
        self._details_created_at_value = QLabel("-", details_panel)
        self._details_modified_at_value = QLabel("-", details_panel)
        self._details_contact_name_value = QLabel("-", details_panel)
        self._details_phone_value = QLabel("-", details_panel)
        self._details_address_value = QLabel("-", details_panel)
        self._details_roof_plane_count_value = QLabel("-", details_panel)
        self._details_net_area_value = QLabel("-", details_panel)
        self._details_notes_value = QLabel("-", details_panel)

        for label in (
            self._details_name_value,
            self._details_created_at_value,
            self._details_modified_at_value,
            self._details_contact_name_value,
            self._details_phone_value,
            self._details_address_value,
            self._details_roof_plane_count_value,
            self._details_net_area_value,
            self._details_notes_value,
        ):
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        details_form.addRow("Nazwa:", self._details_name_value)
        details_form.addRow("Utworzono:", self._details_created_at_value)
        details_form.addRow("Zmodyfikowano:", self._details_modified_at_value)
        details_form.addRow("Osoba kontaktowa:", self._details_contact_name_value)
        details_form.addRow("Telefon:", self._details_phone_value)
        details_form.addRow("Adres:", self._details_address_value)
        details_form.addRow("Połacie:", self._details_roof_plane_count_value)
        details_form.addRow("Powierzchnia netto:", self._details_net_area_value)
        details_form.addRow("Notatki:", self._details_notes_value)
        details_layout.addLayout(details_form)
        self._report_button = QPushButton("Raport", details_panel)
        self._set_report_button_enabled(False)
        self._report_button.clicked.connect(self._open_selected_report)
        details_layout.addWidget(self._report_button)
        details_layout.addStretch(1)

        self._browser_splitter.setStretchFactor(0, 1)
        self._browser_splitter.setStretchFactor(1, 1)
        root.addWidget(self._browser_splitter)
        self._project_list.currentItemChanged.connect(self._on_current_item_changed)

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
            self._delete_button = self._button_box.addButton(
                "Usuń",
                QDialogButtonBox.ButtonRole.ActionRole,
            )
            self._delete_button.clicked.connect(self._delete_selected_project)
        elif self.mode == Mode.OPEN:
            self._button_box.addButton("Otwórz", QDialogButtonBox.ButtonRole.AcceptRole)
            self._delete_button = self._button_box.addButton(
                "Usuń",
                QDialogButtonBox.ButtonRole.ActionRole,
            )
            self._delete_button.clicked.connect(self._delete_selected_project)
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
            item.setData(Qt.ItemDataRole.UserRole, project)
            self._project_list.addItem(item)
        if self._project_list.count():
            self._project_list.setCurrentRow(0)
        else:
            self._clear_project_details()

    def _project_item_text(self, project: ProjectMeta) -> str:
        return f"{project.name}\nOstatnia modyfikacja: {self._format_datetime(project.modified_at)}"

    def _format_datetime(self, value: datetime) -> str:
        return value.astimezone().strftime("%Y-%m-%d %H:%M")

    def _current_project(self) -> ProjectMeta | None:
        item = self._project_list.currentItem()
        if item is None:
            return None
        project = item.data(Qt.ItemDataRole.UserRole)
        return project if isinstance(project, ProjectMeta) else None

    def _set_detail_label(self, label: QLabel, value: str) -> None:
        label.setText(value or "-")

    def _set_report_button_enabled(self, enabled: bool) -> None:
        self._report_button.setEnabled(enabled)
        self._report_button.setToolTip(
            "Otwórz ostatnio wygenerowany raport HTML."
            if enabled
            else "Brak zapisanego raportu dla tego projektu."
        )

    def _clear_project_details(self) -> None:
        if self.mode in {Mode.NEW, Mode.SAVE_AS}:
            return
        for label in (
            self._details_name_value,
            self._details_created_at_value,
            self._details_modified_at_value,
            self._details_contact_name_value,
            self._details_phone_value,
            self._details_address_value,
            self._details_roof_plane_count_value,
            self._details_net_area_value,
            self._details_notes_value,
        ):
            label.setText("-")
        self._set_report_button_enabled(False)

    def _update_project_details(self, project: ProjectMeta | None) -> None:
        if self.mode in {Mode.NEW, Mode.SAVE_AS}:
            return
        if project is None:
            self._clear_project_details()
            return
        self._set_detail_label(self._details_name_value, project.name)
        self._set_detail_label(self._details_created_at_value, self._format_datetime(project.created_at))
        self._set_detail_label(self._details_modified_at_value, self._format_datetime(project.modified_at))
        self._set_detail_label(self._details_contact_name_value, project.contact_name)
        self._set_detail_label(self._details_phone_value, project.phone)
        self._set_detail_label(self._details_address_value, project.address)
        self._set_detail_label(self._details_roof_plane_count_value, str(project.roof_plane_count))
        self._set_detail_label(self._details_net_area_value, f"{project.net_area_m2:.2f} m²")
        self._set_detail_label(self._details_notes_value, project.notes)
        self._set_report_button_enabled(project.has_report)

    def _on_current_item_changed(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        project = current.data(Qt.ItemDataRole.UserRole) if current is not None else None
        self._update_project_details(project if isinstance(project, ProjectMeta) else None)

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

    def _delete_selected_project(self) -> None:
        project = self._current_project()
        if project is None:
            return
        if self._current_project_path is not None and project.config_path == self._current_project_path:
            QMessageBox.warning(self, "Nie można usunąć projektu", "Nie można usunąć aktualnie otwartego projektu.")
            return
        answer = QMessageBox.question(
            self,
            "Usuń projekt",
            f"Czy na pewno usunąć projekt '{project.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            project.project_dir.relative_to(self._projects_dir)
            shutil.rmtree(project.project_dir)
        except OSError as exc:
            QMessageBox.warning(self, "Nie można usunąć projektu", str(exc))
            return
        except ValueError:
            QMessageBox.warning(self, "Nie można usunąć projektu", "Nieprawidłowa ścieżka katalogu projektu.")
            return
        self._reload_projects()

    def _open_selected_report(self) -> None:
        project = self._current_project()
        if project is None or not project.has_report:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(project.report_path)))

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
            self._selected_path = self._project_path_for_name(project_name)
            super().accept()
            return

        item = self._project_list.currentItem()
        if item is None:
            return
        project = self._current_project()
        if project is None:
            return
        self._selected_path = project.config_path
        self._startup_action = "open"
        super().accept()
