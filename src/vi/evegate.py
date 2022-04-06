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

import datetime
import json

from packaging import version

import requests
import logging

from vi.cache.cache import Cache
from vi.version import VERSION
ERROR = -1
NOT_EXISTS = 0
EXISTS = 1


def charNameToId(name, use_outdated=False):
    """ Uses the EVE API to convert a character name to their ID
    """
    cache_key = "_".join(("name", "id", name))
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated)
    if cached_id:
        return cached_id
    else:
        url = "https://esi.evetech.net/latest/search/?categories=character&datasource=tranquility&language=en-us&search={iname}&strict=true"
        response = requests.get(url.format(iname=name))
        response.raise_for_status()
        content = response.json()
        if "character" in content.keys():
            for idFound in content["character"]:
                url = "https://esi.evetech.net/latest/characters/{id}/?datasource=tranquility".format(id=idFound)
                response = requests.get(url.format(name))
                response.raise_for_status()
                details = response.json()
                if "name" in details.keys():
                    name_found = details["name"]
                    if name_found.lower() == name.lower():
                        cache.putIntoCache(cache_key, idFound, 60 * 60 * 24 * 365)
                        return idFound
    return None


def namesToIds(names, use_outdated=False):
    """ Uses the EVE API to convert a list of names to ids_to_names
        names: list of names
        returns a dict: key=name, value=id
    """
    if len(names) == 0:
        return {}
    data = {}
    api_check_names = set()
    cache = Cache()
    # do we have already something in the cache?
    for name in names:
        cache_key = "_".join(("id", "name", name))
        id_from_cache = cache.getFromCache(cache_key, use_outdated)
        if id_from_cache:
            data[name] = id_from_cache
        else:
            api_check_names.add(name)

    try:
        # not in cache? asking the EVE API
        if len(api_check_names) > 0:
            list_of_name = ""
            for name in names:
                if list_of_name != "":
                    list_of_name = list_of_name + ","
                list_of_name = list_of_name + "\"{}\"".format(name)
            url = "https://esi.evetech.net/latest/universe/ids/?datasource=tranquility"
            response = requests.post(url, data="[{}]".format(list_of_name))
            response.raise_for_status()
            content = response.json()
            if "characters" in content.keys():
                for char in content["characters"]:
                    data[char["name"]] = char["id"]
            if "systems" in content.keys():
                for system in content["systems"]:
                    data[system["name"]] = system["id"]
            if "regions" in content.keys():
                for region in content["regions"]:
                    data[region["name"]] = region["id"]

            # writing the cache
            for name in data:
                cache_key = "_".join(("id", "name", name))
                cache.putIntoCache(cache_key, data[name], 60 * 60 * 24 * 365)
    except Exception as e:
        logging.error("Exception during namesToIds: %s", e)
    return data


def getAllRegions(use_outdated=False):
    """ Uses the EVE API to get the list of all region ids
    """
    cache = Cache()
    all_systems = cache.getFromCache("universe_regions", use_outdated)
    if all_systems is not None:
        return eval(all_systems)
    else:
        url = "https://esi.evetech.net/latest/universe/regions/?datasource=tranquility"
        response = requests.get(url)
        response.raise_for_status()
        content = response.json()
        cache.putIntoCache("universe_regions", str(content), 60 * 60 * 24 * 365)
        return content


def idsToNames(ids, use_outdated=False):
    """ Returns the names for ids
        ids = iterable list of ids
        returns a dict key = id, value = name
    """
    data = {}
    if len(ids) == 0:
        return data
    api_check_ids = set()
    cache = Cache()

    # something already in the cache?
    for checked_id in ids:
        cache_key = u"_".join(("name", "id", str(checked_id)))
        name = cache.getFromCache(cache_key, use_outdated)
        if name:
            data[checked_id] = name
        else:
            api_check_ids.add(checked_id)
    if len(api_check_ids) == 0:
        return data

    try:
        list_of_ids = ""
        for checked_id in api_check_ids:
            if list_of_ids != "":
                list_of_ids = list_of_ids + ","
            list_of_ids = list_of_ids + str(checked_id)
        url = "https://esi.evetech.net/latest/universe/names/?datasource=tranquility"
        response = requests.post(url, data="[{}]".format(list_of_ids))
        response.raise_for_status()
        content = response.json()
        if len(content) > 0:
            for elem in content:
                data[elem["id"]] = elem["name"]
            # and writing into cache
            for checked_id in api_check_ids:
                cache_key = u"_".join(("name", "id", str(checked_id)))
                if checked_id in data.keys():
                    cache.putIntoCache(cache_key, data[int(checked_id)], 60 * 60 * 24 * 365)
    except Exception as e:
        logging.error("Exception during idsToNames: %s", e)
    return data


def getAvatarForPlayer(char_name):
    """ Downloading the avatar for a player/character
        char_name = name of the character
        returns None if something gone wrong
    """
    avatar = None
    try:
        char_id = charNameToId(char_name)
        if char_id:
            image_url = "https://images.evetech.net/characters/{id}/portrait?tenant=tranquility&size={size}"
            response = requests.get(image_url.format(id=char_id, size=64))
            response.raise_for_status()
            avatar = response.content

    except Exception as e:
        logging.error("Exception during getAvatarForPlayer: %s", e)
        avatar = None
    return avatar


