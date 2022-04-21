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

import os
import datetime
import sys
import time
import requests
import webbrowser

import vi.version
import logging
from PyQt6.QtGui import *
from PyQt6 import QtGui, QtCore, QtWidgets, uic

from PyQt6.QtCore import QPoint, QPointF, QByteArray, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QMessageBox, QStyleOption, QStyle, QFileDialog
from vi import evegate
from vi import dotlan, filewatcher
from vi import states
from vi.cache.cache import Cache
from vi.resources import resourcePath, resourcePathExists
from vi.soundmanager import SoundManager
from vi.threads import AvatarFindThread, MapStatisticsThread
from vi.ui.systemtray import TrayContextMenu
from vi.ui.styles import Styles
from vi.chatparser.chatparser import ChatParser, Message
from PyQt6.QtGui import QAction, QActionGroup


# Timer intervals
MAP_UPDATE_INTERVAL_MSECS = 1000
CLIPBOARD_CHECK_INTERVAL_MSECS = 4 * 1000

DEFAULT_ROOM_MANES = ["Scald Intel", "FI.RE Intel"]


class MainWindow(QtWidgets.QMainWindow):

    chat_message_added = pyqtSignal(object, object)
    avatar_loaded = pyqtSignal(object, object)

    def __init__(self, pathToLogs, trayIcon, update_splash=None):
        def update_splash_window_info(string):
            if update_splash:
                update_splash(string)

        QtWidgets.QMainWindow.__init__(self)
        update_splash_window_info("Creating local Cache")
        self.cache = Cache()

        update_splash_window_info("Loading MainWindow")
        uic.loadUi(resourcePath(os.path.join("vi", "ui", "MainWindow.ui")), self)
        self.setWindowTitle(
            "Spyglass "
            + vi.version.VERSION
            + "{dev}".format(dev="-SNAPSHOT" if vi.version.SNAPSHOT else "")
        )
        self.updateAvail.hide()

        update_splash_window_info("Setting up UI")
        self.taskbarIconQuiescent = QtGui.QIcon(
            resourcePath(os.path.join("vi", "ui", "res", "logo_small.png"))
        )
        self.taskbarIconWorking = QtGui.QIcon(
            resourcePath(os.path.join("vi", "ui", "res", "logo_small_green.png"))
        )
        self.setWindowIcon(self.taskbarIconQuiescent)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.pathToLogs = pathToLogs
        self.currContent = None
        self.mapTimer = QtCore.QTimer(self)
        self.mapTimer.timeout.connect(self.updateMapView)
        self.statisticTimer = QtCore.QTimer(self)
        self.clipboardTimer = QtCore.QTimer(self)
        self.oldClipboardContent = ""
        self.trayIcon = trayIcon
        self.trayIcon.activated.connect(self.systemTrayActivated)
        self.clipboard = QtWidgets.QApplication.clipboard()
        self.clipboard.clear(mode=self.clipboard.Mode.Clipboard)
        self.alarmDistance = 0
        self.lastStatisticsUpdate = 0
        self.chatEntries = []
        self.frameButton.setVisible(False)
        self.scanIntelForKosRequestsEnabled = False
        self.initialMapPosition = None
        self.mapPositionsDict = {}
        self.invertWheel = True
        self.autoRescanIntelEnabled = Cache().getFromCache("changeAutoRescanIntel")

        # Load user's toon names
        update_splash_window_info("Setting up User Settings")
        self.knownPlayerNames = Cache().getFromCache("known_player_names")
        if self.knownPlayerNames:
            self.knownPlayerNames = set(self.knownPlayerNames.split(","))
        else:
            self.knownPlayerNames = set()
            diagText = "Spyglass scans EVE system logs and remembers your characters as they change systems.\n\nSome features (clipboard KOS checking, alarms, etc.) may not work until your character(s) have been registered. Change systems, with each character you want to monitor, while Spyglass is running to remedy this."
            QMessageBox.warning(
                self,
                "Known Characters not Found",
                diagText,
                QMessageBox.StandardButton.Ok,
            )

        if self.invertWheel is None:
            self.invertWheel = False
        self.actionInvertMouseWheel.triggered.connect(self.wheelDirChanged)
        self.actionInvertMouseWheel.setChecked(self.invertWheel)

        # Set up user's intel rooms
        roomnames = Cache().getFromCache("room_names")
        if roomnames:
            roomnames = roomnames.split(",")
        else:
            roomnames = DEFAULT_ROOM_MANES
            Cache().putIntoCache(
                "room_names", ",".join(roomnames), 60 * 60 * 24 * 365 * 5
            )
        self.roomnames = roomnames

        # Disable the sound UI if sound is not available
        if not SoundManager().soundAvailable:
            self.changeSound(disable=True)
        else:
            self.changeSound()

        # Set up Transparency menu - fill in opacity values and make connections
        self.opacityGroup = QActionGroup(self.menu)
        for i in (100, 80, 60, 40, 20):
            action = QAction("Opacity {0}%".format(i), None, checkable=True)
            action.setChecked(i == 100)
            action.opacity = float(i) / 100.0
            action.triggered.connect(self.changeOpacity)
            self.opacityGroup.addAction(action)
            self.menuTransparency.addAction(action)
        self.intelTimeGroup = QActionGroup(self.menu)
        self.intelTimeGroup.intelTime = 20
        for i in (10, 20, 40, 60):
            action = QAction("Past {0}min".format(i), None, checkable=True)
            action.setChecked(i == self.intelTimeGroup.intelTime)
            action.intelTime = i
            action.triggered.connect(self.changeIntelTime)
            self.intelTimeGroup.addAction(action)
            self.menuTime.addAction(action)

        # Set up Theme menu - fill in list of themes and add connections
        self.themeGroup = QActionGroup(self.menu)
        styles = Styles()
        for theme in styles.getStyles():
            action = QAction(theme, None, checkable=True)
            action.theme = theme
            if action.theme == "default":
                action.setChecked(True)
            logging.info("Adding theme {}".format(theme))
            action.triggered.connect(self.changeTheme)
            self.themeGroup.addAction(action)
            self.menuTheme.addAction(action)
        styles = None

        update_splash_window_info("Setting up ChatParser")
        self.chatparser = ChatParser(
            self.pathToLogs, self.roomnames, None, self.intelTimeGroup.intelTime
        )
        self.wireUpUIConnections()
        self.recallCachedSettings()
        self.setupThreads()
        self.startStatisticTimer()

        initialTheme = Cache().getFromCache("theme")
        if initialTheme:
            self.changeTheme(initialTheme)
        else:
            self.setupMap(True, callback=update_splash_window_info)
        update_splash_window_info("Checking for Updates")
        update_avail = evegate.checkSpyglassVersionUpdate()
        if update_avail[0]:
            self.updateAvail.show()
            self.updateAvail.setText(update_avail[1])

            def openDownloadLink():
                webbrowser.open_new(evegate.getSpyglassUpdateLink())
                self.updateAvail.hide()
                self.updateAvail.disconnect()

            self.updateAvail.clicked.connect(openDownloadLink)

        else:
            self.updateAvail.hide()
            logging.info("no update available: %s", update_avail[1])
        update_splash_window_info("MainWindow done!")

    def wheelDirChanged(self, checked):
        self.invertWheel = checked
        if self.invertWheel:
            self.mapView.wheel_dir = -1.0
        else:
            self.mapView.wheel_dir = 1.0
        self.actionInvertMouseWheel.setChecked(self.invertWheel)

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(
            QStyle.PrimitiveElement.PE_Widget, opt, painter, self
        )

    def recallCachedSettings(self):
        try:
            Cache().recallAndApplySettings(self, "settings")
        except Exception as e:
            logging.error(e)
            # todo: add a button to delete the cache / DB
            self.trayIcon.showMessage(
                "Settings error",
                "Something went wrong loading saved state:\n {0}".format(str(e)),
                1,
            )

    def wireUpUIConnections(self):
        self.clipboard.dataChanged.connect(self.clipboardChanged)
        # self.autoScanIntelAction.triggered.connect(self.changeAutoScanIntel)
        self.zoomInButton.clicked.connect(self.zoomMapIn)
        self.zoomOutButton.clicked.connect(self.zoomMapOut)
        self.statisticsButton.clicked.connect(self.changeStatisticsVisibility)
        self.jumpbridgesButton.clicked.connect(self.changeJumpbridgesVisibility)
        self.chatLargeButton.clicked.connect(self.chatLarger)
        self.chatSmallButton.clicked.connect(self.chatSmaller)
        self.infoAction.triggered.connect(self.showInfo)
        self.showChatAvatarsAction.triggered.connect(self.changeShowAvatars)
        self.alwaysOnTopAction.triggered.connect(self.changeAlwaysOnTop)
        self.chooseChatRoomsAction.triggered.connect(self.showChatroomChooser)
        self.catchRegionAction.triggered.connect(
            lambda: self.handleRegionMenuItemSelected(self.catchRegionAction)
        )
        self.providenceRegionAction.triggered.connect(
            lambda: self.handleRegionMenuItemSelected(self.providenceRegionAction)
        )
        self.queriousRegionAction.triggered.connect(
            lambda: self.handleRegionMenuItemSelected(self.queriousRegionAction)
        )
        self.providenceCatchRegionAction.triggered.connect(
            lambda: self.handleRegionMenuItemSelected(self.providenceCatchRegionAction)
        )
        self.providenceCatchCompactRegionAction.triggered.connect(
            lambda: self.handleRegionMenuItemSelected(
                self.providenceCatchCompactRegionAction
            )
        )
        self.chooseRegionAction.triggered.connect(self.showRegionChooser)
        self.showChatAction.triggered.connect(self.changeChatVisibility)
        self.soundSetupAction.triggered.connect(self.showSoundSetup)
        self.activateSoundAction.triggered.connect(self.changeSound)
        self.useSpokenNotificationsAction.triggered.connect(
            self.changeUseSpokenNotifications
        )
        self.trayIcon.alarm_distance.connect(self.changeAlarmDistance)
        self.framelessWindowAction.triggered.connect(self.changeFrameless)
        self.trayIcon.change_frameless.connect(self.changeFrameless)
        self.frameButton.clicked.connect(self.changeFrameless)
        self.quitAction.triggered.connect(self.close)
        self.trayIcon.quit_signal.connect(self.close)
        self.jumpbridgeDataAction.triggered.connect(self.showJumbridgeChooser)
        self.rescanNowAction.triggered.connect(self.rescanIntel)
        self.clearIntelAction.triggered.connect(self.clearIntelChat)
        self.autoRescanAction.triggered.connect(self.changeAutoRescanIntel)
        self.mapView.webViewResized.connect(self.fixupScrollBars)
        self.mapView.customContextMenuRequested.connect(self.showContextMenu)

        def mapviewScrolled(scrolled):
            if scrolled:
                self.mapTimer.stop()
            else:
                self.mapTimer.start(MAP_UPDATE_INTERVAL_MSECS)

        self.mapView.webViewScrolled.connect(mapviewScrolled)

        def updateX(x):
            pos = self.mapView.scrollPosition()
            pos.setX(x)
            self.mapView.setScrollPosition(pos)

        self.mapHorzScrollBar.valueChanged.connect(updateX)

        def updateY(y):
            pos = self.mapView.scrollPosition()
            pos.setY(y)
            self.mapView.setScrollPosition(pos)

        self.mapVertScrollBar.valueChanged.connect(updateY)

        def hoveCheck(pos: QPoint) -> bool:
            """returns true if the mouse is above a system, else false"""
            for system in self.dotlan.systems.items():
                val = system[1].mapCoordinates
                rc = QtCore.QRectF(val["x"], val["y"], val["width"], val["height"])
                if rc.contains(pos):
                    return True
            return False

        self.mapView.hoveCheck = hoveCheck

        def doubleClicked(pos: QPoint):
            for system in self.dotlan.systems.items():
                val = system[1].mapCoordinates
                rc = QtCore.QRectF(val["x"], val["y"], val["width"], val["height"])
                if rc.contains(pos):
                    self.mapLinkClicked(QtCore.QUrl("map_link/{0}".format(system[0])))

        self.mapView.doubleClicked = doubleClicked

    def setupThreads(self):
        # Set up threads and their connections
        self.avatarFindThread = AvatarFindThread()
        self.avatarFindThread.avatar_update.connect(self.updateAvatarOnChatEntry)
        self.avatarFindThread.start()

        self.filewatcherThread = filewatcher.FileWatcher(self.pathToLogs)
        self.filewatcherThread.file_change.connect(self.logFileChanged)
        self.filewatcherThread.start()

        self.statisticsThread = MapStatisticsThread()
        self.statisticsThread.statistic_data_update.connect(self.updateStatisticsOnMap)
        self.statisticsThread.start()

    def terminateThreads(self):
        # Stop the threads
        try:
            SoundManager().quit()
            SoundManager().wait()
            self.avatarFindThread.quit()
            self.avatarFindThread.wait()
            self.filewatcherThread.quit()
            self.filewatcherThread.wait()
            self.statisticsThread.quit()
            self.statisticsThread.wait()
            self.mapTimer.stop()
        except Exception as ex:
            logging.critical(ex)
            pass

    def changeRegionFromCtxMenu(self, checked):
        selected_system = self.trayIcon.contextMenu().currentSystem
        if selected_system is None:
            return
        self.changeRegionBySystemID(selected_system[1].systemId)

    def focusMapOnSystem(self, system_id):
        """sets the system defind by the id to the focus of the map"""
        if system_id is None:
            return
        system_name = evegate.idsToNames([str(system_id)])[system_id]
        if system_name in self.systems.keys():
            view_center = self.mapView.size() / 2
            pt_system = QPointF(
                self.systems[system_name].mapCoordinates["center_x"] * self.mapView.zoom
                - view_center.width(),
                self.systems[system_name].mapCoordinates["center_y"] * self.mapView.zoom
                - view_center.height(),
            )
            self.mapView.setScrollPosition(pt_system)

    def changeRegionBySystemID(self, system_id):
        """change to the region of the system with the given id, the intel will be rescanned
        and the cache region_name will be updated
        """
        if system_id is None:
            return
        selected_system = evegate.getSolarSystemInformation(system_id)
        selected_constellation = evegate.getConstellationInformation(
            selected_system["constellation_id"]
        )
        selected_region = selected_constellation["region_id"]
        selected_region_name = evegate.idsToNames([selected_region])[selected_region]
        selected_region_name = dotlan.convertRegionName(selected_region_name)
        Cache().putIntoCache("region_name", selected_region_name, 60 * 60 * 24 * 365)
        self.rescanIntel()
        self.updateMapView()
        self.focusMapOnSystem(system_id)

    def prepareContextMenu(self):
        # Menus - only once
        regionName = Cache().getFromCache("region_name")
        logging.info("Initializing contextual menus")

        # Add a contextual menu to the mapView
        def mapContextMenuEvent(event):
            # if QApplication.activeWindow() or QApplication.focusWidget():
            self.trayIcon.contextMenu().updateMenu(None)
            self.trayIcon.contextMenu().exec(
                self.mapToGlobal(QPoint(event.x(), event.y()))
            )

        self.mapView.contextMenuEvent = mapContextMenuEvent
        self.mapView.contextMenu = self.trayIcon.contextMenu()

        # Also set up our app menus
        if not regionName:
            self.providenceCatchRegionAction.setChecked(True)
        elif regionName.startswith("Providencecatch"):
            self.providenceCatchRegionAction.setChecked(True)
        elif regionName.startswith("Catch"):
            self.catchRegionAction.setChecked(True)
        elif regionName.startswith("Providence"):
            self.providenceRegionAction.setChecked(True)
        elif regionName.startswith("Querious"):
            self.queriousRegionAction.setChecked(True)
        else:
            self.chooseRegionAction.setChecked(True)

        self.trayIcon.contextMenu().hasJumpGate = lambda name: Cache().hasJumpGate(name)

    def setupMap(self, initialize=False, callback=None):
        self.filewatcherThread.paused = True
        regionName = Cache().getFromCache("region_name")
        if not regionName:
            regionName = "Providence"
        logging.info("Finding map file {}".format(regionName))
        svg = None
        try:
            res_file_name = os.path.join(
                "vi", "ui", "res", "mapdata", "{0}.svg".format(regionName)
            )
            if resourcePathExists(res_file_name):
                with open(resourcePath(res_file_name)) as svgFile:
                    svg = svgFile.read()
        except Exception as e:
            pass

        try:
            self.dotlan = dotlan.Map(
                regionName, svg, setJumpMapsVisible=self.jumpbridgesButton.isChecked()
            )
            # todo:fix static updates
            # setSatisticsVisible=self.statisticsButton.isChecked()

            self.dotlan._applySystemStatistic(evegate.getPlayerSovereignty(True, callback=callback))
        except dotlan.DotlanException as e:
            logging.error(e)
            QMessageBox.critical(None, "Error getting map", str(e), QMessageBox.Close)
            sys.exit(1)

        if self.dotlan.outdatedCacheError:
            e = self.dotlan.outdatedCacheError
            diagText = (
                "Something went wrong getting map data. Proceeding with older cached data. "
                "Check for a newer version and inform the maintainer.\n\nError: {0} {1}".format(
                    type(e), str(e)
                )
            )
            logging.warning(diagText)
            QMessageBox.warning(None, "Using map from cache", diagText, QMessageBox.Ok)

        # Load the jumpbridges
        logging.debug("Load jump bridges")
        self.setJumpbridges(Cache().getFromCache("jumpbridge_url"))
        self.systems = self.dotlan.systems
        logging.debug("Creating chat parser")
        self.chatparser.systems = self.systems
        self.chatparser = ChatParser(
            self.pathToLogs, self.roomnames, self.systems, self.intelTimeGroup.intelTime
        )

        # Update the new map view, then clear old statistics from the map and request new
        logging.debug("Updating the map")
        self.updateMapView()
        self.setInitialMapPositionForRegion(regionName)
        self.mapTimer.start(MAP_UPDATE_INTERVAL_MSECS)
        # Allow the file watcher to run now that all else is set up
        self.filewatcherThread.paused = False
        logging.debug("Map setup complete")

    def rescanIntel(self):
        logging.info("Intel ReScan begun")
        self.clearIntelChat()

        now = datetime.datetime.now()
        for file in os.listdir(self.pathToLogs):
            if file.endswith(".txt"):
                filePath = self.pathToLogs + str(os.sep) + file
                roomname = file[:-31]

                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(filePath))
                delta = now - mtime
                if (
                    delta.total_seconds() < (60 * self.chatparser.intelTime)
                    and delta.total_seconds() > 0
                ):
                    if roomname in self.roomnames:
                        logging.info("Reading log {}".format(roomname))
                        self.logFileChanged(filePath, rescan=True)
                        # self.logFileChanged(filePath, rescan=True)
        logging.info("Intel ReScan done")
        self.updateMapView()

    def startClipboardTimer(self):
        """
        Start a timer to check the keyboard for changes and kos check them,
        first initializing the content so we dont kos check from random content
        """
        self.oldClipboardContent = tuple(str(self.clipboard.text()))
        self.clipboardTimer.timeout.connect(self.clipboardChanged)
        self.clipboardTimer.start(CLIPBOARD_CHECK_INTERVAL_MSECS)

    def stopClipboardTimer(self):
        if self.clipboardTimer:
            self.clipboardTimer.disconnect()
            self.clipboardTimer.stop()

    def startStatisticTimer(self):
        self.statisticTimer.timeout.connect(self.statisticsThread.requestStatistics)
        self.statisticsThread.requestStatistics()
        self.statisticTimer.start(60000)

    def stopStatisticTimer(self):
        if self.statisticTimer:
            self.statisticTimer.disconnect()
            self.statisticTimer.stop()

    def closeEvent(self, event):
        """
        Persisting things to the cache before closing the window
        """
        # Known player names
        if self.knownPlayerNames:
            value = ",".join(self.knownPlayerNames)
            Cache().putIntoCache("known_player_names", value, 60 * 60 * 24 * 30)

        # Program state to cache (to read it on next startup)
        settings = (
            (None, "restoreGeometry", str(self.saveGeometry()), True),
            (None, "restoreState", str(self.saveState()), True),
            ("splitter", "restoreGeometry", str(self.splitter.saveGeometry()), True),
            ("splitter", "restoreState", str(self.splitter.saveState()), True),
            ("mapView", "setZoomFactor", self.mapView.zoomFactor()),
            (None, "changeChatFontSize", ChatEntryWidget.TEXT_SIZE),
            (None, "setOpacity", self.opacityGroup.checkedAction().opacity),
            (None, "changeAlwaysOnTop", self.alwaysOnTopAction.isChecked()),
            (None, "changeShowAvatars", self.showChatAvatarsAction.isChecked()),
            (None, "changeAlarmDistance", self.alarmDistance),
            (None, "changeSound", self.activateSoundAction.isChecked()),
            (None, "changeChatVisibility", self.showChatAction.isChecked()),
            (None, "loadInitialMapPositions", self.mapPositionsDict),
            (None, "setSoundVolume", SoundManager().soundVolume),
            (None, "changeFrameless", self.framelessWindowAction.isChecked()),
            (
                None,
                "changeUseSpokenNotifications",
                self.useSpokenNotificationsAction.isChecked(),
            ),
            (None, "changeAutoScanIntel", self.scanIntelForKosRequestsEnabled),
            (None, "changeAutoRescanIntel", self.autoRescanIntelEnabled),
            (None, "wheelDirChanged", self.invertWheel),
        )

        Cache().putIntoCache("version", str(vi.version.VERSION), 60 * 60 * 24 * 30)
        Cache().putIntoCache("settings", str(settings), 60 * 60 * 24 * 30)
        self.terminateThreads()
        self.trayIcon.hide()
        event.accept()
        QtCore.QCoreApplication.quit()

    def notifyNewerVersion(self, newestVersion):
        self.trayIcon.showMessage(
            "Newer Version",
            ("An update is available for Spyglass.\n www.crypta.tech"),
            1,
        )

    def changeChatVisibility(self, newValue=None):
        if newValue is None:
            newValue = self.showChatAction.isChecked()
        self.showChatAction.setChecked(newValue)
        self.chatbox.setVisible(newValue)

    def changeAutoScanIntel(self, newValue=None):
        if newValue is None:
            newValue = self.autoScanIntelAction.isChecked()
        self.autoScanIntelAction.setChecked(newValue)
        self.autoRescanIntelEnabled = newValue

    def changeAutoRescanIntel(self, newValue=None):
        if newValue is None:
            newValue = self.autoRescanAction.isChecked()
        self.autoRescanAction.setChecked(newValue)
        self.autoRescanIntelEnabled = newValue

    def changeUseSpokenNotifications(self, newValue=None):
        if SoundManager().platformSupportsSpeech():
            if newValue is None:
                newValue = self.useSpokenNotificationsAction.isChecked()
            self.useSpokenNotificationsAction.setChecked(newValue)
            SoundManager().setUseSpokenNotifications(newValue)
        else:
            self.useSpokenNotificationsAction.setChecked(False)
            self.useSpokenNotificationsAction.setEnabled(False)

    def changeIntelTime(self):
        action = self.intelTimeGroup.checkedAction()
        self.intelTimeGroup.intelTime = action.intelTime
        self.chatparser.intelTime = action.intelTime
        self.timeInfo.setText(
            "All Intel( past{} minutes)".format(self.chatparser.intelTime)
        )
        self.rescanIntel()

    def setOpacity(self, newValue=None):
        if newValue:
            for action in self.opacityGroup.actions():
                action.setChecked(action.opacity == newValue)
        action = self.opacityGroup.checkedAction()
        self.setWindowOpacity(action.opacity)

    def changeOpacity(self, newValue=None):
        action = self.opacityGroup.checkedAction()
        self.setWindowOpacity(action.opacity)

    def changeTheme(self, newTheme=None):
        logging.info("change theme")
        if newTheme is not None:
            for action in self.themeGroup.actions():
                if action.theme == newTheme:
                    action.setChecked(True)
        action = self.themeGroup.checkedAction()
        styles = Styles()
        styles.setStyle(action.theme)
        theme = styles.getStyle()
        self.setStyleSheet(theme)
        self.trayIcon.contextMenu().setStyleSheet(theme)
        logging.info("Setting new theme: {}".format(action.theme))
        Cache().putIntoCache("theme", action.theme, 60 * 60 * 24 * 365)
        self.prepareContextMenu()
        if self.autoRescanIntelEnabled:
            self.rescanIntel()  # calls setupMap
        else:
            self.clearIntelChat()  # calls setupMap

    def changeSound(self, newValue=None, disable=False):
        if disable:
            self.activateSoundAction.setChecked(False)
            self.activateSoundAction.setEnabled(False)
            self.soundSetupAction.setEnabled(False)
            # self.soundButton.setEnabled(False)
            QMessageBox.warning(
                None,
                "Sound disabled",
                "The lib 'pyglet' which is used to play sounds cannot be found, "
                "so the soundsystem is disabled.\nIf you want sound, please install the 'pyglet' library. This warning will not be shown again.",
                QMessageBox.Ok,
            )
        else:
            if newValue is None:
                newValue = self.activateSoundAction.isChecked()
            self.activateSoundAction.setChecked(newValue)
            SoundManager().soundActive = newValue

    def changeAlwaysOnTop(self, newValue=None):
        if newValue is None:
            newValue = self.alwaysOnTopAction.isChecked()
        self.hide()
        self.alwaysOnTopAction.setChecked(newValue)
        if newValue:
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & (~QtCore.Qt.WindowType.WindowStaysOnTopHint))
        self.show()

    def changeFrameless(self, newValue=None):
        if newValue is None:
            newValue = not self.frameButton.isVisible()
        self.hide()
        if newValue:
            self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
            self.changeAlwaysOnTop(True)
        else:
            self.setWindowFlags(self.windowFlags() & (~QtCore.Qt.WindowType.FramelessWindowHint))
        self.menubar.setVisible(not newValue)
        self.frameButton.setVisible(newValue)
        self.framelessWindowAction.setChecked(newValue)

        for cm in TrayContextMenu.instances:
            cm.framelessCheck.setChecked(newValue)
        self.show()

    def changeShowAvatars(self, newValue=None):
        if newValue is None:
            newValue = self.showChatAvatarsAction.isChecked()
        self.showChatAvatarsAction.setChecked(newValue)
        ChatEntryWidget.SHOW_AVATAR = newValue
        for entry in self.chatEntries:
            entry.avatarLabel.setVisible(newValue)

    def changeChatFontSize(self, newSize):
        if newSize:
            for entry in self.chatEntries:
                entry.changeFontSize(newSize)
            ChatEntryWidget.TEXT_SIZE = newSize

    def chatSmaller(self):
        newSize = ChatEntryWidget.TEXT_SIZE - 1
        self.changeChatFontSize(newSize)

    def chatLarger(self):
        newSize = ChatEntryWidget.TEXT_SIZE + 1
        self.changeChatFontSize(newSize)

    def changeAlarmDistance(self, distance):
        self.alarmDistance = distance
        for cm in TrayContextMenu.instances:
            for action in cm.distanceGroup.actions():
                if action.alarmDistance == distance:
                    action.setChecked(True)
        self.trayIcon.alarmDistance = distance

    def changeJumpbridgesVisibility(self):
        newValue = self.dotlan.changeJumpbridgesVisibility()
        self.jumpbridgesButton.setChecked(newValue)
        self.updateMapView()

    def changeStatisticsVisibility(self):
        newValue = self.dotlan.changeStatisticsVisibility()
        self.statisticsButton.setChecked(newValue)
        self.statisticsThread.requestStatistics()

    def clipboardChanged(self, mode=0):
        content = str(self.clipboard.text())
        if content != self.oldClipboardContent:
            parts = content.strip().split()
            if len(parts) > 2 and parts[1] == "»":
                Cache().putJumpGate(src=parts[0], dst=parts[2])
                self.dotlan.setJumpbridges(Cache().getJumpGates())
            self.oldClipboardContent = content

    def mapLinkClicked(self, url: QtCore.QUrl):
        systemName = str(url.path().split("/")[-1]).upper()
        if str(systemName) in self.systems.keys():
            system = self.systems[str(systemName)]
            sc = SystemChat(
                self, SystemChat.SYSTEM, system, self.chatEntries, self.knownPlayerNames
            )
            self.chat_message_added.connect(sc.addChatEntry)
            self.avatar_loaded.connect(sc.newAvatarAvailable)
            sc.location_set.connect(self.setLocation)
            sc.repaint_needed.connect(self.updateMapView)
            sc.show()

    def markSystemOnMap(self, system_name: str):
        if system_name in self.systems.keys():
            self.dotlan.systems[str(system_name)].mark()
            self.updateMapView()
            self.focusMapOnSystem(self.systems[str(system_name)].systemId)

    def setLocation(self, char, system_name: str):
        for system in self.systems.values():
            system.removeLocatedCharacter(char)

        if not system_name == "?" and system_name in self.systems.keys():
            self.systems[system_name].addLocatedCharacter(char)
            self.updateMapView()

    def updateMapView(self):
        try:
            self.dotlan.setIncursionSystems(evegate.getIncursionSystemsIds())
            self.dotlan.setCampaignsSystems(evegate.getCampaignsSystemsIds())
        except:
            pass

        if self.currContent != self.dotlan.svg:
            self.mapTimer.stop()
            if self.mapView.setContent(
                QByteArray(self.dotlan.svg.encode("utf-8")), "text/html"
            ):
                self.currContent = self.dotlan.svg
            self.mapTimer.start(MAP_UPDATE_INTERVAL_MSECS)

    def loadInitialMapPositions(self, new_dictionary):
        self.mapPositionsDict = new_dictionary

    def setInitialMapPositionForRegion(self, region_name):
        try:
            if not region_name:
                region_name = Cache().getFromCache("region_name")
            if region_name:
                xy = self.mapPositionsDict[region_name]
                self.initialMapPosition = QPointF(xy[0], xy[1])
        except Exception:
            pass

    def fixupScrollBars(self):
        fac = self.mapView.zoomFactor()
        pos = self.mapView.scrollPosition()
        size = self.mapView.imgSize
        self.mapHorzScrollBar.setPageStep(size.width())
        self.mapVertScrollBar.setPageStep(size.height())
        self.mapHorzScrollBar.setRange(int(min(pos.x(), 0)), int(size.width() * fac))
        self.mapVertScrollBar.setRange(int(min(pos.y(), 0)), int(size.height() * fac))
        self.mapHorzScrollBar.setValue(int(pos.x()))
        self.mapVertScrollBar.setValue(int(pos.y()))

    def showChatroomChooser(self):
        chooser = ChatroomsChooser(self)
        chooser.rooms_changed.connect(self.changedRoomnames)
        chooser.show()

    def showJumbridgeChooser(self):
        url = Cache().getFromCache("jumpbridge_url")
        chooser = JumpbridgeChooser(self, url)
        chooser.set_jumpbridge_url.connect(self.setJumpbridges)
        chooser.show()

    def setSoundVolume(self, value):
        SoundManager().setSoundVolume(value)

    def setJumpbridges(self, url):
        logging.info("setJB")
        if url is None:
            url = ""
        try:
            data = []
            if url != "":
                if url.startswith("http://") or url.startswith("https://"):
                    resp = requests.get(url)
                    for line in resp.iter_lines(decode_unicode=True):
                        parts = line.strip().split()
                        if len(parts) == 3:
                            data.append(parts)
                else:
                    content = None
                    with open(url, "r") as f:
                        content = f.readlines()

                    for line in content:
                        parts = line.strip().split()
                        # src <-> dst system_id jump_bridge_id
                        if len(parts) > 2:
                            data.append(parts)
                            Cache().putJumpGate(src=parts[0], dst=parts[2])
            else:
                # data = amazon_s3.getJumpbridgeData(self.dotlan.region.lower())
                data = None
            self.dotlan.setJumpbridges(Cache().getJumpGates())
            Cache().putIntoCache("jumpbridge_url", url, 60 * 60 * 24 * 365 * 8)
        except Exception as e:
            logging.error("Error setJumpbridges failed: {0}".format(str(e)))
            QMessageBox.warning(
                None,
                "Loading jumpbridges failed!",
                "Error: {0}".format(str(e)),
                QMessageBox.Ok,
            )

    def handleRegionMenuItemSelected(self, menuAction=None):
        self.catchRegionAction.setChecked(False)
        self.providenceRegionAction.setChecked(False)
        self.queriousRegionAction.setChecked(False)
        self.providenceCatchRegionAction.setChecked(False)
        self.providenceCatchCompactRegionAction.setChecked(False)
        self.chooseRegionAction.setChecked(False)
        if menuAction:
            menuAction.setChecked(True)
            regionName = str(menuAction.property("regionName"))
            regionName = dotlan.convertRegionName(regionName)
            Cache().putIntoCache("region_name", regionName, 60 * 60 * 24 * 365)
            self.setupMap()

    def showRegionChooser(self):
        def handleRegionChosen():
            self.handleRegionMenuItemSelected(None)
            self.chooseRegionAction.setChecked(True)
            self.setupMap()

        self.chooseRegionAction.setChecked(False)
        chooser = RegionChooser(self)
        chooser.finished.connect(handleRegionChosen)
        chooser.show()

    def addMessageToIntelChat(self, message):
        scrollToBottom = False
        if (
            self.chatListWidget.verticalScrollBar().value()
            == self.chatListWidget.verticalScrollBar().maximum()
        ):
            scrollToBottom = True
        chatEntryWidget = ChatEntryWidget(message)
        listWidgetItem = QtWidgets.QListWidgetItem(self.chatListWidget)
        listWidgetItem.setSizeHint(chatEntryWidget.sizeHint())
        self.chatListWidget.addItem(listWidgetItem)
        self.chatListWidget.setItemWidget(listWidgetItem, chatEntryWidget)
        self.avatarFindThread.addChatEntry(chatEntryWidget)
        self.chatEntries.append(chatEntryWidget)
        chatEntryWidget.mark_system.connect(self.markSystemOnMap)
        self.chat_message_added.emit(chatEntryWidget, message.timestamp)
        self.pruneMessages()
        if scrollToBottom:
            self.chatListWidget.scrollToBottom()

    def clearIntelChat(self):
        logging.info("Clearing Intel")
        self.setupMap()
        try:
            for row in range(self.chatListWidget.count()):
                item = self.chatListWidget.item(0)
                entry = self.chatListWidget.itemWidget(item)
                message = entry.message
                self.chatEntries.remove(entry)
                self.chatListWidget.takeItem(0)
                for widgetInMessage in message.widgets:
                    widgetInMessage.removeItemWidget(item)
        except Exception as e:
            logging.error(e)

    def pruneMessages(self):
        try:
            now = time.mktime(evegate.currentEveTime().timetuple())
            now_to = time.time()
            delta_time = now_to - now
            for row in range(self.chatListWidget.count()):
                chatListWidgetItem = self.chatListWidget.item(0)
                chatEntryWidget = self.chatListWidget.itemWidget(chatListWidgetItem)
                message = chatEntryWidget.message
                if now - time.mktime(message.timestamp.timetuple()) > (
                    60 * self.chatparser.intelTime
                ):
                    self.chatEntries.remove(chatEntryWidget)
                    self.chatListWidget.takeItem(0)

                    for widgetInMessage in message.widgets:
                        widgetInMessage.removeItemWidget(chatListWidgetItem)
                else:
                    break
        except Exception as e:
            logging.error(e)

    def changedRoomnames(self, newRoomnames):
        Cache().putIntoCache(
            "room_names", ",".join(newRoomnames), 60 * 60 * 24 * 365 * 5
        )
        self.chatparser.rooms = newRoomnames

    def showInfo(self):
        infoDialog = QtWidgets.QDialog(self)
        uic.loadUi(resourcePath(os.path.join("vi", "ui", "Info.ui")), infoDialog)
        infoDialog.versionLabel.setText("Version: {0}".format(vi.version.VERSION))
        infoDialog.logoLabel.setPixmap(
            QtGui.QPixmap(resourcePath(os.path.join("vi", "ui", "res", "logo.png")))
        )
        infoDialog.closeButton.clicked.connect(infoDialog.accept)
        infoDialog.show()

    def showSoundSetup(self):
        dialog = QtWidgets.QDialog(self)
        uic.loadUi(resourcePath(os.path.join("vi", "ui", "SoundSetup.ui")), dialog)
        dialog.volumeSlider.setValue(SoundManager().soundVolume)
        dialog.volumeSlider.valueChanged[int].connect(SoundManager().setSoundVolume)
        dialog.testSoundButton.clicked.connect(
            lambda: SoundManager().playSound(
                name="alarm", abbreviatedMessage="Testing the playback sound system!"
            )
        )
        dialog.closeButton.clicked.connect(dialog.accept)
        dialog.show()

    def systemTrayActivated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            if self.isMinimized():
                self.showNormal()
                self.activateWindow()
            elif not self.isActiveWindow():
                self.activateWindow()
            else:
                self.showMinimized()

    def updateAvatarOnChatEntry(self, chatEntry, avatarData):
        updated = chatEntry.updateAvatar(avatarData)
        if not updated:
            self.avatarFindThread.addChatEntry(chatEntry, clearCache=True)
        else:
            self.avatar_loaded.emit(chatEntry.message.user, avatarData)

    def updateStatisticsOnMap(self, data):
        if not self.statisticsButton.isChecked():
            return
        if data["result"] == "ok":
            self.dotlan.addSystemStatistics(data["statistics"])
        elif data["result"] == "error":
            text = data["text"]
            self.trayIcon.showMessage("Loading statstics failed", text, 3)
            logging.error("updateStatisticsOnMap, error: %s" % text)

    def zoomMapIn(self):
        self.mapView.zoomIn()

    def zoomMapOut(self):
        self.mapView.zoomOut()

    def logFileChanged(self, path, rescan=False):
        locale_to_set = dict()
        messages = self.chatparser.fileModified(path, rescan)
        for message in messages:
            # If players location has changed
            if message.status == states.LOCATION:
                locale_to_set[message.user] = message.systems[0]
            elif message.status == states.KOS_STATUS_REQUEST:
                # Do not accept KOS requests from any but monitored intel channels
                # as we don't want to encourage the use of xxx in those channels.
                if not message.room in self.roomnames:
                    text = message.message[4:]
                    text = text.replace("  ", ",")
                    parts = (name.strip() for name in text.split(","))
                    self.trayIcon.setIcon(self.taskbarIconWorking)
                    self.kosRequestThread.addRequest(parts, "xxx", False)
            # Otherwise consider it a 'normal' chat message
            elif (
                message.user not in ("EVE-System", "EVE System")
                and message.status != states.IGNORE
            ):
                self.addMessageToIntelChat(message)
                # For each system that was mentioned in the message, check for alarm distance to the current system
                # and alarm if within alarm distance.
                systemList = self.dotlan.systems
                if message.systems:
                    for system in message.systems:
                        system_name = system.name
                        if system_name in systemList.keys():
                            systemList[system_name].setStatus(
                                message.status, message.timestamp
                            )
                        else:
                            return
                        if (
                            message.status in (states.ALARM)
                            and message.user not in self.knownPlayerNames
                        ):
                            alarm_distance = (
                                self.alarmDistance
                                if message.status == states.ALARM
                                else 0
                            )
                            for nSystem, data in system.getNeighbours(
                                alarm_distance
                            ).items():
                                distance = data["distance"]
                                chars = nSystem.getLocatedCharacters()
                                if len(chars) > 0:
                                    if message.user not in chars:
                                        self.trayIcon.showNotification(
                                            message,
                                            system.name,
                                            ", ".join(chars),
                                            distance,
                                        )

        for name, sys in locale_to_set.items():
            self.knownPlayerNames.add(name)
            self.setLocation(name, sys)
        if not rescan:
            self.updateMapView()

    def systemUnderMouse(self, pos: QPoint):
        """returns the name of the system under the mouse pointer"""
        for system in self.dotlan.systems.items():
            val = system[1].mapCoordinates
            rc = QtCore.QRectF(val["x"], val["y"], val["width"], val["height"])
            if rc.contains(pos):
                return system
        return None

    def regionNameFromSystemID(self, selected_sys):
        selected_system = evegate.getSolarSystemInformation(selected_sys[1].systemId)
        selected_constellation = evegate.getConstellationInformation(
            selected_system["constellation_id"]
        )
        selected_region = selected_constellation["region_id"]
        selected_region_name = evegate.idsToNames([selected_region])[selected_region]
        return selected_region_name

    def showContextMenu(self, event):
        """checks if there is a system below the mouse position, if the systems region differs from the current
        region, the menu item to change the current region is added.
        """
        selected_sys = self.systemUnderMouse(self.mapView.mapPosFromPoint(event))
        if selected_sys:
            concurrent_region_name = Cache().getFromCache("region_name")
            selected_region_name = self.regionNameFromSystemID(selected_sys)
            if dotlan.convertRegionName(selected_region_name) == concurrent_region_name:
                selected_region_name = None
            self.trayIcon.contextMenu().updateMenu(selected_sys, selected_region_name)
        else:
            self.trayIcon.contextMenu().updateMenu()
        self.trayIcon.contextMenu().exec_(
            self.mapToGlobal(QPoint(event.x(), event.y()))
        )


