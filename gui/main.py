#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QIcon
except ImportError:
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QIcon
    except ImportError:
        print("[ERR] Neither PyQt6 nor PySide6 could be imported.")
        print("      Please install PyQt6: sudo pacman -S python-pyqt6 (or pip install PyQt6)")
        sys.exit(1)

from gui.app.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("davinci-kit")
    app.setOrganizationName("resolve-kit")
    app.setDesktopFileName("davinci-kit")

    # Set Application Window Dock Icon
    our_icon = PROJECT_ROOT / "gui" / "resources" / "davinci-kit.svg"
    icon_path = str(our_icon) if our_icon.exists() else "/opt/resolve/graphics/DV_Resolve.png"
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)

    # Load QSS stylesheet
    qss_path = PROJECT_ROOT / "gui" / "style.qss"
    if qss_path.exists():
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                stylesheet = f.read().replace("__CHECK_SVG__", str(PROJECT_ROOT / "gui" / "resources" / "check.svg"))
                app.setStyleSheet(stylesheet)
        except Exception as e:
            print(f"[WARN] Failed to load QSS stylesheet: {e}")

    window = MainWindow()
    window.setWindowIcon(QIcon(icon_path))
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
