from __future__ import annotations

from project_files import project_config_path
from ui.dialogs.project_details_dialog import ProjectDetailsDialog

pytest_plugins = ("pytestqt",)


def test_project_details_dialog_requires_non_empty_project_name(qtbot, monkeypatch, tmp_path):
    warnings: list[str] = []
    monkeypatch.setattr(
        "ui.dialogs.project_details_dialog.QMessageBox.warning",
        lambda _parent, _title, message: warnings.append(message),
    )
    dialog = ProjectDetailsDialog(projects_dir=tmp_path, default_name="Nowy")
    qtbot.addWidget(dialog)

    dialog._name_edit.setText("   ")
    dialog.accept()

    assert dialog.result() == 0
    assert dialog.selected_path() is None
    assert warnings == ["Nazwa projektu jest wymagana."]


def test_project_details_dialog_returns_full_project_meta(qtbot, tmp_path):
    dialog = ProjectDetailsDialog(projects_dir=tmp_path, default_name="Nowy")
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
    assert dialog.selected_path() == project_config_path(tmp_path / "dach-kowalski")


def test_project_details_dialog_iterates_project_name_when_target_file_exists(qtbot, tmp_path):
    (tmp_path / "projekt-test").mkdir()
    (tmp_path / "projekt-test-2").mkdir()
    dialog = ProjectDetailsDialog(projects_dir=tmp_path, default_name="Nowy")
    qtbot.addWidget(dialog)

    dialog._name_edit.setText("Projekt Test")
    dialog.accept()

    assert dialog.selected_path() == project_config_path(tmp_path / "projekt-test-3")
    assert dialog.project_name() == "Projekt Test"


def test_project_details_dialog_populates_initial_meta_values(qtbot, tmp_path):
    dialog = ProjectDetailsDialog(
        projects_dir=tmp_path,
        default_name="Nowy",
        initial_meta={
            "name": "Projekt A",
            "address": "Ulica 1",
            "contact_name": "Jan Kowalski",
            "phone": "123 456 789",
            "notes": "Pilny montaż",
        },
    )
    qtbot.addWidget(dialog)

    assert dialog.project_name() == "Projekt A"
    assert dialog._address_edit.text() == "Ulica 1"
    assert dialog._contact_name_edit.text() == "Jan Kowalski"
    assert dialog._phone_edit.text() == "123 456 789"
    assert dialog._notes_edit.toPlainText() == "Pilny montaż"


def test_project_details_dialog_edit_mode_keeps_existing_project_path(qtbot, tmp_path):
    existing_path = project_config_path(tmp_path / "istniejacy")
    dialog = ProjectDetailsDialog(
        projects_dir=tmp_path,
        default_name="Nowy",
        initial_meta={"name": "Projekt A"},
        project_path=existing_path,
    )
    qtbot.addWidget(dialog)

    dialog._name_edit.setText("Projekt A")
    dialog.accept()

    assert dialog.selected_path() == existing_path
    assert dialog.project_name() == "Projekt A"


def test_project_details_dialog_edit_mode_resolves_new_project_directory_from_renamed_project(qtbot, tmp_path):
    existing_path = project_config_path(tmp_path / "stary-projekt")
    dialog = ProjectDetailsDialog(
        projects_dir=tmp_path,
        default_name="Nowy",
        initial_meta={"name": "Stary projekt"},
        project_path=existing_path,
    )
    qtbot.addWidget(dialog)

    dialog._name_edit.setText("Nowy projekt")
    dialog.accept()

    assert dialog.selected_path() == project_config_path(tmp_path / "nowy-projekt")
    assert dialog.project_name() == "Nowy projekt"
