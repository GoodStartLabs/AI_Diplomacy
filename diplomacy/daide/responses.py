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
""" DAIDE Responses - Contains a list of responses sent by the server to the client """
from diplomacy import Map
from diplomacy.communication.responses import _AbstractResponse
from diplomacy.daide.clauses import String, Power, Province, Turn, Unit, add_parentheses, strip_parentheses, \
    parse_string
from diplomacy.daide import tokens
from diplomacy.daide.tokens import Token
from diplomacy.daide.utils import bytes_to_str
from diplomacy.utils.splitter import OrderSplitter

class DaideResponse(_AbstractResponse):
    """ Represents a DAIDE response. """
    def __init__(self, **kwargs):
        """ Constructor """
        self._bytes = b''
        super(DaideResponse, self).__init__(**kwargs)

    def __bytes__(self):
        """ Returning the bytes representation of the response """
        return self._bytes

    def __str__(self):
        """ Returning the string representation of the response """
        return bytes_to_str(self._bytes)

class MapNameResponse(DaideResponse):
    """ Represents a MAP DAIDE response. Sends the name of the current map to the client.

        Syntax: ::

            MAP ('name')
    """
    def __init__(self, map_name, **kwargs):
        """ Builds the response
            :param map_name: String. The name of the current map.
        """
        super(MapNameResponse, self).__init__(**kwargs)
        self._bytes = bytes(tokens.MAP) \
                      + bytes(parse_string(String, map_name))