def checkPlayerName(char_name):
    """ Checking on esi for an exiting exact player name
        returns 1 if exists, 0 if not and -1 if an error occurred
    """
    if not char_name:
        return ERROR
    try:
        url = "https://esi.evetech.net/latest/search/?categories=character&datasource=tranquility&language=en&search={charname}&strict=true"
        response = requests.get(url.format(charname=char_name))
        response.raise_for_status()
        content = response.json()
        if "character" in content.keys():
            if len(content["character"]):
                return EXISTS
            else:
                return NOT_EXISTS
        else:
            return ERROR
    except Exception as e:
        logging.error("Exception on checkPlayerName: %s", e)
    return ERROR


def currentEveTime():
    """ Returns the current eve-time as a datetime.datetime
    """
    return datetime.datetime.utcnow()

def getCharInfoForCharId(char_id, use_outdated=False):
    cache_key = u"_".join(("playerinfo_id_", str(char_id)))
    cache = Cache()
    char_info = cache.getFromCache(cache_key, use_outdated)
    if char_info is not None:
        char_info = eval(char_info)
    else:
        try:
            char_id = int(char_id)
            url = "https://esi.evetech.net/latest/characters/{id}/?datasource=tranquility".format(id=char_id)
            response = requests.get(url)
            response.raise_for_status()
            char_info = eval(response.text)
            # should be valid for up to three days
            cache.putIntoCache(cache_key, response.text, 86400)
        except requests.exceptions.RequestException as e:
            # We get a 400 when we pass non-pilot names for KOS check so fail silently for that one only
            if e.response.status_code != 400:
                logging.error("Exception during getCharInfoForCharId: %s", str(e))
    return char_info




def getCorpIdsForCharId(char_id, use_outdated=True):
    """ Returns a list with the ids if the corporation history of a charId
        returns a list of only the corp ids
    """
    cache_key = u"_".join(("corp_history_id_", str(char_id)))
    cache = Cache()
    corp_ids = cache.getFromCache(cache_key, use_outdated)
    if corp_ids is not None:
        corp_ids = eval(corp_ids)
    else:
        try:
            char_id = int(char_id)
            url = "https://esi.evetech.net/latest/characters/{id}/corporationhistory/?datasource=tranquility".format(id=char_id)
            response = requests.get(url)
            response.raise_for_status()
            corp_ids = response.json()
            cache.putIntoCache(cache_key, response.text, 86400)
        except requests.exceptions.RequestException as e:
            # We get a 400 when we pass non-pilot names for KOS check so fail silently for that one only
            if e.response.status_code != 400:
                logging.error("Exception during getCharInfoForCharId: %s", str(e))
    id_list = list()
    for elem in corp_ids:
        id_list.append(elem["corporation_id"])
    return id_list


def getCurrentCorpForCharId(char_id, use_outdated=True):
    """ Returns the ID of the players current corporation.
    """
    info = getCharInfoForCharId(char_id, use_outdated)
    if info and "corporation_id" in info.keys():
        return info["corporation_id"]
    else:
        logging.error("Unable to get corporation_id of char id:{}".format(char_id))
        return None


def getSystemStatistics():
    """ Reads the informations for all solarsystems from the EVE API
        Reads a dict like:
            systemid: "jumps", "shipkills", "factionkills", "podkills"
    """
    data = {}
    system_data = {}
    cache = Cache()
    # first the data for the jumps
    cache_key = "jumpstatistic"
    jump_data = cache.getFromCache(cache_key)

    try:
        if jump_data is None:
            jump_data = {}
            url = "https://esi.evetech.net/latest/universe/system_jumps/?datasource=tranquility"
            response = requests.get(url)
            response.raise_for_status()
            resp = response.json()
            for row in resp:
                jump_data[int(row["system_id"])] = int(row["ship_jumps"])

            cache.putIntoCache(cache_key, json.dumps(jump_data), 3600)
        else:
            jump_data = json.loads(jump_data)

        # now the further data
        cache_key = "systemstatistic"
        system_data = cache.getFromCache(cache_key)

        if system_data is None:
            system_data = {}
            url = "https://esi.evetech.net/latest/universe/system_kills/?datasource=tranquility"
            response = requests.get(url)
            response.raise_for_status()
            resp = response.json()
            for row in resp:
                system_data[int(row["system_id"])] = {"ship": int(row["ship_kills"]),
                                                      "faction": int(row["npc_kills"]),
                                                      "pod": int(row["pod_kills"])}

            cache.putIntoCache(cache_key, json.dumps(system_data), 3600)
        else:
            system_data = json.loads(system_data)
    except Exception as e:
        logging.error("Exception during getSystemStatistics: : %s", e)

    # We collected all data (or loaded them from cache) - now zip it together
    for i, v in jump_data.items():
        i = int(i)
        if i not in data:
            data[i] = {"shipkills": 0, "factionkills": 0, "podkills": 0}
        data[i]["jumps"] = v
    for i, v in system_data.items():
        i = int(i)
        if i not in data:
            data[i] = {"jumps": 0}
        data[i]["shipkills"] = v["ship"] if "ship" in v else 0
        data[i]["factionkills"] = v["faction"] if "faction" in v else 0
        data[i]["podkills"] = v["pod"] if "pod" in v else 0
    return data


def secondsTillDowntime():
    """ Return the seconds till the next downtime"""
    now = currentEveTime()
    target = now
    if now.hour > 11:
        target = target + datetime.timedelta(1)
    target = datetime.datetime(target.year, target.month, target.day, 11, 0, 0, 0)
    delta = target - now
    return delta.seconds

