"""Helpers for the on-disk project container layout."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

_DEFAULT_PROJECT_DIR_SLUG = "projekt"
_PROJECT_CONFIG_FILENAME = "project.4dach"
_PROJECT_REPORT_FILENAME = "report.html"
_EXTRA_TRANSLITERATION = str.maketrans({"ł": "l", "Ł": "L"})


def slugify_project_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name.translate(_EXTRA_TRANSLITERATION))
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized.lower()).strip("-")
    return slug or _DEFAULT_PROJECT_DIR_SLUG


def project_dir_from_name(projects_dir: Path | str, project_name: str) -> Path:
    return Path(projects_dir) / slugify_project_name(project_name)


def resolve_unique_project_dir(
    projects_dir: Path | str,
    project_name: str,
    current_dir: Path | None = None,
) -> Path:
    root = Path(projects_dir)
    base_dir = project_dir_from_name(root, project_name)
    if current_dir is not None and base_dir == current_dir:
        return current_dir
    if not base_dir.exists():
        return base_dir

    index = 2
    while True:
        candidate = root / f"{base_dir.name}-{index}"
        if current_dir is not None and candidate == current_dir:
            return current_dir
        if not candidate.exists():
            return candidate
        index += 1


def project_config_path(project_dir: Path | str) -> Path:
    return Path(project_dir) / _PROJECT_CONFIG_FILENAME


def project_report_path(project_dir: Path | str) -> Path:
    return Path(project_dir) / _PROJECT_REPORT_FILENAME


def project_dir_from_config_path(config_path: Path | str) -> Path:
    return Path(config_path).parent