class MapDefinitionResponse(DaideResponse):
    """ Represents a MDF DAIDE response. Sends configuration of a map to a client

        Syntax: ::

            MDF (powers) (provinces) (adjacencies)

        powers syntax: ::

            power power ...

        power syntax: ::

            AUS                     # Austria
            ENG                     # England
            FRA                     # France
            GER                     # Germany
            ITA                     # Italy
            RUS                     # Russia
            TUR                     # Turkey

        provinces syntax: ::

            (supply_centres) (non_supply_centres)

        supply_centres syntax: ::

            (power centre centre ...) (power centre centre ...) ...

        supply_centres power syntax: ::

            (power power ...)       # This is currently not supported
            AUS                     # Austria
            ENG                     # England
            FRA                     # France
            GER                     # Germany
            ITA                     # Italy
            RUS                     # Russia
            TUR                     # Turkey
            UNO                     # Unknown power

        non_supply_centres syntax: ::

            province province ...   # List of provinces

        adjacencies syntax: ::

            (prov_adjacencies) (prov_adjacencies) ...

        prov_adjacencies syntax: ::

            province (unit_type adjacent_prov adjacent_prov ...) (unit_type adjacent_prov adjacent_prov ...) ...

        unit_type syntax: ::

            AMY                     # List of provinces an army can move to
            FLT                     # List of provinces a fleet can move to
            (FLT coast)             # List of provinces a fleet can move to from the given coast

        adjacent_prov syntax: ::

            province                # A province which can be moved to
            (province coast)        # A coast of a province that can be moved to
    """
    def __init__(self, map_name, **kwargs):
        """ Builds the response

            :param map_name: The name of the map
        """
        super(MapDefinitionResponse, self).__init__(**kwargs)
        game_map = Map(map_name)

        # (Powers): (power power ...)
        # (Provinces): ((supply_centers) (non_supply_centres))
        # (Adjacencies): ((prov_adjacencies) (prov_adjacencies) ...)
        powers_clause = self._build_powers_clause(game_map)
        provinces_clause = self._build_provinces_clause(game_map)
        adjacencies_clause = self._build_adjacencies_clause(game_map)

        self._bytes = bytes(tokens.MDF) \
                      + powers_clause \
                      + provinces_clause \
                      + adjacencies_clause

    @staticmethod
    def _build_powers_clause(game_map):
        """ Build the powers clause

            Syntax: ::

                (powers)

            powers syntax: ::

                power power ...

            power syntax: ::

                AUS                     # Austria
                ENG                     # England
                FRA                     # France
                GER                     # Germany
                ITA                     # Italy
                RUS                     # Russia
                TUR                     # Turkey
        """
        power_names = game_map.powers[:]
        power_names.sort()

        # (Powers): (power power ...)
        powers_clause = [bytes(parse_string(Power, power_name)) for power_name in power_names]
        powers_clause = add_parentheses(b''.join(powers_clause))
        return powers_clause

    @staticmethod
    def _build_provinces_clause(game_map):
        """ Build the provinces clause

            Syntax: ::

                (provinces)

            provinces syntax: ::

                (supply_centres) (non_supply_centres)

            supply_centres syntax: ::

                (power centre centre ...) (power centre centre ...) ...

            supply_centres power syntax: ::

                (power power ...)       # This is currently not supported
                AUS                     # Austria
                ENG                     # England
                FRA                     # France
                GER                     # Germany
                ITA                     # Italy
                RUS                     # Russia
                TUR                     # Turkey
                UNO                     # Unknown power

            non_supply_centres syntax: ::

                province province ...   # List of provinces
        """
        unowned_scs = game_map.scs[:]
        unowned_scs.sort()

        # (Supply centers): ((power centre centre ...) (power centre centre ...) ...)
        # (Non supply centres): (province province ...)
        scs_clause = []
        non_scs_clause = []

        power_names_centers = [(power_name, centers[:]) for power_name, centers in game_map.centers.items()]
        power_names_centers.sort(key=lambda power_name_center: power_name_center[0])

        # Parsing each power centers
        for power_name, centers in power_names_centers:
            centers.sort()

            power_scs_clause = [bytes(parse_string(Power, power_name))]
            for center in centers:
                power_scs_clause.append(bytes(parse_string(Province, center)))
                unowned_scs.remove(center)

            # (Power supply centers): (power centre centre ...)
            power_scs_clause = add_parentheses(b''.join(power_scs_clause))
            scs_clause.append(power_scs_clause)

        # (Power supply centers): (power centre centre ...)
        power_scs_clause = [bytes(tokens.UNO)]
        power_scs_clause += [bytes(parse_string(Province, center)) for center in unowned_scs]
        power_scs_clause = add_parentheses(b''.join(power_scs_clause))

        # (Supply centers): ((power centre centre ...) (power centre centre ...) ...)
        scs_clause.append(power_scs_clause)
        scs_clause = add_parentheses(b''.join(scs_clause))

        provinces = game_map.locs[:]
        provinces.sort()
        for province in provinces:
            if game_map.area_type(province) == 'SHUT':
                continue

            province = province[:3].upper()
            province_clause = bytes(parse_string(Province, province))
            if province_clause not in non_scs_clause and province not in game_map.scs:
                non_scs_clause.append(province_clause)

        # (Non supply centres): (province province ...)
        non_scs_clause = add_parentheses(b''.join(non_scs_clause))

        # (Provinces): ((supply_centers) (non_supply_centres))
        provinces_clause = [scs_clause, non_scs_clause]
        provinces_clause = add_parentheses(b''.join(provinces_clause))

        return provinces_clause

    @staticmethod
    def _build_adjacencies_clause(game_map):
        """ Build the adjacencies clause

            Syntax: ::

                (adjacencies)

            adjacencies syntax: ::

                (prov_adjacencies) (prov_adjacencies) ...

            prov_adjacencies syntax: ::

                province (unit_type adjacent_prov adjacent_prov ...) (unit_type adjacent_prov adjacent_prov ...) ...

            unit_type syntax: ::

                AMY                     # List of provinces an army can move to
                FLT                     # List of provinces a fleet can move to
                (FLT coast)             # List of provinces a fleet can move to from the given coast

            adjacent_prov syntax: ::

                province                # A province which can be moved to
                (province coast)        # A coast of a province that can be moved to
        """
        adjacencies = {}                # {province: {'A': [], 'F': [], '/': []}        army abuts, fleet abuts, / abuts

        # For each province
        for province in sorted([loc.upper() for loc in game_map.locs if '/' not in loc]):
            province_type = game_map.area_type(province)

            if province_type == 'SHUT':
                continue

            # Creating empty list of adjacent provinces
            adjacencies.setdefault(province, {})
            adjacencies[province].setdefault('A', [])               # List of adjacent provinces where armies can move
            for province_w_coast in sorted(game_map.find_coasts(province)):
                coast = province_w_coast[3:]
                adjacencies[province].setdefault(coast, [])         # List of adjacent provinces where fleets can move

            # Building list of adjacent provinces
            for coast in adjacencies[province]:                     # 'A', '', '/NC', '/SC', '/EC', '/WC'

                # Army adjacencies
                if coast == 'A':
                    for dest in sorted(game_map.dest_with_coasts[province]):
                        if game_map.abuts('A', province, '-', dest):
                            adjacencies[province]['A'].append(bytes(parse_string(Province, dest)))

                # Fleet adjacencies
                else:
                    for dest in sorted(game_map.dest_with_coasts[province + coast]):
                        if game_map.abuts('F', province + coast, '-', dest):
                            adjacencies[province][coast].append(bytes(parse_string(Province, dest)))

            # If province has coasts ('/NC', '/SC'), removing the adjacency for fleets without coast
            if len(adjacencies[province]) > 2:
                del adjacencies[province]['']

        # Building adjacencies clause
        adjacencies_clause = []
        for province in sorted(adjacencies):
            prov_adjacencies_clause = [bytes(parse_string(Province, province))]

            for coast in ('A', '', '/EC', '/NC', '/SC', '/WC'):
                if coast not in adjacencies[province]:
                    continue
                if not adjacencies[province][coast]:
                    continue

                # (Army adjacencies): (AMY adjacent_prov adjacent_prov ...)
                if coast == 'A':
                    amy_adjacencies_clause = [bytes(tokens.AMY)] + adjacencies[province][coast]
                    amy_adjacencies_clause = add_parentheses(b''.join(amy_adjacencies_clause))
                    prov_adjacencies_clause.append(amy_adjacencies_clause)

                # (Fleet provinces): (FLT adjacent_prov adjacent_prov ...)
                elif coast == '':
                    flt_adjacencies_clause = [bytes(tokens.FLT)] + adjacencies[province][coast]
                    flt_adjacencies_clause = add_parentheses(b''.join(flt_adjacencies_clause))
                    prov_adjacencies_clause.append(flt_adjacencies_clause)

                # (Fleet coast): (FLT coast)
                # (Fleet coast provinces): ((FLT coast) adjacent_prov adjacent_prov ...)
                else:
                    flt_clause = bytes(tokens.FLT)
                    coast_clause = bytes(parse_string(Province, coast))
                    coast_flt_adjacencies_clause = [add_parentheses(flt_clause + coast_clause)] \
                                                   + adjacencies[province][coast]
                    coast_flt_adjacencies_clause = add_parentheses(b''.join(coast_flt_adjacencies_clause))
                    prov_adjacencies_clause.append(coast_flt_adjacencies_clause)

            # (Province adjacencies): (province (unit_type adjacent_prov adjacent_prov ...)
            #                          (unit_type adjacent_prov adjacent_prov ...) ...)
            prov_adjacencies_clause = add_parentheses(b''.join(prov_adjacencies_clause))
            adjacencies_clause.append(prov_adjacencies_clause)

        # (Adjacencies): ((prov_adjacencies) (prov_adjacencies) ...)
        adjacencies_clause = add_parentheses(b''.join(adjacencies_clause))
        return adjacencies_clause

