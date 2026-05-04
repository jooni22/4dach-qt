from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def asset_path(*parts: str) -> Path:
    return app_root().joinpath(*parts)


def load_app_icon() -> QIcon:
    return QIcon(str(asset_path("assets", "app_icon.ico")))
