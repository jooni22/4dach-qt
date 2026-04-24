"""Entry point: python -m 4dach  (or  python __main__.py)"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("4Dach")
    app.setOrganizationName("SuperDach")
    app.setStyle("Fusion")

    # Import after QApplication is created so Qt widgets can be instantiated
    from ui.main_window import MainWindow  # noqa: PLC0415

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
