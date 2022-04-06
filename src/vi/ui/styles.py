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

import logging
import yaml
import os

from vi.resources import resourcePath


class Styles:
    defaultStyle = ""
    defaultCommons = ""

    darkStyle = ""
    darkCommons = ""

    styleList = ["light", "abyss"]

    currentStyle = "light"

    def __init__(self):
        try:
            # default theme
            with open(resourcePath(os.path.join("vi", "ui", "res", "styles", "light.css"))) as default:
                Styles.defaultStyle = default.read()
            with open(resourcePath(os.path.join("vi", "ui", "res", "styles", "light.yaml"))) as default:
                Styles.defaultCommons = yaml.full_load(default)
            default = None

            # dark theme
            with open(resourcePath(os.path.join("vi", "ui", "res", "styles", "abyss.css"))) as dark:
                Styles.darkStyle = dark.read()
            with open(resourcePath(os.path.join("vi", "ui", "res", "styles", "abyss.yaml"))) as dark:
                Styles.darkCommons = yaml.full_load(dark)
            dark = None
        except Exception as e:
            logging.critical(e)


    def getStyles(self):
        return self.styleList

    def getStyle(self):
        if (Styles.currentStyle == "light"):
            return self.defaultStyle
        elif Styles.currentStyle == "abyss":
            return self.darkStyle
        else:
            return ""

    def getCommons(self):
        if (Styles.currentStyle == "light" and Styles.defaultCommons != ""):
            return Styles.defaultCommons
        elif (Styles.currentStyle == "abyss" and Styles.darkCommons != ""):
            return Styles.darkCommons
        else:
            def_commons = {
                "bg_colour": '#FFFFFF',
                "change_lines": False,
                "line_colour": '#000000',
                "alarm_colours": ["#FF0000", "#FF9B0F", "#FFFA0F", "#FFFDA2", "#FFFFFF"],
                "unknown_colour": "#FFFFF",
                "clear_colour": "#59FF6C",
                "text_colour": "#000000",
                "text_inverter": True}
            return def_commons

    def setStyle(self, style):
        if style in Styles.styleList:
            Styles.currentStyle = style
        else:
            logging.critical("Attempted to switch to unknown style: {}".format(style))


class TextInverter():
    def getTextColourFromBackground(self, colour):
        if colour[0] == '#':
            colour = colour[1:]
        red = int(colour[0:2], 16)
        green = int(colour[2:4], 16)
        blue = int(colour[4:6], 16)

        # perceptive Luminance formula
        perc = 1 - (((0.299 * red) + (0.587 * green) + (0.114 * blue)) / 255)
        if perc < 0.5:
            return "#000000"
        else:
            return "#FFFFFF"


if __name__ == "__main__":
    inv = TextInverter()
    print("50E661")
    print(inv.getTextColourFromBackground("50E661"))