def getRouteFromEveOnline(jumpGates, src, dst):
    """build rout respecting jump bridges
        returns the list of systems to travel to
    """
    route_elems = ""
    for elem in jumpGates:
        if route_elems != "":
            route_elems = route_elems + ","
        route_elems = route_elems + "{}|{}".format(elem[0], elem[1])

    req = "https://esi.evetech.net/v1/route/{}/{}/?connections={}".format(src, dst, route_elems)
    result = requests.get(req)
    result.raise_for_status()
    return eval(result.text)


def getIncursions(use_outdated=False):
    """builds a list of incursion dicts cached 300s
    """
    cache = Cache()
    cache_key = "incursions"
    result = cache.getFromCache(cache_key, use_outdated)
    if result:
        incursion_list = json.loads(result)
    else:
        req = "https://esi.evetech.net/latest/incursions/?datasource=tranquility"
        result = requests.get(req)
        result.raise_for_status()
        cache.putIntoCache(cache_key, result.text, 300)
        incursion_list = result.json()
    return incursion_list

def getIncursionSystemsIds(use_outdated=False):
    res = list()
    incursion_list = getIncursions(use_outdated)
    for constellations in incursion_list:
        for sys in constellations["infested_solar_systems"]:
            res.append(sys)
    return res


def getCampaigns(use_outdated=False):
    """builds a list of reinforced campaigns for IHUB  and TCU dicts cached 60s
    """
    cache = Cache()
    cache_key = "campaigns"
    result = cache.getFromCache(cache_key, use_outdated)
    if result:
        campaigns_list = json.loads(result)
    else:
        req = "https://esi.evetech.net/latest/sovereignty/campaigns/?datasource=tranquility"
        result = requests.get(req)
        result.raise_for_status()
        cache.putIntoCache(cache_key, result.text, 60)#5 seconds from esi
        campaigns_list = result.json()
    return campaigns_list


def getCampaignsSystemsIds(use_outdated=False):
    """builds a list of system ids being part of campaigns for hubs and tcus dicts cached 60s
    """
    curr_campaigns = list()
    for system in getCampaigns(use_outdated):
        curr_campaigns.append(system["solar_system_id"])
    return curr_campaigns

def getSovereignty(use_outdated=False, fore_refresh=False):
    """builds a list of reinforced campaigns for hubs and tcus dicts cached 60s
       https://esi.evetech.net/ui/?version=latest#/Sovereignty/get_sovereignty_map
    """
    cache = Cache()
    cache_key = "sovereignty"
    result = cache.getFromCache(cache_key, use_outdated)
    if result and not fore_refresh:
        campaigns_list = json.loads(result)
    else:
        req = "https://esi.evetech.net/latest/sovereignty/map/?datasource=tranquility"
        result = requests.get(req)
        result.raise_for_status()
        cache.putIntoCache(cache_key, result.text, 3600)
        campaigns_list = result.json()
    return campaigns_list


def getPlayerSovereignty(use_outdated=False, fore_refresh=True, show_npc=True, callback=None):
    seq = ""
    def update_callback(seq):
        if callback:
            seq = seq + "."
            callback("updating alliance and system database {}".format(seq))
            if len(seq) > 40:
                seq = ""
        return seq

    cache_key = "player_sovereignty"
    cache = Cache()
    cached_result = cache.getFromCache(cache_key, use_outdated)
    if cached_result and not fore_refresh:
        return json.loads(cached_result)
    else:
        player_sov = dict()
        npc_sov = dict()
        list_of_all_alliances = list()
        list_of_all_factions = list()
        for sov in getSovereignty(use_outdated,fore_refresh):
            if len(sov) > 2:
                player_sov[str(sov["system_id"])] = sov
            elif show_npc and len(sov) > 1:
                list_of_all_factions.append(sov["faction_id"])
                npc_sov[str(sov["system_id"])] = sov
        for sov in player_sov.values():
            if "alliance_id" in sov.keys():
                alli_id = sov["alliance_id"]
                sov["ticker"] = getAlliances(alli_id)["ticker"]
            seq = update_callback(seq)

        if show_npc:
            npc_list = idsToNames(list_of_all_factions)
            for sov in npc_sov.values():
                if "faction_id" in sov.keys():
                    faction_id = sov["faction_id"]
                    sov["ticker"] = npc_list[faction_id]
                seq = update_callback(seq)

            player_sov.update(npc_sov)

        cache.putIntoCache(cache_key, json.dumps(player_sov), 3600)
        return player_sov

class JumpBridge(object):
    def __init__(self, name:str, structureId:int, systemId:int, ownerId:int):
        tok = name.split(" ")
        self.src_system_name = tok[0]
        self.dst_system_name = tok[2]
        self.name = name
        self.structureId = structureId
        self.systemId = systemId
        self.ownerId = ownerId
        self.paired = False
        self.links = 0


def sanityCheckGates(gates):
    """ grant that all item of gates builds valid pairs of jump bridges src<->dst and also dst<->src
        all other items will be removed
    """
    for gate in gates:
        for elem in gates:
            if (gate.src_system_name == elem.dst_system_name) and (gate.dst_system_name == elem.src_system_name):
                gate.paired = True
                elem.paired = True

    for gate in gates:
        if not gate.paired:
            gates.remove(gate)
    return gates


