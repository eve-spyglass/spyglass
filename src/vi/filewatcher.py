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

import os
import stat
import time
import logging

from PyQt5 import QtCore

# from PyQt5.QtCore import SIGNAL
from PyQt5.QtCore import pyqtSignal

"""
There is a problem with the QFIleWatcher on Windows and the log
files from EVE.
The first implementation (now FileWatcher_orig) works fine on Linux, but
on Windows it seems ther is something buffered. Only a file-operation on
the watched directory another event there, which tirggers the OS to
reread the files informations, trigger the QFileWatcher.
So here is a workaround implementation.
We use here also a QFileWatcher, only to the directory. It will notify it
if a new file was created. We watch only the newest (last 24h), not all!
"""

DEFAULT_MAX_AGE = 60 * 60 * 24


class FileWatcher(QtCore.QThread):

    file_change = pyqtSignal(object,object)

    def __init__(self, path, maxAge=DEFAULT_MAX_AGE):
        QtCore.QThread.__init__(self)
        self.path = path
        self.maxAge = maxAge
        self.files = {}
        self.updateWatchedFiles()
        self.qtfw = QtCore.QFileSystemWatcher()
        self.qtfw.directoryChanged.connect(self.directoryChanged)
        self.qtfw.addPath(path)
        self.paused = True
        self.active = True

    def directoryChanged(self):
        self.updateWatchedFiles()

    def run(self):
        while True:
            time.sleep(0.5)
            if not self.active:
                return
            if self.paused:
                continue
            for path, modified in self.files.items():
                pathStat = os.stat(path)
                if not stat.S_ISREG(pathStat.st_mode):
                    continue
                if modified < pathStat.st_size:
                    self.file_change.emit(path, True)
                self.files[path] = pathStat.st_size

    def quit(self):
        self.active = False
        QtCore.QThread.quit(self)

    def updateWatchedFiles(self):
        # Reading all files from the directory
        fullPath = None
        now = time.time()
        path = self.path
        filesInDir = {}
        for f in os.listdir(path):
            try:
                fullPath = os.path.join(path, f)
                pathStat = os.stat(fullPath)
                if not stat.S_ISREG(pathStat.st_mode):
                    continue
                if self.maxAge and ((now - pathStat.st_mtime) > self.maxAge):
                    continue
                filesInDir[fullPath] = self.files.get(fullPath, 0)
            except:
                pass
        self.files = filesInDir
