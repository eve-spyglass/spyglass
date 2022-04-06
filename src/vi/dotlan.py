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

###########################################################################
# Little lib and tool to get the map and information from dotlan		  #
###########################################################################

import math
import datetime
import requests
import logging
from bs4 import BeautifulSoup
from vi import states
from vi.cache.cache import Cache
from vi.ui.styles import Styles, TextInverter

from . import evegate

JB_COLORS = ("800000", "808000", "BC8F8F", "ff00ff", "c83737", "FF6347", "917c6f", "ffcc00",
             "88aa00" "FFE4E1", "008080", "00BFFF", "4682B4", "00FF7F", "7FFF00", "ff6600",
             "CD5C5C", "FFD700", "66CDAA", "AFEEEE", "5F9EA0", "FFDEAD", "696969", "2F4F4F")


class DotlanException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class Map(object):
    """
        The map including all information from dotlan
    """
    DOTLAN_BASIC_URL = u"https://evemaps.dotlan.net/svg/{0}.svg"
    styles = Styles()

    @property
    def svg(self):
        # Re-render all systems
        for system in self.systems.values():
            system.update()

        # Update the marker, the marker should be visible for 20s
        if float(self.marker["opacity"]) > 0.0:
            delta = datetime.datetime.utcnow().timestamp() - float(self.marker["activated"])
            newOpacity = (1.0-delta/20.0)
            if newOpacity < 0:
                newOpacity=0.0
            self.marker["opacity"] = newOpacity
        if True:
            content = str(self.soup)
        else:
            content = str(self.soup.select("svg")[0])
        return content

    def __init__(self, region, svgFile=None, setJumpMapsVisible=False,setSatisticsVisible=False):
        self.region = region
        self.width = None
        self.height = None
        cache = Cache()
        self.outdatedCacheError = None
        if self.region == "Providencecatch" or self.region == "Providence-catch-compact":
            region_to_load = "providence-catch"
        else:
            region_to_load = self.region
        # Get map from dotlan if not in the cache
        if not svgFile:
            svg = cache.getFromCache("map_" + self.region)
        else:
            svg = svgFile
        if not svg or svg.startswith("region not found"):
            try:
                svg = self._getSvgFromDotlan(region_to_load)
                if not svg or svg.startswith("region not found"):
                    svg = self._getSvgFromDotlan("providence")
                cache.putIntoCache("map_" + self.region, svg,
                                   24 * 60 * 60)  ###evegate.secondsTillDowntime() + ### 60 * 60)
            except Exception as e:
                self.outdatedCacheError = e
                svg = cache.getFromCache("map_" + self.region, True)
                if not svg or svg.startswith("region not found"):
                    t = "No Map in cache, nothing from dotlan. Must give up " \
                        "because this happened:\n{0} {1}\n\nThis could be a " \
                        "temporary problem (like dotlan is not reachable), or " \
                        "everything went to hell. Sorry. This makes no sense " \
                        "without the map.\n\nRemember the site for possible " \
                        "updates: https://github.com/Crypta-Eve/spyglass".format(type(e), str(e))
                    raise DotlanException(t)
        # Create soup from the svg
        self.soup = BeautifulSoup(svg, 'html.parser')
        for scr in self.soup.findAll('script'):
            scr.extract()
        for scr in self.soup.select('#controls'):
            scr.extract()
        for leg in self.soup.findAll(id="legend"):
            leg.extract()

        for tag in self.soup.findAll(attrs={"onload": True}):
            del (tag["onload"])

        if "compact" in self.region:
            scale = 0.9
        elif "tactical" in self.region:
            scale = 1.5
        else:
            scale = 1.0
        self.systems = self._extractSystemsFromSoup(self.soup, scale)
        self.systemsById = {}
        for system in self.systems.values():
            self.systemsById[system.systemId] = system

        self._extractSizeFromSoup(self.soup)
        self._prepareSvg(self.soup, self.systems)
        self._connectNeighbours()
        self.jumpBridges = []
        self._jumpMapsVisible = setJumpMapsVisible
        self._statisticsVisible = setSatisticsVisible
        self.marker = self.soup.select("#select_marker")[0]
        self.updateJumpbridgesVisibility()
        self.updateStatisticsVisibility()

    def setIncursionSystems(self, lst_system_ids):
        for sys_id, sys in self.systemsById.items():
            sys.setIncursion(sys_id in lst_system_ids)

    def setCampaignsSystems(self, lst_system_ids):
        for sys_id, sys in self.systemsById.items():
            sys.setCampaigns(sys_id in lst_system_ids)

    def _extractSizeFromSoup(self, soup):
        svg = soup.select("svg")[0]
        box = svg["viewbox"]
        if box:
            box = box.split(" ")
            self.width = float(box[2])
            self.height = float(box[3])

        #width = svg["width"]
        #height = svg["height"]

    def _extractSystemsFromSoup(self, soup, scale):
        #default size of the systems to calculate the center point
        svg_width  = 62.5
        svg_height = 30
        systems = {}
        uses = {}
        for use in soup.select("use"):
            useId = use["xlink:href"][1:]
            use.attrs["width"] = svg_width
            use.attrs["height"] = svg_height
            use.attrs["x"] = str(float(use.attrs["x"]) * scale)
            use.attrs["y"] = str(float(use.attrs["y"]) * scale)
            uses[useId] = use

        for use in soup.select("line"):
            use.attrs["x1"] = str((float(use.attrs["x1"])-svg_width/2.0) * scale+svg_width/2.0)
            use.attrs["y1"] = str((float(use.attrs["y1"])-svg_height/2.0) * scale+svg_height/2.0)
            use.attrs["x2"] = str((float(use.attrs["x2"])-svg_width/2.0) * scale+svg_width/2.0)
            use.attrs["y2"] = str((float(use.attrs["y2"])-svg_height/2.0) * scale+svg_height/2.0)

        symbols = soup.select("symbol")
        for symbol in symbols:
            symbolId = symbol["id"]
            systemId = symbolId[3:]
            try:
                systemId = int(systemId)
            except ValueError as e:
                continue
            for element in symbol.select(".sys"):
                name = element.select("text")[0].text.strip().upper()
                mapCoordinates = {}
                for keyname in ("x", "y", "width", "height"):
                    try:
                        mapCoordinates[keyname] = float(uses[symbolId][keyname])
                    except KeyError:
                        mapCoordinates[keyname] = 0

                mapCoordinates["center_x"] = (mapCoordinates["x"] + 1.0+56.0/2.0) #(mapCoordinates["width"] / 2.0))
                mapCoordinates["center_y"] = (mapCoordinates["y"] + (mapCoordinates["height"] / 2.0))
                try:
                    if symbolId in uses.keys():
                        keys = uses[symbolId]
                        if uses[symbolId].find("transform"):
                            transform = uses[symbolId]["transform"]
                        else:
                            transform = None
                        systems[name] = System(name, element, self.soup, mapCoordinates, transform, systemId)
                    else:
                        logging.error("System {} not found.".format(name))

                except KeyError:
                    logging.critical("Unable to prepare system {}.".format(name))
                    pass

        return systems

    def _applySystemStatistic(self, systems_stats):
        for sys_id, sys in self.systemsById.items():
            sid = str(sys_id)
            if sid in systems_stats.keys():
                if "ticker" in systems_stats[sid].keys():
                    sys.ticker = systems_stats[sid]["ticker"]
                    sys.setStatus(states.UNKNOWN)

    def _prepareGradients(self, soup):

        grad_located = soup.new_tag("radialGradient", id="grad_located")
        stop = soup.new_tag("stop")
        stop["offset"] = "50%"
        stop["stop-color"] = "#8b008d"
        stop["stop-opacity"] = "1"
        grad_located.append(stop)
        stop = soup.new_tag("stop")
        stop["offset"] = "100%"
        stop["stop-color"] = "#8b008d"
        stop["stop-opacity"] = "0"
        grad_located.append(stop)

        grad_watch = soup.new_tag("radialGradient", id="grad_watch")
        stop = soup.new_tag("stop")
        stop["offset"] = "50%"
        stop["stop-color"] = "#909090"
        stop["stop-opacity"] = "1"
        grad_watch.append(stop)
        stop = soup.new_tag("stop")
        stop["offset"] = "100%"
        stop["stop-color"] = "#909090"
        stop["stop-opacity"] = "0"
        grad_watch.append(stop)


        grad_camBg = soup.new_tag("radialGradient", id="camBg")
        stop = soup.new_tag("stop")
        stop["offset"] = "50%"
        stop["stop-color"] = "#FF8800"
        stop["stop-opacity"] = "1"
        grad_camBg.append(stop)
        stop = soup.new_tag("stop")
        stop["offset"] = "100%"
        stop["stop-color"] = "#FF8800"
        stop["stop-opacity"] = "0"
        grad_camBg.append(stop)

        grad_camActiveBg = soup.new_tag("radialGradient", id="camActiveBg")
        stop = soup.new_tag("stop")
        stop["offset"] = "50%"
        stop["stop-color"] = "#ff0000"
        stop["stop-opacity"] = "1.0"
        grad_camActiveBg.append(stop)
        stop2 = soup.new_tag("stop")
        stop2["offset"] = "100%"
        stop2["stop-color"] = "#ff0000"
        stop2["stop-opacity"] = "0.0"
        grad_camActiveBg.append(stop2)

        grad_incBg = soup.new_tag("radialGradient", id="incBg")
        stop = soup.new_tag("stop")
        stop["offset"] = "50%"
        stop["stop-color"] = "#FFC800"
        stop["stop-opacity"] = "1"
        grad_incBg.append(stop)
        stop = soup.new_tag("stop")
        stop["offset"] = "100%"
        stop["stop-color"] = "#FFC800"
        stop["stop-opacity"] = "0"
        grad_incBg.append(stop)

        grad_incStBg = soup.new_tag("radialGradient", id="incStBg")
        stop = soup.new_tag("stop")
        stop["offset"] = "50%"
        stop["stop-color"] = "#FFC800"
        stop["stop-opacity"] = "1"
        grad_incStBg.append(stop)
        stop = soup.new_tag("stop")
        stop["offset"] = "100%"
        stop["stop-color"] = "#FF0000"
        stop["stop-opacity"] = "0"
        grad_incStBg.append(stop)
        svg = soup.select("svg")[0]

        for defs in svg.select("defs"):
            defs.append(grad_located)
            defs.append(grad_watch)
            defs.append(grad_camBg)
            defs.append(grad_camActiveBg)
            defs.append(grad_incBg)
            defs.append(grad_incStBg)
    #todo:use /sovereignty/campaigns/ and /sovereignty/structures/ and /incursions/ to define system fill




    def _prepareSvg(self, soup, systems):
        svg = soup.select("svg")[0]
        svg.attrs = {key: value for key, value in svg.attrs.items() if key not in ["style", "onmousedown", "viewbox"]}
        # Disable dotlan mouse functionality
        #css = soup.select("style")[0]
        #svg["style"] = "background: {}".format(self.styles.getCommons()["bg_colour"])
        if self.styles.getCommons()["change_lines"]:
            for line in soup.select("line"):
                line["class"] = "j"
        # Current system marker ellipse
        group = soup.new_tag("g", id="select_marker", opacity="0", activated="0", transform="translate(0, 0)")
        ellipse = soup.new_tag("ellipse", cx="0", cy="0", rx="56", ry="28", style="fill:#462CFF")
        group.append(ellipse)

        self._prepareGradients( soup )

        # The giant cross-hairs
        for coord in ((0, -10000), (-10000, 0), (10000, 0), (0, 10000)):
            line = soup.new_tag("line", x1=coord[0], y1=coord[1], x2="0", y2="0", style="stroke:#462CFF")
            group.append(line)
        svg.insert(0, group)

        map = svg.select("#map")

        for defs in svg.select("defs"):
            for tag in defs.select("a"):
                tag.attrs = {key: value for key, value in tag.attrs.items() if key not in ["target","xlink:href"]}
                tag.name = "a"

        for defs in svg.select("defs"):
            for symbol in defs.select("symbol"):
                if symbol:
                    symbol.name = "g"
                    map.insert(0, symbol)
        try:
            jumps = soup.select("#jumps")[0]
        except Exception as e:
            jumps = list()


        # Set up the tags for system statistics
        for systemId, system in self.systemsById.items():
            coords = system.mapCoordinates
            text = "stats n/a"
            style = "text-anchor:middle;font-size:7;font-weight:normal;font-family:Arial;"
            system.svgtext = soup.new_tag("text", x=coords["center_x"], y=coords["y"] + coords["height"] + 4, fill="blue",
                                   style=style, visibility="hidden", transform=system.transform)
            system.svgtext["id"] = "stats_" + str(systemId)
            system.svgtext["class"] = "statistics"
            system.svgtext.string = text
            jumps.append(system.svgtext)

    def _connectNeighbours(self):
        """
            This will find all neighbours of the systems and connect them.
            It takes a look at all the jumps on the map and gets the system under
            which the line ends
        """
        for jump in self.soup.select("#jumps")[0].select(".j,.jc,.jr"):
            if "jumpbridge" in jump["class"]:
                continue
            parts = jump["id"].split("-")
            if parts[0] == "j":
                startSystem = self.systemsById[int(parts[1])]
                stopSystem = self.systemsById[int(parts[2])]
                startSystem.addNeighbour(stopSystem)

    def _getSvgFromDotlan(self, region):
        url = self.DOTLAN_BASIC_URL.format(region)
        content = requests.get(url).text
        return content

    def addSystemStatistics(self, statistics):
        if statistics is not None:
            for systemId, system in self.systemsById.items():
                if systemId in statistics.keys():
                    system.setStatistics(statistics[systemId])
        else:
            for system in self.systemsById.values():
                system.setStatistics(None)

    def setJumpbridges(self, jumpbridgesData):
        """
            Adding the jumpbridges to the map soup; format of data:
            tuples with at least 3 values (sys1, connection, sys2) connection is <->
        """
        # todo:disable jbs during init
        self.jumpBridges = []
        if jumpbridgesData is None:
            self.jumpBridges = []
            return
        soup = self.soup
        for bridge in soup.select(".jumpbridge"):
            bridge.decompose()
        jumps = soup.select("#jumps")
        if jumps!=None:
            jumps = soup.select("#jumps")[0]
        else:
            return

        colorCount = 0
        for bridge in jumpbridgesData:
            sys1 = bridge[0]
            connection = bridge[1]
            sys2 = bridge[2]
            if not (sys1 in self.systems and sys2 in self.systems):
                continue

            if colorCount > len(JB_COLORS) - 1:
                colorCount = 0
            jbColor = JB_COLORS[colorCount]
            colorCount += 1
            systemOne = self.systems[sys1]
            systemTwo = self.systems[sys2]
            self.jumpBridges.append([systemOne.systemId,systemTwo.systemId])
            systemOneCoords = systemOne.mapCoordinates
            systemTwoCoords = systemTwo.mapCoordinates
            systemOneOffsetPoint = systemOne.getTransformOffsetPoint()
            systemTwoOffsetPoint = systemTwo.getTransformOffsetPoint()

            # systemOne.setJumpbridgeColor(jbColor)
            # systemTwo.setJumpbridgeColor(jbColor)
            # Construct the line, color it and add it to the jumps
            if False:
                x1 = systemOneCoords["center_x"] + systemOneOffsetPoint[0]
                y1 = systemOneCoords["center_y"] + systemOneOffsetPoint[1]
                x2 = systemTwoCoords["center_x"] + systemTwoOffsetPoint[0]
                y2 = systemTwoCoords["center_y"] + systemTwoOffsetPoint[1]
                dx = (x2 - x1) / 2.0
                dy = (y2 - y1) / 2.0
                offset = 0.4 * math.sqrt( dx*dx+dy*dy)
                angle = math.atan2(dy, dx) - math.pi / 2.0
                mx = x1 + dx + offset * math.cos(angle)
                my = y1 + dy + offset * math.sin(angle)

                line = soup.new_tag( "path",d="M{} {} Q {} {} {} {}".format(x1,y1,mx,my,x2,y2),
                                        visibility = "hidden",
                                        fill="transparent",
                                        style="stroke:#{0}".format(jbColor))

            else:
                line = soup.new_tag("line", x1=systemOneCoords["center_x"] + systemOneOffsetPoint[0],
                                        y1=systemOneCoords["center_y"] + systemOneOffsetPoint[1],
                                        x2=systemTwoCoords["center_x"] + systemTwoOffsetPoint[0],
                                        y2=systemTwoCoords["center_y"] + systemTwoOffsetPoint[1],
                                        visibility="hidden",
                                        style="stroke:#{0}".format(jbColor))
            line["stroke-width"] = 2
            line["class"] = ["jumpbridge", ]
            if "<" in connection:
                line["marker-start"] = "url(#arrowstart_{0})".format(jbColor)
            if ">" in connection:
                line["marker-end"] = "url(#arrowend_{0})".format(jbColor)
            jumps.insert(0, line)
        self.updateJumpbridgesVisibility()

    def updateStatisticsVisibility(self):
        value = "visible" if self._statisticsVisible else "hidden"
        for line in self.soup.select(".statistics"):
            line["visibility"] = value
            line["fill"] = "red"

    def changeStatisticsVisibility(self):
        self._statisticsVisible = False if self._statisticsVisible else True
        self.updateStatisticsVisibility()
        return self._statisticsVisible

    def updateJumpbridgesVisibility(self):
        value = "visible" if self._jumpMapsVisible else "hidden"
        for line in self.soup.select(".jumpbridge"):
            line["visibility"] = value

    def changeJumpbridgesVisibility(self):
        self._jumpMapsVisible = False if self._jumpMapsVisible else True
        self.updateJumpbridgesVisibility()
        return self._jumpMapsVisible

