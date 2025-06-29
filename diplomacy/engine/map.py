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
# -*- coding: utf-8 -*-
# pylint: disable=too-many-lines
""" Map
    - Contains the map object which represents a map where the game can be played
"""
from copy import deepcopy
import os
from diplomacy import settings
from diplomacy.utils import KEYWORDS, ALIASES
import diplomacy.utils.errors as err

# Constants
UNDETERMINED, POWER, UNIT, LOCATION, COAST, ORDER, MOVE_SEP, OTHER = 0, 1, 2, 3, 4, 5, 6, 7
MAP_CACHE = {}


class Map:
    """ Map Class

        Properties:

        - **abbrev**: Contains the power abbreviation, otherwise defaults to first letter of PowerName
          e.g. {'ENGLISH': 'E'}
        - **abuts_cache**: Contains a cache of abuts for ['A,'F'] between all locations for orders ['S', 'C', '-']
          e.g. {(A, PAR, -, MAR): 1, ...}
        - **aliases**: Contains a dict of all the aliases (e.g. full province name to 3 char)
          e.g. {'EAST': 'EAS', 'STP ( /SC )': 'STP/SC', 'FRENCH': 'FRANCE', 'BUDAPEST': 'BUD', 'NOR': 'NWY', ... }
        - **centers**: Contains a dict of owned supply centers for each player at the beginning of the map
          e.g. {'RUSSIA': ['MOS', 'SEV', 'STP', 'WAR'], 'FRANCE': ['BRE', 'MAR', 'PAR'], ... }
        - **convoy_paths**: Contains a list of all possible convoys paths bucketed by number of fleets
          format: {nb of fleets: [(START_LOC, {FLEET LOC}, {DEST LOCS})]}
        - **dest_with_coasts**: Contains a dictionary of locs with all destinations (incl coasts) that can be reached
          e.g. {'PAR': ['BRE', 'PIC', 'BUR', ...], ...}
        - **dummies**: Indicates the list of powers that are dummies
          e.g. ['FRANCE', 'ITALY']
        - **error**: Contains a list of errors that the map generated
          e.g. [''DUPLICATE MAP ALIAS OR POWER: JAPAN']
        - **files**: Contains a list of files that were loaded (e.g. USES keyword)
          e.g. ['standard.map', 'standard.politics', 'standard.geography', 'standard.military']
        - **first_year**: Indicates the year where the game is starting.
          e.g. 1901
        - **flow**: List that contains the seasons with the phases
          e.g. ['SPRING:MOVEMENT,RETREATS', 'FALL:MOVEMENT,RETREATS', 'WINTER:ADJUSTMENTS']
        - **flow_sign**: Indicate the direction of flow (1 is positive, -1 is negative)
          e.g. 1
        - **homes**: Contains the list of supply centers where units can be built (i.e. assigned at the beginning)
          e.g. {'RUSSIA': ['MOS', 'SEV', 'STP', 'WAR'], 'FRANCE': ['BRE', 'MAR', 'PAR'], ... }
        - **inhabits**: List that indicates which power have a INHABITS, HOME, or HOMES line
          e.g. ['FRANCE']
        - **keywords**: Contains a dict of keywords to parse status files and orders
          e.g. {'BUILDS': 'B', '>': '', 'SC': '/SC', 'REMOVING': 'D', 'WAIVED': 'V', 'ATTACK': '', ... }
        - **loc_abut**: Contains a adjacency list for each province
          e.g. {'LVP': ['CLY', 'edi', 'IRI', 'NAO', 'WAL', 'yor'], ...}
        - **loc_coasts**: Contains a mapping of all coasts for every location
          e.g. {'PAR': ['PAR'], 'BUL': ['BUL', 'BUL/EC', 'BUL/SC'], ... }
        - **loc_name**: Dict that indicates the 3 letter name of each location
          e.g. {'GULF OF LYON': 'LYO', 'BREST': 'BRE', 'BUDAPEST': 'BUD', 'RUHR': 'RUH', ... }
        - **loc_type**: Dict that indicates if each location is 'WATER', 'COAST', 'LAND', or 'PORT'
          e.g. {'MAO': 'WATER', 'SER': 'LAND', 'SYR': 'COAST', 'MOS': 'LAND', 'VEN': 'COAST', ... }
        - **locs**: List of 3 letter locations (With coasts)
          e.g. ['ADR', 'AEG', 'ALB', 'ANK', 'APU', 'ARM', 'BAL', 'BAR', 'BEL', 'BER', ... ]
        - **name**: Name of the map (or full path to a custom map file)
          e.g. 'standard' or '/some/path/to/file.map'
        - **own_word**: Dict to indicate the word used to refer to people living in each power's country
          e.g. {'RUSSIA': 'RUSSIAN', 'FRANCE': 'FRENCH', 'UNOWNED': 'UNOWNED', 'TURKEY': 'TURKISH', ... }
        - **owns**: List that indicates which power have a OWNS or CENTERS line
          e.g. ['FRANCE']
        - **phase**: String to indicate the beginning phase of the map
          e.g. 'SPRING 1901 MOVEMENT'
        - **phase_abbrev**: Dict to indicate the 1 letter abbreviation for each phase
          e.g. {'A': 'ADJUSTMENTS', 'M': 'MOVEMENT', 'R': 'RETREATS'}
        - **pow_name**: Dict to indicate the power's name
          e.g. {'RUSSIA': 'RUSSIA', 'FRANCE': 'FRANCE', 'TURKEY': 'TURKEY', 'GERMANY': 'GERMANY', ... }
        - **powers**: Contains the list of powers (players) in the game
          e.g. ['AUSTRIA', 'ENGLAND', 'FRANCE', 'GERMANY', 'ITALY', 'RUSSIA', 'TURKEY']
        - **root_map**: Contains the name of the original map file loaded (before the USES keyword are applied)
          A map that is called with MAP is the root_map. e.g. 'standard'
        - **rules**: Contains a list of rules used by all variants (for display only)
          e.g. ['RULE_1']
        - **scs**: Contains a list of all the supply centers in the game
          e.g. ['MOS', 'SEV', 'STP', 'WAR', 'BRE', 'MAR', 'PAR', 'BEL', 'BUL', 'DEN', 'GRE', 'HOL', 'NWY', ... ]
        - **seq**: [] Contains the sequence of seasons in format 'SEASON_NAME SEASON_TYPE'
          e.g. ['NEWYEAR', 'SPRING MOVEMENT', 'SPRING RETREATS', 'FALL MOVEMENT', 'FALL RETREATS', 'WINTER ADJUSTMENTS']
        - **unclear**: Contains the alias for ambiguous places
          e.g. {'EAST': 'EAS'}
        - **unit_names**: {} Contains a dict of the unit names
          e.g. {'F': 'FLEET', 'A': 'ARMY'}
        - **units**: Dict that contains the current position of each unit by power
          e.g. {'FRANCE': ['F BRE', 'A MAR', 'A PAR'], 'RUSSIA': ['A WAR', 'A MOS', 'F SEV', 'F STP/SC'], ... }
        - **validated**: Boolean to indicate if the map file has been validated
          e.g. 1
        - **victory**: Indicates the number of supply centers to win the game (>50% required if None)
          e.g. 18
    """
    # pylint: disable=too-many-instance-attributes

    __slots__ = ['name', 'first_year', 'victory', 'phase', 'validated', 'flow_sign', 'root_map', 'abuts_cache',
                 'homes', 'loc_name', 'loc_type', 'loc_abut', 'loc_coasts', 'own_word', 'abbrev', 'centers', 'units',
                 'pow_name', 'rules', 'files', 'powers', 'scs', 'owns', 'inhabits', 'flow', 'dummies', 'locs', 'error',
                 'seq', 'phase_abbrev', 'unclear', 'unit_names', 'keywords', 'aliases', 'convoy_paths',
                 'dest_with_coasts']

    def __new__(cls, name='standard', use_cache=True):
        """ New function - Retrieving object from cache if possible

            :param name: Name of the map to load
            :param use_cache: Boolean flag to indicate we want a blank object that doesn't use cache
        """
        if name in MAP_CACHE and use_cache:
            return MAP_CACHE[name]
        return object.__new__(cls)

    def __init__(self, name='standard', use_cache=True):
        """ Constructor function

            :param name: Name of the map to load (or full path to a custom map file)
            :param use_cache: Boolean flag to indicate we want a blank object that doesn't use cache
        """
        if name in MAP_CACHE:
            return
        self.name = name
        self.first_year = 1901
        self.victory = self.phase = self.validated = self.flow_sign = None
        self.root_map = None
        self.abuts_cache = {}
        self.homes, self.loc_name, self.loc_type, self.loc_abut, self.loc_coasts = {}, {}, {}, {}, {}
        self.own_word, self.abbrev, self.centers, self.units, self.pow_name = {}, {}, {}, {}, {}
        self.rules, self.files, self.powers, self.scs, self.owns, self.inhabits = [], [], [], [], [], []
        self.flow, self.dummies, self.locs = [], [], []
        self.error, self.seq = [], []
        self.phase_abbrev, self.unclear, self.dest_with_coasts = {}, {}, {}
        self.unit_names = {'A': 'ARMY', 'F': 'FLEET'}
        self.keywords, self.aliases = KEYWORDS.copy(), ALIASES.copy()
        self.load()
        self.build_cache()
        self.validate()
        if name not in CONVOYS_PATH_CACHE and use_cache:
            CONVOYS_PATH_CACHE[name] = add_to_cache(name)
        self.convoy_paths = CONVOYS_PATH_CACHE.get(name, {})
        if use_cache:
            MAP_CACHE[name] = self

    def __deepcopy__(self, memo):
        """ Fast deep copy implementation """
        actual_init = self.__class__.__init__
        self.__class__.__init__ = lambda *args, **kwargs: None
        instance = self.__class__(name=self.name, use_cache=False)
        self.__class__.__init__ = actual_init
        for key in self.__slots__:
            setattr(instance, key, deepcopy(getattr(self, key)))
        return instance

    def __str__(self):
        return self.name

    @property
    def svg_path(self):
        """ Return path to the SVG file of this map (or None if it does not exist) """
        for file_name in [self.name + '.svg', self.root_map + '.svg']:
            svg_path = os.path.join(settings.PACKAGE_DIR, 'maps', 'svg', file_name)
            if os.path.exists(svg_path):
                return svg_path
        return None

    def validate(self, force=0):
        """ Validate that the configuration from a map file is correct

            :param force: Indicate that we want to force a validation, even if the map is already validated
            :return: Nothing
        """
        # pylint: disable=too-many-branches
        # Already validated, returning (except if forced or if validating phases)
        if not force and self.validated:
            return
        self.validated = 1

        # Root map
        self.root_map = self.root_map or self.name

        # Validating powers
        self.powers = [power_name for power_name in self.homes if power_name != 'UNOWNED']
        self.powers.sort()
        if len(self.powers) < 2:
            self.error += [err.MAP_LEAST_TWO_POWERS]

        # Validating area type
        for place in self.loc_name.values():
            if place.upper() not in self.powers and not self.area_type(place):
                self.error += [err.MAP_LOC_NOT_FOUND % place]

        # Validating adjacencies
        for place, abuts in self.loc_abut.items():
            up_abuts = [loc.upper() for loc in abuts]
            for abut in abuts:
                up_abut = abut.upper()
                if up_abuts.count(up_abut) > 1:
                    self.error += [err.MAP_SITE_ABUTS_TWICE % (place.upper(), up_abut)]
                    while up_abut in up_abuts:
                        up_abuts.remove(up_abut)

            # Checking full name
            if place.upper() not in self.loc_name.values():
                self.error += [err.MAP_NO_FULL_NAME % place]

            # Checking one-way adjacency
            # Adjacencies between lower-case coast and water are supposed to be one-way
            for loc in abuts:
                if self.area_type(place) != 'SHUT' \
                        and self.area_type(loc) != 'SHUT' \
                        and not self.abuts('A', loc, '-', place) \
                        and not self.abuts('F', loc, '-', place) \
                        and not (place.islower() and self.area_type(loc) == 'WATER'):
                    self.error.append(err.MAP_ONE_WAY_ADJ % (place, loc))

            # Loc without coasts (e.g. 'spa' on the standard map) need to be adjacent to all nearby water locations
            # Computing the list of water locs adjacent from coast locs (e.g. 'SPA/NC') and making sure they
            # are also adjacent to the coast without loc (i.e. 'spa')
            if place != place.lower():
                continue

            adj_water_locs = set()
            for coast_loc in self.find_coasts(place):
                if coast_loc.upper() == place.upper():
                    continue
                adj_water_locs |= {loc.upper() for loc in self.loc_abut[coast_loc] if self.area_type(loc) == 'WATER'}
            missing_water_locs = adj_water_locs - set(up_abuts)
            for water_loc in missing_water_locs:
                self.error.append(err.MAP_MISSING_ADJ % (place, water_loc))

        # Validating home centers
        for power_name, places in self.homes.items():
            for site in places:
                # Adding home as supply center
                if site not in self.scs:
                    self.scs += [site]
                if not self.area_type(site):
                    self.error += [err.MAP_BAD_HOME % (power_name, site)]

                # Remove home centers from unowned list.
                # It's perfectly OK for 2 powers to share a home center, as long
                # as no more than one owns it at the same time.
                if power_name != 'UNOWNED':
                    if site in self.homes['UNOWNED']:
                        self.homes['UNOWNED'].remove(site)

        # Valid supply centers
        for scs in self.centers.values():
            self.scs.extend([center for center in scs if center not in self.scs])

        # Validating initial centers and units
        for power_name, places in self.centers.items():
            for loc in places:
                if not self.area_type(loc):
                    self.error.append(err.MAP_BAD_INITIAL_OWN_CENTER % (power_name, loc))

        # Checking if power has OWN line
        for power_name in self.powers:
            if power_name not in self.owns:
                self.centers[power_name] = self.homes[power_name][:]
            for unit in self.units.get(power_name, []):
                if not self.is_valid_unit(unit):
                    self.error.append(err.MAP_BAD_INITIAL_UNITS % (power_name, unit))

        # Checking for multiple owners
        for power_name, centers in self.centers.items():
            for site in centers:
                for other, locs in self.centers.items():
                    if other == power_name and locs.count(site) != 1:
                        self.error += [err.MAP_CENTER_MULT_OWNED % site]
                    elif other != power_name and locs.count(site) != 0:
                        self.error += [err.MAP_CENTER_MULT_OWNED % site]
        if 'UNOWNED' in self.homes:
            del self.homes['UNOWNED']

        # Ensure a default game-year FLOW
        self.flow = ['SPRING:MOVEMENT,RETREATS', 'FALL:MOVEMENT,RETREATS', 'WINTER:ADJUSTMENTS']
        self.flow_sign = 1
        self.seq = ['NEWYEAR', 'SPRING MOVEMENT', 'SPRING RETREATS', 'FALL MOVEMENT', 'FALL RETREATS',
                    'WINTER ADJUSTMENTS']
        self.phase_abbrev = {'M': 'MOVEMENT', 'R': 'RETREATS', 'A': 'ADJUSTMENTS'}

        # Validating initial game phase
        self.phase = self.phase or 'SPRING 1901 MOVEMENT'
        phase = self.phase.split()
        if len(phase) != 3:
            self.error += [err.MAP_BAD_PHASE % self.phase]
        else:
            self.first_year = int(phase[1])

    def load(self, file_name=None):
        """ Loads a map file from disk

            :param file_name: Optional. A string representing the file to open. Otherwise, defaults to the map name
            :return: Nothing
        """
        # pylint: disable=too-many-nested-blocks,too-many-statements,too-many-branches
        # If file_name is string, opening file from disk
        # Otherwise file_name is the file handler
        power = 0
        if file_name is None:
            file_name = '{}.map'.format(self.name) if not self.name.endswith('.map') else self.name

        # If file_name is a path to a custom map, we use that path, otherwise, we check in the maps folder
        if os.path.exists(file_name):
            file_path = file_name
        else:
            file_path = os.path.join(settings.PACKAGE_DIR, 'maps', file_name)

        # Checking if file exists:
        found_map = 1 if os.path.exists(file_path) else 0
        if not found_map:
            self.error.append(err.MAP_FILE_NOT_FOUND % file_name)
            return

        # Adding to parsed files
        self.files += [file_name]

        # Parsing file
        with open(file_path, encoding='utf-8') as file:
            variant = 0

            for line in file:
                word = line.split()

                # -- # comment...
                if not word or word[0][0] == '#':
                    continue
                upword = word[0].upper()

                # ----------------------------------
                # Centers needed to obtain a VICTORY
                # -- VICTORY centerCount...
                if upword == 'VICTORY':
                    try:
                        self.victory = [int(word) for word in word[1:]]
                    except ValueError:
                        self.error += [err.MAP_BAD_VICTORY_LINE]

                # ---------------------------------
                # Inclusion of other base map files
                # -- USE[S] fileName...
                # -- MAP mapName
                elif upword in ('USE', 'USES', 'MAP'):
                    if upword == 'MAP':
                        if len(word) != 2:
                            self.error += [err.MAP_BAD_ROOT_MAP_LINE]
                        elif self.root_map:
                            self.error += [err.MAP_TWO_ROOT_MAPS]
                        else:
                            self.root_map = word[1].split('.')[0]
                    for new_file in word[1:]:
                        if '.' not in new_file:
                            new_file = '{}.map'.format(new_file)
                        if new_file not in self.files:
                            self.load(new_file)
                        else:
                            self.error += [err.MAP_FILE_MULT_USED % new_file]

                # ------------------------------------
                # Set BEGIN phase
                # -- BEGIN season year phaseType
                elif upword == 'BEGIN':
                    self.phase = ' '.join(word[1:]).upper()

                # ------------------------------------
                # RULEs specific to this map
                elif upword in ('RULE', 'RULES'):
                    if (variant or 'ALL') == 'ALL':
                        self.rules += line.upper().split()[1:]

                # ------------------------------------
                # -- [oldAbbrev ->] placeName = abbreviation alias...
                elif '=' in line:
                    token = line.upper().split('=')
                    if len(token) == 1:
                        self.error += [err.MAP_BAD_ALIASES_IN_FILE % token[0]]
                        token += ['']
                    old_name, name, word = 0, token[0].strip(), token[1].split()
                    parts = [part.strip() for part in name.split('->')]
                    if len(parts) == 2:
                        old_name, name = parts
                    elif len(parts) > 2:
                        self.error += [err.MAP_BAD_RENAME_DIRECTIVE % name]
                    if not (word[0][0] + word[0][-1]).isalnum() or word[0] != self.norm(word[0]).replace(' ', ''):
                        self.error += [err.MAP_INVALID_LOC_ABBREV % word[0]]

                    # Rename no longer supported
                    # Making sure place not already there
                    if old_name:
                        self.error += [err.MAP_RENAME_NOT_SUPPORTED]
                    if name in self.keywords:
                        self.error += [err.MAP_LOC_RESERVED_KEYWORD % name]
                        normed = name
                    else:
                        normed = self.norm(name)
                    if name in self.loc_name or normed in self.aliases:
                        self.error += [err.MAP_DUP_LOC_OR_POWER % name]
                    self.loc_name[name] = self.aliases[normed] = word[0]

                    # Ambiguous place names end with a ?
                    for alias in word[1:]:
                        unclear = alias[-1] == '?'
                        # For ambiguous place names, let's do just a minimal normalization
                        # otherwise they might become unrecognizable (e.g. "THE")
                        normed = alias[:-1].replace('+', ' ').upper() if unclear else self.norm(alias)
                        if unclear:
                            self.unclear[normed] = word[0]
                        elif normed in self.aliases:
                            if self.aliases[normed] != word[0]:
                                self.error += [err.MAP_DUP_ALIAS_OR_POWER % alias]
                        else:
                            self.aliases[normed] = word[0]

                # ------------------------------------
                # Center ownership (!= Home Ownership)
                # -- OWNS center...
                # -- CENTERS [center...]
                elif upword in ('OWNS', 'CENTERS'):
                    if not power:
                        self.error += [err.MAP_OWNS_BEFORE_POWER % (upword, ' '.join(word))]
                    else:
                        if power not in self.owns:
                            self.owns.append(power)
                        # CENTERS resets the list of centers, OWNS only appends
                        if upword[0] == 'C' or power not in self.centers:
                            self.centers[power] = line.upper().split()[1:]
                        else:
                            self.centers[power].extend(
                                [center for center in line.upper().split()[1:] if center not in self.centers[power]])

                # ------------------------------------
                # Home centers, overriding those from the power declaration line
                # -- INHABITS center...
                elif upword == 'INHABITS':
                    if not power:
                        self.error += [err.MAP_INHABITS_BEFORE_POWER % ' '.join(word)]
                    else:
                        reinit = power not in self.inhabits
                        if reinit:
                            self.inhabits.append(power)
                        self.add_homes(power, word[1:], reinit)

                # -- HOME(S) [center...]
                elif upword in ('HOME', 'HOMES'):
                    if not power:
                        self.error += [err.MAP_HOME_BEFORE_POWER % (upword, ' '.join(word))]
                    else:
                        if power not in self.inhabits:
                            self.inhabits.append(power)
                        self.add_homes(power, word[1:], 1)

                # ------------------------------------
                # Clear known units for a power
                # -- UNITS
                elif upword == 'UNITS':
                    if power:
                        self.units[power] = []
                    else:
                        self.error += [err.MAP_UNITS_BEFORE_POWER]

                # ------------------------------------
                # Unit Designation (A or F)
                # -- unit location
                elif upword in ('A', 'F'):
                    unit = ' '.join(word).upper()
                    if not power:
                        self.error += [err.MAP_UNIT_BEFORE_POWER]
                    elif len(word) == 2:
                        for units in self.units.values():
                            for current_unit in units:
                                if current_unit[2:5] == unit[2:5]:
                                    units.remove(current_unit)
                        self.units.setdefault(power, []).append(unit)
                    else:
                        self.error += [err.MAP_INVALID_UNIT % unit]

                # ------------------------------------
                # Dummies
                # -- DUMMY [ALL] -or-
                # -- DUMMY [ALL EXCEPT] powerName... -or-
                # -- DUMMIES ALL -or-
                # -- DUMMIES [ALL EXCEPT] powerName...
                elif upword in ('DUMMY', 'DUMMIES'):
                    if len(word) > 1:
                        power = None
                    # DUMMY
                    if len(word) == 1:
                        if upword == 'DUMMIES':
                            self.error += [err.MAP_DUMMY_REQ_LIST_POWERS]
                        elif not power:
                            self.error += [err.MAP_DUMMY_BEFORE_POWER]
                        elif power not in self.dummies:
                            self.dummies += [power]
                    # DUMMY powerName powerName
                    elif word[1].upper() != 'ALL':
                        self.dummies.extend(
                            [dummy for dummy in [self.norm_power(p_name) for p_name in word[1:]]
                             if dummy not in self.dummies])
                    # DUMMY ALL
                    elif len(word) == 2:
                        self.dummies = [power_name for power_name in self.homes if power_name != 'UNOWNED']
                    # DUMMY ALL powerName
                    elif word[2].upper() != 'EXCEPT':
                        self.error += [err.MAP_NO_EXCEPT_AFTER_DUMMY_ALL % upword]
                    # DUMMY ALL EXCEPT
                    elif len(word) == 3:
                        self.error += [err.MAP_NO_POWER_AFTER_DUMMY_ALL_EXCEPT % upword]
                    # DUMMY ALL EXCEPT powerName powerName
                    else:
                        self.dummies = [power_name for power_name in self.homes if power_name not in
                                        (['UNOWNED'] + [self.norm_power(except_pow) for except_pow in word[3:]])]

                # ------------------------------------
                # -- DROP abbreviation...
                elif upword == 'DROP':
                    for place in [loc.upper() for loc in word[1:]]:
                        self.drop(place)

                # ------------------------------------
                # Terrain type and adjacencies (with special adjacency rules)
                # -- COAST abbreviation [ABUTS [abut...]] -or-
                # -- LAND  abbreviation [ABUTS [abut...]] -or-
                # -- WATER abbreviation [ABUTS [abut...]] -or-
                # -- PORT  abbreviation [ABUTS [abut...]] -or-
                # -- SHUT  abbreviation [ABUTS [abut...]] -or-
                # -- AMEND abbreviation [ABUTS [abut...]]
                # --    - removes an abut
                elif len(word) > 1 and upword in ('AMEND', 'WATER', 'LAND', 'COAST', 'PORT', 'SHUT'):
                    place, other = word[1], word[1].swapcase()

                    # Removing the place and all its coasts
                    if other in self.locs:
                        self.locs.remove(other)
                        if upword == 'AMEND':
                            self.loc_type[place] = self.loc_type[other]
                            self.loc_abut[place] = self.loc_abut[other]
                        del self.loc_type[other]
                        del self.loc_abut[other]
                        if place.isupper():
                            for loc in self.locs:
                                if loc.startswith(place):
                                    self.drop(loc)
                    if place in self.locs:
                        self.locs.remove(place)

                    # Re-adding the place and its type
                    self.locs += [place]
                    if upword != 'AMEND':
                        self.loc_type[place] = word[0]
                        if len(word) > 2:
                            self.loc_abut[place] = []
                    elif place not in self.loc_type:
                        self.error += [err.MAP_NO_DATA_TO_AMEND_FOR % place]
                    if len(word) > 2 and word[2].upper() != 'ABUTS':
                        self.error += [err.MAP_NO_ABUTS_FOR % place]

                    # Processing ABUTS (adjacencies)
                    for dest in word[3:]:

                        # Removing abuts if they start with -
                        if dest[0] == '-':
                            for site in self.loc_abut[place][:]:
                                if site.upper().startswith(dest[1:].upper()):
                                    self.loc_abut[place].remove(site)
                            continue

                        # Now add the adjacency
                        self.loc_abut[place] += [dest]

                # ------------------------------------
                # Removal of an existing power
                # -- UNPLAYED [ALL] -or-
                # -- UNPLAYED [ALL EXCEPT] powerName...
                elif upword == 'UNPLAYED':
                    goners = []
                    # UNPLAYED powerName
                    if len(word) == 1:
                        if not power:
                            self.error += [err.MAP_UNPLAYED_BEFORE_POWER]
                        else:
                            goners = [power]
                    # UNPLAYED powerName powerName
                    elif word[1].upper() != 'ALL':
                        goners = [self.norm_power(power_name) for power_name in word[1:]]
                    # UNPLAYED ALL
                    elif len(word) == 2:
                        goners = [power_name for power_name in self.homes if power_name != 'UNOWNED']
                    # UNPLAYED ALL playerName
                    elif word[2].upper() != 'EXCEPT':
                        self.error += [err.MAP_NO_EXCEPT_AFTER_UNPLAYED_ALL]
                    # UNPLAYED ALL EXCEPT
                    elif len(word) == 3:
                        self.error += [err.MAP_NO_POWER_AFTER_UNPLAYED_ALL_EXCEPT]
                    # UNPLAYED ALL EXCEPT powerName
                    else:
                        goners = [power_name for power_name in self.homes if power_name not in
                                  (['UNOWNED'] + [self.norm_power(pow_except) for pow_except in word[3:]])]

                    # Removing each power
                    for goner in goners:
                        try:
                            del self.pow_name[goner]
                            del self.own_word[goner]
                            del self.homes[goner]
                            self.dummies = [x for x in self.dummies if x != goner]
                            self.inhabits = [x for x in self.inhabits if x != goner]
                            if goner in self.centers:
                                del self.centers[goner]
                            self.owns = [x for x in self.owns if x != goner]
                            if goner in self.abbrev:
                                del self.abbrev[goner]
                            if goner in self.units:
                                del self.units[goner]
                            self.powers = [x for x in self.powers if x != goner]
                        except KeyError:
                            self.error += [err.MAP_NO_SUCH_POWER_TO_REMOVE % goner]
                    power = None

                else:
                    # ------------------------------------
                    # Power name, ownership word, and home centers
                    # -- [oldName ->] powerName [([ownWord][:[abbrev]])] [center...]
                    # -- UNOWNED [center...] -or-
                    # -- NEUTRAL [center...] -or-
                    # -- CENTERS [center...]
                    if upword in ('NEUTRAL', 'CENTERS'):
                        upword = 'UNOWNED'
                    power = self.norm_power(upword) if upword != 'UNOWNED' else 0

                    # Renaming power (Not Supported)
                    if len(word) > 2 and word[1] == '->':
                        old_power = power
                        word = word[2:]
                        upword = word[0].upper()
                        if upword in ('NEUTRAL', 'CENTERS'):
                            upword = 'UNOWNED'
                        power = self.norm_power(upword) if upword != 'UNOWNED' else 0
                        if not old_power or not power:
                            self.error += [err.MAP_RENAMING_UNOWNED_DIR_NOT_ALLOWED]
                        elif not self.pow_name.get(old_power):
                            self.error += [err.MAP_RENAMING_UNDEF_POWER % old_power]
                        else:
                            self.error += [err.MAP_RENAMING_POWER_NOT_SUPPORTED]

                    # Adding power
                    if power and not self.pow_name.get(power):
                        self.pow_name[power] = upword
                        normed = self.norm(power)
                        # Add power to aliases even if the normed form is identical. That way
                        # it becomes part of the vocabulary.
                        if not normed:
                            self.error += [err.MAP_POWER_NAME_EMPTY_KEYWORD % power]
                            normed = power
                        if normed not in self.aliases:
                            if len(normed.split('/')[0]) in (1, 3):
                                self.error += [err.MAP_POWER_NAME_CAN_BE_CONFUSED % normed]
                            self.aliases[normed] = power
                        elif self.aliases[normed] != power:
                            self.error += [err.MAP_DUP_LOC_OR_POWER % normed]

                    # Processing own word and abbreviations
                    upword = power or upword
                    if power and len(word) > 1 and word[1][0] == '(':
                        self.own_word[upword] = word[1][1:-1] or power
                        normed = self.norm(self.own_word[upword])
                        if normed == power:
                            pass
                        elif normed not in self.aliases:
                            self.aliases[normed] = power
                        elif self.aliases[normed] != power:
                            self.error += [err.MAP_DUP_LOC_OR_POWER % normed]
                        if ':' in word[1]:
                            owner, abbrev = self.own_word[upword].split(':')
                            self.own_word[upword] = owner or power
                            self.abbrev[upword] = abbrev[:1].upper()
                            if not abbrev or self.abbrev[upword] in 'M?':
                                self.error += [err.MAP_ILLEGAL_POWER_ABBREV]
                        del word[1]
                    else:
                        self.own_word.setdefault(upword, upword)

                    # Adding homes
                    reinit = upword in self.inhabits
                    if reinit:
                        self.inhabits.remove(upword)
                    self.add_homes(upword, word[1:], reinit)

    def build_cache(self):
        """ Builds a cache to speed up abuts and coasts lookup """
        # Adding all coasts to loc_coasts
        for loc in self.locs:
            self.loc_coasts[loc.upper()] = \
                [map_loc.upper() for map_loc in self.locs if loc.upper()[:3] == map_loc.upper()[:3]]

        # Building abuts cache
        for unit_type in ['A', 'F']:
            for unit_loc in self.locs:
                for other_loc in self.locs:
                    for order_type in ['-', 'S', 'C']:

                        # Calculating and setting in cache
                        unit_loc, other_loc = unit_loc.upper(), other_loc.upper()
                        query_tuple = (unit_type, unit_loc, order_type, other_loc)
                        self.abuts_cache[query_tuple] = self._abuts(*query_tuple)

        # Building dest_with_coasts
        for loc in self.locs:
            loc = loc.upper()
            dest_1_hops = [l.upper() for l in self.abut_list(loc, incl_no_coast=True)]
            dest_with_coasts = [self.find_coasts(dest) for dest in dest_1_hops]
            self.dest_with_coasts[loc] = list({val for sublist in dest_with_coasts for val in sublist})

    def add_homes(self, power, homes, reinit):
        """ Add new homes (and deletes previous homes if reinit)

            :param power: Name of power (e.g. ITALY)
            :param homes: List of homes e.g. ``['BUR', '-POR', '*ITA', ... ]``
            :param reinit: Indicates that we want to strip the list of homes before adding
            :return: Nothing
        """
        # Reset homes
        if reinit:
            self.homes[power] = []
        else:
            self.homes.setdefault(power, [])
        self.homes.setdefault('UNOWNED', [])

        # For each home:
        # '-' indicates we want to remove home
        for home in ' '.join(homes).upper().split():
            remove = 0
            while home:
                if home[0] == '-':
                    remove = 1
                else:
                    break
                home = home[1:]
            if not home:
                continue

            # Removing the home if already there
            if home in self.homes[power]:
                self.homes[power].remove(home)
            if power != 'UNOWNED':
                self.homes['UNOWNED'].append(home)

            # Re-adding it
            if not remove:
                self.homes[power].append(home)

    def drop(self, place):
        """ Drop a place

            :param place: Name of place to remove
            :return: Nothing
        """
        # Removing from locs
        for loc in list(self.locs):
            if loc.upper().startswith(place):
                self.locs.remove(loc)

        # Loc_name
        for full_name, loc in list(self.loc_name.items()):
            if loc.startswith(place):
                self.loc_name.pop(full_name)

        # Aliases
        for alias, loc in list(self.aliases.items()):
            if loc.startswith(place):
                self.aliases.pop(alias)

        # Homes
        for power_name, power_homes in list(self.homes.items()):
            if place in power_homes:
                self.homes[power_name].remove(place)

        # Units
        for power_name, power_units in list(self.units.items()):
            for unit in power_units:
                if unit[2:5] == place[:3]:
                    self.units[power_name].remove(unit)

        # Supply Centers
        for center in list(self.scs):
            if center.upper().startswith(place):
                self.scs.remove(center)

        # Centers ownerships
        for power_name, power_centers in list(self.centers.items()):
            for center in power_centers:
                if center.startswith(place):
                    self.centers[power_name].remove(center)

        # Removing from adjacencies list
        for site_name, site_abuts in list(self.loc_abut.items()):
            for site in [loc for loc in site_abuts if loc.upper().startswith(place)]:
                self.loc_abut[site_name].remove(site)
            if site_name.startswith(place):
                self.loc_abut.pop(site_name)

        # Removing loc_type
        for loc in list(self.loc_type):
            if loc.startswith(place):
                self.loc_type.pop(loc)

    def norm_power(self, power):
        """ Normalise the name of a power (removes spaces)

            :param power: Name of power to normalise
            :return: Normalised power name
        """
        return self.norm(power).replace(' ', '')

    def norm(self, phrase):
        """ Normalise a sentence (add spaces before /, replace -+, with ' ', remove .:

            :param phrase: Phrase to normalise
            :return: Normalised sentences
        """
        phrase = phrase.upper().replace('/', ' /').replace(' / ', '')
        for token in '.:-+,':
            phrase = phrase.replace(token, ' ')
        for token in '|*?!~()[]=_^':
            phrase = phrase.replace(token, ' {} '.format(token))

        # Replace keywords which, contrary to aliases, all consist of a single word
        return ' '.join([self.keywords.get(keyword, keyword) for keyword in phrase.strip().split()])

    def compact(self, phrase):
        """ Compacts a full sentence into a list of short words

            :param phrase: The full sentence to compact (e.g. 'England: Fleet Western Mediterranean -> Tyrrhenian
               Sea. (*bounce*)')
            :return: The compacted phrase in an array (e.g. ['ENGLAND', 'F', 'WES', 'TYS', '|'])
        """
        if ':' in phrase:
            # Check if first part of phrase (before colon) is a power, and remove it if that's the case.
            index_colon = phrase.index(':')
            first_part = phrase[:index_colon]
            result = self.vet(self.compact(first_part))
            if len(result) == 1 and result[0][1] == POWER:
                phrase = phrase[(index_colon + 1):]
        word, result = self.norm(phrase).split(), []
        while word:
            alias, i = self.alias(word)
            if alias:
                result += alias.split()
            word = word[i:]
        return result

    def alias(self, word):
        """ This function is used to replace multi-words with their acronyms

            :param word: The current list of words to try to shorten
            :return: alias, ix - alias is the shorten list of word, ix is the ix of the next non-processed word
        """
        # pylint: disable=too-many-return-statements
        # Assume that word already was subject to norm()
        # Process with content inside square or round brackets
        j = -1
        alias = word[0]
        if alias in '([':
            for j in range(1, len(word)):
                if word[j] == '])'[alias == '(']:
                    break
            else:
                return alias, 1
            if j == 1:
                return '', 2
            if word[1] + word[j - 1] == '**':
                word2 = word[2:j - 1]
            else:
                word2 = word[1:j]
                alias2 = self.aliases.get(' '.join(word2) + ' \\', '')
                if alias2[-2:] == ' \\':
                    return alias2[:-2], j + 1
            result = []
            while word2:
                alias2, i = self.alias(word2)
                if alias2:
                    result += [alias2]
                word2 = word2[i:]
            return ' '.join(result), j + 1
        for i in range(len(word), 0, -1):
            key = ' '.join(word[:i])
            if key in self.aliases:
                alias = self.aliases[key]
                break
        else:
            i = 1

        # Concatenate coasts
        if i == len(word):
            return self._resolve_unclear(alias), i
        if alias[0] != '/' and ' ' not in alias:
            alias2, j = self.alias(word[i:])
            if alias2[0] != '/' or ' ' in alias2:
                return self._resolve_unclear(alias), i
        elif alias[-2:] == ' \\':
            alias2, j = self.alias(word[i:])
            if alias2[0] == '/' or ' ' in alias2:
                return alias, i
            alias, alias2 = alias2, alias[:-2]
        else:
            return self._resolve_unclear(alias), i

        # Check if the location is also an ambiguous power name
        # and replace with its other name if that's the case
        alias = self._resolve_unclear(alias)

        # Check if the coast is mapped to another coast
        if alias + ' ' + alias2 in self.aliases:
            return self.aliases[alias + ' ' + alias2], i + j
        return alias + alias2, i + j

    def _resolve_unclear(self, alias):
        """ Check if given aliases string is an unclear power name.
            If that's the case, return other name associated to this alias.
            Otherwise, return alias unchanged,
        """
        if alias in self.powers and alias in self.unclear:
            alias = self.unclear[alias]
        return alias

    def vet(self, word, strict=0):
        """ Determines the type of every word in a compacted order phrase

            0 - Undetermined,
            1 - Power,
            2 - Unit,
            3 - Location,
            4 - Coastal location
            5 - Order,
            6 - Move Operator ``(-=_^)``,
            7 - Non-move separator ``(|?~)`` or result ``(*!?~+)``

            :param word: The list of words to vet (e.g. ``['A', 'POR', 'S', 'SPA/NC']``)
            :param strict: Boolean to indicate that we want to verify that the words actually exist.
                           Numbers become negative if they don't exist
            :return: A list of tuple (e.g. ``[('A', 2), ('POR', 3), ('S', 5), ('SPA/NC', 4)]``)
        """
        result = []
        for thing in word:
            if ' ' in thing:
                data_type = UNDETERMINED
            elif len(thing) == 1:
                if thing in self.unit_names:
                    data_type = UNIT
                elif thing.isalnum():
                    data_type = ORDER
                elif thing in '-=_':
                    data_type = MOVE_SEP
                else:
                    data_type = OTHER
            elif '/' in thing:
                if thing.find('/') == 3:
                    data_type = COAST
                else:
                    data_type = POWER
            elif thing == 'VIA':
                data_type = ORDER
            elif len(thing) == 3:
                data_type = LOCATION
            else:
                data_type = POWER
            if strict and thing not in list(self.aliases.values()) + list(self.keywords.values()):
                data_type = -data_type
            result += [(thing, data_type)]
        return result

    def rearrange(self, word):
        """ This function is used to parse commands

            :param word: The list of words to vet (e.g. ['ENGLAND', 'F', 'WES', 'TYS', '|'])
            :return: The list of words in the correct order to be processed (e.g. ['ENGLAND', 'F', 'WES', '-', 'TYS'])
        """
        # pylint: disable=too-many-branches
        # Add | to start and end of list (to simplify edge cases) (they will be returned as ('|', 7))
        # e.g. [('|', 7), ('A', 2), ('POR', 3), ('S', 5), ('SPA/NC', 4), ('|', 7)]
        result = self.vet(['|'] + word + ['|'])

        # Remove result tokens (7) at start and end of string (but keep |)
        result[0] = ('|', UNDETERMINED)
        while result[-2][1] == OTHER:
            del result[-2]
        if len(result) == 2:
            return []
        result[0] = ('|', OTHER)
        while result[1][1] == OTHER:
            del result[1]

        # Move "with" unit and location to the start. There should be only one
        # Ignore the rest
        found = 0
        while ('?', OTHER) in result:
            i = result.index(('?', OTHER))
            del result[i]
            if found:
                continue
            j = -1
            for j in range(i, len(result)):
                if result[j][1] in (POWER, UNIT):
                    continue
                if result[j][1] in (LOCATION, COAST):
                    j += 1
                break
            if j != i:
                found = 1
                k = 0
                for k in range(1, i):
                    if result[k][1] not in (POWER, UNIT):
                        break
                if k < i:
                    result[k:k] = result[i:j]
                    result[j:2 * j - i] = []

        # Move "from" location before any preceding locations
        while ('\\', OTHER) in result:
            i = result.index(('\\', OTHER))
            del result[i]
            if result[i][1] not in (LOCATION, COAST):
                continue
            for j in range(i - 1, -1, -1):
                if result[j][1] not in (LOCATION, COAST) and result[j][0] != '~':
                    break
            if j + 1 != i:
                result[j + 1:j + 1] = result[i:i + 1]
                del result[i + 1]

        # Move "via" locations between the two preceding locations.
        while ('~', OTHER) in result:
            i = result.index(('~', OTHER))
            del result[i]
            if (result[i][1] not in (LOCATION, COAST)
                    or result[i - 1][1] not in (LOCATION, COAST)
                    or result[i - 2][1] not in (LOCATION, COAST)):
                continue
            for j in range(i + 1, len(result)):
                if result[j][1] not in (LOCATION, COAST):
                    break
            result[j:j] = result[i - 1:i]
            del result[i - 1]

        # Move order beyond first location
        i = 0
        for j in range(1, len(result)):
            if result[j][1] in (LOCATION, COAST):
                if i:
                    result[j + 1:j + 1] = result[i:i + 1]
                    del result[i]
                break
            elif result[j][1] == ORDER:
                i = j
            elif result[j][0] == '|':
                break

        # Put the power before the unit, or replace it with a location if there's ambiguity
        vet = 0
        for i, result_i in enumerate(result):
            if result_i[1] == POWER:
                if vet > 0 and result_i[0] in self.unclear:
                    result[i] = (self.unclear[result_i[0]], LOCATION)
                elif vet == 1:
                    result[i + 1:i + 1] = result[i - 1:i]
                    del result[i - 1]
                vet = 2
            elif not vet and result_i[1] == UNIT:
                vet = 1
            elif result_i[1] == ORDER:
                vet = 0
            else:
                vet = 2

        # Insert hyphens between subsequent locations
        for i in range(len(result) - 1, 1, -1):
            if result[i][1] in (LOCATION, COAST) and result[i - 1][1] in (LOCATION, COAST):
                result[i:i] = [('-', MOVE_SEP)]

        # Remove vertical bars at start and end
        return [x for x, y in result[1:-1]]

    def area_type(self, loc):
        """ Returns 'WATER', 'COAST', 'PORT', 'LAND', 'SHUT'

            :param loc: The name of the location to query
            :return: Type of the location ('WATER', 'COAST', 'PORT', 'LAND', 'SHUT')
        """
        return self.loc_type.get(loc.upper()) or self.loc_type.get(loc.lower())

    def default_coast(self, word):
        """ Returns the coast for a fleet move order that can only be to a single coast
            (e.g. F GRE-BUL returns F GRE-BUL/SC)

            :param word: A list of tokens (e.g. ['F', 'GRE', '-', 'BUL'])
            :return: The updated list of tokens (e.g. ['F', 'GRE', '-', 'BUL/SC'])
        """
        if len(word) == 4 and word[0] == 'F' and word[2] == '-' and '/' not in word[3]:
            unit_loc, new_loc, single_coast = word[1], word[3], None
            for place in self.abut_list(unit_loc):
                up_place = place.upper()
                if new_loc == up_place:                 # Target location found with no coast, original query is correct
                    return word
                if new_loc == up_place[:3]:
                    if single_coast:                    # Target location has multiple coasts, unable to decide
                        return word
                    single_coast = up_place             # Found a potential candidate, storing it
            word[3] = single_coast or new_loc           # Only one candidate found, modifying the order to include it
        return word

    def find_coasts(self, loc):
        """ Finds all coasts for a given location

            :param loc: The name of a location (e.g. 'BUL')
            :return: Returns the list of all coasts, including the location (e.g. ['BUL', 'BUL/EC', 'BUL/SC']
        """
        return self.loc_coasts.get(loc.upper(), [])

    def abuts(self, unit_type, unit_loc, order_type, other_loc):
        """ Determines if a order for unit_type from unit_loc to other_loc is adjacent.

            **Note**: This method uses the precomputed cache

            :param unit_type: The type of unit ('A' or 'F')
            :param unit_loc: The location of the unit ('BUR', 'BUL/EC')
            :param order_type: The type of order ('S' for Support, 'C' for Convoy', '-' for move)
            :param other_loc: The location of the other unit
            :return: 1 if the locations are adjacent for the move, 0 otherwise
        """
        if unit_type == '?':
            return (self.abuts_cache.get(('A', unit_loc.upper(), order_type, other_loc.upper()), 0) or
                    self.abuts_cache.get(('F', unit_loc.upper(), order_type, other_loc.upper()), 0))

        query_tuple = (unit_type, unit_loc.upper(), order_type, other_loc.upper())
        return self.abuts_cache.get(query_tuple, 0)

    def _abuts(self, unit_type, unit_loc, order_type, other_loc):
        """ Determines if a order for unit_type from unit_loc to other_loc is adjacent

            **Note**: This method is used to generate the abuts_cache

            :param unit_type: The type of unit ('A' or 'F')
            :param unit_loc: The location of the unit ('BUR', 'BUL/EC')
            :param order_type: The type of order ('S' for Support, 'C' for Convoy', '-' for move)
            :param other_loc: The location of the other unit
            :return: 1 if the locations are adjacent for the move, 0 otherwise
        """
        # pylint: disable=too-many-return-statements
        unit_loc, other_loc = unit_loc.upper(), other_loc.upper()

        # If the unit is not valid on the current location, returning 0
        if not self.is_valid_unit(unit_type + ' ' + unit_loc):
            return 0

        # Removing coasts for support
        # Otherwise, if army, not adjacent since army can't move, hold, or convoy on coasts
        if '/' in other_loc:
            if order_type == 'S':
                other_loc = other_loc[:3]
            elif unit_type == 'A':
                return 0

        # Looking for adjacency between unit_loc and other_loc
        # If the break line is not executed, not adjacency were found
        place = ''
        for place in self.abut_list(unit_loc):
            up_place = place.upper()
            up_loc = up_place[:3]
            if other_loc in (up_place, up_loc):
                break
        else:
            return 0

        # If the target location is impassible, returning 0
        other_loc_type = self.area_type(other_loc)
        if other_loc_type == 'SHUT':
            return 0

        # If the unit type is unknown, then assume the adjacency is okay
        if unit_type == '?':
            return 1

        # Fleets cannot affect LAND and fleets are not adjacent to any location listed in lowercase
        # (except when offering support into such an area, as in F BOT S A MOS-STP), or listed in
        # the adjacency list in lower-case (F VEN-TUS)

        # Fleet should be supporting a adjacent 'COAST', 'WATER' or 'PORT', with a name starting with a capital letter
        if unit_type == 'F':
            if (other_loc_type == 'LAND'
                    or place[0] != up_loc[0]
                    or order_type != 'S'
                    and other_loc not in self.loc_type):
                return 0

        # Armies cannot move to water (unless this is a convoy). Note that the caller
        # is responsible for determining if a fleet exists at the adjacent spot to convoy
        # the army. Also, armies can't move to spaces listed in Mixed case.
        elif order_type != 'C' and (other_loc_type == 'WATER' or place == place.title()):
            return 0

        # It's adjacent.
        return 1

    def is_valid_unit(self, unit, no_coast_ok=0, shut_ok=0):
        """ Determines if a unit and location combination is valid (e.g. 'A BUR') is valid

            :param unit: The name of the unit with its location (e.g. F SPA/SC)
            :param no_coast_ok: Indicates if a coastal location with no coast (e.g. SPA vs SPA/SC) is acceptable
            :param shut_ok: Indicates if a impassable country (e.g. Switzerland) is OK
            :return: A boolean to indicate if the unit/location combination is valid
        """
        unit_type, loc = unit.upper().split()
        area_type = self.area_type(loc)
        if area_type == 'SHUT':
            return 1 if shut_ok else 0
        if unit_type == '?':
            return 1 if area_type is not None else 0
        # Army can be anywhere, except in 'WATER'
        if unit_type == 'A':
            return '/' not in loc and area_type in ('LAND', 'COAST', 'PORT')
        # Fleet must be in WATER, COAST, or PORT
        # Coastal locations are stored in CAPS with coasts and non-caps with non-coasts
        # e.g. SPA/NC, SPA/SC, spa
        return (unit_type == 'F'
                and area_type in ('WATER', 'COAST', 'PORT')
                and (no_coast_ok or loc.lower() not in self.loc_abut))

    def abut_list(self, site, incl_no_coast=False):
        """ Returns the adjacency list for the site

            :param site: The province we want the adjacency list for
            :param incl_no_coast: Boolean flag that indicates to also include province without coast if it has coasts
                 e.g. will return ['BUL/SC', 'BUL/EC'] if False, and ['bul', 'BUL/SC', 'BUL/EC'] if True
            :return: A list of adjacent provinces

            Note: abuts are returned in **mixed cases**

                - An adjacency that is lowercase (e.g. 'bur') can only be used by an army
                - An adjacency that starts with a capital letter (e.g. 'Bal') can only be used by a fleet
                - An adjacency that is uppercase can be used by both an army and a fleet
        """
        if site in self.loc_abut:
            abut_list = self.loc_abut.get(site, [])
        else:
            abut_list = self.loc_abut.get(site.lower(), [])
        if incl_no_coast:
            abut_list = abut_list[:]
            for loc in list(abut_list):
                if '/' in loc and loc[:3] not in abut_list:
                    abut_list += [loc[:3]]
        return abut_list

    def find_next_phase(self, phase, phase_type=None, skip=0):
        """ Returns the long name of the phase coming immediately after the phase

            :param phase: The long name of the current phase (e.g. SPRING 1905 RETREATS)
            :param phase_type: The type of phase we are looking for
                (e.g. 'M' for Movement, 'R' for Retreats, 'A' for Adjust.)
            :param skip: The number of match to skip (e.g. 1 to find not the next phase, but the one after)
            :return: The long name of the next phase (e.g. FALL 1905 MOVEMENT)
        """
        # If len < 3, Phase is FORMING or COMPLETED, unable to find previous phase
        now = phase.split()
        if len(now) < 3:
            return phase

        # Parsing year and season index
        year = int(now[1])
        season_ix = (self.seq.index('%s %s' % (now[0], now[2])) + 1) % len(self.seq)
        seq_len = len(self.seq)

        # Parsing the sequence of seasons
        while seq_len:
            seq_len -= 1
            new = self.seq[season_ix].split()

            # Looking for IFYEARDIV DIV or IFYEARDIV DIV=MOD
            if new[0] == 'IFYEARDIV':
                if '=' in new[1]:
                    div, mod = map(int, new[1].split('='))
                else:
                    div, mod = int(new[1]), 0
                if year % div != mod:
                    season_ix = -1

            # NEWYEAR [X] indicates to increase years by [X] (or 1 by default)
            elif new[0] == 'NEWYEAR':
                year += len(new) == 1 or int(new[1])

            # Found phase
            elif phase_type in (None, new[1][0]):
                if skip == 0:
                    return '%s %s %s' % (new[0], year, new[1])
                skip -= 1
                seq_len = len(self.seq)
            season_ix += 1
            season_ix %= len(self.seq)

        # Could not find next phase
        return ''

    def find_previous_phase(self, phase, phase_type=None, skip=0):
        """ Returns the long name of the phase coming immediately prior the phase

            :param phase: The long name of the current phase (e.g. SPRING 1905 RETREATS)
            :param phase_type: The type of phase we are looking for
                (e.g. 'M' for Movement, 'R' for Retreats, 'A' for Adjust.)
            :param skip: The number of match to skip (e.g. 1 to find not the next phase, but the one after)
            :return: The long name of the previous phase (e.g. SPRING 1905 MOVEMENT)
        """
        # If len < 3, Phase is FORMING or COMPLETED, unable to find previous phase
        now = phase.split()
        if len(now) < 3:
            return phase

        # Parsing year and season index
        year = int(now[1])
        season_ix = self.seq.index('%s %s' % (now[0], now[2]))
        seq_len = len(self.seq)

        # Parsing the sequence of seasons
        while seq_len:
            seq_len -= 1
            season_ix -= 1

            # No more seasons in seq
            if season_ix == -1:
                for new in [x.split() for x in self.seq]:
                    # Looking for IFYEARDIV DIV or IFYEARDIV DIV=MOD
                    if new[0] == 'IFYEARDIV':
                        if '=' in new[1]:
                            div, mod = map(int, new[1].split('='))
                        else:
                            div, mod = int(new[1]), 0
                        if year % div != mod:
                            break
                    season_ix += 1

            # Parsing next seq
            new = self.seq[season_ix].split()
            if new[0] == 'IFYEARDIV':
                pass

            # NEWYEAR [X] indicates to increase years by [X] (or 1 by default)
            elif new[0] == 'NEWYEAR':
                year -= len(new) == 1 or int(new[1])

            # Found phase
            elif phase_type in (None, new[1][0]):
                if skip == 0:
                    return '%s %s %s' % (new[0], year, new[1])
                skip -= 1
                seq_len = len(self.seq)

        # Could not find prev phase
        return ''

    def compare_phases(self, phase1, phase2):
        """ Compare 2 phases (Strings) and return 1, -1, or 0 to indicate which phase is larger

            :param phase1:  The first phase (e.g. S1901M, FORMING, COMPLETED)
            :param phase2:  The second phase (e.g. S1901M, FORMING, COMPLETED)
            :return: 1 if phase1 > phase2, -1 if phase2 > phase1 otherwise 0 if they are equal
        """
        # If the phase ends with '?', we assume it's the last phase type of that season
        # e.g. S1901? -> S1901R  W1901? -> W1901A
        if phase1[-1] == '?':
            phase1 = phase1[:-1] + [season.split()[1][0] for season in self.seq if season[0] == phase1[0]][-1]
        if phase2[-1] == '?':
            phase2 = phase2[:-1] + [season.split()[1][0] for season in self.seq if season[0] == phase2[0]][-1]

        # Converting S1901M (abbrv) to long phase (SPRING 1901 MOVEMENT)
        if len(phase1.split()) == 1:
            phase1 = self.phase_long(phase1, phase1.upper())
        if len(phase2.split()) == 1:
            phase2 = self.phase_long(phase2, phase2.upper())
        if phase1 == phase2:
            return 0
        now1, now2 = phase1.split(), phase2.split()

        # One of the phase is either FORMING, or COMPLETED
        # Syntax is (bool1 and int1 or bool2 and int2) will return int1 if bool1, else int2 if bool2
        # 1 = FORMING, 2 = Normal Phase, 3 = COMPLETED, 0 = UNKNOWN
        if len(now1) < 3 or len(now2) < 3:
            order1 = (len(now1) > 2 and 2 or phase1 == 'FORMING' and 1 or phase1 == 'COMPLETED' and 3 or 0)
            order2 = (len(now2) > 2 and 2 or phase2 == 'FORMING' and 1 or phase2 == 'COMPLETED' and 3 or 0)
            return order1 > order2 and 1 or order1 < order2 and -1 or 0

        # Comparing years
        year1, year2 = int(now1[1]), int(now2[1])
        if year1 != year2:
            return (year1 > year2 and 1 or -1) * (self.flow_sign or 1)

        # Comparing seasons
        # Returning the inverse if NEW_YEAR is between the 2 seasons
        season_ix1 = self.seq.index('%s %s' % (now1[0], now1[2]))
        season_ix2 = self.seq.index('%s %s' % (now2[0], now2[2]))
        if season_ix1 > season_ix2:
            return -1 if 'NEWYEAR' in [x.split()[0] for x in self.seq[(season_ix2) + (1):season_ix1]] else 1
        if season_ix1 < season_ix2:
            return 1 if 'NEWYEAR' in [x.split()[0] for x in self.seq[(season_ix1) + (1):season_ix2]] else -1
        return 0

    @staticmethod
    def phase_abbr(phase, default='?????'):
        """ Constructs a 5 character representation (S1901M) from a phase (SPRING 1901 MOVEMENT)

            :param phase: The full phase (e.g. SPRING 1901 MOVEMENT)
            :param default: The default value to return in case conversion fails
            :return: A 5 character representation of the phase
        """
        if phase in ('FORMING', 'COMPLETED'):
            return phase
        parts = tuple(phase.split())
        return ('%.1s%04d%.1s' % (parts[0], int(parts[1]), parts[2])).upper() if len(parts) == 3 else default

    def phase_long(self, phase_abbr, default='?????'):
        """ Constructs a full sentence of a phase from a 5 character abbreviation

            :param phase_abbr: 5 character abbrev. (e.g. S1901M)
            :param default: The default value to return in case conversion fails
            :return: A full phase description (e.g. SPRING 1901 MOVEMENT)
        """
        try:
            year = int(phase_abbr[1:-1])
            for season in self.seq:
                parts = season.split()
                if parts[0] not in ('NEWYEAR', 'IFYEARDIV') \
                        and parts[0][0].upper() == phase_abbr[0].upper() \
                        and parts[1][0].upper() == phase_abbr[-1].upper():
                    return '{} {} {}'.format(parts[0], year, parts[1]).upper()
        except ValueError:
            pass
        return default

# Loading at the bottom, to avoid load recursion
from diplomacy.utils.convoy_paths import add_to_cache, get_convoy_paths_cache   # pylint: disable=wrong-import-position
CONVOYS_PATH_CACHE = get_convoy_paths_cache()
