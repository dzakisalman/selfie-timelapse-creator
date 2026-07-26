"""
Selfie Timelapse Creator — Entry Point
Python 3.11+ / PySide6
"""
from __future__ import annotations

import sys
import traceback
import logging
from pathlib import Path

# ── Setup crash logging to file ─────────────────────────────────────
_SRC = Path(__file__).parent
_LOG = _SRC.parent / "crash.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(_LOG, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("SelfieTimelapse")


def _exception_hook(exc_type, exc_value, exc_tb):
    """Global exception hook — tulis semua unhandled exception ke crash.log."""
    logger.critical("UNHANDLED EXCEPTION", exc_info=(exc_type, exc_value, exc_tb))
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = _exception_hook


# Ensure `src/` is on sys.path when running directly
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

logger.info("Starting Selfie Timelapse Creator...")
logger.info(f"Python {sys.version}")
logger.info(f"src = {_SRC}")

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt, QtMsgType, qInstallMessageHandler

from ui.main_window import MainWindow


def _qt_message_handler(mode, context, message):
    """Tangkap Qt warning/fatal messages ke crash.log."""
    if mode == QtMsgType.QtFatalMsg:
        logger.critical(f"QT FATAL: {message} (file: {context.file}, line: {context.line})")
    elif mode == QtMsgType.QtCriticalMsg:
        logger.error(f"QT CRITICAL: {message}")
    elif mode == QtMsgType.QtWarningMsg:
        logger.warning(f"QT WARNING: {message}")
    else:
        logger.debug(f"QT: {message}")


def main() -> None:
    # Enable Windows dark title bar
    if sys.platform == "win32":
        sys.argv += ["-platform", "windows:darkmode=2"]

    qInstallMessageHandler(_qt_message_handler)

    app = QApplication(sys.argv)
    app.setApplicationName("Selfie Timelapse Creator")
    app.setApplicationDisplayName("Selfie Timelapse Creator")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("SelfieTimelapse")

    # Global font
    app.setFont(QFont("Segoe UI", 10))

    # Load QSS theme
    qss_path = _SRC / "ui" / "styles" / "theme.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
        logger.info(f"Loaded theme from {qss_path}")
    else:
        logger.warning(f"theme.qss not found at {qss_path}")

    logger.info("Creating MainWindow...")
    window = MainWindow()
    window.show()
    logger.info("MainWindow shown, entering event loop")

    ret = app.exec()
    logger.info(f"Event loop exited with code {ret}")
    sys.exit(ret)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.critical("FATAL ERROR IN MAIN", exc_info=True)
        sys.exit(1)
