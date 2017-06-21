#!/usr/bin/env python
###########################################################################
#  Spyglass - Visual Intel Chat Analyzer								  #
#  Copyright (C) 2017 Crypta Eve (crypta@crypta.tech)                     #
#																		  #
#  This program is free software: you can redistribute it and/or modify	  #
#  it under the terms of the GNU General Public License as published by	  #
#  the Free Software Foundation, either version 3 of the License, or	  #
#  (at your option) any later version.									  #
#																		  #
#  This program is distributed in the hope that it will be useful,		  #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of		  #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the		  #
#  GNU General Public License for more details.							  #
#																		  #
#																		  #
#  You should have received a copy of the GNU General Public License	  #
#  along with this program.	 If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

import sys
import os
import logging
import traceback

from logging.handlers import RotatingFileHandler
from logging import StreamHandler

from PyQt4 import QtGui
from vi import version, PanningWebView
from vi.ui import viui, systemtray
from vi.cache import cache
from vi.resources import resourcePath
from vi.cache.cache import Cache
from PyQt4.QtGui import QApplication, QMessageBox


def exceptHook(exceptionType, exceptionValue, tracebackObject):
    """
        Global function to catch unhandled exceptions.
    """
    try:
        logging.critical("-- Unhandled Exception --")
        logging.critical(''.join(traceback.format_tb(tracebackObject)))
        logging.critical('{0}: {1}'.format(exceptionType, exceptionValue))
        logging.critical("-- ------------------- --")
    except Exception:
        pass


sys.excepthook = exceptHook
backGroundColor = "#c6d9ec"


class Application(QApplication):
    def __init__(self, args):
        super(Application, self).__init__(args)

        splash = QtGui.QSplashScreen(QtGui.QPixmap(resourcePath("vi/ui/res/logo_splash.png")))
        splash.show()

        # Set up paths
        chatLogDirectory = ""
        if len(sys.argv) > 1:
            chatLogDirectory = sys.argv[1]

        if not os.path.exists(chatLogDirectory):
            if sys.platform.startswith("darwin"):
                chatLogDirectory = os.path.join(os.path.expanduser("~"), "Documents", "EVE", "logs", "Chatlogs")
                if not os.path.exists(chatLogDirectory):
                    chatLogDirectory = os.path.join(os.path.expanduser("~"), "Library", "Application Support",
                                                    "Eve Online",
                                                    "p_drive", "User", "My Documents", "EVE", "logs", "Chatlogs")
            elif sys.platform.startswith("linux"):
                chatLogDirectory = os.path.join(os.path.expanduser("~"), "EVE", "logs", "Chatlogs")
            elif sys.platform.startswith("win32") or sys.platform.startswith("cygwin"):
                import ctypes.wintypes
                buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
                ctypes.windll.shell32.SHGetFolderPathW(0, 5, 0, 0, buf)
                documentsPath = buf.value
                chatLogDirectory = os.path.join(documentsPath, "EVE", "logs", "Chatlogs")
        if not os.path.exists(chatLogDirectory):
            # None of the paths for logs exist, bailing out
            QMessageBox.critical(None, "No path to Logs", "No logs found at: " + chatLogDirectory, "Quit")
            sys.exit(1)

        # Setting local directory for cache and logging
        spyglassDir = os.path.join(os.path.dirname(os.path.dirname(chatLogDirectory)), "spyglass")
        if not os.path.exists(spyglassDir):
            os.mkdir(spyglassDir)
        cache.Cache.PATH_TO_CACHE = os.path.join(spyglassDir, "cache-2.sqlite3")

        vintelLogDirectory = os.path.join(spyglassDir, "logs")
        if not os.path.exists(vintelLogDirectory):
            os.mkdir(vintelLogDirectory)

        vintelCache = Cache()
        logLevel = vintelCache.getFromCache("logging_level")
        if not logLevel:
            logLevel = logging.WARN
        # logLevel = logging.INFO #For Testing
        backGroundColor = vintelCache.getFromCache("background_color")
        if backGroundColor:
            self.setStyleSheet("QWidget { background-color: %s; }" % backGroundColor)

        self.processEvents()

        # Setup logging for console and rotated log files
        formatter = logging.Formatter('%(asctime)s| %(message)s', datefmt='%m/%d %I:%M:%S')
        rootLogger = logging.getLogger()
        rootLogger.setLevel(level=logLevel)

        logFilename = vintelLogDirectory + "/output.log"
        fileHandler = RotatingFileHandler(maxBytes=(1048576 * 5), backupCount=7, filename=logFilename, mode='a')
        fileHandler.setFormatter(formatter)
        rootLogger.addHandler(fileHandler)

        consoleHandler = StreamHandler()
        consoleHandler.setFormatter(formatter)
        rootLogger.addHandler(consoleHandler)

        logging.critical("")
        logging.critical("------------------- Spyglass %s starting up -------------------", version.VERSION)
        logging.critical("")
        logging.debug("Looking for chat logs at: %s", chatLogDirectory)
        logging.debug("Cache maintained here: %s", cache.Cache.PATH_TO_CACHE)
        logging.debug("Writing logs to: %s", vintelLogDirectory)

        trayIcon = systemtray.TrayIcon(self)
        trayIcon.show()
        self.mainWindow = viui.MainWindow(chatLogDirectory, trayIcon, backGroundColor)
        self.mainWindow.show()
        self.mainWindow.raise_()
        splash.finish(self.mainWindow)


# The main application
if __name__ == "__main__":
    app = Application(sys.argv)
    sys.exit(app.exec_())