class HelloResponse(DaideResponse):
    """ Represents a HLO DAIDE response. Sends the power to be played by the client with the passcode to rejoin the
        game and the details of the game.

        Syntax: ::

            HLO (power) (passcode) (variant) (variant) ...

        Variant syntax: ::

            LVL n           # Level of the syntax accepted
            MTL seconds     # Movement time limit
            RTL seconds     # Retreat time limit
            BTL seconds     # Build time limit
            DSD             # Disables the time limit when a client disconects
            AOA             # Any orders accepted

        LVL 10:

        Variant syntax: ::

            PDA             # Accept partial draws
            NPR             # No press during retreat phases
            NPB             # No press during build phases
            PTL seconds     # Press time limit
    """
    def __init__(self, power_name, passcode, level, deadline, rules, **kwargs):
        """ Builds the response

            :param power_name: The name of the power being played.
            :param passcode: Integer. A passcode to rejoin the game.
            :param level: Integer. The daide syntax level of the game
            :param deadline: Integer. The number of seconds per turn (0 to disable)
            :param rules: The list of game rules.
        """
        super(HelloResponse, self).__init__(**kwargs)
        power = parse_string(Power, power_name)
        passcode = Token(from_int=passcode)

        if 'NO_PRESS' in rules:
            level = 0
        variants = add_parentheses(bytes(tokens.LVL) + bytes(Token(from_int=level)))

        if deadline > 0:
            variants += add_parentheses(bytes(tokens.MTL) + bytes(Token(from_int=deadline)))
            variants += add_parentheses(bytes(tokens.RTL) + bytes(Token(from_int=deadline)))
            variants += add_parentheses(bytes(tokens.BTL) + bytes(Token(from_int=deadline)))

        if 'NO_CHECK' in rules:
            variants += add_parentheses(bytes(tokens.AOA))

        self._bytes = bytes(tokens.HLO) \
                      + add_parentheses(bytes(power)) \
                      + add_parentheses(bytes(passcode)) \
                      + add_parentheses(bytes(variants))

