from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QMessageBox

from core.geometry import build_rectangle_outline
from core.models import Polygon2D
from project_files import project_config_path, project_report_path
from ui.dialogs.project_manager_dialog import Mode, ProjectManagerDialog, scan_projects_dir

pytest_plugins = ("pytestqt",)


def _write_project(
    project_dir,
    *,
    name: str,
    created_at: datetime | None = None,
    modified_at: datetime,
    address: str = "",
    contact_name: str = "",
    phone: str = "",
    notes: str = "",
    roof_planes=None,
    with_report: bool = False,
) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    path = project_config_path(project_dir)
    path.write_text(
        json.dumps(
            {
                "project_meta": {
                    "name": name,
                    "address": address,
                    "contact_name": contact_name,
                    "phone": phone,
                    "notes": notes,
                    "created_at": (created_at or modified_at).isoformat(),
                    "modified_at": modified_at.isoformat(),
                },
                "project_state": {"roof_planes": roof_planes or []},
                "materials": {"order": [], "items": {}},
                "blachy": [],
            }
        ),
        encoding="utf-8",
    )
    if with_report:
        project_report_path(project_dir).write_text("<html>raport</html>", encoding="utf-8")


def test_scan_projects_dir_returns_empty_for_missing_dir(tmp_path):
    assert scan_projects_dir(tmp_path / "missing") == []


def test_scan_projects_dir_skips_corrupted_json_and_sorts_by_modified_at(tmp_path):
    older = datetime.now(UTC) - timedelta(days=2)
    newer = datetime.now(UTC)
    _write_project(tmp_path / "older", name="Starszy", modified_at=older)
    _write_project(tmp_path / "newer", name="Nowszy", modified_at=newer)
    broken_dir = tmp_path / "broken"
    broken_dir.mkdir()
    project_config_path(broken_dir).write_text("{broken", encoding="utf-8")

    projects = scan_projects_dir(tmp_path)

    assert [project.name for project in projects] == ["Nowszy", "Starszy"]
    assert [project.config_path for project in projects] == [
        project_config_path(tmp_path / "newer"),
        project_config_path(tmp_path / "older"),
    ]


def test_project_manager_save_mode_builds_4dach_path(qtbot, tmp_path):
    dialog = ProjectManagerDialog(mode=Mode.SAVE_AS, projects_dir=tmp_path, default_name="Nowy")
    qtbot.addWidget(dialog)

    dialog._name_edit.setText("Projekt Test")
    dialog.accept()

    assert dialog.selected_path() == project_config_path(tmp_path / "projekt-test")
    assert dialog.project_name() == "Projekt Test"


def test_project_manager_requires_non_empty_project_name(qtbot, monkeypatch, tmp_path):
    warnings: list[str] = []
    monkeypatch.setattr(
        "ui.dialogs.project_manager_dialog.QMessageBox.warning",
        lambda _parent, _title, message: warnings.append(message),
    )
    dialog = ProjectManagerDialog(mode=Mode.NEW, projects_dir=tmp_path, default_name="Nowy")
    qtbot.addWidget(dialog)

    dialog._name_edit.setText("   ")
    dialog.accept()

    assert dialog.result() == 0
    assert dialog.selected_path() is None
    assert warnings == ["Nazwa projektu jest wymagana."]


def test_project_manager_startup_new_does_not_reserve_default_path(qtbot, tmp_path):
    dialog = ProjectManagerDialog(mode=Mode.STARTUP, projects_dir=tmp_path)
    qtbot.addWidget(dialog)

    dialog._accept_new_from_startup()

    assert dialog.result() == dialog.DialogCode.Accepted
    assert dialog.startup_action() == "new"
    assert dialog.selected_path() is None


def test_project_manager_returns_full_project_meta(qtbot, tmp_path):
    dialog = ProjectManagerDialog(mode=Mode.SAVE_AS, projects_dir=tmp_path, default_name="Nowy")
    qtbot.addWidget(dialog)

    dialog._name_edit.setText("Dach Kowalski")
    dialog._address_edit.setText("Ulica 1")
    dialog._contact_name_edit.setText("Jan Kowalski")
    dialog._phone_edit.setText("123 456 789")
    dialog._notes_edit.setPlainText("Pilny montaż")
    dialog.accept()

    assert dialog.project_meta() == {
        "name": "Dach Kowalski",
        "address": "Ulica 1",
        "contact_name": "Jan Kowalski",
        "phone": "123 456 789",
        "notes": "Pilny montaż",
    }


def test_project_manager_iterates_project_name_when_target_file_exists(qtbot, tmp_path):
    (tmp_path / "projekt-test").mkdir()
    (tmp_path / "projekt-test-2").mkdir()
    dialog = ProjectManagerDialog(mode=Mode.SAVE_AS, projects_dir=tmp_path, default_name="Nowy")
    qtbot.addWidget(dialog)

    dialog._name_edit.setText("Projekt Test")
    dialog.accept()

    assert dialog.selected_path() == project_config_path(tmp_path / "projekt-test-3")
    assert dialog.project_name() == "Projekt Test"


