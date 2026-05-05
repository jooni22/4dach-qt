from __future__ import annotations

import json
from pathlib import Path

from core.app_settings import AppSettings
from user_preferences import USER_LEVEL_KEYS, UserPreferences, default_user_preferences_path


def test_user_preferences_uses_explicit_path_and_ignores_missing_file(tmp_path):
    prefs_path = tmp_path / "prefs" / "user_preferences.json"

    prefs = UserPreferences(path=prefs_path)

    assert prefs.path == prefs_path
    assert prefs.to_dict() == {}


def test_user_preferences_saves_atomically_to_explicit_path(tmp_path):
    prefs_path = tmp_path / "prefs" / "user_preferences.json"
    prefs = UserPreferences(path=prefs_path)

    assert prefs.update({"company_data": {"name": "Firma"}, "projects_dir": str(tmp_path)})
    assert prefs.save() is True

    assert json.loads(prefs_path.read_text(encoding="utf-8")) == {
        "company_data": {"name": "Firma"},
        "projects_dir": str(tmp_path),
    }
    assert list(prefs_path.parent.glob("*.tmp")) == []


def test_user_preferences_ignores_corrupted_file(tmp_path):
    prefs_path = tmp_path / "user_preferences.json"
    prefs_path.write_text("{broken", encoding="utf-8")

    prefs = UserPreferences(path=prefs_path)

    assert prefs.to_dict() == {}


def test_user_preferences_migrates_only_user_level_keys(tmp_path):
    prefs = UserPreferences(path=tmp_path / "user_preferences.json")
    legacy_payload = {
        "company_data": {"name": "Firma"},
        "ksztalty": {"prostokat": {"szerokosc": 320}},
        "add_polac_dialog": {"last_shape": "prostokat"},
        "wycinki": {"prostokat": {"szerokosc": 80}},
        "app_settings": AppSettings(show_grid=False).to_dict(),
        "projects_dir": str(tmp_path),
        "materials": {"order": []},
        "project_state": {"roof_planes": []},
        "blachy": [],
    }

    assert prefs.migrate_from_config(legacy_payload) is True

    migrated = prefs.to_dict()
    assert set(migrated) == USER_LEVEL_KEYS
    assert migrated["company_data"] == {"name": "Firma"}
    assert "materials" not in migrated
    assert "project_state" not in migrated
    assert "blachy" not in migrated


def test_user_preferences_migrates_legacy_values_over_fresh_defaults(tmp_path):
    prefs = UserPreferences(path=tmp_path / "user_preferences.json", initialize_defaults=True)

    assert prefs.migrate_from_config({"company_data": {"name": "Legacy Firma"}}) is True

    assert prefs.to_dict()["company_data"] == {"name": "Legacy Firma"}


def test_user_preferences_injects_into_project_payload_without_projects_dir(tmp_path):
    prefs = UserPreferences(path=tmp_path / "user_preferences.json")
    prefs.update(
        {
            "company_data": {"name": "Firma"},
            "app_settings": {"show_grid": False},
            "projects_dir": str(tmp_path),
        }
    )
    payload = {"project_state": {"roof_planes": []}}

    injected = prefs.inject_into_config(payload)

    assert injected is payload
    assert payload["company_data"] == {"name": "Firma"}
    assert payload["app_settings"] == {"show_grid": False}
    assert "projects_dir" not in payload


def test_default_user_preferences_path_is_documents_4dach(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    assert default_user_preferences_path() == tmp_path / "Documents" / "4Dach" / "user_preferences.json"


def test_default_user_preferences_creates_directory_and_full_defaults(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    prefs = UserPreferences()

    prefs_path = tmp_path / "Documents" / "4Dach" / "user_preferences.json"
    payload = json.loads(prefs_path.read_text(encoding="utf-8"))
    assert prefs.path == prefs_path
    assert set(payload) == USER_LEVEL_KEYS
    assert payload["app_settings"] == AppSettings().to_dict()
    assert payload["projects_dir"] == str(tmp_path / "Documents" / "4Dach")
    assert payload["company_data"] == {"name": "", "nip": "", "address": "", "website": "", "logo": ""}
    assert "prostokat" in payload["ksztalty"]
    assert "last_shape" in payload["add_polac_dialog"]
    assert payload["wycinki"] == {"prostokat": {"szerokosc": 100, "wysokosc": 100}}


def test_default_user_preferences_falls_back_to_application_dir(monkeypatch, tmp_path):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    blocked_home = tmp_path / "blocked"

    def fake_probe(path):
        return path != blocked_home / "Documents" / "4Dach"

    monkeypatch.setattr(Path, "home", lambda: blocked_home)
    monkeypatch.setattr("user_preferences.APP_DIR", app_dir)
    monkeypatch.setattr("user_preferences._is_writable_dir", fake_probe)

    prefs = UserPreferences()

    assert prefs.path == app_dir / "user_preferences.json"
    assert prefs.projects_dir == app_dir


def test_default_user_preferences_reports_unavailable_storage(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    monkeypatch.setattr("user_preferences.APP_DIR", tmp_path / "app")
    monkeypatch.setattr("user_preferences._is_writable_dir", lambda _path: False)

    prefs = UserPreferences()

    assert prefs.storage_ready is False
    assert prefs.storage_candidates == [
        tmp_path / "home" / "Documents" / "4Dach",
        tmp_path / "app",
    ]
