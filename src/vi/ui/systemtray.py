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

import time
import os
import logging

from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QAction, QActionGroup
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QSystemTrayIcon
from vi.resources import resourcePath
from vi import states
from vi.soundmanager import SoundManager

class TrayContextMenu(QtWidgets.QMenu):
    instances = set()

    def __init__(self, trayIcon):
        """ trayIcon = the object with the methods to call
        """
        QtWidgets.QMenu.__init__(self)
        TrayContextMenu.instances.add(self)
        self.trayIcon = trayIcon
        self._buildMenu()

    def hasJumpGate(sys_name=None) -> bool:
        return False

    def updateMenu(self, sys_name=None, rgn_name=None):
        pass

    def _buildMenu(self):
        self.framelessCheck = QtWidgets.QAction("Frameless Window", self, checkable=True)
        self.framelessCheck.triggered.connect(self.trayIcon.changeFrameless)
        self.addAction(self.framelessCheck)
        self.addSeparator()
        self.requestCheck = QtWidgets.QAction("Show status request notifications", self, checkable=True)
        self.requestCheck.setChecked(True)
        self.addAction(self.requestCheck)
        self.requestCheck.triggered.connect(self.trayIcon.switchRequest)
        self.alarmCheck = QtWidgets.QAction("Show alarm notifications", self, checkable=True)
        self.alarmCheck.setChecked(True)
        self.alarmCheck.triggered.connect(self.trayIcon.switchAlarm)
        self.addAction(self.alarmCheck)
        distanceMenu = self.addMenu("Alarm Distance")
        self.distanceGroup = QActionGroup(self)
        for i in range(0, 6):
            action = QAction("{0} Jumps".format(i), None, checkable=True)
            if i == 0:
                action.setChecked(True)
            action.alarmDistance = i
            action.triggered.connect(self.changeAlarmDistance)
            self.distanceGroup.addAction(action)
            distanceMenu.addAction(action)
        self.addMenu(distanceMenu)
        self.addSeparator()
        self.quitAction = QAction("Quit", self)
        self.quitAction.triggered.connect(self.trayIcon.quit)
        self.addAction(self.quitAction)

    def changeAlarmDistance(self):
        for action in self.distanceGroup.actions():
            if action.isChecked():
                self.trayIcon.alarmDistance = action.alarmDistance
                self.trayIcon.changeAlarmDistance()


class TrayIcon(QtWidgets.QSystemTrayIcon):
    # Min seconds between two notifications
    MIN_WAIT_NOTIFICATION = 15

    alarm_distance = pyqtSignal(int)
    change_frameless = pyqtSignal()
    quit_signal = pyqtSignal()

    def __init__(self, app):
        self.icon = QIcon(resourcePath(os.path.join("vi", "ui", "res", "logo_small.png")))
        QSystemTrayIcon.__init__(self, self.icon, app)
        self.setToolTip("Your Spyglass Information Service! :)")
        self.lastNotifications = {}
        self.setContextMenu(TrayContextMenu(self))
        self.showAlarm = True
        self.showRequest = True
        self.alarmDistance = 0


    def changeAlarmDistance(self):
        distance = self.alarmDistance
        self.alarm_distance.emit(distance)

    def changeFrameless(self):
        self.change_frameless.emit()

    @property
    def distanceGroup(self):
        return self.contextMenu().distanceGroup

    def quit(self):
        self.quit_signal.emit()

    def switchAlarm(self):
        newValue = not self.showAlarm
        for cm in TrayContextMenu.instances:
            cm.alarmCheck.setChecked(newValue)
        self.showAlarm = newValue

    def switchRequest(self):
        newValue = not self.showRequest
        for cm in TrayContextMenu.instances:
            cm.requestCheck.setChecked(newValue)
        self.showRequest = newValue

    def showNotification(self, message, system, char, distance):
        logging.debug("shownotification")
        if message is None:
            return
        room = message.room
        title = None
        text = None
        icon = None
        text = ""

        if (message.status == states.ALARM and self.showAlarm and self.lastNotifications.get(states.ALARM,
                                                                                             0) < time.time() - self.MIN_WAIT_NOTIFICATION):
            title = "ALARM!"
            icon = 2
            speechText = (u"{0} alarmed in {1}, {2} jumps from {3}".format(system, room, distance, char))
            text = speechText + (u"\nText: %s" % text)
            logging.debug("playing alarm sound!")
            SoundManager().playSound("alarm", text, speechText)
            self.lastNotifications[states.ALARM] = time.time()
        elif (message.status == states.REQUEST and self.showRequest and self.lastNotifications.get(states.REQUEST,
                                                                                                   0) < time.time() - self.MIN_WAIT_NOTIFICATION):
            title = "Status request"
            icon = 1
            text = (u"Someone is requesting status of {0} in {1}.".format(system, room))
            self.lastNotifications[states.REQUEST] = time.time()
            #SoundManager().playSound("request", text)
        if not (title is None or text is None or icon):
            text = text.format(**locals())
            self.showMessage(title, text, icon)