def test_scan_projects_dir_reads_meta_and_calculates_statistics(tmp_path):
    roof_planes = [
        {
            "id": "p1",
            "name": "1",
            "outline": [[point.x, point.y] for point in build_rectangle_outline(300, 200).points],
            "holes": [
                [
                    [point.x, point.y]
                    for point in Polygon2D.rectangle(100, 50, origin_x=20, origin_y=20).points
                ]
            ],
        },
        {
            "id": "p2",
            "name": "2",
            "outline": [[point.x, point.y] for point in build_rectangle_outline(200, 100).points],
            "holes": [],
        },
    ]
    _write_project(
        tmp_path / "meta",
        name="Dach Kowalski",
        address="Ulica 1",
        contact_name="Jan Kowalski",
        phone="123",
        notes="Pilne",
        modified_at=datetime.now(UTC),
        roof_planes=roof_planes,
    )

    [project] = scan_projects_dir(tmp_path)

    assert project.name == "Dach Kowalski"
    assert project.project_dir == tmp_path / "meta"
    assert project.config_path == project_config_path(tmp_path / "meta")
    assert project.report_path == project_report_path(tmp_path / "meta")
    assert project.has_report is False
    assert project.address == "Ulica 1"
    assert project.contact_name == "Jan Kowalski"
    assert project.phone == "123"
    assert project.notes == "Pilne"
    assert project.roof_plane_count == 2
    assert project.net_area_m2 == 7.5


def test_project_list_displays_meta_and_statistics(qtbot, tmp_path):
    _write_project(
        tmp_path / "meta",
        name="Dach Kowalski",
        address="Ulica 1",
        contact_name="Jan Kowalski",
        notes="Pilne",
        modified_at=datetime.now(UTC),
        roof_planes=[
            {
                "id": "p1",
                "name": "1",
                "outline": [[point.x, point.y] for point in build_rectangle_outline(100, 100).points],
                "holes": [],
            },
        ],
    )
    dialog = ProjectManagerDialog(mode=Mode.OPEN, projects_dir=tmp_path)
    qtbot.addWidget(dialog)

    text = dialog._project_list.item(0).text()

    assert "Dach Kowalski" in text
    assert "Ostatnia modyfikacja:" in text
    assert "Ulica 1" not in text
    assert "Połacie: 1" not in text


def test_project_manager_open_mode_builds_browser_split_view(qtbot, tmp_path):
    _write_project(
        tmp_path / "meta",
        name="Dach Kowalski",
        modified_at=datetime.now(UTC),
    )
    dialog = ProjectManagerDialog(mode=Mode.OPEN, projects_dir=tmp_path)
    qtbot.addWidget(dialog)

    assert dialog._browser_splitter.count() == 2
    assert dialog._project_list.parentWidget() is not None
    assert dialog._details_name_value.text() == "Dach Kowalski"


def test_project_manager_preview_updates_when_selection_changes(qtbot, tmp_path):
    first_created = datetime(2024, 1, 10, 8, 30, tzinfo=UTC)
    first_modified = datetime(2024, 1, 12, 14, 15, tzinfo=UTC)
    second_created = datetime(2024, 2, 5, 9, 0, tzinfo=UTC)
    second_modified = datetime(2024, 2, 6, 16, 45, tzinfo=UTC)
    _write_project(
        tmp_path / "first",
        name="Projekt A",
        created_at=first_created,
        modified_at=first_modified,
        address="Ulica 1",
        contact_name="Jan Kowalski",
        phone="123 456 789",
        notes="Pilny montaż",
        roof_planes=[
            {
                "id": "p1",
                "name": "1",
                "outline": [[point.x, point.y] for point in build_rectangle_outline(100, 100).points],
                "holes": [],
            },
        ],
    )
    _write_project(
        tmp_path / "second",
        name="Projekt B",
        created_at=second_created,
        modified_at=second_modified,
        address="Ulica 2",
        contact_name="Anna Nowak",
        phone="987 654 321",
        notes="Bez uwag",
        roof_planes=[
            {
                "id": "p1",
                "name": "1",
                "outline": [[point.x, point.y] for point in build_rectangle_outline(200, 100).points],
                "holes": [],
            },
            {
                "id": "p2",
                "name": "2",
                "outline": [[point.x, point.y] for point in build_rectangle_outline(100, 100).points],
                "holes": [],
            },
        ],
    )
    dialog = ProjectManagerDialog(mode=Mode.OPEN, projects_dir=tmp_path)
    qtbot.addWidget(dialog)

    dialog._project_list.setCurrentRow(1)

    assert dialog._details_name_value.text() == "Projekt A"
    assert dialog._details_address_value.text() == "Ulica 1"
    assert dialog._details_contact_name_value.text() == "Jan Kowalski"
    assert dialog._details_phone_value.text() == "123 456 789"
    assert dialog._details_notes_value.text() == "Pilny montaż"
    assert dialog._details_roof_plane_count_value.text() == "1"
    assert dialog._details_net_area_value.text() == "1.00 m²"
    assert dialog._details_created_at_value.text() == dialog._format_datetime(first_created.astimezone())
    assert dialog._details_modified_at_value.text() == dialog._format_datetime(first_modified.astimezone())


