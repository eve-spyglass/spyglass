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
import logging

from PyQt5.QtCore import QThread, QLocale
from .resources import resourcePath
from vi.singleton import Singleton
from PyQt5.QtMultimedia import QSoundEffect
from PyQt5.QtTextToSpeech import QTextToSpeech
from PyQt5.QtWidgets import qApp
from PyQt5.QtCore import *
from vi.cache.cache import Cache


class SoundManager(metaclass=Singleton):
    SOUNDS = {
        "alarm": "178032__zimbot__redalert-klaxon-sttos-recreated.wav",
    }

    soundVolume = 25  # Must be an integer between 0 and 100
    soundAvailable = True
    useSpokenNotifications = False

    def __init__(self):
        self.sounds = {}
        self.worker = QThread()
        self.speach_engine = QTextToSpeech()
        cache = Cache()
        self.setSoundFile(
            "alarm", "178032__zimbot__redalert-klaxon-sttos-recreated.wav"
        )
        vol = cache.getFromCache("soundsetting.volume")
        if vol:
            self.setSoundVolume(float(vol))
        self.loadSoundFiles()

    def soundFile(self, mask):
        if mask in self.SOUNDS.keys():
            return self.SOUNDS[mask]
        else:
            return ""

    def setSoundFile(self, mask, filename):
        if mask in self.SOUNDS.keys():
            if filename == "":
                filename = "178032__zimbot__redalert-klaxon-sttos-recreated.wav"
            self.SOUNDS[mask] = filename
            self.sounds[mask] = QSoundEffect()
            url = QUrl.fromLocalFile(self.SOUNDS[mask])
            self.sounds[mask].setSource(url)
            Cache().putIntoCache("soundsetting.{}".format(mask), filename)
            self.loadSoundFiles()

    def loadSoundFiles(self):
        for itm in self.SOUNDS:
            self.sounds[itm] = QSoundEffect()
            if self.SOUNDS[itm] != None and os.path.exists(self.SOUNDS[itm]):
                url = QUrl.fromLocalFile(self.SOUNDS[itm])
            elif self.SOUNDS[itm] != None:
                url = QUrl.fromLocalFile(
                    resourcePath(
                        os.path.join("vi", "ui", "res", "{0}".format(self.SOUNDS[itm]))
                    )
                )
            else:
                url = None
            if url != None:
                logging.debug("setting sound [{}] to [{}]".format(itm, url))
                self.sounds[itm].setSource(url)
                # logging.debug("sound source set as  {}".format(self.sounds[itm].source()))

    def platformSupportsAudio(self):
        return True

    def platformSupportsSpeech(self):
        avail_engines = self.speach_engine.availableEngines()
        if len(avail_engines):
            for eng_name in avail_engines:
                logging.info("Available sound engine '{}'".format(eng_name))
            self.speach_engine.setLocale(QLocale(QLocale.English))
            return True
        else:
            self.useSpokenNotifications = False
            logging.critical(
                " There is no text to speak engine available, all text to speak function disabled."
            )
            return False

    def setUseSpokenNotifications(self, new_value):
        self.useSpokenNotifications = new_value

    def setSoundVolume(self, newValue):
        self.soundVolume = max(0.0, min(100.0, newValue))
        Cache().putIntoCache("soundsetting.volume", self.soundVolume)
        for itm in self.sounds.keys():
            self.sounds[itm].setVolume(self.soundVolume / 100)

    def playSound(self, name="alarm", message="", abbreviatedMessage=""):
        logging.debug(
            "playsound. name: {}, amessage: {}, volume: {}".format(
                name, abbreviatedMessage, self.soundVolume
            )
        )
        logging.debug(self.sounds)
        if self.soundAvailable and self.soundActive:
            if self.useSpokenNotifications and abbreviatedMessage != "":
                self.speach_engine.setVolume(self.soundVolume / 100.0)
                self.speach_engine.say(abbreviatedMessage)
            elif name in self.sounds.keys():
                self.sounds[name].setVolume(self.soundVolume / 100.0)
                self.sounds[name].setMuted(False)
                logging.debug(dir(self.sounds[name]))
                logging.debug(self.sounds[name].source())
                self.sounds[name].play()
                self.sounds[name].status()
            else:
                self.sounds["alarm"].setVolume(self.soundVolume / 100.0)
                self.sounds["alarm"].setMuted(False)
                self.sounds["alarm"].play()
                self.sounds["alarm"].status()
        qApp.processEvents()

    def quit(self):
        qApp.processEvents()

    def wait(self):
        qApp.processEvents()