def countCheckGates( gates ):
    for gate in gates:
        for elem in gates:
            if (gate.src_system_name == elem.src_system_name) or (gate.src_system_name == elem.dst_system_name):
                gate.links = gate.links+1


def getAllJumpGates(nameChar:str,systemName="", callback=None, use_outdated=False):
    """ updates all jump bridge data via api searching for names which have a substring  %20%C2%BB%20 means " >> "
    """
    if nameChar == None:
        logging.error("getAllJumpGates needs the eve-online api account.")
        return None
    token = checkTokenTimeLine(getTokenOfChar(nameChar))
    if token == None:
        logging.error("getAllJumpGates needs the eve-online api account.")
        return None

    req = "https://esi.evetech.net/v3/characters/{id}/search/?datasource=tranquility&categories=structure&search={sys}%20%C2%BB%20&token={tok}".format(id=token.CharacterID, tok=token.access_token,sys=systemName)
    res = requests.get(req)
    res.raise_for_status()
    structs = eval(res.text)
    gates = list()
    if token and len(structs):
        process = 0
        if callback and not callback(len(structs["structure"]), process):
            return gates
        for id_structure in structs["structure"]:
            item = getStructures(nameChar=nameChar, id_structure=id_structure, use_outdated=use_outdated)
            process = process + 1
            if callback and not callback(len(structs["structure"]), process):
                break
            try:
                if "type_id" in item.keys():
                    if item["type_id"] == 35841 or item["type_id"] == 35837:
                        gates.append(JumpBridge(name=item["name"], systemId=item["solar_system_id"], structureId=id_structure,ownerId=item["owner_id"]))
            except Exception as e:
                pass
    #gates=sanityCheckGates(gates)
    countCheckGates(gates)
    return gates


def writeGatestToFile(gates, filename="jb.txt"):
    gates_list = list()
    with open(filename, "w")as gf:
        for gate in gates:
            s_t_d = "{} <-> {}".format(gate.src_system_name, gate.dst_system_name)
            d_t_s = "{} <-> {}".format(gate.dst_system_name, gate.src_system_name)
            if (not s_t_d in gates_list) and (not d_t_s in gates_list):
                gf.write("{} {} {} {} ({} {})\n".format(s_t_d, gate.systemId, gate.structureId, gate.ownerId, gate.links,gate.paired))
                gates_list.append(s_t_d)
        gf.close()

def getStargateInformation(starget_id,use_outdated=False):
    """gets the solar system info from system id
    """
    cache_key = "_".join(("universe", "systems", str(starget_id)))
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated)
    if cached_id:
        return eval(cached_id)
    else:
        req = "https://esi.evetech.net/latest/universe/stargates/{}/?datasource=tranquility&language=en".format(starget_id)
        res_system = requests.get(req)
        res_system.raise_for_status()
        cache.putIntoCache(cache_key, res_system.text)
        return res_system.json()

def getSolarSystemInformation(system_id,use_outdated=False):
    """gets the solar system info from system id
    """
    cache_key = "_".join(("universe", "systems", str(system_id)))
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated)
    if cached_id:
        return eval(cached_id)
    else:
        req = "https://esi.evetech.net/latest/universe/systems/{}/?datasource=tranquility&language=en".format(system_id)
        res_system = requests.get(req)
        res_system.raise_for_status()
        cache.putIntoCache(cache_key, res_system.text)
        return res_system.json()


def getAlliances(alliance_id, use_outdated=True):
    """gets the alliance from allicance id
    """
    cache_key = "_".join(("alliance", str(alliance_id)))
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated)
    if cached_id:
        return eval(cached_id)
    else:
        req = "https://esi.evetech.net/latest/alliances/{}/?datasource=tranquility".format(alliance_id)
        res_system = requests.get(req)
        res_system.raise_for_status()
        cache.putIntoCache(cache_key, res_system.text, 3600)
        return res_system.json()

def getRegionInformation(region_id:int,use_outdated=False):
    cache_key = "_".join(("universe", "regions", str(region_id)))
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated)
    if cached_id:
        return eval(cached_id)
    else:
        req = "https://esi.evetech.net/latest/universe/regions/{}/?datasource=tranquility&language=en".format(region_id)
        res_region = requests.get(req)
        res_region.raise_for_status()
        cache.putIntoCache(cache_key, res_region.text, 24*60*60)
        return res_region.json()


def getConstellationInformation(constellation_id:int,use_outdated=False):
    cache_key = "_".join(("universe", "constellations", str(constellation_id)))
    cache = Cache()
    cached_id = cache.getFromCache(cache_key, use_outdated)
    if cached_id:
        return eval(cached_id)
    else:
        req = "https://esi.evetech.net/latest/universe/constellations/{}/?datasource=tranquility&language=en".format(constellation_id)
        res_constellation = requests.get(req)
        res_constellation.raise_for_status()
        cache.putIntoCache(cache_key, res_constellation.text)
        return res_constellation.json()

def applyRouteToEveOnline(name_char, jump_list):
    if name_char is None:
        logging.error("applyRouteToEveOnline needs the eve-online api account.")
        return None
    for id_system in jump_list:
        if hasAnsiblex(id_system):
            pass
        else:
            setDestination(name_char, id_system, beginning=False, clear_all=False)


