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

import time
import logging
import queue
from PyQt5.QtCore import QThread, QTimer, pyqtSignal
from vi import evegate
from vi.cache.cache import Cache
from vi.resources import resourcePath

STATISTICS_UPDATE_INTERVAL_MSECS = 1 * 60 * 1000


class AvatarFindThread(QThread):

    avatar_update = pyqtSignal(object, object)

    def __init__(self):
        QThread.__init__(self)
        self.queue = queue.Queue()
        self.active = True

    def addChatEntry(self, chatEntry, clearCache=False):
        try:
            if clearCache:
                cache = Cache()
                cache.removeAvatar(chatEntry.message.user)

            # Enqeue the data to be picked up in run()
            self.queue.put(chatEntry)
        except Exception as e:
            logging.error("Error in AvatarFindThread: %s", e)

    def run(self):
        cache = Cache()
        lastCall = 0
        wait = 500  # time between 2 requests in ms
        while True:
            try:
                # Block waiting for addChatEntry() to enqueue something
                chatEntry = self.queue.get()
                if not self.active:
                    return
                charname = chatEntry.message.user
                logging.debug("AvatarFindThread getting avatar for %s" % charname)
                avatar = None
                if charname == "SPYGLASS":
                    with open(
                        resourcePath(os.path.join("vi", "ui", "res", "logo_small.png")),
                        "rb",
                    ) as f:
                        avatar = f.read()
                if avatar is None:
                    avatar = cache.getAvatar(charname)
                    if avatar:
                        logging.debug(
                            "AvatarFindThread found cached avatar for %s" % charname
                        )
                if avatar is None:
                    diffLastCall = time.time() - lastCall
                    if diffLastCall < wait:
                        time.sleep((wait - diffLastCall) / 1000.0)
                    avatar = evegate.getAvatarForPlayer(charname)
                    lastCall = time.time()
                    if avatar is None:
                        cache.removeAvatar(charname)
                    else:
                        cache.putAvatar(charname, avatar)
                if avatar:
                    logging.debug(
                        "AvatarFindThread emit avatar_update for %s" % charname
                    )
                    self.avatar_update.emit(chatEntry, avatar)
                else:
                    logging.warning(
                        "AvatarFindThread unable to find avatar for %s" % charname
                    )
            except Exception as e:
                logging.error("Error in AvatarFindThread : %s", e)

    def quit(self):
        self.active = False
        self.queue.put(None)
        QThread.quit(self)


class MapStatisticsThread(QThread):

    statistic_data_update = pyqtSignal(dict)

    def __init__(self):
        QThread.__init__(self)
        self.queue = queue.Queue(maxsize=1)
        self.active = True

    def requestStatistics(self):
        self.queue.put(None)

    def run(self):
        evegate.getPlayerSovereignty(fore_refresh=False, show_npc=False)
        evegate.getIncursionSystemsIds(False)
        evegate.getCampaignsSystemsIds(False)
        evegate.getSystemStatistics()
        while True:
            self.queue.get()
            if not self.active:
                return
            try:
                evegate.getIncursionSystemsIds(False)
                evegate.getCampaignsSystemsIds(False)
                statistics = evegate.getSystemStatistics()
                statistics_data = {"result": "ok", "statistics": statistics}
            except Exception as e:
                logging.error("Error in MapStatisticsThread: %s", e)
                statistics_data = {"result": "error", "text": str(e)}
            self.statistic_data_update.emit(statistics_data)

    def quit(self):
        self.active = False
        self.queue.put(None)
        QThread.quit(self)
