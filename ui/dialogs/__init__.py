"""ui/dialogs/__init__.py — re-exports all dialog classes."""
from ui.dialogs.add_polac_dialog import AddPolacDialog
from ui.dialogs.company_dialog import DaneFirmyDialog
from ui.dialogs.material_dialog import BlachyDialog, DaneBlachyDialog
from ui.dialogs.project_details_dialog import ProjectDetailsDialog
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.shape_dialogs import (
    CutoutRectangleDialog,
    ProstokatDialog,
    TrapezDialog,
    TrojkatDialog,
)

__all__ = [
    "AddPolacDialog",
    "ProstokatDialog",
    "CutoutRectangleDialog",
    "TrojkatDialog",
    "TrapezDialog",
    "BlachyDialog",
    "DaneBlachyDialog",
    "DaneFirmyDialog",
    "ProjectDetailsDialog",
    "SettingsDialog",
]
