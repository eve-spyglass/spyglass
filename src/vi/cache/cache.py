###########################################################################
#  Vintel - Visual Intel Chat Analyzer									  #
#  Copyright (C) 2014-15 Sebastian Meyer (sparrow.242.de+eve@gmail.com )  #
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

import sqlite3
import threading
import time
import logging
import vi.version
from vi.cache.dbstructure import updateDatabase


def to_blob(x):
    return x


def from_blob(x):
    return x


class Cache(object):
    # Cache checks PATH_TO_CACHE when init, so you can set this on a
    # central place for all Cache instances.
    PATH_TO_CACHE = None

    # Ok, this is dirty. To make sure we check the database only
    # one time/runtime we will change this class variable after the
    # check. Following inits of Cache will now, that we already checked.
    VERSION_CHECKED = False

    # Cache-Instances in various threads: must handle concurrent writings
    SQLITE_WRITE_LOCK = threading.Lock()

    # Dirty trick to know if we updated the DB this launch
    WAS_UPDATED = False

    def __init__(self, pathToSQLiteFile="cache.sqlite3"):
        """pathToSQLiteFile=path to sqlite-file to save the cache. will be ignored if you set Cache.PATH_TO_CACHE
        before init
        """
        if Cache.PATH_TO_CACHE:
            pathToSQLiteFile = Cache.PATH_TO_CACHE
        self.con = sqlite3.connect(pathToSQLiteFile)
        if not Cache.VERSION_CHECKED:
            with Cache.SQLITE_WRITE_LOCK:
                self.checkVersion()
        Cache.VERSION_CHECKED = True

    def checkVersion(self):
        query = "SELECT version FROM version;"
        version = 0
        try:
            version = self.con.execute(query).fetchall()[0][0]
        except Exception as e:
            if isinstance(
                e, sqlite3.OperationalError
            ) and "no such table: version" in str(e):
                pass
            elif isinstance(e, IndexError):
                pass
            else:
                raise e
        self.WAS_UPDATED = updateDatabase(version, self.con)

    def putIntoCache(self, key, value, max_age=60 * 60 * 24 * 3):
        """Putting something in the cache maxAge is maximum age in seconds"""
        with Cache.SQLITE_WRITE_LOCK:
            query = "DELETE FROM cache WHERE key = ?"
            self.con.execute(query, (key,))
            query = (
                "INSERT INTO cache (key, data, modified, maxAge) VALUES (?, ?, ?, ?)"
            )
            self.con.execute(query, (key, value, time.time(), max_age))
            self.con.commit()

    def getFromCache(self, key, outdated=False):
        """Getting a value from cache
        key = the key for the value
        outdated = returns the value also if it is outdated
        """
        query = "SELECT key, data, modified, maxage FROM cache WHERE key = ?"
        founds = self.con.execute(query, (key,)).fetchall()
        if len(founds) == 0:
            return None
        elif founds[0][2] + founds[0][3] < time.time() and not outdated:
            return None
        else:
            return founds[0][1]

    def putPlayerName(self, name, status):
        """Putting a playername into the cache"""
        with Cache.SQLITE_WRITE_LOCK:
            query = "DELETE FROM playernames WHERE charname = ?"
            self.con.execute(query, (name,))
            query = (
                "INSERT INTO playernames (charname, status, modified) VALUES (?, ?, ?)"
            )
            self.con.execute(query, (name, status, time.time()))
            self.con.commit()

    def getPlayerName(self, name):
        """Getting back infos about playername from Cache. Returns None if the name was not found, else it returns
        the status
        """
        selectquery = "SELECT charname, status FROM playernames WHERE charname = ?"
        founds = self.con.execute(selectquery, (name,)).fetchall()
        if len(founds) == 0:
            return None
        else:
            return founds[0][1]

    def putAvatar(self, name, data):
        """Put the picture of an player into the cache"""
        with Cache.SQLITE_WRITE_LOCK:
            # data is a blob, so we have to change it to buffer
            data = to_blob(data)
            query = "DELETE FROM avatars WHERE charname = ?"
            self.con.execute(query, (name,))
            query = "INSERT INTO avatars (charname, data, modified) VALUES (?, ?, ?)"
            self.con.execute(query, (name, data, time.time()))
            self.con.commit()

    def getAvatar(self, name):
        """Getting the avatars_pictures data from the Cache. Returns None if there is no entry in the cache"""
        select_query = "SELECT data FROM avatars WHERE charname = ?"
        founds = self.con.execute(select_query, (name,)).fetchall()
        if len(founds) == 0:
            return None
        else:
            # dats is buffer, we convert it back to str
            data = from_blob(founds[0][0])
            return data

    def removeAvatar(self, name):
        """Removing an avatar from the cache"""
        with Cache.SQLITE_WRITE_LOCK:
            query = "DELETE FROM avatars WHERE charname = ?"
            self.con.execute(query, (name,))
            self.con.commit()

    def recallAndApplySettings(self, responder, settings_identifier):
        version = self.getFromCache("version")
        restore_gui = version == vi.version.VERSION
        settings = self.getFromCache(settings_identifier)
        if settings:
            settings = eval(settings)
            for setting in settings:
                obj = responder if not setting[0] else getattr(responder, setting[0])
                # logging.debug("{0} | {1} | {2}".format(str(obj), setting[1], setting[2]))
                try:
                    if restore_gui and setting[1] == "restoreGeometry":
                        if not obj.restoreGeometry(eval(setting[2])):
                            logging.error(
                                "Fail to call {0} | {1} | {2}".format(
                                    str(obj), setting[1], setting[2]
                                )
                            )
                    elif restore_gui and setting[1] == "restoreState":
                        if not getattr(obj, setting[1])(eval(setting[2])):
                            logging.error(
                                "Fail to call {0} | {1} | {2}".format(
                                    str(obj), setting[1], setting[2]
                                )
                            )
                    elif len(setting) > 3 and setting[3]:
                        if restore_gui:
                            getattr(obj, setting[1])(eval(setting[2]))
                    else:
                        getattr(obj, setting[1])(setting[2])

                except Exception as e:
                    logging.error(
                        "Recall application setting failed to set attribute {0} | {1} | {2} | error {3}".format(
                            str(obj), setting[1], setting[2], e
                        )
                    )

    def putJumpGate(
        self, src, dst, src_id=None, dst_id=None, max_age=60 * 60 * 24 * 14
    ):
        """ """
        with Cache.SQLITE_WRITE_LOCK:
            # data is a blob, so we have to change it to buffer
            query = "DELETE FROM jumpbridge WHERE src LIKE ? or dst LIKE ? or src LIKE ? or dst LIKE ?"
            self.con.execute(query, (src, src, dst, dst))
            query = "INSERT INTO jumpbridge (src, dst, id_src, id_dst, modified, maxage) VALUES (?, ?, ?, ?, ?, ?)"
            self.con.execute(query, (src, dst, src_id, dst_id, time.time(), max_age))
            self.con.commit()

    def clearJumpGate(self, src):
        """ """
        with Cache.SQLITE_WRITE_LOCK:
            # data is a blob, so we have to change it to buffer
            query = "DELETE FROM jumpbridge WHERE src LIKE ? or dst LIKE ?"
            self.con.execute(query, (src, src))
            self.con.commit()

    def hasJumpGate(self, src) -> bool:
        """ """
        with Cache.SQLITE_WRITE_LOCK:
            # data is a blob, so we have to change it to buffer
            query = "SELECT SRC FROM jumpbridge WHERE src LIKE ? or dst LIKE ?"
            res = self.con.execute(query, (src, src)).fetchall()
        return len(res) > 0

    def getJumpGates(self, src=None):
        """ """
        selectquery = "SELECT src, ' ', dst FROM jumpbridge "
        founds = self.con.execute(selectquery, ()).fetchall()
        if len(founds) == 0:
            return None
        else:
            return founds
