"""Entry point: python -m 4dach  (or  python __main__.py)"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app_assets import load_app_icon


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("4Dach")
    app.setOrganizationName("SuperDach")
    app.setStyle("Fusion")
    app_icon = load_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    # Import after QApplication is created so Qt widgets can be instantiated
    from ui.main_window import MainWindow  # noqa: PLC0415

    window = MainWindow()
    if not app_icon.isNull():
        window.setWindowIcon(app_icon)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