class System(object):
    """
        A System on the Map
    """

    styles = Styles()
    textInv = TextInverter()
    SYSTEM_STYLE = "font-family: Arial, Helvetica, sans-serif; font-size: 8px; fill: {};"
    ALARM_STYLE = "font-family: Arial, Helvetica, sans-serif; font-size: 7px; fill: {};"

    ALARM_BASE_T = 60 #set 1 for testing
    ALARM_COLORS = [(ALARM_BASE_T * 5,  "#FF0000", "#FFFFFF"),
                    (ALARM_BASE_T * 10, "#FF9B0F", "#FFFFFF"),
                    (ALARM_BASE_T * 15, "#FFFA0F", "#000000"),
                    (ALARM_BASE_T * 20, "#FFFDA2", "#000000"),
                    (0,       "#FFFFFF", "#000000")]

    CLEAR_COLORS = [(ALARM_BASE_T * 5,  "#00FF00", "#000000"),
                    (ALARM_BASE_T * 10, "#40FF40", "#000000"),
                    (ALARM_BASE_T * 15, "#80FF80", "#000000"),
                    (ALARM_BASE_T * 20, "#C0FFC0", "#000000"),
                    (0,       "#FFFFFF", "#000000")]

    ALARM_COLOR = ALARM_COLORS[0][1]
    UNKNOWN_COLOR = styles.getCommons()["unknown_colour"]
    CLEAR_COLOR = CLEAR_COLORS[0][1]

    def __init__(self, name, svgElement, mapSoup, mapCoordinates, transform, systemId, ticker="npc"):
        self.status = states.UNKNOWN
        self.name = name
        self.ticker = ticker
        self.svgElement = svgElement
        self.mapSoup = mapSoup
        self.origSvgElement = svgElement
        self.rect = svgElement.select("rect")[0]
        self.firstLine = svgElement.select("text")[0]
        self.secondLine = svgElement.select("text")[1]
        self.lastAlarmTime = 0
        self.lastAlarmTimestamp = 0
        self.messages = []
        self.setStatus(states.UNKNOWN)
        self.__locatedCharacters = []
        self.backgroundColor = self.styles.getCommons()["bg_colour"]
        self.mapCoordinates = mapCoordinates
        self.systemId = systemId
        self.transform = "translate(0, 0)" if transform is None else transform
        self.cachedOffsetPoint = None
        self._neighbours = set()
        self.statistics = {"jumps": "?", "shipkills": "?", "factionkills": "?", "podkills": "?"}
        self.currentStyle = ""
        self.__hasCampaigns = False
        self.__hasIncursion = False
        self.__hasIncursionBoss = False
        self.svgtext = None
    def getTransformOffsetPoint(self):
        if not self.cachedOffsetPoint:
            if self.transform:
                # Convert data in the form 'transform(0,0)' to a list of two floats
                pointString = self.transform[9:].strip('()').split(',')
                self.cachedOffsetPoint = [float(pointString[0]), float(pointString[1])]
            else:
                self.cachedOffsetPoint = [0.0, 0.0]
        return self.cachedOffsetPoint

    def setJumpbridgeColor(self, color):
        idName = self.name + u"_jb_marker"
        for element in self.mapSoup.select("#" + idName):
            element.decompose()
        coords = self.mapCoordinates
        offsetPoint = self.getTransformOffsetPoint()
        x = coords["x"] - 3 + offsetPoint[0]
        y = coords["y"] + offsetPoint[1]
        style = "fill:{0};stroke:{0};stroke-width:2;fill-opacity:0.4"
        tag = self.mapSoup.new_tag("rect", x=x, y=y, width=coords["width"] + 1.5, height=coords["height"], id=idName,
                                   style=style.format(color), visibility="hidden")
        tag["class"] = ["jumpbridge", ]
        jumps = self.mapSoup.select("#jumps")[0]
        jumps.insert(0, tag)

    def mark(self):
        marker = self.mapSoup.select("#select_marker")[0]
        offsetPoint = self.getTransformOffsetPoint()
        x = self.mapCoordinates["center_x"] + offsetPoint[0]
        y = self.mapCoordinates["center_y"] + offsetPoint[1]
        marker["transform"] = "translate({x},{y})".format(x=x, y=y)
        marker["opacity"] = 1.0
        marker["activated"] = datetime.datetime.utcnow().timestamp()

    def addLocatedCharacter(self, charname):
        idName = self.name + u"_loc"
        wasLocated = bool(self.__locatedCharacters)
        if charname not in self.__locatedCharacters:
            self.__locatedCharacters.append(charname)
        if not wasLocated:
            coords = self.mapCoordinates
            newTag = self.mapSoup.new_tag("rect", x=coords["x"]-10, y=coords["y"]-8,
                                          width=coords["width"]+16, height=coords["height"]+16, id=idName,
                                          rx=12, ry=12, fill="url(#grad_located)")
            jumps = self.mapSoup.select("#jumps")[0]
            jumps.insert(0, newTag)

    def setCampaigns(self, campaigns: bool):
        id_name = self.name + u"_campaigns"
        if campaigns and not self.__hasCampaigns:
            camp_node = self.mapSoup.find(id=id_name)
            if camp_node is None:
                coords = self.mapCoordinates
                new_tag = self.mapSoup.new_tag("rect", x=coords["x"]-10, y=coords["y"]-8,
                                          width=coords["width"]+16, height=coords["height"]+16, id=id_name,
                                          rx=12, ry=12, fill="url(#camActiveBg)")
                jumps = self.mapSoup.select("#jumps")[0]
                jumps.insert(0, new_tag)
        elif not campaigns and self.__hasCampaigns:
            camp_node = self.mapSoup.find(id=id_name)
            camp_node.decompose()

    def setIncursion(self, incursion: bool, hasBoss=False):
        id_name = self.name + u"_incursion"
        if incursion and not self.__hasIncursion:
            curr_node = self.mapSoup.find(id=id_name)
            if curr_node is None:
                coords = self.mapCoordinates
                new_tag = self.mapSoup.new_tag("rect", x=coords["x"]-10, y=coords["y"]-8,
                                          width=coords["width"]+16, height=coords["height"]+16, id=id_name,
                                          rx=12, ry=12, fill="url(#incStBg)" if hasBoss else "url(#incBg)")
                jumps = self.mapSoup.select("#jumps")[0]
                jumps.insert(0, new_tag)
        elif not incursion and self.__hasIncursion:
            camp_node = self.mapSoup.find(id=id_name)
            camp_node.decompose()
        self.__hasIncursion = incursion
        self.__hasIncursionBoss = hasBoss



    def setBackgroundColor(self, color):
        for rect in self.svgElement("rect"):
            if "location" not in rect.get("class", []) and "marked" not in rect.get("class", []):
                rect["style"] = "fill: {0};".format(color)
        self.backgroundColor = color

    def getLocatedCharacters(self):
        characters = []
        for char in self.__locatedCharacters:
            characters.append(char)
        return characters

    def removeLocatedCharacter(self, charname):
        idName = self.name + u"_loc"
        if charname in self.__locatedCharacters:
            self.__locatedCharacters.remove(charname)
            if not self.__locatedCharacters:
                try:
                    elem = self.mapSoup.find(id=idName)
                    if elem is not None:
                        logging.debug("removeLocatedCharacter {0} Decompose {1}".format(charname, str(elem)))
                        elem.decompose()
                except Exception as e:
                    logging.critical("Error in removeLocatedCharacter  {0}".format(str(e)))
                    pass

    def addNeighbour(self, neighbourSystem):
        """
            Add a neigbour system to this system
            neighbour_system: a system (not a system's name!)
        """
        self._neighbours.add(neighbourSystem)
        neighbourSystem._neighbours.add(self)

    def getNeighbours(self, distance=1):
        """
            Get all neigboured system with a distance of distance.
            example: sys1 <-> sys2 <-> sys3 <-> sys4 <-> sys5
            sys3(distance=1) will find sys2, sys3, sys4
            sys3(distance=2) will find sys1, sys2, sys3, sys4, sys5
            returns a dictionary with the system (not the system's name!)
            as key and a dict as value. key "distance" contains the distance.
            example:
            {sys3: {"distance"}: 0, sys2: {"distance"}: 1}
        """
        #todo:change distance calculaten to esi to enable detection of
        systems = {self: {"distance": 0}}
        currentDistance = 0
        while currentDistance < distance:
            currentDistance += 1
            newSystems = []
            for system in systems.keys():
                for neighbour in system._neighbours:
                    if neighbour not in systems:
                        newSystems.append(neighbour)
            for newSystem in newSystems:
                systems[newSystem] = {"distance": currentDistance}
        return systems

    def removeNeighbour(self, system):
        """
            Removes the link between to neighboured systems
        """
        if system in self._neighbours:
            self._neighbours.remove(system)
        if self in system._neighbours:
            system._neigbours.remove(self)

    def setStatus(self, newStatus, alarm_time=datetime.datetime.utcnow()):
        if newStatus == states.ALARM:
            self.lastAlarmTimestamp = alarm_time.timestamp()
            if "stopwatch" not in self.secondLine["class"]:
                self.secondLine["class"].append("stopwatch")
            self.setBackgroundColor(self.ALARM_COLOR)
            self.firstLine["style"] = self.SYSTEM_STYLE.format(self.textInv.getTextColourFromBackground(self.backgroundColor))
            self.secondLine["style"] = self.ALARM_STYLE.format(
            self.textInv.getTextColourFromBackground(self.backgroundColor))
        elif newStatus == states.CLEAR:
            self.lastAlarmTimestamp = alarm_time.timestamp()
            self.setBackgroundColor(self.CLEAR_COLOR)
            if "stopwatch" not in self.secondLine["class"]:
                self.secondLine["class"].append("stopwatch")
            self.firstLine["style"] = self.SYSTEM_STYLE.format(self.textInv.getTextColourFromBackground(self.backgroundColor))
            self.secondLine["style"] = self.ALARM_STYLE.format(self.textInv.getTextColourFromBackground(self.backgroundColor))
            self.secondLine.string = "clear"
        elif newStatus == states.UNKNOWN:
            self.setBackgroundColor(self.UNKNOWN_COLOR)
            # second line in the rects is reserved for the clock
            self.secondLine.string = self.ticker
            self.firstLine["style"] = self.SYSTEM_STYLE.format(
                self.textInv.getTextColourFromBackground(self.backgroundColor))
            self.secondLine["style"] = self.ALARM_STYLE.format(
                self.textInv.getTextColourFromBackground(self.backgroundColor))
        if newStatus not in (states.NOT_CHANGE, states.REQUEST):  # unknown not affect system status
            self.status = newStatus

    def setStatistics(self, statistics):
        if self.svgtext is not None:
            if statistics is None:
                self.svgtext.string = "stats n/a"
            else:
                self.svgtext.string = "j-{jumps} f-{factionkills} s-{shipkills} p-{podkills}".format(**statistics)


    def update(self):
        # state changed?
        # print (self.secondLine)
        # self.firstLine["style"] = "fill: #FFFFFF" #System name
        # self.secondLine["style"] = "fill: #FFFFFF" #Timer / ?

        last_cycle = True
        if (self.currentStyle is not self.styles.currentStyle):
            self.currentStyle = self.styles.currentStyle
            self.updateStyle()

        alarmTime = datetime.datetime.utcnow().timestamp() - self.lastAlarmTimestamp
        if self.status == states.ALARM:
            for maxDiff, alarmColour, lineColour in self.ALARM_COLORS:
                if alarmTime < maxDiff:
                    if self.backgroundColor != alarmColour:
                        self.backgroundColor = alarmColour
                        for rect in self.svgElement("rect"):
                            if "location" not in rect.get("class", []) and "marked" not in rect.get("class", []):
                                rect["style"] = self.SYSTEM_STYLE.format(self.backgroundColor)
                        self.updateLineColour()
                    last_cycle = False
                    break
        elif self.status == states.CLEAR:
            for maxDiff, clearColour, lineColour in self.CLEAR_COLORS:
                if alarmTime < maxDiff:
                    if self.backgroundColor != clearColour:
                        self.backgroundColor = clearColour
                        for rect in self.svgElement("rect"):
                            if "location" not in rect.get("class", []) and "marked" not in rect.get("class", []):
                                rect["style"] = self.SYSTEM_STYLE.format(self.backgroundColor)
                        self.updateLineColour()
                    last_cycle = False
                    break

        if self.status in (states.ALARM, states.CLEAR):
            if last_cycle:
                self.status = states.UNKNOWN
                self.setBackgroundColor(self.UNKNOWN_COLOR)
                self.updateLineColour()

            minutes = int(math.floor(alarmTime / 60))
            seconds = int(alarmTime - minutes * 60)

            self.secondLine.string = "{m:02d}:{s:02d}".format(m=minutes, s=seconds, ticker=self.ticker)
            # print self.backgroundColor, self.name, self.status

    def updateLineColour(self):
        lineColour = self.textInv.getTextColourFromBackground(self.backgroundColor)
        self.firstLine["style"] = self.SYSTEM_STYLE.format(lineColour)
        self.secondLine["style"] = self.ALARM_STYLE.format(lineColour)

    def updateStyle(self):
        for i in range(5):
            self.ALARM_COLORS[i] = (self.ALARM_COLORS[i][0], self.styles.getCommons()["alarm_colours"][i],
                                    self.textInv.getTextColourFromBackground(self.ALARM_COLORS[i][1]))
        self.ALARM_COLOR = self.ALARM_COLORS[0][1]
        self.UNKNOWN_COLOR = self.styles.getCommons()["unknown_colour"]
        self.CLEAR_COLOR = self.styles.getCommons()["clear_colour"]
        self.setBackgroundColor(self.UNKNOWN_COLOR)
        self.status = states.UNKNOWN
        lineColour = self.textInv.getTextColourFromBackground(self.backgroundColor)
        self.firstLine["style"] = self.SYSTEM_STYLE.format(lineColour)
        self.secondLine["style"] = self.ALARM_STYLE.format(lineColour)


def convertRegionName(name):
    """
        Converts a (system)name to the format that dotland uses
    """
    converted = []
    nextUpper = False

    for index, char in enumerate(name):
        if index == 0:
            converted.append(char.upper())
        else:
            if char in (u" ", u"_"):
                char = "_"
                nextUpper = True
            else:
                if nextUpper:
                    char = char.upper()
                else:
                    char = char.lower()
                nextUpper = False
            converted.append(char)
    return u"".join(converted)


# this is for testing:
if __name__ == "__main__":
    map = Map("providence")
    s = map.systems["I7S-1S"]
    s.setStatus(states.ALARM)
    logging.error(map.svg)
