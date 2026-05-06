from __future__ import annotations

from project_files import (
    project_config_path,
    project_dir_from_config_path,
    project_dir_from_name,
    project_report_path,
    resolve_unique_project_dir,
    slugify_project_name,
)


def test_slugify_project_name_normalizes_to_safe_ascii_slug():
    assert slugify_project_name("  Zażółć gęślą jaźń 2026  ") == "zazolc-gesla-jazn-2026"


def test_slugify_project_name_falls_back_for_empty_slug():
    assert slugify_project_name("...___...") == "projekt"


def test_project_dir_from_name_builds_slugged_project_directory(tmp_path):
    assert project_dir_from_name(tmp_path, "Projekt Test") == tmp_path / "projekt-test"


def test_resolve_unique_project_dir_iterates_directory_suffixes(tmp_path):
    (tmp_path / "projekt-a").mkdir()
    (tmp_path / "projekt-a-2").mkdir()

    assert resolve_unique_project_dir(tmp_path, "Projekt A") == tmp_path / "projekt-a-3"


def test_resolve_unique_project_dir_reuses_current_directory(tmp_path):
    current_dir = tmp_path / "projekt-a"
    current_dir.mkdir()
    (tmp_path / "projekt-a-2").mkdir()

    assert resolve_unique_project_dir(tmp_path, "Projekt A", current_dir=current_dir) == current_dir


def test_project_paths_are_derived_from_project_directory(tmp_path):
    project_dir = tmp_path / "projekt-a"

    assert project_config_path(project_dir) == project_dir / "project.4dach"
    assert project_report_path(project_dir) == project_dir / "report.html"
    assert project_dir_from_config_path(project_dir / "project.4dach") == project_dir