class ChatroomsChooser(QtWidgets.QDialog):
    rooms_changed = pyqtSignal(list)

    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        uic.loadUi(resourcePath(os.path.join("vi", "ui", "ChatroomsChooser.ui")), self)
        self.defaultButton.clicked.connect(self.setDefaults)
        self.cancelButton.clicked.connect(self.accept)
        self.saveButton.clicked.connect(self.saveClicked)
        room_names = Cache().getFromCache("room_names")
        if not room_names:
            room_names = ",".join(DEFAULT_ROOM_MANES)
        self.roomnamesField.setPlainText(room_names)

    def saveClicked(self):
        text = str(self.roomnamesField.toPlainText())
        rooms = [str(name.strip()) for name in text.split(",")]
        self.accept()
        self.rooms_changed.emit(rooms)

    def setDefaults(self):
        self.roomnamesField.setPlainText(",".join(DEFAULT_ROOM_MANES))


class RegionChooser(QtWidgets.QDialog):
    new_region_chosen = pyqtSignal()

    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        uic.loadUi(resourcePath(os.path.join("vi", "ui", "RegionChooser.ui")), self)
        self.strList = QtWidgets.QCompleter(
            [
                "{}".format(name)
                for key, name in evegate.idsToNames(evegate.getAllRegions()).items()
            ],
            parent=self,
        )
        self.strList.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self.regionNameField.setCompleter(self.strList)
        self.cancelButton.clicked.connect(self.accept)
        self.saveButton.clicked.connect(self.saveClicked)
        cache = Cache()
        regionName = cache.getFromCache("region_name")
        if not regionName:
            regionName = "Providence"
        self.regionNameField.setText(regionName)

    def saveClicked(self):
        text = str(self.regionNameField.text())
        text = dotlan.convertRegionName(text)
        self.regionNameField.setText(text)
        correct = False
        try:
            url = dotlan.Map.DOTLAN_BASIC_URL.format(text)
            content = requests.get(url).text
            if "not found" in content:
                try:
                    correct = resourcePathExists(
                        os.path.join(
                            "vi", "ui", "res", "mapdata", "{0}.svg".format(text)
                        )
                    )
                except Exception as e:
                    logging.error(e)
                    correct = False
                if not correct:
                    QMessageBox.warning(
                        self,
                        "No such region!",
                        "I can't find a region called '{0}'".format(text),
                    )
            else:
                correct = True
        except Exception as e:
            QMessageBox.critical(
                self,
                "Something went wrong!",
                "Error while testing existing '{0}'".format(str(e)),
            )
            logging.error(e)
            correct = False
        if correct:
            Cache().putIntoCache("region_name", text, 60 * 60 * 24 * 365)
            self.accept()
            self.new_region_chosen.emit()