class SupplyCenterResponse(DaideResponse):
    """ Represents a SCO DAIDE response. Sends the current supply centre ownership.

        Syntax: ::

            SCO (power centre centre ...) (power centre centre ...) ...
    """
    def __init__(self, powers_centers, map_name, **kwargs):
        """ Builds the response

            :param powers_centers: A dict of {power_name: centers} objects
            :param map_name: The name of the map
        """
        super(SupplyCenterResponse, self).__init__(**kwargs)
        remaining_scs = Map(map_name).scs[:]
        all_powers_bytes = []

        # Parsing each power
        for power_name in sorted(powers_centers):
            centers = sorted(powers_centers[power_name])
            power_clause = parse_string(Power, power_name)
            power_bytes = bytes(power_clause)

            for center in centers:
                sc_clause = parse_string(Province, center)
                power_bytes += bytes(sc_clause)
                remaining_scs.remove(center)

            all_powers_bytes += [power_bytes]

        # Parsing unowned center
        uno_token = tokens.UNO
        power_bytes = bytes(uno_token)

        for center in remaining_scs:
            sc_clause = parse_string(Province, center)
            power_bytes += bytes(sc_clause)

        all_powers_bytes += [power_bytes]

        # Storing full response
        self._bytes = bytes(tokens.SCO) \
                      + b''.join([add_parentheses(power_bytes) for power_bytes in all_powers_bytes])

class CurrentPositionResponse(DaideResponse):
    """ Represents a NOW DAIDE response. Sends the current turn, and the current unit positions.

        Syntax: ::

            NOW (turn) (unit) (unit) ...

        Unit syntax: ::

            power unit_type province
            power unit_type province MRT (province province ...)
    """

    def __init__(self, phase_name, powers_units, powers_retreats, **kwargs):
        """ Builds the response

            :param phase_name: The name of the current phase (e.g. 'S1901M')
            :param powers: A list of `diplomacy.engine.power.Power` objects
        """
        super(CurrentPositionResponse, self).__init__(**kwargs)
        units_bytes_buffer = []

        # Turn
        turn_clause = parse_string(Turn, phase_name)

        # Units
        for power_name, units in sorted(powers_units.items()):
            # Regular units
            for unit in units:
                unit_clause = parse_string(Unit, '%s %s' % (power_name, unit))
                units_bytes_buffer += [bytes(unit_clause)]

            # Dislodged units
            for unit, retreat_provinces in sorted(powers_retreats[power_name].items()):
                unit_clause = parse_string(Unit, '%s %s' % (power_name, unit))
                retreat_clauses = [parse_string(Province, province) for province in retreat_provinces]
                units_bytes_buffer += [add_parentheses(strip_parentheses(bytes(unit_clause))
                                                       + bytes(tokens.MRT)
                                                       + add_parentheses(b''.join([bytes(province)
                                                                                   for province in retreat_clauses])))]

        # Storing full response
        self._bytes = bytes(tokens.NOW) + bytes(turn_clause) + b''.join(units_bytes_buffer)

class ThanksResponse(DaideResponse):
    """ Represents a THX DAIDE response. Sends the result of an order after submission.

        Syntax: ::

            THX (order) (note)

        Note syntax: ::

            MBV     # Order is OK.
            FAR     # Not adjacent.
            NSP     # No such province
            NSU     # No such unit
            NAS     # Not at sea (for a convoying fleet)
            NSF     # No such fleet (in VIA section of CTO or the unit performing a CVY)
            NSA     # No such army (for unit being ordered to CTO or for unit being CVYed)
            NYU     # Not your unit
            NRN     # No retreat needed for this unit
            NVR     # Not a valid retreat space
            YSC     # Not your supply centre
            ESC     # Not an empty supply centre
            HSC     # Not a home supply centre
            NSC     # Not a supply centre
            CST     # No coast specified for fleet build in StP, or an attempt
                      to build a fleet inland, or an army at sea.
            NMB     # No more builds allowed
            NMR     # No more removals allowed
            NRS     # Not the right season
    """
    def __init__(self, order_bytes, results, **kwargs):
        """ Builds the response

            :param order_bytes: The bytes received for the order
            :param results: An array containing the error codes.
        """
        super(ThanksResponse, self).__init__(**kwargs)
        if not results or 0 in results:                 # Order success response
            note_clause = tokens.MBV
        else:                                           # Generic order failure response
            note_clause = tokens.NYU

        # Storing full response
        self._bytes = bytes(tokens.THX) + order_bytes + add_parentheses(bytes(note_clause))

