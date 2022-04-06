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

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtWebEngine import QtWebEngine
from vi import version, PanningWebView
from vi.ui import viui, systemtray
from vi.cache import cache
from vi.ui.styles import Styles
from vi.resources import resourcePath
from vi.cache.cache import Cache
from PyQt5.QtWidgets import QApplication, QMessageBox


def exceptHook(exceptionType, exceptionValue, tracebackObject):
    """
    Global function to catch unhandled exceptions.
    """
    try:
        logging.critical("-- Unhandled Exception --")
        logging.critical("".join(traceback.format_tb(tracebackObject)))
        # traceback.print_tb(tracebackObject)
        logging.critical("{0}: {1}".format(exceptionType, exceptionValue))
        logging.critical("-- ------------------- --")
    except Exception:
        pass


sys.excepthook = exceptHook
backGroundColor = "#c6d9ec"


class Application(QApplication):
    def __init__(self, args):
        super(Application, self).__init__(args)
        QtWebEngine.initialize()
        splash = QtWidgets.QSplashScreen(
            QtGui.QPixmap(resourcePath("vi/ui/res/logo_splash.png"))
        )
        splash.show()
        if version.SNAPSHOT:
            QMessageBox.critical(
                None, "Snapshot", "This is a snapshot release... Use as you will...."
            )

        # Set up paths
        chatLogDirectory = ""
        if len(sys.argv) > 1:
            chatLogDirectory = sys.argv[1]

        if not os.path.exists(chatLogDirectory):
            if sys.platform.startswith("darwin"):
                chatLogDirectory = os.path.join(
                    os.path.expanduser("~"), "Documents", "EVE", "logs", "Chatlogs"
                )
                if not os.path.exists(chatLogDirectory):
                    chatLogDirectory = os.path.join(
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
                chatLogDirectory = os.path.join(
                    os.path.expanduser("~"), "Documents", "EVE", "logs", "Chatlogs"
                )
            elif sys.platform.startswith("win32") or sys.platform.startswith("cygwin"):
                import ctypes.wintypes

                buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
                ctypes.windll.shell32.SHGetFolderPathW(0, 0x05, 0, 0, buf)
                documents_path = buf.value
                from os.path import expanduser

                chatLogDirectory = os.path.join(
                    documents_path, "EVE", "logs", "Chatlogs"
                )
                # Now I need to just make sure... Some old pcs could still be on XP
                if not os.path.exists(chatLogDirectory):
                    chatLogDirectory = os.path.join(
                        os.path.expanduser("~"),
                        "My Documents",
                        "EVE",
                        "logs",
                        "Chatlogs",
                    )

        # todo show select folder dialog if path is not valid
        if not os.path.exists(chatLogDirectory):
            chatLogDirectory = QtWidgets.QFileDialog.getExistingDirectory(
                None,
                caption="Select EVE Online chat  logfiles directory",
                directory=chatLogDirectory,
            )

        if not os.path.exists(chatLogDirectory):
            # None of the paths for logs exist, bailing out
            QMessageBox.critical(
                None,
                "No path to Logs",
                "No logs found at: " + chatLogDirectory,
                QMessageBox.Close,
            )
            sys.exit(1)

        # Setting local directory for cache and logging
        spyglassDir = os.path.join(
            os.path.dirname(os.path.dirname(chatLogDirectory)), "spyglass"
        )
        if not os.path.exists(spyglassDir):
            os.mkdir(spyglassDir)
        cache.Cache.PATH_TO_CACHE = os.path.join(spyglassDir, "cache-2.sqlite3")

        spyglassLogDirectory = os.path.join(spyglassDir, "logs")
        if not os.path.exists(spyglassLogDirectory):
            os.mkdir(spyglassLogDirectory)

        spyglassCache = Cache()
        logLevel = spyglassCache.getFromCache("logging_level")
        if not logLevel:
            logLevel = logging.WARN
        if version.SNAPSHOT:
            logLevel = logging.DEBUG  # For Testing
        backGroundColor = spyglassCache.getFromCache("background_color")

        if backGroundColor:
            self.setStyleSheet("background-color: %s;" % backGroundColor)
        css = Styles().getStyle()
        self.setStyleSheet(css)
        del css

        # Setup logging for console and rotated log files
        formatter = logging.Formatter(
            "%(asctime)s| %(message)s", datefmt="%m/%d %I:%M:%S"
        )
        rootLogger = logging.getLogger()
        rootLogger.setLevel(level=logLevel)

        logFilename = spyglassLogDirectory + "/output.log"

        fileHandler = RotatingFileHandler(
            maxBytes=(1048576 * 5), backupCount=7, filename=logFilename, mode="a"
        )
        fileHandler.setFormatter(formatter)
        rootLogger.addHandler(fileHandler)

        consoleHandler = StreamHandler()
        consoleHandler.setFormatter(formatter)
        rootLogger.addHandler(consoleHandler)

        logging.critical("")
        logging.critical(
            "------------------- Spyglass %s starting up -------------------",
            version.VERSION,
        )
        logging.critical("")
        logging.critical(" Looking for chat logs at: {0}".format(chatLogDirectory))
        logging.critical(
            " Cache maintained here: {0}".format(cache.Cache.PATH_TO_CACHE)
        )
        logging.critical(" Writing logs to: {0}".format(spyglassLogDirectory))
        trayIcon = systemtray.TrayIcon(self)
        trayIcon.show()

        def change_splash_text(txt):
            if len(txt):
                splash.showMessage(
                    "    {} ...".format(txt),
                    QtCore.Qt.AlignLeft,
                    QtGui.QColor(0x808000),
                )

        self.mainWindow = viui.MainWindow(
            chatLogDirectory, trayIcon, change_splash_text
        )
        self.mainWindow.show()
        self.mainWindow.raise_()


# The main application
if __name__ == "__main__":
    app = Application(sys.argv)
    sys.exit(app.exec_())