SHIPIDS = [24692,22448,2836,23919,32872,642,11936,17726,37604,29266,11969,628,23757,11202,28850,643,11938,32305,17922,22466,33468,608,625,29337,11567,648,582,33820,11985,630,1944,17920,37480,632,34328,598,12013,16229,33151,599,12731,11192,42246,45647,17619,672,32788,621,17634,16240,633,11993,33675,20185,11182,42243,23915,33397,48648,11196,22468,16236,583,34317,32876,16238,34496,17476,12729,11176,2161,37453,17926,11184,20125,16231,17720,42242,47269,22474,17928,37457,12023,12017,645,32307,32874,24698,33153,17932,52254,49711,12011,3532,617,37135,44995,12044,22442,655,671,22460,32790,589,634,29344,11957,17841,20189,16227,35781,22464,32207,11129,33816,17715,3756,11940,28710,21097,584,37455,11987,11011,21628,24696,33155,11381,11379,35683,22852,11172,33079,22452,605,651,12034,11961,22544,24702,33157,48636,11387,24690,601,52252,607,615,35779,596,12753,17703,594,590,30842,12042,12005,657,34828,11400,11174,602,49710,37458,11194,45649,28661,654,11971,29986,33513,47271,3764,37606,45645,29990,17738,22548,24694,29248,37483,11186,3516,624,652,12032,44996,12747,609,37456,641,13202,17728,603,656,32811,4363,4388,32209,11132,37605,623,42241,45534,33395,19724,12015,24700,4306,19722,592,11377,650,52250,33472,24483,22470,17736,37607,2998,28846,23913,20187,12745,2006,17709,11989,11995,635,4302,28606,33818,620,29340,44993,28659,22440,17718,12021,19726,11965,33677,37481,42244,47466,2863,586,17480,16233,12733,33697,29988,20183,12735,597,12038,42245,23773,11963,11178,17918,638,17636,26840,588,22428,17812,11393,17478,19720,3514,28844,587,49712,24688,11959,28352,629,22456,12019,37460,11978,640,4005,32309,631,29336,11190,19744,11942,22430,22546,54731,585,22444,622,17713,11198,37482,54732,33470,17924,42685,34562,33081,4308,32878,11200,649,639,17732,26842,29984,52267,37459,23911,627,16242,54733,48635,591,4310,593,644,32311,2834,11999,3518,42132,42126,28665,47270,42124,606,42125,42133,11365,32880,626,17843,12743,45531,34590,3766,37454,17722,17740,33083,45530,22446,33673,22436,11371,17930,653,23917,49713,12003,2078,52907]

