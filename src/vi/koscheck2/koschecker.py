###########################################################################
#  Provi I - The Eye of Provience								          #
#  Copyright (C) 2017 Crypta Eve (crypta@crypta.tech )                    #
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
import logging

import grequests as grequests
import requests
from requests import RequestException, Request

from ..expiringdict import ExpiringDict

UNKNOWN = "No Result"
NOT_KOS = 'Not Kos'
KOS = "KOS"
RED_BY_LAST = "Red by last"
CVA_KOS_URL = "http://kos.cva-eve.org/api/"

class pilotData():
    def __init__(self, name):


class KOSCache():
    def __init__(self):
        self.pcache = ExpiringDict(max_len=1000, max_age_seconds=3600)
        self.acache = ExpiringDict(max_len=250, max_age_seconds=3600)
        self.ccache = ExpiringDict(max_len=500, max_age_seconds=3600)

    """
    Check a pilot for cached KOS Status
    """

    def checkPilot(self, id):
        if self.pcache.get(id) is None:
            return None
        else:
            return self.pcache.get(self, id, with_age=True)

    """
    Check an alliance for cached KOS Status
    """

    def checkAlliance(self, id):
        if self.acache.get(id) is None:
            return None
        else:
            return self.acache.get(self, id, with_age=True)

    """
    Check a corporation for cached KOS Status
    """

    def checkCorp(self, id):
        if self.ccache.get(id) is None:
            return None
        else:
            return self.ccache.get(self, id, with_age=True)

    """
    Add a pilot to the cache. 
    Stored as a boolean where true is KOS and false is Not KOS
    No result is not stored so that it can be checked again
    """

    def addPilot(self, id, kos):
        if self.pcache.get(id) is not None:
            self.pcache.pop(id)
        self.pcache[id] = kos

    """
    Add an alliance to the cache. 
    Stored as a boolean where true is KOS and false is Not KOS
    No result is not stored so that it can be checked again
    """

    def addAlliance(self, id, kos):
        if self.acache.get(id) is not None:
            self.acache.pop(id)
        self.acache[id] = kos

    """
    Add a corporation to the cache. 
    Stored as a boolean where true is KOS and false is Not KOS
    No result is not stored so that it can be checked again
    """

    def addCorp(self, id, kos):
        if self.ccache.get(id) is not None:
            self.ccache.pop(id)
        self.ccache[id] = kos


class CVAKosAPI():
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'None'})
        self.session.get(CVA_KOS_URL)

    def checkName(self, name):
        try:
            kosData = requests.get(CVA_KOS_URL, params={'c': 'json', 'type': 'unit', 'q': name}).json()
        except RequestException as e:
            kosData = None
            logging.error("Error on pilot KOS check request %s", str(e))
        return kosData

    def checkBulkNames(self, names):
        try:
            kosData = requests.get(CVA_KOS_URL, params={'c': 'json', 'type': 'multi', 'q': ','.join(names)}).json()
        except RequestException as e:
            kosData = None
            logging.error("Error on pilot KOS check request %s", str(e))
        return kosData

    def getSingleURL(self, name):
        req = Request('GET', CVA_KOS_URL,params = {'c': 'json', 'type': 'unit', 'q': name})
        prepped = self.session.prepare_request(req)
        return prepped.url

    def bulkURLGet(self, urls):
        rs = (grequests.get(u) for u in urls)
        return grequests.map(rs)

cache = KOSCache()

def cacheCheck(pilot):
    #First Check the cache, in the order Pilot > Alliance > Corporation
    plt = cache.checkPilot(pilot.id)
    if plt is not None:
        return plt

    ali = cache.checkAlliance(pilot.alliance)
    if ali is not None:
        return ali

    crp = cache.checkCorp(pilot.corporation)
    if crp is not None:
        return crp
