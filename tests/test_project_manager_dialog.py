from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from core.geometry import build_rectangle_outline
from core.models import Polygon2D
from ui.dialogs.project_manager_dialog import Mode, ProjectManagerDialog, scan_projects_dir

pytest_plugins = ("pytestqt",)


def _write_project(
    path,
    *,
    name: str,
    modified_at: datetime,
    address: str = "",
    contact_name: str = "",
    phone: str = "",
    notes: str = "",
    roof_planes=None,
) -> None:
    path.write_text(
        json.dumps(
            {
                "project_meta": {
                    "name": name,
                    "address": address,
                    "contact_name": contact_name,
                    "phone": phone,
                    "notes": notes,
                    "modified_at": modified_at.isoformat(),
                },
                "project_state": {"roof_planes": roof_planes or []},
                "materials": {"order": [], "items": {}},
                "blachy": [],
            }
        ),
        encoding="utf-8",
    )


def test_scan_projects_dir_returns_empty_for_missing_dir(tmp_path):
    assert scan_projects_dir(tmp_path / "missing") == []


def test_scan_projects_dir_skips_corrupted_json_and_sorts_by_modified_at(tmp_path):
    older = datetime.now(UTC) - timedelta(days=2)
    newer = datetime.now(UTC)
    _write_project(tmp_path / "older.4dach", name="Starszy", modified_at=older)
    _write_project(tmp_path / "newer.4dach", name="Nowszy", modified_at=newer)
    (tmp_path / "broken.4dach").write_text("{broken", encoding="utf-8")

    projects = scan_projects_dir(tmp_path)

    assert [project.name for project in projects] == ["Nowszy", "Starszy"]
    assert [project.path.name for project in projects] == ["newer.4dach", "older.4dach"]


def test_project_manager_save_mode_builds_4dach_path(qtbot, tmp_path):
    dialog = ProjectManagerDialog(mode=Mode.SAVE_AS, projects_dir=tmp_path, default_name="Nowy")
    qtbot.addWidget(dialog)

    dialog._name_edit.setText("Projekt Test")
    dialog.accept()

    assert dialog.selected_path() == tmp_path / "Projekt Test.4dach"
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
    (tmp_path / "Projekt Test.4dach").write_text("{}", encoding="utf-8")
    (tmp_path / "Projekt Test 2.4dach").write_text("{}", encoding="utf-8")
    dialog = ProjectManagerDialog(mode=Mode.SAVE_AS, projects_dir=tmp_path, default_name="Nowy")
    qtbot.addWidget(dialog)

    dialog._name_edit.setText("Projekt Test")
    dialog.accept()

    assert dialog.selected_path() == tmp_path / "Projekt Test 3.4dach"
    assert dialog.project_name() == "Projekt Test 3"


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
        tmp_path / "meta.4dach",
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
    assert project.address == "Ulica 1"
    assert project.contact_name == "Jan Kowalski"
    assert project.phone == "123"
    assert project.notes == "Pilne"
    assert project.roof_plane_count == 2
    assert project.net_area_m2 == 7.5


def test_project_list_displays_meta_and_statistics(qtbot, tmp_path):
    _write_project(
        tmp_path / "meta.4dach",
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
    assert "Ulica 1" in text
    assert "Jan Kowalski" in text
    assert "Pilne" in text
    assert "Połacie: 1" in text
    assert "Powierzchnia netto: 1.00 m²" in text
