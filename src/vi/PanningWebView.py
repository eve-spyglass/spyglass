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

from PyQt5.QtWebEngineWidgets  import QWebEngineView
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import *
from PyQt5 import QtCore

from PyQt5.QtCore import QPoint
from PyQt5.QtCore import QEvent


class PanningWebView(QWebEngineView):
    def __init__(self, parent=None):
        super(PanningWebView, self).__init__()
        self.pressed = False
        self.scrolling = False
        self.ignored = []
        self.position = None
        self.offset = 0
        self.handIsClosed = False
        self.clickedInScrollBar = False

    def mousePressEvent(self, mouseEvent):
        pos = mouseEvent.pos()

        if self.pointInScroller(pos, QtCore.Qt.Vertical) or self.pointInScroller(pos, QtCore.Qt.Horizontal):
            self.clickedInScrollBar = True
        else:
            if self.ignored.count(mouseEvent):
                self.ignored.remove(mouseEvent)
                return QWebEngineView.mousePressEvent(self, mouseEvent)

            if not self.pressed and not self.scrolling and mouseEvent.modifiers() == QtCore.Qt.NoModifier:
                if mouseEvent.buttons() == QtCore.Qt.LeftButton:
                    self.pressed = True
                    self.scrolling = False
                    self.handIsClosed = False
                    QApplication.setOverrideCursor(QtCore.Qt.OpenHandCursor)

                    self.position = mouseEvent.pos()
                    frame = self.page().mainFrame()
                    xTuple = frame.evaluateJavaScript("window.scrollX").toInt()
                    yTuple = frame.evaluateJavaScript("window.scrollY").toInt()
                    self.offset = QPoint(xTuple[0], yTuple[0])
                    return

        return QWebEngineView.mousePressEvent(self, mouseEvent)

    def mouseReleaseEvent(self, mouseEvent):
        if self.clickedInScrollBar:
            self.clickedInScrollBar = False
        else:
            if self.ignored.count(mouseEvent):
                self.ignored.remove(mouseEvent)
                return QWebEngineView.mousePressEvent(self, mouseEvent)

            if self.scrolling:
                self.pressed = False
                self.scrolling = False
                self.handIsClosed = False
                QApplication.restoreOverrideCursor()
                return

            if self.pressed:
                self.pressed = False
                self.scrolling = False
                self.handIsClosed = False
                QApplication.restoreOverrideCursor()

                event1 = QMouseEvent(QEvent.MouseButtonPress, self.position, QtCore.Qt.LeftButton, QtCore.Qt.LeftButton,
                                     QtCore.Qt.NoModifier)
                event2 = QMouseEvent(mouseEvent)
                self.ignored.append(event1)
                self.ignored.append(event2)
                QApplication.postEvent(self, event1)
                QApplication.postEvent(self, event2)
                return
        return QWebView.mouseReleaseEvent(self, mouseEvent)

    def mouseMoveEvent(self, mouseEvent):
        if not self.clickedInScrollBar:
            if self.scrolling:
                if not self.handIsClosed:
                    QApplication.restoreOverrideCursor()
                    QApplication.setOverrideCursor(QtCore.Qt.ClosedHandCursor)
                    self.handIsClosed = True
                delta = mouseEvent.pos() - self.position
                p = self.offset - delta
                frame = self.page().mainFrame()
                frame.evaluateJavaScript("window.scrollTo(%1, %2);".arg(p.x()).arg(p.y()));
                return

            if self.pressed:
                self.pressed = False
                self.scrolling = True
                return
        return QWebEngineView.mouseMoveEvent(self, mouseEvent)

    def pointInScroller(self, position, orientation):
        rect = self.page().mainFrame().scrollBarGeometry(orientation)
        leftTop = self.mapToGlobal(QtCore.QPoint(rect.left(), rect.top()))
        rightBottom = self.mapToGlobal(QtCore.QPoint(rect.right(), rect.bottom()))
        globalRect = QtCore.QRect(leftTop.x(), leftTop.y(), rightBottom.x(), rightBottom.y())
        return globalRect.contains(self.mapToGlobal(position))
