# ==============================================================================
# Copyright (C) 2019 - Philip Paquette
#
#  This program is free software: you can redistribute it and/or modify it under
#  the terms of the GNU Affero General Public License as published by the Free
#  Software Foundation, either version 3 of the License, or (at your option) any
#  later version.
#
#  This program is distributed in the hope that it will be useful, but WITHOUT
#  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
#  FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
#  details.
#
#  You should have received a copy of the GNU Affero General Public License along
#  with this program.  If not, see <https://www.gnu.org/licenses/>.
# ==============================================================================
""" Aliases and keywords

    - Contains aliases and keywords
    - Keywords are always single words
    - Aliases are only converted in a second pass, so if they contain a keyword, you should replace
      the keyword with its abbreviation.
"""

KEYWORDS = {'>': '', '-': '-', 'ARMY': 'A', 'FLEET': 'F', 'WING': 'W', 'THE': '', 'NC': '/NC', 'SC': '/SC',
            'EC': '/EC', 'WC': '/WC', 'MOVE': '', 'MOVES': '', 'MOVING': '', 'ATTACK': '', 'ATTACKS': '',
            'ATTACKING': '', 'RETREAT': 'R', 'RETREATS': 'R', 'RETREATING': 'R', 'SUPPORT': 'S', 'SUPPORTS': 'S',
            'SUPPORTING': 'S', 'CONVOY': 'C', 'CONVOYS': 'C', 'CONVOYING': 'C', 'HOLD': 'H', 'HOLDS': 'H',
            'HOLDING': 'H', 'BUILD': 'B', 'BUILDS': 'B', 'BUILDING': 'B', 'DISBAND': 'D', 'DISBANDS': 'D',
            'DISBANDING': 'D', 'DESTROY': 'D', 'DESTROYS': 'D', 'DESTROYING': 'D', 'REMOVE': 'D', 'REMOVES': 'D',
            'REMOVING': 'D', 'WAIVE': 'V', 'WAIVES': 'V', 'WAIVING': 'V', 'WAIVED': 'V', 'KEEP': 'K', 'KEEPS': 'K',
            'KEEPING': 'K', 'PROXY': 'P', 'PROXIES': 'P', 'PROXYING': 'P', 'IS': '', 'WILL': '', 'IN': '', 'AT': '',
            'ON': '', 'TO': '', 'OF': '\\', 'FROM': '\\', 'WITH': '?', 'TSR': '=', 'VIA': 'VIA', 'THROUGH': '~',
            'OVER': '~', 'BY': '~', 'OR': '|', 'BOUNCE': '|', 'CUT': '|', 'VOID': '?', 'DISLODGED': '~',
            'DESTROYED': '*'}

ALIASES = {'NORTH COAST \\': '/NC \\', 'SOUTH COAST \\': '/SC \\', 'EAST COAST \\': '/EC \\',
           'WEST COAST \\': '/WC \\', 'AN A': 'A', 'A F': 'F', 'A W': 'W', 'NO C': '?', '~ C': '^',
           '~ =': '=', '? =': '=', '~ LAND': '_', '~ WATER': '_', '~ SEA': '_', 'VIA C': 'VIA',
           'TRANS SIBERIAN RAILROAD': '=', 'V B': 'B V'}