def test_project_manager_delete_removes_selected_project_after_confirmation(qtbot, monkeypatch, tmp_path):
    project_dir = tmp_path / "delete-me"
    project_path = project_config_path(project_dir)
    _write_project(project_dir, name="Usuń mnie", modified_at=datetime.now(UTC))
    monkeypatch.setattr(
        "ui.dialogs.project_manager_dialog.QMessageBox.question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    dialog = ProjectManagerDialog(mode=Mode.OPEN, projects_dir=tmp_path)
    qtbot.addWidget(dialog)

    dialog._delete_selected_project()

    assert project_dir.exists() is False
    assert project_path.exists() is False
    assert dialog._project_list.count() == 0
    assert dialog._details_name_value.text() == "-"


def test_project_manager_delete_is_cancelled_when_confirmation_rejected(qtbot, monkeypatch, tmp_path):
    project_dir = tmp_path / "keep-me"
    project_path = project_config_path(project_dir)
    _write_project(project_dir, name="Zostaw mnie", modified_at=datetime.now(UTC))
    monkeypatch.setattr(
        "ui.dialogs.project_manager_dialog.QMessageBox.question",
        lambda *args, **kwargs: QMessageBox.StandardButton.No,
    )
    dialog = ProjectManagerDialog(mode=Mode.OPEN, projects_dir=tmp_path)
    qtbot.addWidget(dialog)

    dialog._delete_selected_project()

    assert project_dir.exists() is True
    assert project_path.exists() is True
    assert dialog._project_list.count() == 1
    assert dialog._details_name_value.text() == "Zostaw mnie"


def test_project_manager_delete_blocks_currently_open_project(qtbot, monkeypatch, tmp_path):
    project_dir = tmp_path / "current"
    project_path = project_config_path(project_dir)
    _write_project(project_dir, name="Bieżący", modified_at=datetime.now(UTC))
    warnings: list[str] = []
    monkeypatch.setattr(
        "ui.dialogs.project_manager_dialog.QMessageBox.warning",
        lambda _parent, _title, message: warnings.append(message),
    )
    dialog = ProjectManagerDialog(
        mode=Mode.OPEN,
        projects_dir=tmp_path,
        current_project_path=project_path,
    )
    qtbot.addWidget(dialog)

    dialog._delete_selected_project()

    assert project_path.exists() is True
    assert warnings == ["Nie można usunąć aktualnie otwartego projektu."]


def test_scan_projects_dir_marks_report_availability(tmp_path):
    _write_project(tmp_path / "with-report", name="Z raportem", modified_at=datetime.now(UTC), with_report=True)

    [project] = scan_projects_dir(tmp_path)

    assert project.has_report is True
    assert project.report_path == project_report_path(tmp_path / "with-report")


def test_project_manager_report_button_state_follows_report_file(qtbot, tmp_path):
    _write_project(tmp_path / "with-report", name="Z raportem", modified_at=datetime.now(UTC), with_report=True)
    _write_project(tmp_path / "without-report", name="Bez raportu", modified_at=datetime.now(UTC) - timedelta(days=1))
    dialog = ProjectManagerDialog(mode=Mode.OPEN, projects_dir=tmp_path)
    qtbot.addWidget(dialog)

    assert dialog._report_button.isEnabled() is True
    assert dialog._report_button.toolTip() == "Otwórz ostatnio wygenerowany raport HTML."

    dialog._project_list.setCurrentRow(1)

    assert dialog._report_button.isEnabled() is False
    assert dialog._report_button.toolTip() == "Brak zapisanego raportu dla tego projektu."


def test_project_manager_report_button_opens_existing_report(qtbot, monkeypatch, tmp_path):
    _write_project(tmp_path / "with-report", name="Z raportem", modified_at=datetime.now(UTC), with_report=True)
    opened_urls: list[QUrl] = []
    monkeypatch.setattr(
        "ui.dialogs.project_manager_dialog.QDesktopServices.openUrl",
        lambda url: opened_urls.append(url) or True,
    )
    dialog = ProjectManagerDialog(mode=Mode.OPEN, projects_dir=tmp_path)
    qtbot.addWidget(dialog)

    dialog._open_selected_report()

    assert opened_urls == [QUrl.fromLocalFile(str(project_report_path(tmp_path / "with-report")))]
