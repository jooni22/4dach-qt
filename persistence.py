"""persistence.py — configuration load/save with proper IO error handling.

This module is the single source of truth for reading and writing config.json.
It is Qt-free so that core/ modules can import it if needed.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config(path: Path | str | None = None) -> dict:
    """Load configuration from config.json.

    Returns an empty dict if the file does not exist or cannot be parsed.
    """
    config_path = Path(path) if path is not None else _CONFIG_PATH
    try:
        with open(config_path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(config_data: dict, parent_widget=None, path: Path | str | None = None) -> bool:
    """Persist *config_data* to config.json.

    Returns ``True`` on success.  On ``OSError`` the method returns ``False``
    and, when *parent_widget* is not ``None``, shows a ``QMessageBox.critical``
    dialog so the user is informed about the failure.
    """
    config_path = Path(path) if path is not None else _CONFIG_PATH
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=config_path.parent,
            delete=False,
            suffix=".tmp",
        ) as fh:
            json.dump(config_data, fh, ensure_ascii=False, separators=(",", ":"))
            temp_path = Path(fh.name)
        temp_path.replace(config_path)
        return True
    except OSError as exc:
        if parent_widget is not None:
            # Import here so persistence.py stays Qt-free when used without QApplication
            from PySide6.QtWidgets import QMessageBox  # noqa: PLC0415

            QMessageBox.critical(
                parent_widget,
                "Błąd zapisu",
                f"Nie można zapisać pliku konfiguracji:\n{exc}",
            )
        return False