class SystemChat(QtWidgets.QDialog):
    SYSTEM = 0
    location_set = QtCore.pyqtSignal(str, str)
    repaint_needed = QtCore.pyqtSignal()

    def __init__(self, parent, chatType, selector, chatEntries, knownPlayerNames):
        QtWidgets.QDialog.__init__(self, parent)
        uic.loadUi(resourcePath(os.path.join("vi", "ui", "SystemChat.ui")), self)
        self.chatType = 0
        self.selector = selector
        self.chatEntries = []
        for entry in chatEntries:
            self.addChatEntry(entry)
        titleName = ""
        if self.chatType == SystemChat.SYSTEM:
            titleName = self.selector.name
            self.system = selector
        for name in knownPlayerNames:
            self.playerNamesBox.addItem(name)
        self.setWindowTitle("Chat for {0}".format(titleName))
        self.closeButton.clicked.connect(self.closeDialog)
        self.alarmButton.clicked.connect(self.setSystemAlarm)
        self.clearButton.clicked.connect(self.setSystemClear)
        self.locationButton.clicked.connect(self.locationSet)
        self.dotlanButton.clicked.connect(self.openDotlan)

    def _addMessageToChat(self, message, avatarPixmap):
        scrollToBottom = False
        if (
            self.chat.verticalScrollBar().value()
            == self.chat.verticalScrollBar().maximum()
        ):
            scrollToBottom = True
        entry = ChatEntryWidget(message)
        entry.avatarLabel.setPixmap(avatarPixmap)
        listWidgetItem = QtWidgets.QListWidgetItem(self.chat)
        listWidgetItem.setSizeHint(entry.sizeHint())
        self.chat.addItem(listWidgetItem)
        self.chat.setItemWidget(listWidgetItem, entry)
        self.chatEntries.append(entry)
        # entry.mark_system.connect(super(MainWindow,self.parent()).markSystemOnMap)
        if scrollToBottom:
            self.chat.scrollToBottom()

    def addChatEntry(self, entry):
        if self.chatType == SystemChat.SYSTEM:
            message = entry.message
            avatarPixmap = entry.avatarLabel.pixmap()
            if self.selector in message.systems:
                self._addMessageToChat(message, avatarPixmap)

    def openDotlan(self):
        try:
            url = "https://evemaps.dotlan.net/system/{system}".format(
                system=self.system.name
            )
            webbrowser.open_new_tab(url)
        except webbrowser.Error as e:
            logging.critical("Unable to open browser {0}".format(e))
            return

    def locationSet(self):
        char = str(self.playerNamesBox.currentText())
        self.location_set.emit(char, self.system.name)

    def newAvatarAvailable(self, charname, avatarData):
        for entry in self.chatEntries:
            if entry.message.user == charname:
                entry.updateAvatar(avatarData)

    def setSystemAlarm(self):
        self.system.setStatus(states.ALARM, datetime.datetime.utcnow())
        self.repaint_needed.emit()

    def setSystemClear(self):
        self.system.setStatus(states.CLEAR, datetime.datetime.utcnow())
        self.repaint_needed.emit()

    def closeDialog(self):
        self.accept()