SHIPNAMES = (u'ABADDON',u'ABSOLUTION',u'ADRESTIA',u'AEON',u'ALGOS',u'APOCALYPSE',
            u'APOCALYPSE IMPERIAL ISSUE',u'APOCALYPSE NAVY ISSUE',u'APOSTLE',u'APOTHEOSIS',u'ARAZU',u'ARBITRATOR',
            u'ARCHON',u'ARES',u'ARK',u'ARMAGEDDON',u'ARMAGEDDON IMPERIAL ISSUE',
            u'ARMAGEDDON NAVY ISSUE',u'ASHIMMU',u'ASTARTE',u'ASTERO',u'ATRON',u'AUGOROR',u'AUGOROR NAVY ISSUE',
            u'AVATAR',u'BADGER',u'BANTAM',u'BARGHEST',u'BASILISK',u'BELLICOSE',u'BESTOWER',u'BHAALGORN',
            u'BIFROST',u'BLACKBIRD',u'BOWHEAD',u'BREACHER',u'BROADSWORD',u'BRUTIX',
            u'BRUTIX NAVY ISSUE',u'BURST',u'BUSTARD',u'BUZZARD',u'CAEDES',u'CAIMAN',u'CALDARI NAVY HOOKBILL',
            u'CALDARI SHUTTLE',u'CAMBION',u'CARACAL',u'CARACAL NAVY ISSUE',u'CATALYST',u'CELESTIS',u'CERBERUS',
            u'CHAMELEON',u'CHARON',u'CHEETAH',u'CHEMOSH',u'CHIMERA',u'CHREMOAS',u'CITIZEN VENTURE',u'CLAW',
            u'CLAYMORE',u'COERCER',u'CONDOR',u'CONFESSOR',u'CORAX',u'CORMORANT',
            u'COUNCIL DIPLOMATIC SHUTTLE',u'COVETOR',u'CRANE',u'CROW',u'CRUCIFIER',u'CRUCIFIER NAVY ISSUE',u'CRUOR',
            u'CRUSADER',u'CURSE',u'CYCLONE',u'CYNABAL',u'DAGON',u'DAMAVIK',u'DAMNATION',u'DAREDEVIL',
            u'DEACON',u'DEIMOS',u'DEVOTER',u'DOMINIX',u'DOMINIX NAVY ISSUE',u'DRAGOON',u'DRAKE',
            u'DRAKE NAVY ISSUE',u'DRAMIEL',u'DRAUGUR',u'DREKAVAC',u'EAGLE',u'ECHELON',u'ECHO',u'ENDURANCE',
            u'ENFORCER',u'ENYO',u'EOS',u'EPITHAL',u'EREBUS',u'ERIS',u'ETANA',u'EXECUTIONER',u'EXEQUROR',
            u'EXEQUROR NAVY ISSUE',u'FALCON',u'FEDERATION NAVY COMET',u'FENRIR',u'FEROX',u'FIEND',u'FLYCATCHER',
            u'FREKI',u'GALLENTE SHUTTLE',u'GARMUR',u'GILA',u'GNOSIS',u'GOLD MAGNATE',u'GOLEM',
            u'GORU\'S SHUTTLE',u'GRIFFIN',u'GRIFFIN NAVY ISSUE',u'GUARDIAN',u'GUARDIAN-VEXOR',
            u'GURISTAS SHUTTLE',u'HARBINGER',u'HARBINGER NAVY ISSUE',u'HARPY',u'HAWK',u'HECATE',u'HEL',u'HELIOS',
            u'HEMATOS',u'HERETIC',u'HERON',u'HOARDER',u'HOUND',u'HUGINN',u'HULK',u'HURRICANE',
            u'HURRICANE FLEET ISSUE',u'HYDRA',u'HYENA',u'HYPERION',u'IBIS',u'IKITURSA',u'IMICUS',u'IMMOLATOR',u'IMP',
            u'IMPAIROR',u'IMPEL',u'IMPERIAL NAVY SLICER',u'INCURSUS',u'INQUISITOR',
            u'INTERBUS SHUTTLE',u'ISHKUR',u'ISHTAR',u'ITERON MARK V',u'JACKDAW',u'JAGUAR',u'KERES',u'KESTREL',
            u'KIKIMORA',u'KIRIN',u'KITSUNE',u'KOMODO',u'KRONOS',u'KRYOS',u'LACHESIS',u'LEGION',u'LEOPARD',
            u'LESHAK',u'LEVIATHAN',u'LIF',u'LOGGERHEAD',u'LOKI',u'MACHARIEL',u'MACKINAW',u'MAELSTROM',
            u'MAGNATE',u'MAGUS',u'MALEDICTION',u'MALICE',u'MALLER',u'MAMMOTH',u'MANTICORE',u'MARSHAL',
            u'MASTODON',u'MAULUS',u'MAULUS NAVY ISSUE',u'MEGATHRON',u'MEGATHRON FEDERATE ISSUE',
            u'MEGATHRON NAVY ISSUE',u'MERLIN',u'MIASMOS',u'MIASMOS AMASTRIS EDITION',
            u'MIASMOS QUAFE ULTRA EDITION',u'MIASMOS QUAFE ULTRAMARINE EDITION',u'MIMIR',u'MINMATAR SHUTTLE',
            u'MINOKAWA',u'MOA',u'MOLOK',u'MONITOR',u'MORACHA',u'MOROS',u'MUNINN',u'MYRMIDON',u'NAGA',
            u'NAGLFAR',u'NAVITAS',u'NEMESIS',u'NEREUS',u'NERGAL',u'NESTOR',u'NIDHOGGUR',u'NIGHTHAWK',
            u'NIGHTMARE',u'NINAZU',u'NOCTIS',u'NOMAD',u'NYX',u'OBELISK',u'OCCATOR',u'OMEN',
            u'OMEN NAVY ISSUE',u'ONEIROS',u'ONYX',u'OPUX LUXURY YACHT',u'ORACLE',u'ORCA',u'ORTHRUS',u'OSPREY',
            u'OSPREY NAVY ISSUE',u'PACIFIER',u'PALADIN',u'PANTHER',u'PHANTASM',u'PHOBOS',u'PHOENIX',u'PILGRIM',
            u'POLICE PURSUIT COMET',u'PONTIFEX',u'PORPOISE',u'PRAXIS',u'PRIMAE',u'PROBE',u'PROCURER',u'PROPHECY',
            u'PRORATOR',u'PROSPECT',u'PROTEUS',u'PROVIDENCE',u'PROWLER',u'PUNISHER',u'PURIFIER',u'RABISU',
            u'RAGNAROK',u'RAPIER',u'RAPTOR',u'RATTLESNAKE',u'RAVEN',u'RAVEN NAVY ISSUE',
            u'RAVEN STATE ISSUE',u'REAPER',u'REDEEMER',u'REPUBLIC FLEET FIRETAIL',u'RETRIBUTION',u'RETRIEVER',
            u'REVELATION',u'REVENANT',u'RHEA',u'RIFTER',u'RODIVA',u'ROKH',u'ROOK',u'RORQUAL',u'RUPTURE',
            u'SABRE',u'SACRILEGE',u'SCALPEL',u'SCIMITAR',u'SCORPION',u'SCORPION ISHUKONE WATCH',
            u'SCORPION NAVY ISSUE',u'SCYTHE',u'SCYTHE FLEET ISSUE',u'SENTINEL',u'SIGIL',u'SILVER MAGNATE',u'SIN',
            u'SKIFF',u'SKYBREAKER',u'SLASHER',u'SLEIPNIR',u'STABBER',u'STABBER FLEET ISSUE',
            u'STILETTO',u'STORK',u'STORMBRINGER',u'STRATIOS',u'SUCCUBUS',u'SUNESIS',u'SVIPUL',u'TAIPAN',
            u'TALOS',u'TALWAR',u'TARANIS',u'TAYRA',u'TEMPEST',u'TEMPEST FLEET ISSUE',
            u'TEMPEST TRIBAL ISSUE',u'TENGU',u'TEST SITE MALLER',u'THALIA',u'THANATOS',u'THORAX',u'THRASHER',
            u'THUNDERCHILD',u'TIAMAT',u'TORMENTOR',u'TORNADO',u'TRISTAN',u'TYPHOON',u'TYPHOON FLEET ISSUE',
            u'UTU',u'VAGABOND',u'VANGEL',u'VANGUARD',u'VANQUISHER',u'VARGUR',u'VEDMAK',u'VEHEMENT',
            u'VELATOR',u'VENDETTA',u'VENERABLE',u'VENGEANCE',u'VENTURE',u'VEXOR',u'VEXOR NAVY ISSUE',
            u'VIATOR',u'VICTOR',u'VICTORIEUX LUXURY YACHT',u'VIGIL',u'VIGIL FLEET ISSUE',
            u'VIGILANT',u'VINDICATOR',u'VIOLATOR',u'VIRTUOSO',u'VULTURE',u'WHIPTAIL',u'WIDOW',u'WOLF',
            u'WORM',u'WREATHE',u'WYVERN',u'ZARMAZD',u'ZEALOT',u'ZEPHYR',u'ZIRNITRA')

