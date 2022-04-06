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

""" 12.02.2015
	I know this is a little bit dirty, but I prefer to have all the functions
	to parse the chat in this file together.
	Wer are now work directly with the html-formatted text, which we use to
	display it. We are using a HTML/XML-Parser to have the benefit, that we
	can only work and analyze those text, that is still not on tags, because
	all the text in tags was allready identified.
	f.e. the ship_parser:
		we call it from the chatparser and give them the rtext (richtext).
		if the parser hits a shipname, it will modifiy the tree by creating
		a new tag and replace the old text with it (calls tet_replace),
		than it returns True.
		The chatparser will call the function again until it return False
		(None is False) otherwise.
		We have to call the parser again after a hit, because a hit will change
		the tree and so the original generator is not longer stable.
"""


import vi.evegate as evegate
from bs4 import BeautifulSoup
from bs4.element import NavigableString
from vi import states

CHARS_TO_IGNORE = ("*", "?", ",", "!", ".")


def textReplace(element, newText):
    newText = "<t>" + newText + "</t>"
    newElements = []
    for newPart in BeautifulSoup(newText, "html.parser").select("t")[0].contents:
        newElements.append(newPart)
    for newElement in newElements:
        element.insert_before(newElement)
    element.replace_with("")


def parseStatus(rtext):
    texts = [t for t in rtext.contents if isinstance(t, NavigableString)]
    for text in texts:
        upperText = text.strip().upper()
        originalText = upperText
        for char in CHARS_TO_IGNORE:
            upperText = upperText.replace(char, "")
        upperWords = upperText.split()
        if ("CLEAR" in upperWords or "CLR" in upperWords) and not originalText.endswith(
            "?"
        ):
            return states.CLEAR
        elif "STAT" in upperWords or "STATUS" in upperWords:
            return states.REQUEST
        elif "?" in originalText:
            return states.REQUEST
        elif text.strip().upper() in (
            "BLUE",
            "BLUES ONLY",
            "ONLY BLUE" "STILL BLUE",
            "ALL BLUES",
        ):
            return states.CLEAR


def parseShips(rtext):
    def formatShipName(text, word):
        newText = """<span style="color:#d95911;font-weight:bold"> {0}</span>"""
        text = text.replace(word, newText.format(word))
        return text

    texts = [t for t in rtext.contents if isinstance(t, NavigableString)]
    for text in texts:
        upperText = text.upper()
        for shipName in evegate.SHIPNAMES:
            if shipName in upperText:
                hit = True
                start = upperText.find(shipName)
                end = start + len(shipName)
                if (start > 0 and upperText[start - 1] not in (" ", "X")) or (
                    end < len(upperText) - 1 and upperText[end] not in ("S", " ")
                ):
                    hit = False
                if hit:
                    shipInText = text[start:end]
                    formatted = formatShipName(text, shipInText)
                    textReplace(text, formatted)
                    return True


def parseSystems(systems, rtext, foundSystems):
    systemNames = systems.keys()

    # words to ignore on the system parser. use UPPER CASE
    WORDS_TO_IGNORE = ("IN", "IS", "AS")

    def formatSystem(text, word, system):
        newText = """<a style="color:#CC8800;font-weight:bold" href="mark_system/{0}">{1}</a>"""
        text = text.replace(word, newText.format(system, word))
        return text

    texts = [t for t in rtext.contents if isinstance(t, NavigableString) and len(t)]
    for wtIdx, text in enumerate(texts):
        worktext = text
        for char in CHARS_TO_IGNORE:
            worktext = worktext.replace(char, "")

        # Drop redundant whitespace so as to not throw off word index
        worktext = " ".join(worktext.split())
        words = worktext.split(" ")

        for idx, word in enumerate(words):

            # Is this about another a system's gate?
            if len(words) > idx + 1:
                if words[idx + 1].upper() == "GATE":
                    bailout = True
                    if len(words) > idx + 2:
                        if words[idx + 2].upper() == "TO":
                            # Could be '___ GATE TO somewhere' so check this one.
                            bailout = False
                    if bailout:
                        # '_____ GATE' mentioned in message, which is not what we're
                        # interested in, so go to checking next word.
                        continue

            upperWord = word.upper()
            if upperWord != word and upperWord in WORDS_TO_IGNORE:
                continue
            if upperWord in systemNames:  # - direct hit on name
                foundSystems.add(systems[upperWord])  # of the system?
                formattedText = formatSystem(text, word, upperWord)
                textReplace(text, formattedText)
                return True
            elif 1 < len(upperWord) < 5:  # - upperWord < 4 chars.
                for system in systemNames:  # system begins with?
                    if system.startswith(upperWord):
                        foundSystems.add(systems[system])
                        formattedText = formatSystem(text, word, system)
                        textReplace(text, formattedText)
                        return True
            elif "-" in upperWord and len(upperWord) > 2:  # - short with - (minus)
                upperWordParts = upperWord.split("-")  # (I-I will match I43-IF3)
                for system in systemNames:
                    systemParts = system.split("-")
                    if (
                        len(upperWordParts) == 2
                        and len(systemParts) == 2
                        and len(upperWordParts[0]) > 1
                        and len(upperWordParts[1]) > 1
                        and len(systemParts[0]) > 1
                        and len(systemParts[1]) > 1
                        and len(upperWordParts) == len(systemParts)
                        and upperWordParts[0][0] == systemParts[0][0]
                        and upperWordParts[1][0] == systemParts[1][0]
                    ):
                        foundSystems.add(systems[system])
                        formattedText = formatSystem(text, word, system)
                        textReplace(text, formattedText)
                        return True
            elif len(upperWord) > 1:  # what if F-YH58 is named FY?
                for system in systemNames:
                    clearedSystem = system.replace("-", "")
                    if clearedSystem.startswith(upperWord):
                        foundSystems.add(systems[system])
                        formattedText = formatSystem(text, word, system)
                        textReplace(text, formattedText)
                        return True

    return False


def parseUrls(rtext):
    def findUrls(s):
        # yes, this is faster than regex and less complex to read
        urls = []
        prefixes = ("http://", "https://")
        for prefix in prefixes:
            start = 0
            while start >= 0:
                start = s.find(prefix, start)
                if start >= 0:
                    stop = s.find(" ", start)
                    if stop < 0:
                        stop = len(s)
                    urls.append(s[start:stop])
                    start += 1
        return urls

    def formatUrl(text, url):
        newText = (
            """<a style="color:#28a5ed;font-weight:bold" href="link/{0}">{0}</a>"""
        )
        text = text.replace(url, newText.format(url))
        return text

    texts = [t for t in rtext.contents if isinstance(t, NavigableString)]
    for text in texts:
        urls = findUrls(text)
        for url in urls:
            textReplace(text, formatUrl(text, url))
            return True
