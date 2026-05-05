"""User-level preferences kept outside project files."""
from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

from core.app_settings import AppSettings
from core.models import CompanyData

USER_LEVEL_KEYS = {
    "company_data",
    "ksztalty",
    "add_polac_dialog",
    "wycinki",
    "app_settings",
    "projects_dir",
}
CONFIG_INJECTION_KEYS = USER_LEVEL_KEYS - {"projects_dir"}
APP_DIR = Path(__file__).resolve().parent


def default_user_preferences_path() -> Path:
    return Path.home() / "Documents" / "4Dach" / "user_preferences.json"


def _default_projects_dir() -> Path:
    return default_user_preferences_path().parent


def _is_writable_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path, delete=True):
            pass
        return True
    except OSError:
        return False


def _storage_candidates() -> list[Path]:
    return [_default_projects_dir(), APP_DIR]


def _resolve_storage_dir() -> tuple[Path, bool, list[Path]]:
    candidates = _storage_candidates()
    for candidate in candidates:
        if _is_writable_dir(candidate):
            return candidate, True, candidates
    return candidates[0], False, candidates


def default_user_preferences_data(projects_dir: Path | str | None = None) -> dict:
    resolved_projects_dir = Path(projects_dir) if projects_dir is not None else _default_projects_dir()
    return {
        "company_data": CompanyData().to_dict(),
        "ksztalty": {
            "prostokat": {"szerokosc": 300, "wysokosc": 300},
            "trojkat": {
                "typ": "równoramienny",
                "podstawa": 320,
                "wysokosc": 220,
                "ramie": 360,
                "ramie_enabled": False,
            },
            "trapez": {
                "typ": "równoramienny",
                "podstawa_dolna": 420,
                "podstawa_gorna": 260,
                "wysokosc": 240,
            },
        },
        "add_polac_dialog": {
            "last_shape": "prostokat",
            "last_cutout": "none",
            "flip_h": False,
            "flip_v": False,
            "shapes": {
                "prostokat": {"A": 800, "B": 300},
                "trojkat": {"A": 800, "B": 300},
                "trapez_row": {"A": 800, "B": 300, "C": 500},
                "trapez_prl": {"A": 800, "B": 300, "C": 500},
                "trapez_l": {"A": 800, "B": 300, "C": 500},
                "trapez6": {"A": 800, "B": 300, "C": 500},
                "trapez7": {"A": 800, "B": 300, "C": 500},
                "pieciokat": {"A": 800, "B": 300},
                "pieciokat2": {"A": 800, "B": 300},
            },
            "cutouts": {
                "lukarna1": {"A": 80, "H1": 120, "X": 50, "Y": 50},
                "lukarna2": {"A": 100, "H": 120, "X": 50, "Y": 50},
                "lukarna3": {"A": 100, "H1": 80, "H": 120, "X": 50, "Y": 50},
            },
        },
        "wycinki": {"prostokat": {"szerokosc": 100, "wysokosc": 100}},
        "app_settings": AppSettings().to_dict(),
        "projects_dir": str(resolved_projects_dir),
    }


class UserPreferences:
    def __init__(self, path: Path | str | None = None, *, initialize_defaults: bool | None = None) -> None:
        self.storage_candidates: list[Path]
        if path is None:
            storage_dir, self.storage_ready, self.storage_candidates = _resolve_storage_dir()
            self.path = storage_dir / "user_preferences.json"
            if initialize_defaults is None:
                initialize_defaults = True
        else:
            self.path = Path(path)
            self.storage_ready = True
            self.storage_candidates = [self.path.parent]
            if initialize_defaults is None:
                initialize_defaults = False
        self._data: dict = self._load()
        self._bootstrapped_defaults = False
        if initialize_defaults and not self._data:
            self._data = default_user_preferences_data(self.path.parent)
            self._bootstrapped_defaults = True
            if self.storage_ready:
                self.storage_ready = self.save()

    def _load(self) -> dict:
        try:
            with self.path.open(encoding="utf-8") as fh:
                payload = json.load(fh)
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return {}
        if not isinstance(payload, dict):
            return {}
        return {
            key: copy.deepcopy(value)
            for key, value in payload.items()
            if key in USER_LEVEL_KEYS
        }

    def to_dict(self) -> dict:
        return copy.deepcopy(self._data)

    def get(self, key: str, default=None):
        return copy.deepcopy(self._data.get(key, default))

    @property
    def projects_dir(self) -> Path:
        configured = self._data.get("projects_dir")
        if configured:
            return Path(configured)
        return self.path.parent

    def update(self, values: dict) -> bool:
        changed = False
        for key, value in values.items():
            if key not in USER_LEVEL_KEYS:
                continue
            next_value = copy.deepcopy(value)
            if self._data.get(key) != next_value:
                self._data[key] = next_value
                changed = True
        return changed

    def set(self, key: str, value) -> bool:
        return self.update({key: value})

    def migrate_from_config(self, config_data: dict | None) -> bool:
        if not isinstance(config_data, dict):
            return False
        values = {}
        for key in USER_LEVEL_KEYS:
            if key not in config_data:
                continue
            if key not in self._data or self._bootstrapped_defaults:
                values[key] = copy.deepcopy(config_data[key])
        changed = self.update(values)
        if changed:
            self._bootstrapped_defaults = False
        return changed

    def inject_into_config(self, config_data: dict) -> dict:
        for key in CONFIG_INJECTION_KEYS:
            if key in self._data:
                config_data[key] = copy.deepcopy(self._data[key])
        return config_data

    def save(self) -> bool:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                delete=False,
                suffix=".tmp",
            ) as fh:
                json.dump(self._data, fh, ensure_ascii=False, separators=(",", ":"))
                temp_path = Path(fh.name)
            temp_path.replace(self.path)
            return True
        except OSError:
            return False