SHIPNAMES = sorted(SHIPNAMES, key=lambda x: len(x), reverse=True)

PC_CORPS_IDS = [ 1000032, 1000164, 1000033, 1000165, 1000297, 1000034, 1000166, 1000298, 1000035, 1000167, 1000299, 1000036, 1000168, 1000300, 1000037, 1000169, 1000301, 1000038,  1000170, 1000039, 1000171, 1000040, 1000172, 1000041, 1000173, 1000042, 1000174, 1000043, 1000175, 1000044, 1000176, 1000045, 1000177, 1000046, 1000178, 1000047, 1000179, 1000048, 1000180, 1000049, 1000181, 1000050, 1000182, 1000051, 1000052, 1000053,  1000054, 1000055, 1000056, 1000057, 1000058, 1000059, 1000060, 1000061,  1000193, 1000062, 1000063, 1000064, 1000065, 1000197, 1000066, 1000198, 1000067, 1000068,  1000069, 1000070, 1000071, 1000072, 1000073, 1000205, 1000074, 1000206,  1000075, 1000207, 1000076, 1000208, 1000077, 1000078, 1000079, 1000080, 1000081, 1000213, 1000082, 1000214, 1000083, 1000215, 1000084, 1000216, 1000085, 1000217,  1000086, 1000218, 1000087, 1000219, 1000088, 1000220, 1000089, 1000090, 1000222, 1000091, 1000223, 1000092, 1000224, 1000093, 1000225, 1000094, 1000226, 1000095,  1000227, 1000096, 1000228, 1000097, 1000229, 1000098, 1000230, 1000099, 1000231, 1000100, 1000232, 1000101, 1000233, 1000102, 1000234, 1000103, 1000235, 1000104,  1000236, 1000105, 1000237, 1000106, 1000238, 1000107, 1000239, 1000108, 1000240, 1000109, 1000110, 1000111, 1000243, 1000112, 1000244, 1000113, 1000245, 1000114,  1000246, 1000115, 1000247, 1000116, 1000248, 1000117, 1000249, 1000118, 1000250, 1000119, 1000251, 1000120, 1000252, 1000121, 1000253, 1000122, 1000254, 1000123,  1000255, 1000124, 1000256, 1000125, 1000257, 1000126, 1000258, 1000127, 1000259, 1000128, 1000129, 1000261, 1000130, 1000262, 1000131, 1000263, 1000132, 1000001,  1000133, 1000002, 1000134, 1000003, 1000135, 1000004, 1000136, 1000005, 1000137, 1000006, 1000138, 1000270, 1000007, 1000139, 1000271, 1000008, 1000140, 1000009,  1000141, 1000010, 1000142, 1000274, 1000011, 1000143, 1000012, 1000144, 1000276, 1000013, 1000145, 1000277, 1000409, 1000014, 1000146, 1000015, 1000147, 1000279,  1000016, 1000148, 1000280, 1000017, 1000149, 1000281, 1000018, 1000150, 1000282, 1000019, 1000151, 1000283, 1000020, 1000152, 1000284, 1000021, 1000153, 1000285,  1000022, 1000154, 1000286, 1000023, 1000155, 1000287, 1000024, 1000156, 1000288, 1000025, 1000157, 1000289, 1000026, 1000158, 1000290, 1000027, 1000159, 1000291,  1000028, 1000160, 1000292, 1000029, 1000161, 1000293, 1000030, 1000162, 1000294, 1000031, 1000163]

