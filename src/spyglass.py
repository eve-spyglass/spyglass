#!/usr/bin/env python
###########################################################################
#  Spyglass - Visual Intel Chat Analyzer								  #
#  Copyright (C) 2017 Crypta Eve (crypta@crypta.tech)                     #
# 																		  #
#  This program is free software: you can redistribute it and/or modify	  #
#  it under the terms of the GNU General Public License as published by	  #
#  the Free Software Foundation, either version 3 of the License, or	  #
#  (at your option) any later version.									  #
# 																		  #
#  This program is distributed in the hope that it will be useful,		  #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of		  #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the		  #
#  GNU General Public License for more details.							  #
# 																		  #
# 																		  #
#  You should have received a copy of the GNU General Public License	  #
#  along with this program.	 If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

import sys
import os
import logging
import traceback

from logging.handlers import RotatingFileHandler
from logging import StreamHandler

from PyQt6 import QtGui, QtWidgets, QtCore
from PyQt6.QtWebEngineQuick import QtWebEngineQuick
from vi import version, PanningWebView
from vi.ui import viui, systemtray
from vi.cache import cache
from vi.ui.styles import Styles
from vi.resources import resourcePath
from vi.cache.cache import Cache
from PyQt6.QtWidgets import QApplication, QMessageBox


def except_hook(exception_type, exception_value, traceback_object):
    # pylint: disable=broad-except,logging-fstring-interpolation
    """
    Global function to catch unhandled exceptions.
    """
    try:
        logging.critical("-- Unhandled Exception --")
        logging.critical("".join(traceback.format_tb(traceback_object)))
        # traceback.print_tb(tracebackObject)
        logging.critical(f"{exception_type}: {exception_value}")
        logging.critical("-- ------------------- --")
    except Exception:
        pass


sys.excepthook = except_hook
BACKGROUND_COLOR = "#c6d9ec"


class Application(QApplication):
    def __init__(self, args):
        super(Application, self).__init__(args)
        QtWebEngineQuick.initialize()
        splash = QtWidgets.QSplashScreen(
            QtGui.QPixmap(resourcePath("vi/ui/res/logo_splash.png"))
        )
        splash.show()
        if version.SNAPSHOT:
            QMessageBox.critical(
                splash, "Snapshot", "This is a snapshot release... Use as you will...."
            )

        def change_splash_text(txt):
            if len(txt):
                splash.showMessage(
                    f"    {txt} ...",
                    QtCore.Qt.AlignmentFlag.AlignLeft,
                    QtGui.QColor(0x808000),
                )

        # Set up paths
        chat_log_directory = ""
        if len(sys.argv) > 1:
            chat_log_directory = sys.argv[1]

        if not os.path.exists(chat_log_directory):
            change_splash_text("Searching for EVE Logs")
            if sys.platform.startswith("darwin"):
                chat_log_directory = os.path.join(
                    os.path.expanduser("~"), "Documents", "EVE", "logs", "Chatlogs"
                )
                if not os.path.exists(chat_log_directory):
                    chat_log_directory = os.path.join(
                        os.path.expanduser("~"),
                        "Library",
                        "Application Support",
                        "Eve Online",
                        "p_drive",
                        "User",
                        "My Documents",
                        "EVE",
                        "logs",
                        "Chatlogs",
                    )
            elif sys.platform.startswith("linux"):
                chat_log_directory = os.path.join(
                    os.path.expanduser("~"), "Documents", "EVE", "logs", "Chatlogs"
                )
            elif sys.platform.startswith("win32") or sys.platform.startswith("cygwin"):
                import ctypes.wintypes

                buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
                ctypes.windll.shell32.SHGetFolderPathW(0, 0x05, 0, 0, buf)
                documents_path = buf.value

                chat_log_directory = os.path.join(
                    documents_path, "EVE", "logs", "Chatlogs"
                )
                # Now I need to just make sure... Some old pcs could still be on XP
                if not os.path.exists(chat_log_directory):
                    chat_log_directory = os.path.join(
                        os.path.expanduser("~"),
                        "My Documents",
                        "EVE",
                        "logs",
                        "Chatlogs",
                    )

        if not os.path.exists(chat_log_directory):
            chat_log_directory = QtWidgets.QFileDialog.getExistingDirectory(
                None,
                caption="Select EVE Online chat  logfiles directory",
                directory=chat_log_directory,
            )

        if not os.path.exists(chat_log_directory):
            # None of the paths for logs exist, bailing out
            QMessageBox.critical(
                splash,
                "No path to Logs",
                "No logs found at: " + chat_log_directory,
                QMessageBox.Close,
            )
            sys.exit(1)

        # Setting local directory for cache and logging
        change_splash_text("Setting Spyglass Directories")
        spyglass_dir = os.path.join(
            os.path.dirname(os.path.dirname(chat_log_directory)), "spyglass"
        )
        if not os.path.exists(spyglass_dir):
            os.mkdir(spyglass_dir)
        cache.Cache.PATH_TO_CACHE = os.path.join(spyglass_dir, "cache-2.sqlite3")

        spyglass_log_directory = os.path.join(spyglass_dir, "logs")
        if not os.path.exists(spyglass_log_directory):
            os.mkdir(spyglass_log_directory)

        change_splash_text("Connecting to Cache")
        spyglass_cache = Cache()
        log_level = spyglass_cache.getFromCache("logging_level")
        if not log_level:
            log_level = logging.WARN
        if version.SNAPSHOT:
            log_level = logging.DEBUG  # For Testing
        BACKGROUND_COLOR = spyglass_cache.getFromCache("background_color")

        if BACKGROUND_COLOR:
            self.setStyleSheet(f"background-color: {BACKGROUND_COLOR};")
        css = Styles().getStyle()
        self.setStyleSheet(css)
        del css

        # Setup logging for console and rotated log files
        formatter = logging.Formatter(
            "%(asctime)s| %(message)s", datefmt="%m/%d %I:%M:%S"
        )
        root_logger = logging.getLogger()
        root_logger.setLevel(level=log_level)

        log_filename = spyglass_log_directory + "/output.log"

        file_handler = RotatingFileHandler(
            maxBytes=(1048576 * 5), backupCount=7, filename=log_filename, mode="a"
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        console_handler = StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        logging.critical("")
        logging.critical(
            "------------------- Spyglass %s starting up -------------------",
            version.VERSION,
        )
        logging.critical("")
        logging.critical(" Looking for chat logs at: %s", chat_log_directory)
        logging.critical(
            " Cache maintained here: %s", cache.Cache.PATH_TO_CACHE
        )
        logging.critical(" Writing logs to: %s", spyglass_log_directory)
        tray_icon = systemtray.TrayIcon(self)
        tray_icon.show()

        self.main_window = viui.MainWindow(
            chat_log_directory, tray_icon, change_splash_text
        )
        self.main_window.show()
        self.main_window.raise_()


# The main application
if __name__ == "__main__":
    app = Application(sys.argv)
    sys.exit(app.exec())
