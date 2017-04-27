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

#This is for any unauthenticated API requests

import requests

"""
Pass a character name to get the character ID back
"""
def searchFromCharName(name):
    url = "https://esi.tech.ccp.is/latest/search/?categories=character&datasource=tranquility&language=en-us&search={}&strict=true".format(name)
    data = requests.get(url).json()
    return data

"""
Pass in a character ID and get back the public info for a character:

{
    'alliance_id': 154104258, 
    'name': 'Crypta Eve', 
    'ancestry_id': 1, 
    'gender': 'male', 
    'bloodline_id': 5, 
    'corporation_id': 98056040, 
    'security_status': 0.0027996570240089503, 
    'birthday': '2017-03-21T03:21:43Z', 
    'race_id': 4, 
    'description': ''
}

"""
def getCharInfoFromID(id):
    url = "https://esi.tech.ccp.is/latest/characters/{}/?datasource=tranquility".format(id)
    data = requests.get(url).json()
    return data

"""
Pass in a list of char IDs (as a string "[2112562768]") and get back '{'character_id': 2112562768, 'corporation_id': 98056040, 'alliance_id': 154104258}'
"""
def getBulkCharInfoFromIDs(ids):
    data = requests.post("https://esi.tech.ccp.is/latest/characters/affiliation/?datasource=tranquility", data=ids).json()
    return data