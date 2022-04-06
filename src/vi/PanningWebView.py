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

from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtGui import *
from PyQt5 import QtCore, QtSvg

from PyQt5.QtCore import QPoint, QPointF
from PyQt5.QtCore import Qt
import logging


class PanningWebView(QWidget):
    ZOOM_WHEEL = 0.2
    webViewScrolled = QtCore.pyqtSignal(bool)
    webViewResized = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(PanningWebView, self).__init__()
        self.zoom = 1.0
        self.wheel_dir = 1.0
        self.setImgSize(QtCore.QSize(100, 80))
        self.pressed = False
        self.scrolling = False
        self.positionMousePress = None
        self.scrollMousePress = None
        self.handIsClosed = False
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.scrollPos = QPointF(0.0, 0.0)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setMouseTracking(True)
        self.svgRenderer = QtSvg.QSvgRenderer()
        self.svgRenderer.setAspectRatioMode(Qt.KeepAspectRatioByExpanding)
        self.svgRenderer.repaintNeeded.connect(self.update)

    def setContent(self, cnt, type):
        if self.scrolling:
            return False
        if not self.svgRenderer.load(cnt):
            logging.error("error during parse of svg data")
        self.setImgSize(self.svgRenderer.defaultSize())
        self.svgRenderer.setFramesPerSecond(0)
        self.svgRenderer.setAspectRatioMode(Qt.KeepAspectRatio)
        return True

    def setImgSize(self, newsize: QtCore.QSize):
        self.imgSize = newsize

    def resizeEvent(self, event: QResizeEvent):
        self.webViewResized.emit()
        super().resizeEvent(event)

    def paintEvent(self, event):
        if self.svgRenderer:
            painter = QPainter(self)
            rect = QtCore.QRectF(
                -self.scrollPos.x(),
                -self.scrollPos.y(),
                self.svgRenderer.defaultSize().width() * self.zoom,
                self.svgRenderer.defaultSize().height() * self.zoom,
            )
            self.svgRenderer.render(painter, rect)

    def setZoomFactor(self, zoom):
        if zoom > 8:
            zoom = 8
        elif zoom < 0.5:
            zoom = 0.5
        if self.zoom != zoom:
            self.zoom = zoom
            self.webViewResized.emit()
            if self.imgSize.isValid():
                self.setImgSize(self.imgSize)
            self.update()

    def zoomFactor(self):
        return self.zoom

    def scrollPosition(self) -> QPointF:
        return self.scrollPos

    def setScrollPosition(self, pos: QPoint):
        if self.scrollPos != pos:
            self.scrollPos = pos
            self.webViewResized.emit()
        self.update()

    def zoomIn(self, pos=None):
        if pos == None:
            self.setZoomFactor(self.zoomFactor() * (1.0 + self.ZOOM_WHEEL))
        else:
            elemOri = self.mapPosFromPos(pos)
            self.setZoomFactor(self.zoom * (1.0 + self.ZOOM_WHEEL))
            elemDelta = elemOri - self.mapPosFromPos(pos)
            self.scrollPos = self.scrollPos + elemDelta * self.zoom

    def zoomOut(self, pos=None):
        if pos == None:
            self.setZoomFactor(self.zoom * (1.0 - self.ZOOM_WHEEL))
        else:
            elem_ori = self.mapPosFromPos(pos)
            self.setZoomFactor(self.zoom * (1.0 - self.ZOOM_WHEEL))
            elem_delta = elem_ori - self.mapPosFromPos(pos)
            self.scrollPos = self.scrollPos + elem_delta * self.zoom

    def wheelEvent(self, event: QWheelEvent):
        if (self.wheel_dir * event.angleDelta().y()) < 0:
            self.zoomIn(event.position())
        elif (self.wheel_dir * event.angleDelta().y()) > 0:
            self.zoomOut(event.position())

    def mousePressEvent(self, mouseEvent: QMouseEvent):
        if (
            not self.pressed
            and not self.scrolling
            and mouseEvent.modifiers() == QtCore.Qt.NoModifier
        ):
            if mouseEvent.buttons() == QtCore.Qt.LeftButton:
                self.pressed = True
                self.scrolling = False
                self.handIsClosed = False
                QApplication.setOverrideCursor(QtCore.Qt.OpenHandCursor)
                self.scrollMousePress = self.scrollPosition()
                self.positionMousePress = mouseEvent.pos()

    def mouseReleaseEvent(self, mouseEvent: QMouseEvent):
        if self.scrolling:
            self.pressed = False
            self.scrolling = False
            self.handIsClosed = False
            self.positionMousePress = None
            QApplication.restoreOverrideCursor()
            self.webViewScrolled.emit(False)
            return

        if self.pressed:
            self.pressed = False
            self.scrolling = False
            self.handIsClosed = False
            QApplication.restoreOverrideCursor()
            return

    def hoveCheck(self, pos: QPointF) -> bool:
        return False

    def doubleClicked(self, pos: QPoint) -> bool:
        return False

    def mouseDoubleClickEvent(self, mouseEvent: QMouseEvent):
        self.doubleClicked(self.mapPosFromEvent(mouseEvent))

    def mapPosFromPos(self, pos: QPointF) -> QPointF:
        return (pos + self.scrollPos) / self.zoom

    def mapPosFromPoint(self, mouseEvent: QPoint) -> QPoint:
        return (mouseEvent + self.scrollPos) / self.zoom

    def mapPosFromEvent(self, mouseEvent: QMouseEvent) -> QPointF:
        return (QPointF(mouseEvent.pos()) + self.scrollPos) / self.zoom

    def mouseMoveEvent(self, mouseEvent: QMouseEvent):
        if self.scrolling:
            if not self.handIsClosed:
                QApplication.restoreOverrideCursor()
                QApplication.setOverrideCursor(QtCore.Qt.OpenHandCursor)
                self.handIsClosed = True
            if self.scrollMousePress != None:
                delta = mouseEvent.pos() - self.positionMousePress
                self.setScrollPosition(self.scrollMousePress - delta)
            return
        if self.pressed:
            self.pressed = False
            self.scrolling = True
            self.webViewScrolled.emit(True)
            return
        if self.hoveCheck(self.mapPosFromEvent(mouseEvent)):
            QApplication.setOverrideCursor(QtCore.Qt.PointingHandCursor)
        else:
            QApplication.setOverrideCursor(QtCore.Qt.ArrowCursor)
        return