class MissingOrdersResponse(DaideResponse):
    """ Represents a MIS DAIDE response. Sends the list of unit for which an order is missing or indication about
        required disbands or builds.

        Syntax: ::

            MIS (unit) (unit) ...
            MIS (unit MRT (province province ...)) (unit MRT (province province ...)) ...
            MIS (number)
    """
    def __init__(self, phase_name, power, **kwargs):
        """ Builds the response

            :param phase_name: The name of the current phase (e.g. 'S1901M')
            :param power: The power to check for missing orders
            :type power: diplomacy.engine.power.Power
        """
        super(MissingOrdersResponse, self).__init__(**kwargs)
        assert phase_name[-1] in 'MRA', 'Invalid phase "%s"' & phase_name
        {'M': self._build_movement_phase,
         'R': self._build_retreat_phase,
         'A': self._build_adjustment_phase}[phase_name[-1]](power)

    def _build_movement_phase(self, power):
        """ Builds the missing orders response for a movement phase """
        units_with_no_order = [unit for unit in power.units]

        # Removing units for which we have orders
        for key, value in power.orders.items():
            unit = key                              # Regular game {e.g. 'A PAR': '- BUR')
            if key[0] in 'RIO':                     # No-check game (key is INVALID, ORDER x, REORDER x)
                unit = ' '.join(value.split()[:2])
            if unit in units_with_no_order:
                units_with_no_order.remove(unit)

        # Storing full response
        self._bytes = bytes(tokens.MIS) + \
                      b''.join([bytes(parse_string(Unit, '%s %s' % (power.name, unit)))
                                for unit in units_with_no_order])

    def _build_retreat_phase(self, power):
        """ Builds the missing orders response for a retreat phase """
        units_bytes_buffer = []

        units_with_no_order = {unit: retreat_provinces for unit, retreat_provinces in power.retreats.items()}

        # Removing units for which we have orders
        for key, value in power.orders.items():
            unit = key                              # Regular game {e.g. 'A PAR': '- BUR')
            if key[0] in 'RIO':                     # No-check game (key is INVALID, ORDER x, REORDER x)
                unit = ' '.join(value.split()[:2])
            if unit in units_with_no_order:
                del units_with_no_order[unit]

        # Sorting by the unit's province ASC so results are deterministic
        for unit, retreat_provinces in sorted(units_with_no_order.items(),
                                              key=lambda key_val: key_val[0].split()[-1]):
            unit_clause = parse_string(Unit, '%s %s' % (power.name, unit))
            retreat_clauses = [parse_string(Province, province) for province in retreat_provinces]
            units_bytes_buffer += [add_parentheses(strip_parentheses(bytes(unit_clause))
                                                   + bytes(tokens.MRT)
                                                   + add_parentheses(b''.join([bytes(province)
                                                                               for province in retreat_clauses])))]

        self._bytes = bytes(tokens.MIS) + b''.join(units_bytes_buffer)

    def _build_adjustment_phase(self, power):
        """ Builds the missing orders response for a build phase """
        adjusts = [OrderSplitter(adjust) for adjust in power.adjust]
        build_cnt = sum(1 for adjust in adjusts if adjust.order_type == 'B')
        disband_cnt = sum(1 for adjust in adjusts if adjust.order_type == 'D')
        disbands_status = (len(power.units) + build_cnt) - (len(power.centers) + disband_cnt)

        if disbands_status < 0:
            available_homes = power.homes[:]

            # Removing centers for which it's impossible to build
            for unit in [unit.split() for unit in power.units]:
                province = unit[1]
                if province in available_homes:
                    available_homes.remove(province)

            disbands_status = max(-len(available_homes), disbands_status)

        self._bytes += bytes(tokens.MIS) + add_parentheses(bytes(Token(from_int=disbands_status)))

