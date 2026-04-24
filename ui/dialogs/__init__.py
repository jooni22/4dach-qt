# This Python file uses the following encoding: utf-8
"""ui/dialogs/__init__.py — re-exports all dialog classes."""
from ui.dialogs.shape_dialogs import ProstokatDialog, TrojkatDialog, TrapezDialog
from ui.dialogs.material_dialog import BlachyDialog, DaneBlachyDialog
from ui.dialogs.company_dialog import DaneFirmyDialog

__all__ = [
    "ProstokatDialog",
    "TrojkatDialog",
    "TrapezDialog",
    "BlachyDialog",
    "DaneBlachyDialog",
    "DaneFirmyDialog",
]
