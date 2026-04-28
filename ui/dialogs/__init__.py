"""ui/dialogs/__init__.py — re-exports all dialog classes."""
from ui.dialogs.company_dialog import DaneFirmyDialog
from ui.dialogs.material_dialog import BlachyDialog, DaneBlachyDialog
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.shape_dialogs import ProstokatDialog, TrapezDialog, TrojkatDialog

__all__ = [
    "ProstokatDialog",
    "TrojkatDialog",
    "TrapezDialog",
    "BlachyDialog",
    "DaneBlachyDialog",
    "DaneFirmyDialog",
    "SettingsDialog",
]