class ChatEntryWidget(QtWidgets.QWidget):
    TEXT_SIZE = 11
    DIM_IMG = 64
    SHOW_AVATAR = True
    questionMarkPixmap = None

    mark_system = pyqtSignal(str)

    def __init__(self, message):
        QtWidgets.QWidget.__init__(self)
        if not self.questionMarkPixmap:
            self.questionMarkPixmap = QtGui.QPixmap(
                resourcePath(os.path.join("vi", "ui", "res", "qmark.png"))
            ).scaledToHeight(self.DIM_IMG)
        uic.loadUi(resourcePath(os.path.join("vi", "ui", "ChatEntry.ui")), self)
        self.avatarLabel.setPixmap(self.questionMarkPixmap)
        self.message = message
        self.updateText()
        self.textLabel.linkActivated["QString"].connect(self.linkClicked)
        self.changeFontSize(self.TEXT_SIZE)
        if not ChatEntryWidget.SHOW_AVATAR:
            self.avatarLabel.setVisible(False)

    def linkClicked(self, link):
        link = str(link)
        function, parameter = link.split("/", 1)
        if function == "mark_system":
            self.mark_system.emit(parameter)
        elif function == "link":
            webbrowser.open_new_tab(parameter)

    def updateText(self):
        time = datetime.datetime.strftime(self.message.timestamp, "%H:%M:%S")
        text = "<small>{time} - <b>{user}</b> - <i>{room}</i></small><br>{text}".format(
            user=self.message.user,
            room=self.message.room,
            time=time,
            text=self.message.message.rstrip(" \r\n").lstrip(" \r\n"),
        )
        self.textLabel.setText(text)

    def updateAvatar(self, avatar_data):
        image = QImage.fromData(avatar_data)
        pixmap = QPixmap.fromImage(image)
        if pixmap.isNull():
            return False
        scaledAvatar = pixmap.scaled(self.DIM_IMG, self.DIM_IMG)
        try:
            if self.avatarLabel:
                self.avatarLabel.setPixmap(scaledAvatar)
        except Exception as ex:
            logging.warning("Updating a deleted chat item")
            self.avatarLabel = None
            self = None
        return True

    def changeFontSize(self, newSize):
        font = self.textLabel.font()
        font.setPointSize(newSize)
        self.textLabel.setFont(font)


class JumpbridgeChooser(QtWidgets.QDialog):
    set_jumpbridge_url = pyqtSignal(str)

    def __init__(self, parent, url):
        QtWidgets.QDialog.__init__(self, parent)
        uic.loadUi(resourcePath(os.path.join("vi", "ui", "JumpbridgeChooser.ui")), self)
        self.saveButton.clicked.connect(self.savePath)
        self.fileChooser.clicked.connect(self.choosePath)
        self.urlField.setText(url)
        # loading format explanation from textfile
        with open(resourcePath(os.path.join("docs", "jumpbridgeformat.txt"))) as f:
            self.formatInfoField.setPlainText(f.read())

    def savePath(self):
        try:
            url = str(self.urlField.text())
            self.set_jumpbridge_url.emit(url)
            self.accept()
        except Exception as e:
            QMessageBox.critical(
                None, "Finding jump bridge data failed", "Error: {0}".format(str(e))
            )

    def choosePath(self):
        path = QFileDialog.getOpenFileName(self, caption="Open JB Text File")[0]
        self.urlField.setText(str(path))