NPC_CORPS = (u'Republic Justice Department', u'House of Records', u'24th Imperial Crusade', u'Template:NPC corporation',
             u'Khanid Works', u'Caldari Steel', u'School of Applied Knowledge', u'NOH Recruitment Center',
             u'Sarum Family', u'Impro', u'Guristas', u'Carthum Conglomerate', u'Secure Commerce Commission',
             u'Amarr Trade Registry', u'Anonymous', u'Federal Defence Union', u'Federal Freight', u'Ardishapur Family',
             u'Thukker Mix', u'Sebiestor tribe', u'Core Complexion Inc.', u'Federal Navy Academy', u'Dominations',
             u'Ishukone Watch', u'Kaalakiota Corporation', u'Nurtura', u'Center for Advanced Studies', u'CONCORD',
             u'Ammatar Consulate', u'HZO Refinery', u'Joint Harvesting', u'Caldari Funds Unlimited', u'Propel Dynamics',
             u'Caldari Navy', u'Amarr Navy', u'Amarr Certified News', u'Serpentis Corporation', u'CreoDron',
             u'Society of Conscious Thought', u'Shapeset', u'Kor-Azor Family', u'Khanid Transport',
             u'Imperial Chancellor', u'Rapid Assembly', u'Khanid Innovation', u'Combined Harvest',
             u'Peace and Order Unit', u'The Leisure Group', u'CBD Sell Division', u'DED', u'Six Kin Development',
             u'Zero-G Research Firm', u'Defiants', u'Noble Appliances', u'Guristas Production', u'Intaki Space Police',
             u'Spacelane Patrol', u'User talk:ISD Crystal Carbonide', u'Caldari Provisions', u'Brutor tribe',
             u'True Power', u'Nefantar Miner Association', u'Garoun Investment Bank', u'FedMart', u'Prosper',
             u'Inherent Implants', u'Chief Executive Panel', u'Top Down', u'Federation Customs',
             u'Lai Dai Protection Service', u'Roden Shipyards', u'Wiyrkomi Peace Corps', u'Allotek Industries',
             u'Minedrill', u'Court Chamberlain', u'Intaki Syndicate', u'Caldari Constructions',
             u'State and Region Bank', u'Amarr Civil Service', u'Pend Insurance', u'Zainou', u'Material Institute',
             u'Republic Fleet', u'Intaki Bank', u'Hyasyoda Corporation', u'Nugoeihuvi Corporation', u'Modern Finances',
             u'Bank of Luminaire', u'Ministry of War', u'Genolution', u'Pator Tech School', u'Hedion University',
             u'Kador Family', u'Ducia Foundry', u'Prompt Delivery', u'Trust Partners', u'Material Acquisition',
             u'Jovian Directorate', u'DUST 514 NPC Corporations', u'Ministry of Assessment', u'Expert Distribution',
             u'Ishukone Corporation', u'Caldari Business Tribunal', u'The Scope', u'Eifyr and Co.',
             u'Jovian directorate', u'Lai Dai Corporation', u'Chemal Tech', u'CBD Corporation', u'Internal Security',
             u'Salvation Angels', u'TransStellar Shipping', u'InterBus', u'Outer Ring Excavations',
             u'Tribal Liberation Force', u'Impetus', u'Intaki Commerce', u'University of Caille', u'Home Guard',
             u'The Draconis Family', u'The Sanctuary', u'Republic University', u'Federal Intelligence Office',
             u'Egonics Inc.', u'Native Freshfood', u'Republic Security Services', u'Wiyrkomi Corporation',
             u'Sukuuvestaa Corporation', u'Vherokior tribe', u'Republic Parliament', u'Ytiri', u'Mercantile Club',
             u'Civic Court', u'Imperial Academy', u'Tash-Murkon Family', u'Viziam', u'Ammatar Fleet',
             u'Urban Management', u'Royal Amarr Institute', u'Echelon Entertainment', u'Archangels',
             u'Poteque Pharmaceuticals', u'Imperial Armaments', u'Academy of Aggressive Behaviour',
             u'Duvolle Laboratories', u'Ministry of Internal Order', u'Quafe Company', u'Serpentis Inquest',
             u'True Creations', u'Science and Trade Institute', u'Further Foodstuffs', u'Poksu Mineral Group',
             u'Astral Mining Inc.', u'Krusual tribe', u'Blood Raiders', u'Amarr Constructions', u'Federation Navy',
             u'Inner Circle', u'State War Academy', u'Zoar and Sons', u'Boundless Creation', u'Guardian Angels',
             u'Food Relief', u'Royal Khanid Navy', u'Imperial Shipment', u'Perkone', u'Federal Administration',
             u'Emperor Family', u'Inner Zone Shipping', u'Theology Council', u'Aliastra', u'Republic Military School',
             u'Freedom Extension', u'Sisters of EVE', u'President', u'Expert Housing', u'Deep Core Mining Inc.',
             u'Senate', u"Mordu's Legion", u'State Protectorate', u'Jove Navy', u'X-Sense', u'Corporate Police Force',
             u'Minmatar Mining Corporation', u'Supreme Court')

def checkSpyglassVersionUpdate(current_version=VERSION):
    """check github for a new latest release
    """
    new_version = None
    req = "https://github.com/crypta-eve/spyglass/releases/latest"
    res_constellation = requests.get(req)
    res_constellation.raise_for_status()
    page_ver_found = res_constellation.text.find(".exe")
    if page_ver_found:
        page_ver_found_start = res_constellation.text.rfind('-',page_ver_found-32,page_ver_found)+1
        if page_ver_found_start:
            new_version = res_constellation.text[page_ver_found_start:page_ver_found]
    if new_version is None:
        return [False, "Unable to read version from github."]

    if version.parse(new_version) > version.parse(current_version):
        return [True,
                "An newer Spyglass Version {} is available, you are currently running Version {}.".format(
                    new_version, current_version)]
    else:
        return [False,
                "You are running the actual Spyglass Version {}.".format(current_version)]

def getSpyglassUpdateLink(ver=VERSION):
    req = "https://github.com/crypta-eve/spyglass/releases/latest"
    res_constellation = requests.get(req)
    res_constellation.raise_for_status()
    pos_start = res_constellation.text.find("crypta-eve/spyglass/releases/download/")
    pos_exe = res_constellation.text.find(".exe")
    return "https://github.com/{}.exe".format(res_constellation.text[pos_start:pos_exe])