class OrderResultResponse(DaideResponse):
    """ Represents a ORD DAIDE response. Sends the result of an order after the turn has been processed.

        Syntax: ::

            ORD (turn) (order) (result)
            ORD (turn) (order) (result RET)

        Result syntax: ::

            SUC         # Order succeeded (can apply to any order).
            BNC         # Move bounced (only for MTO, CTO or RTO orders).
            CUT         # Support cut (only for SUP orders).
            DSR         # Move via convoy failed due to dislodged convoying fleet (only for CTO orders).
            NSO         # No such order (only for SUP, CVY or CTO orders).
            RET         # Unit was dislodged and must retreat.
    """
    def __init__(self, phase_name, order_bytes, results, **kwargs):
        """ Builds the response

            :param phase_name: The name of the current phase (e.g. 'S1901M')
            :param order_bytes: The bytes received for the order
            :param results: An array containing the error codes.
        """
        super(OrderResultResponse, self).__init__(**kwargs)
        turn_clause = parse_string(Turn, phase_name)
        if not results or 0 in results:                 # Order success response
            result_clause = tokens.SUC
        else:                                           # Generic order failure response
            result_clause = tokens.NSO

        self._bytes = bytes(tokens.ORD) + bytes(turn_clause) + add_parentheses(order_bytes) + \
                      add_parentheses(bytes(result_clause))

class TimeToDeadlineResponse(DaideResponse):
    """ Represents a TME DAIDE response. Sends the time to the next deadline.

        Syntax: ::

            TME (seconds)
    """
    def __init__(self, seconds, **kwargs):
        """ Builds the response

            :param seconds: Integer. The number of seconds before deadline
        """
        super(TimeToDeadlineResponse, self).__init__(**kwargs)
        self._bytes = bytes(tokens.TME) + add_parentheses(bytes(Token(from_int=seconds)))

class AcceptResponse(DaideResponse):
    """ Represents a YES DAIDE request.

        Syntax: ::

            YES (TME (seconds))                                 # Accepts to set the time when a
                                                                  TME message will be sent
            YES (NOT (TME))                                     # Accepts to cancel all requested time messages
            YES (NOT (TME (seconds)))                           # Accepts to cancel a specific requested time message
            YES (GOF)                                           # Accepts to wait until the deadline before processing
                                                                  the orders for the turn
            YES (NOT (GOF))                                     # Accepts to cancel to wait until the deadline before
                                                                  processing the orders for the turn
            YES (DRW)                                           # Accepts to draw
            YES (NOT (DRW))                                     # Accepts to cancel a draw request

        LVL 10: ::

            YES (DRW (power power ...))                         # Accepts a partial draw
            YES (NOT (DRW (power power ...)))                   # Accepts to cancel a partial draw request
                                                                  (? not mentinned in the DAIDE doc)
            YES (SND (power power ...) (press_message))         # Accepts a press message
            YES (SND (turn) (power power ...) (press_message))  # Accepts a press message
    """
    def __init__(self, request_bytes, **kwargs):
        """ Builds the response

            :param request_bytes: The bytes received for the request
        """
        super(AcceptResponse, self).__init__(**kwargs)
        self._bytes = bytes(tokens.YES) + add_parentheses(request_bytes)

class RejectResponse(DaideResponse):
    """ Represents a REJ DAIDE request.

        Syntax: ::

            REJ (NME ('name') ('version'))                      # Rejects a client in the game
            REJ (IAM (power) (passcode))                        # Rejects a client to rejoin the game
            REJ (HLO)                                           # Rejects to send the HLO message
            REJ (HST (turn))                                    # Rejects to send a copy of a previous
                                                                  ORD, SCO and NOW messages
            REJ (SUB (order) (order))                           # Rejects a submition of orders
            REJ (SUB (turn) (order) (order))                    # Rejects a submition of orders
            REJ (NOT (SUB (order)))                             # Rejects a cancellation of a submitted order
            REJ (MIS)                                           # Rejects to send a copy of the current MIS message
            REJ (GOF)                                           # Rejects to wait until the deadline before processing
                                                                  the orders for the turn
            REJ (NOT (GOF))                                     # Rejects to cancel to wait until the deadline before
                                                                  processing the orders for the turn
            REJ (TME (seconds))                                 # Rejects to set the time when a
                                                                  TME message will be sent
            REJ (NOT (TME))                                     # Rejects to cancel all requested time messages
            REJ (NOT (TME (seconds)))                           # Rejects to cancel a specific requested time message
            REJ (ADM ('name') ('message')                       # Rejects the admin message
            REJ (DRW)                                           # Rejects to draw
            REJ (NOT (DRW))                                     # Rejects to cancel a draw request

        LVL 10: ::

            REJ (DRW (power power ...))                         # Rejects to partially draw
            REJ (NOT (DRW (power power ...)))                   # Rejects to cancel a partial draw request
            REJ (SND (power power ...) (press_message))         # Rejects a press message
            REJ (SND (turn) (power power ...) (press_message))  # Rejects a press message
    """
    def __init__(self, request_bytes, **kwargs):
        """ Builds the response

            :param request_bytes: The bytes received for the request
        """
        super(RejectResponse, self).__init__(**kwargs)
        self._bytes = bytes(tokens.REJ) + add_parentheses(request_bytes)

