"""SmartScan entry point."""

from __future__ import annotations

import sys
import traceback


def main() -> int:
    # Keep the Windows taskbar icon correct for a PyInstaller build.
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SmartScan.App")
        except Exception:  # noqa: BLE001 - purely cosmetic
            pass

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QApplication, QMessageBox

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("SmartScan")
    app.setApplicationDisplayName("SmartScan")
    app.setOrganizationName("SmartScan")
    app.setApplicationVersion("1.1.1")

    from app.ui.theme import apply_theme

    apply_theme(app)

    from app.core.settings import load_settings
    from app.ui.main_window import MainWindow

    try:
        window = MainWindow(load_settings())
        window.show()
        # Files passed on the command line (or via "Open with") are loaded too.
        args = [a for a in sys.argv[1:] if not a.startswith("-")]
        if args:
            from pathlib import Path

            paths = [Path(a) for a in args if Path(a).is_file()]
            if paths:
                window.load_paths(paths)
    except Exception:  # noqa: BLE001 - last-resort crash dialog
        QMessageBox.critical(
            None, "SmartScan could not start", traceback.format_exc(limit=8)
        )
        return 1

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