class NotResponse(DaideResponse):
    """ Represents a NOT DAIDE response.

        Syntax: ::

            NOT (CCD (power))
    """
    def __init__(self, response_bytes, **kwargs):
        """ Builds the response
            :param response_bytes: The bytes received for the request
        """
        super(NotResponse, self).__init__(**kwargs)
        self._bytes = bytes(tokens.NOT) + add_parentheses(response_bytes)

class PowerInCivilDisorderResponse(DaideResponse):
    """ Represents a CCD DAIDE response. Sends the name of the power in civil disorder.

        Syntax: ::

            CCD (power)
    """
    def __init__(self, power_name, **kwargs):
        """ Builds the response

            :param power_name: The name of the power being played.
        """
        super(PowerInCivilDisorderResponse, self).__init__(**kwargs)
        power = parse_string(Power, power_name)
        self._bytes = bytes(tokens.CCD) + add_parentheses(bytes(power))

class PowerIsEliminatedResponse(DaideResponse):
    """ Represents a OUT DAIDE response. Sends the name of the power eliminated.

        Syntax: ::

            OUT (power)
    """
    def __init__(self, power_name, **kwargs):
        """ Builds the response

            :param power_name: The name of the power being played.
        """
        super(PowerIsEliminatedResponse, self).__init__(**kwargs)
        power = parse_string(Power, power_name)
        self._bytes = bytes(tokens.OUT) + add_parentheses(bytes(power))

class ParenthesisErrorResponse(DaideResponse):
    """ Represents a PRN DAIDE response.

        Syntax: ::

            PRN (message)
    """
    def __init__(self, request_bytes, **kwargs):
        """ Builds the response

            :param request_bytes: The bytes received for the request
        """
        super(ParenthesisErrorResponse, self).__init__(**kwargs)
        self._bytes = bytes(tokens.PRN) + add_parentheses(request_bytes)

class SyntaxErrorResponse(DaideResponse):
    """ Represents a HUH DAIDE response.

        Syntax: ::

            HUH (message)
    """
    def __init__(self, request_bytes, error_index, **kwargs):
        """ Builds the response

            :param request_bytes: The bytes received for the request
            :param error_index: The index of the faulty token
        """
        super(SyntaxErrorResponse, self).__init__(**kwargs)
        message_with_err = request_bytes[:error_index] + bytes(tokens.ERR) + request_bytes[error_index:]
        self._bytes = bytes(tokens.HUH) + add_parentheses(message_with_err)

class TurnOffResponse(DaideResponse):
    """ Represents an OFF DAIDE response. Requests a client to exit

        Syntax: ::

            OFF
    """
    def __init__(self, **kwargs):
        """ Builds the response """
        super(TurnOffResponse, self).__init__(**kwargs)
        self._bytes = bytes(tokens.OFF)

MAP = MapNameResponse
MDF = MapDefinitionResponse
HLO = HelloResponse
SCO = SupplyCenterResponse
NOW = CurrentPositionResponse
THX = ThanksResponse
MIS = MissingOrdersResponse
ORD = OrderResultResponse
TME = TimeToDeadlineResponse
YES = AcceptResponse
REJ = RejectResponse
NOT = NotResponse
CCD = PowerInCivilDisorderResponse
OUT = PowerIsEliminatedResponse
OFF = TurnOffResponse
PRN = ParenthesisErrorResponse
HUH = SyntaxErrorResponse
