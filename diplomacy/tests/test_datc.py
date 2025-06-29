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
""" DATC Test Cases
    - Contains the diplomacy adjudication test cases
"""
# pylint: disable=too-many-lines
from diplomacy.engine.game import Game
from diplomacy.utils.order_results import OK, NO_CONVOY, BOUNCE, VOID, CUT, DISLODGED, DISRUPTED, DISBAND

# -----------------
# DATC TEST CASES
# -----------------
class TestDATC:
    """ DATC test cases"""
    # pylint: disable=too-many-public-methods

    @staticmethod
    def create_game():
        """ Creates a game object"""
        return Game()

    @staticmethod
    def clear_units(game):
        """ Clears units """
        game.clear_units()

    @staticmethod
    def clear_centers(game):
        """ Clears supply centers """
        game.clear_centers()

    @staticmethod
    def set_units(game, power_name, units):
        """ Sets units on the map """
        game.set_units(power_name, units)

    @staticmethod
    def set_centers(game, power_name, centers):
        """ Transfers SC ownership to power """
        game.set_centers(power_name, centers)

    @staticmethod
    def set_orders(game, power_name, orders):
        """ Submit orders """
        game.set_orders(power_name, orders)

    @staticmethod
    def process(game):
        """ Processes the game """
        # Calculating hash before
        hash_before_1 = game.get_hash()
        hash_before_2 = game.rebuild_hash()

        # Processing
        game.process()

        # Calculating hash after
        hash_after_1 = game.get_hash()
        hash_after_2 = game.rebuild_hash()

        # Checking
        assert hash_before_1 == hash_before_2
        assert hash_after_1 == hash_after_2

    @staticmethod
    def owner_name(game, unit):
        """ Retrieves owner name """
        has_coast = '/' in unit
        owner = game._unit_owner(unit, coast_required=has_coast)    # pylint: disable=protected-access
        if owner is not None:
            return owner.name
        return None

    @staticmethod
    def check_results(game, unit, value, phase='M'):
        """ Checks adjudication results """
        # pylint: disable=too-many-return-statements
        if not game:
            return False

        result = game.result_history.last_value()

        # Checking if the results contain duplicate values
        unit_result = result.get(unit, [])
        if len(unit_result) != len(set(unit_result)):
            raise RuntimeError('Duplicate values detected in %s' % unit_result)

        # Done self.processing a retreats phase
        if phase == 'R':
            if value == VOID and VOID in unit_result:
                return True
            if value == OK:
                success = unit not in game.popped and unit_result == []
                if not success:
                    print('Results: %s - Expected: []' % result.get(unit, '<Not Found>'))
                return success

            success = unit in game.popped and value in unit_result
            if not success:
                print('Results: %s - Expected: %s' % (result.get(unit, '<Not Found>'), value))
            return success

        # Done self.processing a retreats phase
        if phase == 'A':
            if value == VOID and VOID in unit_result:
                return True
            success = value == unit_result
            if not success:
                print('Results: %s - Expected: %s' % (result.get(unit, '<Not Found>'), value))
            return success

        order_status = game.get_order_status(unit=unit)

        # Finding all ordered units
        ordered_units = []
        for power_name in game.ordered_units:
            ordered_units += game.ordered_units[power_name]

        # Invalid order
        if value == VOID:
            if VOID in result.get(unit, []):
                return True
            if unit not in ordered_units:
                return True
            return False

        # Invalid unit
        if unit not in game.command:
            print('Results: %s NOT FOUND - Expected: %s' % (unit, value))
            return False

        # Expected no errors
        if value == OK:
            if order_status:
                print('Results: %s - Expected: []' % order_status)
                return False
            return True

        # Incorrect error
        if value not in game.get_order_status(unit=unit):
            print('Results: %s - Expected: %s' % (order_status, value))
            return False

        # Correct value
        return True

    @staticmethod
    def move_to_phase(game, new_phase):
        """ Move to a specific phase"""
        if not game:
            raise RuntimeError()
        game.set_current_phase(new_phase)

    # ------------- Tests --------------------
    def test_6_a_1(self):
        """ 6.A.1 TEST CASE, MOVING TO AN AREA THAT IS NOT A NEIGHBOUR
            Check if an illegal move (without convoy) will fail.
            England: F North Sea - Picardy
            Order should fail.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', 'F NTH')
        self.set_orders(game, 'ENGLAND', 'F NTH - PIC')
        self.process(game)
        assert self.check_results(game, 'F NTH', VOID)
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'F PIC') is None

    def test_6_a_2(self):
        """ 6.A.2. TEST CASE, MOVE ARMY TO SEA
            Check if an army could not be moved to open sea.
            England: A Liverpool - Irish Sea
            Order should fail.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', 'A LVP')
        self.set_orders(game, 'ENGLAND', 'A LVP - IRI')
        self.process(game)
        assert self.check_results(game, 'A LVP', VOID)
        assert self.owner_name(game, 'A LVP') == 'ENGLAND'
        assert self.owner_name(game, 'A IRI') is None

    def test_6_a_3(self):
        """ 6.A.3. TEST CASE, MOVE FLEET TO LAND
            Check whether a fleet can not move to land.
            Germany: F Kiel - Munich
            Order should fail.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'GERMANY', 'F KIE')
        self.set_orders(game, 'GERMANY', 'F KIE - MUN')
        self.process(game)
        assert self.check_results(game, 'F KIE', VOID)
        assert self.owner_name(game, 'F KIE') == 'GERMANY'
        assert self.owner_name(game, 'F MUN') is None

    def test_6_a_4(self):
        """ 6.A.4. TEST CASE, MOVE TO OWN SECTOR
            Moving to the same sector is an illegal move (2000 rulebook, page 4,
            "An Army can be ordered to move into an adjacent inland or coastal province.").
            Germany: F Kiel - Kiel
            Program should not crash.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'GERMANY', 'F KIE')
        self.set_orders(game, 'GERMANY', 'F KIE - KIE')
        self.process(game)
        assert self.check_results(game, 'F KIE', VOID)
        assert self.owner_name(game, 'F KIE') == 'GERMANY'

    def test_6_a_5(self):
        """ 6.A.5. TEST CASE, MOVE TO OWN SECTOR WITH CONVOY
            Moving to the same sector is still illegal with convoy (2000 rulebook, page 4,
            "Note: An Army can move across water provinces from one coastal province to another...").
            England: F North Sea Convoys A Yorkshire - Yorkshire
            England: A Yorkshire - Yorkshire
            England: A Liverpool Supports A Yorkshire - Yorkshire
            Germany: F London - Yorkshire
            Germany: A Wales Supports F London - Yorkshire
            The move of the army in Yorkshire is illegal. This makes the support of Liverpool also illegal and without
            the support, the Germans have a stronger force. The army in London dislodges the army in Yorkshire.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F NTH', 'A YOR', 'A LVP'])
        self.set_units(game, 'GERMANY', ['F LON', 'A WAL'])
        self.set_orders(game, 'ENGLAND', ['F LON C A YOR - YOR', 'A YOR - YOR', 'A LVP S A YOR - YOR'])
        self.set_orders(game, 'GERMANY', ['F LON - YOR', 'A WAL S F LON - YOR'])
        self.process(game)
        assert self.check_results(game, 'A YOR', VOID)
        assert self.check_results(game, 'A YOR', DISLODGED)
        assert self.check_results(game, 'A LVP', VOID)
        assert check_dislodged(game, 'A YOR', 'F LON')
        assert self.check_results(game, 'F LON', OK)
        assert self.check_results(game, 'A WAL', OK)
        assert self.owner_name(game, 'F YOR') == 'GERMANY'

    def test_6_a_6(self):
        """ 6.A.6. TEST CASE, ORDERING A UNIT OF ANOTHER COUNTRY
            Check whether someone can not order a unit that is not his own unit.
            England has a fleet in London.
            Germany: F London - North Sea
            Order should fail.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F LON'])
        self.set_orders(game, 'GERMANY', ['F LON - NTH'])
        self.process(game)
        assert self.check_results(game, 'F LON', OK)
        assert self.owner_name(game, 'F LON') == 'ENGLAND'
        assert self.owner_name(game, 'F NTH') is None

    def test_6_a_7(self):
        """ 6.A.7. TEST CASE, ONLY ARMIES CAN BE CONVOYED
            A fleet can not be convoyed.
            England: F London - Belgium
            England: F North Sea Convoys A London - Belgium
            Move from London to Belgium should fail.
        """
        # -------------------------------------------
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F LON', 'F NTH'])
        self.set_orders(game, 'ENGLAND', ['F LON - BEL', 'F NTH C A LON - BEL'])
        self.process(game)
        assert self.check_results(game, 'F LON', VOID)
        assert self.check_results(game, 'F NTH', VOID)
        assert self.owner_name(game, 'F LON') == 'ENGLAND'
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'F BEL') is None
        # -------------------------------------------
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F LON', 'F NTH'])
        self.set_orders(game, 'ENGLAND', ['F LON - BEL', 'F NTH C LON - BEL'])
        self.process(game)
        assert self.check_results(game, 'F LON', VOID)
        assert self.check_results(game, 'F NTH', VOID)
        assert self.owner_name(game, 'F LON') == 'ENGLAND'
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'F BEL') is None
        # -------------------------------------------

    def test_6_a_8(self):
        """ 6.A.8. TEST CASE, SUPPORT TO HOLD YOURSELF IS NOT POSSIBLE
            An army can not get an additional hold power by supporting itself.
            Italy: A Venice - Trieste
            Italy: A Tyrolia Supports A Venice - Trieste
            Austria: F Trieste Supports F Trieste
            The army in Trieste should be dislodged.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ITALY', ['A VEN', 'A TYR'])
        self.set_units(game, 'AUSTRIA', 'F TRI')
        self.set_orders(game, 'ITALY', ['A VEN - TRI', 'A TYR S A VEN - TRI'])
        self.set_orders(game, 'AUSTRIA', 'F TRI S F TRI')
        self.process(game)
        assert self.check_results(game, 'F TRI', VOID)
        assert self.check_results(game, 'F TRI', DISLODGED)
        assert check_dislodged(game, 'F TRI', 'A VEN')
        assert self.owner_name(game, 'A TRI') == 'ITALY'
        assert self.owner_name(game, 'A VEN') is None

    def test_6_a_9(self):
        """ 6.A.9. TEST CASE, FLEETS MUST FOLLOW COAST IF NOT ON SEA
            If two places are adjacent, that does not mean that a fleet can move between
            those two places. An implementation that only holds one list of adj. places for each place, is incorrect
            Italy: F Rome - Venice
            Move fails. An army can go from Rome to Venice, but a fleet can not.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ITALY', 'F ROM')
        self.set_orders(game, 'ITALY', 'F ROM - VEN')
        self.process(game)
        assert self.check_results(game, 'F ROM', VOID)
        assert self.owner_name(game, 'F ROM') == 'ITALY'
        assert self.owner_name(game, 'F VEN') is None

    def test_6_a_10(self):
        """ 6.A.10. TEST CASE, SUPPORT ON UNREACHABLE DESTINATION NOT POSSIBLE
            The destination of the move that is supported must be reachable by the supporting unit.
            Austria: A Venice Hold
            Italy: F Rome Supports A Apulia - Venice
            Italy: A Apulia - Venice
            The support of Rome is illegal, because Venice can not be reached from Rome by a fleet.
            Venice is not dislodged.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ITALY', ['F ROM', 'A APU'])
        self.set_units(game, 'AUSTRIA', 'A VEN')
        self.set_orders(game, 'ITALY', ['F ROM S A APU - VEN', 'A APU - VEN'])
        self.set_orders(game, 'AUSTRIA', 'A VEN H')
        self.process(game)
        assert self.check_results(game, 'F ROM', VOID)
        assert self.check_results(game, 'A APU', BOUNCE)
        assert self.owner_name(game, 'F ROM') == 'ITALY'
        assert self.owner_name(game, 'A VEN') == 'AUSTRIA'

    def test_6_a_11(self):
        """ 6.A.11. TEST CASE, SIMPLE BOUNCE
            Two armies bouncing on each other.
            Austria: A Vienna - Tyrolia
            Italy: A Venice - Tyrolia
            The two units bounce.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ITALY', 'A VEN')
        self.set_units(game, 'AUSTRIA', 'A VIE')
        self.set_orders(game, 'ITALY', 'A VEN - TYR')
        self.set_orders(game, 'AUSTRIA', 'A VIE - TYR')
        self.process(game)
        assert self.check_results(game, 'A VEN', BOUNCE)
        assert self.check_results(game, 'A VIE', BOUNCE)
        assert self.owner_name(game, 'A VEN') == 'ITALY'
        assert self.owner_name(game, 'A VIE') == 'AUSTRIA'
        assert self.owner_name(game, 'A TYR') is None

    def test_6_a_12(self):
        """ 6.A.12. TEST CASE, BOUNCE OF THREE UNITS
            If three units move to the same place, the adjudicator should not bounce
            the first two units and then let the third unit go to the now open place.
            Austria: A Vienna - Tyrolia
            Germany: A Munich - Tyrolia
            Italy: A Venice - Tyrolia
            The three units bounce.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'AUSTRIA', 'A VIE')
        self.set_units(game, 'GERMANY', 'A MUN')
        self.set_units(game, 'ITALY', 'A VEN')
        self.set_orders(game, 'AUSTRIA', 'A VIE - TYR')
        self.set_orders(game, 'GERMANY', 'A MUN - TYR')
        self.set_orders(game, 'ITALY', 'A VEN - TYR')
        self.process(game)
        assert self.check_results(game, 'A VEN', BOUNCE)
        assert self.check_results(game, 'A VIE', BOUNCE)
        assert self.check_results(game, 'A MUN', BOUNCE)
        assert self.owner_name(game, 'A VIE') == 'AUSTRIA'
        assert self.owner_name(game, 'A MUN') == 'GERMANY'
        assert self.owner_name(game, 'A VEN') == 'ITALY'
        assert self.owner_name(game, 'A TYR') is None

    # 6.B. TEST CASES, COASTAL ISSUES
    def test_6_b_1(self):
        """ 6.B.1. TEST CASE, MOVING WITH UNSPECIFIED COAST WHEN COAST IS NECESSARY
            Coast is significant in this case:
            France: F Portugal - Spain
            Some adjudicators take a default coast (see issue 4.B.1).
            I prefer that the move fails.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'FRANCE', 'F POR')
        self.set_orders(game, 'FRANCE', 'F POR - SPA')
        self.process(game)
        assert self.check_results(game, 'F POR', VOID)
        assert self.owner_name(game, 'F POR') == 'FRANCE'
        assert self.owner_name(game, 'F SPA') is None
        assert self.owner_name(game, 'F SPA/NC') is None
        assert self.owner_name(game, 'F SPA/SC') is None

    def test_6_b_2(self):
        """ 6.B.2. TEST CASE, MOVING WITH UNSPECIFIED COAST WHEN COAST IS NOT NECESSARY
            There is only one coast possible in this case:
            France: F Gascony - Spain
            Since the North Coast is the only coast that can be reached, it seems logical that
            the a move is attempted to the north coast of Spain. Some adjudicators require that a coast
            is also specified in this case and will decide that the move fails or take a default coast (see 4.B.2).
            I prefer that an attempt is made to the only possible coast, the north coast of Spain.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'FRANCE', 'F GAS')
        self.set_orders(game, 'FRANCE', 'F GAS - SPA')
        self.process(game)
        assert self.check_results(game, 'F GAS', OK)
        assert self.owner_name(game, 'F GAS') is None
        assert self.owner_name(game, 'F SPA/NC') == 'FRANCE'
        assert self.owner_name(game, 'F SPA/SC') is None

    def test_6_b_3(self):
        """ 6.B.3. TEST CASE, MOVING WITH WRONG COAST WHEN COAST IS NOT NECESSARY
            If only one coast is possible, but the wrong coast can be specified.
            France: F Gascony - Spain(sc)
            If the rules are played very clemently, a move will be attempted to the north coast of Spain.
            However, since this order is very clear and precise, it is more common that the move fails (see 4.B.3).
            I prefer that the move fails.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'FRANCE', 'F GAS')
        self.set_orders(game, 'FRANCE', 'F GAS - SPA/SC')
        self.process(game)
        assert self.check_results(game, 'F GAS', VOID)
        assert self.owner_name(game, 'F GAS') == 'FRANCE'
        assert self.owner_name(game, 'F SPA') is None
        assert self.owner_name(game, 'F SPA/NC') is None
        assert self.owner_name(game, 'F SPA/SC') is None

    def test_6_b_4(self):
        """ 6.B.4. TEST CASE, SUPPORT TO UNREACHABLE COAST ALLOWED
            A fleet can give support to a coast where it can not go.
            France: F Gascony - Spain(nc)
            France: F Marseilles Supports F Gascony - Spain(nc)
            Italy: F Western Mediterranean - Spain(sc)
            Although the fleet in Marseilles can not go to the north coast it can still
            support targeting the north coast. So, the support is successful, the move of the fleet
            in Gasgony succeeds and the move of the Italian fleet fails.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'FRANCE', ['F GAS', 'F MAR'])
        self.set_units(game, 'ITALY', 'F WES')
        self.set_orders(game, 'FRANCE', ['F GAS - SPA/NC', 'F MAR S F GAS - SPA/NC'])
        self.set_orders(game, 'ITALY', 'F WES - SPA/SC')
        self.process(game)
        assert self.check_results(game, 'F WES', BOUNCE)
        assert self.owner_name(game, 'F SPA/NC') == 'FRANCE'
        assert self.owner_name(game, 'F MAR') == 'FRANCE'
        assert self.owner_name(game, 'F WES') == 'ITALY'

    def test_6_b_5(self):
        """ 6.B.5. TEST CASE, SUPPORT FROM UNREACHABLE COAST NOT ALLOWED
            A fleet can not give support to an area that can not be reached from the current coast of the fleet.
            France: F Marseilles - Gulf of Lyon
            France: F Spain(nc) Supports F Marseilles - Gulf of Lyon
            Italy: F Gulf of Lyon Hold
            The Gulf of Lyon can not be reached from the North Coast of Spain. Therefore, the support of
            Spain is invalid and the fleet in the Gulf of Lyon is not dislodged.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'FRANCE', ['F MAR', 'F SPA/NC'])
        self.set_units(game, 'ITALY', 'F LYO')
        self.set_orders(game, 'FRANCE', ['F MAR - LYO', 'F SPA/NC S F MAR - LYO'])
        self.set_orders(game, 'ITALY', 'F LYO H')
        self.process(game)
        assert self.check_results(game, 'F SPA/NC', VOID)
        assert self.check_results(game, 'F MAR', BOUNCE)
        assert self.owner_name(game, 'F MAR') == 'FRANCE'
        assert self.owner_name(game, 'F SPA/NC') == 'FRANCE'
        assert self.owner_name(game, 'F LYO') == 'ITALY'

    def test_6_b_6(self):
        """ 6.B.6. TEST CASE, SUPPORT CAN BE CUT WITH OTHER COAST
            Support can be cut from the other coast.
            England: F Irish Sea Supports F North Atlantic Ocean - Mid-Atlantic Ocean
            England: F North Atlantic Ocean - Mid-Atlantic Ocean
            France: F Spain(nc) Supports F Mid-Atlantic Ocean
            France: F Mid-Atlantic Ocean Hold
            Italy: F Gulf of Lyon - Spain(sc)
            The Italian fleet in the Gulf of Lyon will cut the support in Spain. That means
            that the French fleet in the Mid Atlantic Ocean will be dislodged by the English fleet
            in the North Atlantic Ocean.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F IRI', 'F NAO'])
        self.set_units(game, 'FRANCE', ['F SPA/NC', 'F MAO'])
        self.set_units(game, 'ITALY', 'F LYO')
        self.set_orders(game, 'ENGLAND', ['F IRI S F NAO - MAO', 'F NAO - MAO'])
        self.set_orders(game, 'FRANCE', ['F SPA/NC S F MAO', 'F MAO H'])
        self.set_orders(game, 'ITALY', 'F LYO - SPA/SC')
        self.process(game)
        assert self.check_results(game, 'F SPA/NC', CUT)
        assert self.check_results(game, 'F MAO', DISLODGED)
        assert check_dislodged(game, 'F MAO', 'F NAO')
        assert self.owner_name(game, 'F IRI') == 'ENGLAND'
        assert self.owner_name(game, 'F NAO') is None
        assert self.owner_name(game, 'F MAO') == 'ENGLAND'
        assert self.owner_name(game, 'F SPA/NC') == 'FRANCE'
        assert self.owner_name(game, 'F LYO') == 'ITALY'

    def test_6_b_7(self):
        """ 6.B.7. TEST CASE, SUPPORTING WITH UNSPECIFIED COAST
            Most house rules accept support orders without coast specification.
            France: F Portugal Supports F Mid-Atlantic Ocean - Spain
            France: F Mid-Atlantic Ocean - Spain(nc)
            Italy: F Gulf of Lyon Supports F Western Mediterranean - Spain(sc)
            Italy: F Western Mediterranean - Spain(sc)
            See issue 4.B.4. If coasts are not required in support orders, then the support of Portugal is successful.
            This means that the Italian fleet in the Western Mediterranean bounces. Some adjudicators may not accept a
            support order without coast (the support will fail or a default coast is taken). In that case the
            support order of Portugal fails (in case of a default coast the coast will probably the south coast) and
            the Italian fleet in the Western Mediterranean will successfully move.
            I prefer that the support succeeds and the Italian fleet in the Western Mediterranean bounces.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'FRANCE', ['F POR', 'F MAO'])
        self.set_units(game, 'ITALY', ['F LYO', 'F WES'])
        self.set_orders(game, 'FRANCE', ['F POR S F MAO - SPA', 'F MAO - SPA/NC'])
        self.set_orders(game, 'ITALY', ['F LYO S F WES - SPA/SC', 'F WES - SPA/SC'])
        self.process(game)
        assert self.check_results(game, 'F POR', OK)
        assert self.check_results(game, 'F LYO', OK)
        assert self.check_results(game, 'F MAO', BOUNCE)
        assert self.check_results(game, 'F WES', BOUNCE)
        assert self.owner_name(game, 'F POR') == 'FRANCE'
        assert self.owner_name(game, 'F MAO') == 'FRANCE'
        assert self.owner_name(game, 'F LYO') == 'ITALY'
        assert self.owner_name(game, 'F WES') == 'ITALY'
        assert self.owner_name(game, 'F SPA') is None
        assert self.owner_name(game, 'F SPA/SC') is None
        assert self.owner_name(game, 'F SPA/NC') is None

    def test_6_b_8(self):
        """ 6.B.8. TEST CASE, SUPPORTING WITH UNSPECIFIED COAST WHEN ONLY ONE COAST IS POSSIBLE
            Some hardliners require a coast in a support order even when only one coast is possible.
            France: F Portugal Supports F Gascony - Spain
            France: F Gascony - Spain(nc)
            Italy: F Gulf of Lyon Supports F Western Mediterranean - Spain(sc)
            Italy: F Western Mediterranean - Spain(sc)
            See issue 4.B.4. If coasts are not required in support orders, then the support of Portugal is successful.
            This means that the Italian fleet in the Western Mediterranean bounces. Some adjudicators may not accept a
            support order without coast (the support will fail or a default coast is taken). In that case the
            support order of Portugal fails (in case of a default coast the coast will probably the south coast) and
            the Italian fleet in the Western Mediterranean will successfully move.
            I prefer that supporting without coasts should be allowed. So I prefer that the support of Portugal
            is successful and that the Italian fleet in the Western Mediterranean bounces.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'FRANCE', ['F POR', 'F GAS'])
        self.set_units(game, 'ITALY', ['F LYO', 'F WES'])
        self.set_orders(game, 'FRANCE', ['F POR S F GAS - SPA', 'F GAS - SPA/NC'])
        self.set_orders(game, 'ITALY', ['F LYO S F WES - SPA/SC', 'F WES - SPA/SC'])
        self.process(game)
        assert self.check_results(game, 'F POR', OK)
        assert self.check_results(game, 'F LYO', OK)
        assert self.check_results(game, 'F GAS', BOUNCE)
        assert self.check_results(game, 'F WES', BOUNCE)
        assert self.owner_name(game, 'F POR') == 'FRANCE'
        assert self.owner_name(game, 'F GAS') == 'FRANCE'
        assert self.owner_name(game, 'F LYO') == 'ITALY'
        assert self.owner_name(game, 'F WES') == 'ITALY'
        assert self.owner_name(game, 'F SPA') is None
        assert self.owner_name(game, 'F SPA/SC') is None
        assert self.owner_name(game, 'F SPA/NC') is None

    def test_6_b_9(self):
        """ 6.B.9. TEST CASE, SUPPORTING WITH WRONG COAST
            Coasts can be specified in a support, but the result depends on the house rules.
            France: F Portugal Supports F Mid-Atlantic Ocean - Spain(nc)
            France: F Mid-Atlantic Ocean - Spain(sc)
            Italy: F Gulf of Lyon Supports F Western Mediterranean - Spain(sc)
            Italy: F Western Mediterranean - Spain(sc)
            See issue 4.B.4. If it is required that the coast matches, then the support of the French fleet in the
            Mid-Atlantic Ocean fails and that the Italian fleet in the Western Mediterranean moves successfully. Some
            adjudicators ignores the coasts in support orders. In that case, the move of the Italian fleet bounces.
            I prefer that the support fails and that the Italian fleet in the Western Mediterranean moves successfully.
        """
        # Order expansion will rewrite F POR S F MAO - SPA/NC -> F POR S F MAO - SPA/SC
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'FRANCE', ['F POR', 'F MAO'])
        self.set_units(game, 'ITALY', ['F LYO', 'F WES'])
        self.set_orders(game, 'FRANCE', ['F POR S F MAO - SPA/NC', 'F MAO - SPA/SC'])
        self.set_orders(game, 'ITALY', ['F LYO S F WES - SPA/SC', 'F WES - SPA/SC'])
        self.process(game)
        assert self.check_results(game, 'F POR', OK)
        assert self.check_results(game, 'F MAO', BOUNCE)
        assert self.check_results(game, 'F LYO', OK)
        assert self.check_results(game, 'F WES', BOUNCE)
        assert self.owner_name(game, 'F POR') == 'FRANCE'
        assert self.owner_name(game, 'F MAO') == 'FRANCE'
        assert self.owner_name(game, 'F SPA') is None
        assert self.owner_name(game, 'F SPA/NC') is None
        assert self.owner_name(game, 'F SPA/SC') is None
        assert self.owner_name(game, 'F LYO') == 'ITALY'
        assert self.owner_name(game, 'F WES') == 'ITALY'

    def test_6_b_10(self):
        """ 6.B.10. TEST CASE, UNIT ORDERED WITH WRONG COAST
            A player might specify the wrong coast for the ordered unit.
            France has a fleet on the south coast of Spain and orders:
            France: F Spain(nc) - Gulf of Lyon
            If only perfect orders are accepted, then the move will fail, but since the coast for the ordered unit
            has no purpose, it might also be ignored (see issue 4.B.5).
            I prefer that a move will be attempted.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'FRANCE', 'F SPA/SC')
        self.set_orders(game, 'FRANCE', 'F SPA/NC - LYO')
        self.process(game)
        assert self.check_results(game, 'F SPA/SC', OK)
        assert self.owner_name(game, 'F SPA') is None
        assert self.owner_name(game, 'F SPA/SC') is None
        assert self.owner_name(game, 'F LYO') == 'FRANCE'

    def test_6_b_11(self):
        """ 6.B.11. TEST CASE, COAST CAN NOT BE ORDERED TO CHANGE
            The coast can not change by just ordering the other coast.
            France has a fleet on the north coast of Spain and orders:
            France: F Spain(sc) - Gulf of Lyon
            The move fails.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'FRANCE', 'F SPA/NC')
        self.set_orders(game, 'FRANCE', 'F SPA/SC - LYO')
        self.process(game)
        assert self.check_results(game, 'F SPA/SC', VOID)
        assert self.owner_name(game, 'F SPA') == 'FRANCE'
        assert self.owner_name(game, 'F SPA/NC') == 'FRANCE'
        assert self.owner_name(game, 'F SPA/SC') is None
        assert self.owner_name(game, 'F LYO') is None

    def test_6_b_12(self):
        """ 6.B.12. TEST CASE, ARMY MOVEMENT WITH COASTAL SPECIFICATION
            For armies the coasts are irrelevant:
            France: A Gascony - Spain(nc)
            If only perfect orders are accepted, then the move will fail. But it is also possible that coasts are
            ignored in this case and a move will be attempted (see issue 4.B.6).
            I prefer that a move will be attempted.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'FRANCE', 'A GAS')
        self.set_orders(game, 'FRANCE', 'A GAS - SPA/NC')
        self.process(game)
        assert self.check_results(game, 'A GAS', OK)
        assert self.owner_name(game, 'A GAS') is None
        assert self.owner_name(game, 'A SPA') == 'FRANCE'
        assert self.owner_name(game, 'A SPA/NC') is None
        assert self.owner_name(game, 'A SPA/SC') is None

    def test_6_b_13(self):
        """ 6.B.13. TEST CASE, COASTAL CRAWL NOT ALLOWED
            If a fleet is leaving a sector from a certain coast while in the opposite direction another fleet
            is moving to another coast of the sector, it is still a head to head battle. This has been decided in
            the great revision of the 1961 rules that resulted in the 1971 rules.
            Turkey: F Bulgaria(sc) - Constantinople
            Turkey: F Constantinople - Bulgaria(ec)
            Both moves fail.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'TURKEY', ['F BUL/SC', 'F CON'])
        self.set_orders(game, 'TURKEY', ['F BUL/SC - CON', 'F CON - BUL/EC'])
        self.process(game)
        assert self.check_results(game, 'F BUL/SC', BOUNCE)
        assert self.check_results(game, 'F CON', BOUNCE)
        assert self.owner_name(game, 'F BUL/SC') == 'TURKEY'
        assert self.owner_name(game, 'F CON') == 'TURKEY'
        assert self.owner_name(game, 'F BUL/EC') is None

    def test_6_b_14(self):
        """ 6.B.14. TEST CASE, BUILDING WITH UNSPECIFIED COAST
            Coast must be specified in certain build cases:
            Russia: Build F St Petersburg
            If no default coast is taken (see issue 4.B.7), the build fails.
            I do not like default coast, so I prefer that the build fails.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_centers(game, 'RUSSIA', 'STP')
        self.move_to_phase(game, 'W1901A')
        self.set_orders(game, 'RUSSIA', 'F STP B')
        self.process(game)
        assert self.check_results(game, 'F STP', VOID, phase='A')
        assert self.owner_name(game, 'F STP') is None
        assert self.owner_name(game, 'F STP/SC') is None
        assert self.owner_name(game, 'F STP/NC') is None

    # 6.C. TEST CASES, CIRCULAR MOVEMENT
    def test_6_c_1(self):
        """ 6.C.1. TEST CASE, THREE ARMY CIRCULAR MOVEMENT
            Three units can change place, even in spring 1901.
            Turkey: F Ankara - Constantinople
            Turkey: A Constantinople - Smyrna
            Turkey: A Smyrna - Ankara
            All three units will move.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'TURKEY', ['F ANK', 'A CON', 'A SMY'])
        self.set_orders(game, 'TURKEY', ['F ANK - CON', 'A CON - SMY', 'A SMY - ANK'])
        self.process(game)
        assert self.check_results(game, 'F ANK', OK)
        assert self.check_results(game, 'A CON', OK)
        assert self.check_results(game, 'A SMY', OK)
        assert self.owner_name(game, 'A ANK') == 'TURKEY'
        assert self.owner_name(game, 'F CON') == 'TURKEY'
        assert self.owner_name(game, 'A SMY') == 'TURKEY'

    def test_6_c_2(self):
        """ 6.C.2. TEST CASE, THREE ARMY CIRCULAR MOVEMENT WITH SUPPORT
            Three units can change place, even when one gets support.
            Turkey: F Ankara - Constantinople
            Turkey: A Constantinople - Smyrna
            Turkey: A Smyrna - Ankara
            Turkey: A Bulgaria Supports F Ankara - Constantinople
            Of course the three units will move, but knowing how programs are written, this can confuse the adjudicator.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'TURKEY', ['F ANK', 'A CON', 'A SMY', 'A BUL'])
        self.set_orders(game, 'TURKEY', ['F ANK - CON', 'A CON - SMY', 'A SMY - ANK', 'A BUL S F ANK - CON'])
        self.process(game)
        assert self.check_results(game, 'F ANK', OK)
        assert self.check_results(game, 'A CON', OK)
        assert self.check_results(game, 'A SMY', OK)
        assert self.check_results(game, 'A BUL', OK)
        assert self.owner_name(game, 'A ANK') == 'TURKEY'
        assert self.owner_name(game, 'F CON') == 'TURKEY'
        assert self.owner_name(game, 'A SMY') == 'TURKEY'
        assert self.owner_name(game, 'A BUL') == 'TURKEY'

    def test_6_c_3(self):
        """ 6.C.3. TEST CASE, A DISRUPTED THREE ARMY CIRCULAR MOVEMENT
            When one of the units bounces, the whole circular movement will hold.
            Turkey: F Ankara - Constantinople
            Turkey: A Constantinople - Smyrna
            Turkey: A Smyrna - Ankara
            Turkey: A Bulgaria - Constantinople
            Every unit will keep its place.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'TURKEY', ['F ANK', 'A CON', 'A SMY', 'A BUL'])
        self.set_orders(game, 'TURKEY', ['F ANK - CON', 'A CON - SMY', 'A SMY - ANK', 'A BUL - CON'])
        self.process(game)
        assert self.check_results(game, 'F ANK', BOUNCE)
        assert self.check_results(game, 'A CON', BOUNCE)
        assert self.check_results(game, 'A SMY', BOUNCE)
        assert self.check_results(game, 'A BUL', BOUNCE)
        assert self.owner_name(game, 'F ANK') == 'TURKEY'
        assert self.owner_name(game, 'A CON') == 'TURKEY'
        assert self.owner_name(game, 'A SMY') == 'TURKEY'
        assert self.owner_name(game, 'A BUL') == 'TURKEY'

    def test_6_c_4(self):
        """ 6.C.4. TEST CASE, A CIRCULAR MOVEMENT WITH ATTACKED CONVOY
            When the circular movement contains an attacked convoy, the circular movement succeeds.
            The adjudication algorithm should handle attack of convoys before calculating circular movement.
            Austria: A Trieste - Serbia
            Austria: A Serbia - Bulgaria
            Turkey: A Bulgaria - Trieste
            Turkey: F Aegean Sea Convoys A Bulgaria - Trieste
            Turkey: F Ionian Sea Convoys A Bulgaria - Trieste
            Turkey: F Adriatic Sea Convoys A Bulgaria - Trieste
            Italy: F Naples - Ionian Sea
            The fleet in the Ionian Sea is attacked but not dislodged. The circular movement succeeds.
            The Austrian and Turkish armies will advance.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'AUSTRIA', ['A TRI', 'A SER'])
        self.set_units(game, 'TURKEY', ['A BUL', 'F AEG', 'F ION', 'F ADR'])
        self.set_units(game, 'ITALY', 'F NAP')
        self.set_orders(game, 'AUSTRIA', ['A TRI - SER', 'A SER - BUL'])
        self.set_orders(game, 'TURKEY', ['A BUL - TRI', 'F AEG C A BUL - TRI', 'F ION C A BUL - TRI',
                                         'F ADR C A BUL - TRI'])
        self.set_orders(game, 'ITALY', 'F NAP - ION')
        self.process(game)
        assert self.check_results(game, 'A TRI', OK)
        assert self.check_results(game, 'A SER', OK)
        assert self.check_results(game, 'A BUL', OK)
        assert self.check_results(game, 'F AEG', OK)
        assert self.check_results(game, 'F ION', OK)
        assert self.check_results(game, 'F ADR', OK)
        assert self.check_results(game, 'F NAP', BOUNCE)
        assert self.owner_name(game, 'A TRI') == 'TURKEY'
        assert self.owner_name(game, 'A SER') == 'AUSTRIA'
        assert self.owner_name(game, 'A BUL') == 'AUSTRIA'
        assert self.owner_name(game, 'F AEG') == 'TURKEY'
        assert self.owner_name(game, 'F ION') == 'TURKEY'
        assert self.owner_name(game, 'F ADR') == 'TURKEY'
        assert self.owner_name(game, 'F NAP') == 'ITALY'

    def test_6_c_5(self):
        """ 6.C.5. TEST CASE, A DISRUPTED CIRCULAR MOVEMENT DUE TO DISLODGED CONVOY
            When the circular movement contains a convoy, the circular movement is disrupted when the convoying
            fleet is dislodged. The adjudication algorithm should disrupt convoys before calculating circular movement.
            Austria: A Trieste - Serbia
            Austria: A Serbia - Bulgaria
            Turkey: A Bulgaria - Trieste
            Turkey: F Aegean Sea Convoys A Bulgaria - Trieste
            Turkey: F Ionian Sea Convoys A Bulgaria - Trieste
            Turkey: F Adriatic Sea Convoys A Bulgaria - Trieste
            Italy: F Naples - Ionian Sea
            Italy: F Tunis Supports F Naples - Ionian Sea
            Due to the dislodged convoying fleet, all Austrian and Turkish armies will not move.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'AUSTRIA', ['A TRI', 'A SER'])
        self.set_units(game, 'TURKEY', ['A BUL', 'F AEG', 'F ION', 'F ADR'])
        self.set_units(game, 'ITALY', ['F NAP', 'F TUN'])
        self.set_orders(game, 'AUSTRIA', ['A TRI - SER', 'A SER - BUL'])
        self.set_orders(game, 'TURKEY', ['A BUL - TRI', 'F AEG C A BUL - TRI', 'F ION C A BUL - TRI',
                                         'F ADR C A BUL - TRI'])
        self.set_orders(game, 'ITALY', ['F NAP - ION', 'F TUN S F NAP - ION'])
        self.process(game)
        assert self.check_results(game, 'A TRI', BOUNCE)
        assert self.check_results(game, 'A SER', BOUNCE)
        assert self.check_results(game, 'A BUL', NO_CONVOY)
        assert self.check_results(game, 'F AEG', NO_CONVOY)
        assert self.check_results(game, 'F ION', DISLODGED)
        assert self.check_results(game, 'F ADR', NO_CONVOY)
        assert self.check_results(game, 'F NAP', OK)
        assert self.check_results(game, 'F TUN', OK)
        assert check_dislodged(game, 'F ION', 'F NAP')
        assert self.owner_name(game, 'A TRI') == 'AUSTRIA'
        assert self.owner_name(game, 'A SER') == 'AUSTRIA'
        assert self.owner_name(game, 'A BUL') == 'TURKEY'
        assert self.owner_name(game, 'F AEG') == 'TURKEY'
        assert self.owner_name(game, 'F ION') == 'ITALY'
        assert self.owner_name(game, 'F ADR') == 'TURKEY'
        assert self.owner_name(game, 'F NAP') is None
        assert self.owner_name(game, 'F TUN') == 'ITALY'

    def test_6_c_6(self):
        """ 6.C.6. TEST CASE, TWO ARMIES WITH TWO CONVOYS
            Two armies can swap places even when they are not adjacent.
            England: F North Sea Convoys A London - Belgium
            England: A London - Belgium
            France: F English Channel Convoys A Belgium - London
            France: A Belgium - London
            Both convoys should succeed.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F NTH', 'A LON'])
        self.set_units(game, 'FRANCE', ['F ENG', 'A BEL'])
        self.set_orders(game, 'ENGLAND', ['F NTH C A LON - BEL', 'A LON - BEL'])
        self.set_orders(game, 'FRANCE', ['F ENG C A BEL - LON', 'A BEL - LON'])
        self.process(game)
        assert self.check_results(game, 'F NTH', OK)
        assert self.check_results(game, 'A LON', OK)
        assert self.check_results(game, 'F ENG', OK)
        assert self.check_results(game, 'A BEL', OK)
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'A BEL') == 'ENGLAND'
        assert self.owner_name(game, 'F ENG') == 'FRANCE'
        assert self.owner_name(game, 'A LON') == 'FRANCE'

    def test_6_c_7(self):
        """ 6.C.7. TEST CASE, DISRUPTED UNIT SWAP
            If in a swap one of the unit bounces, then the swap fails.
            England: F North Sea Convoys A London - Belgium
            England: A London - Belgium
            France: F English Channel Convoys A Belgium - London
            France: A Belgium - London
            France: A Burgundy - Belgium
            None of the units will succeed to move.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F NTH', 'A LON'])
        self.set_units(game, 'FRANCE', ['F ENG', 'A BEL', 'A BUR'])
        self.set_orders(game, 'ENGLAND', ['F NTH C A LON - BEL', 'A LON - BEL'])
        self.set_orders(game, 'FRANCE', ['F ENG C A BEL - LON', 'A BEL - LON', 'A BUR - BEL'])
        self.process(game)
        assert self.check_results(game, 'F NTH', OK)
        assert self.check_results(game, 'A LON', BOUNCE)
        assert self.check_results(game, 'F ENG', OK)
        assert self.check_results(game, 'A BEL', BOUNCE)
        assert self.check_results(game, 'A BUR', BOUNCE)
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'A LON') == 'ENGLAND'
        assert self.owner_name(game, 'F ENG') == 'FRANCE'
        assert self.owner_name(game, 'A BEL') == 'FRANCE'
        assert self.owner_name(game, 'A BUR') == 'FRANCE'

    # 6.D. TEST CASES, SUPPORTS AND DISLODGES
    def test_6_d_1(self):
        """ 6.D.1. TEST CASE, SUPPORTED HOLD CAN PREVENT DISLODGEMENT
            The most simple support to hold order.
            Austria: F Adriatic Sea Supports A Trieste - Venice
            Austria: A Trieste - Venice
            Italy: A Venice Hold
            Italy: A Tyrolia Supports A Venice
            The support of Tyrolia prevents that the army in Venice is dislodged. The army in Trieste will not move.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'AUSTRIA', ['F ADR', 'A TRI'])
        self.set_units(game, 'ITALY', ['A VEN', 'A TYR'])
        self.set_orders(game, 'AUSTRIA', ['F ADR S A TRI - VEN', 'A TRI - VEN'])
        self.set_orders(game, 'ITALY', ['A VEN H', 'A TYR S A VEN'])
        self.process(game)
        assert self.check_results(game, 'F ADR', OK)
        assert self.check_results(game, 'A TRI', BOUNCE)
        assert self.check_results(game, 'A VEN', OK)
        assert self.check_results(game, 'A TYR', OK)
        assert self.owner_name(game, 'F ADR') == 'AUSTRIA'
        assert self.owner_name(game, 'A TRI') == 'AUSTRIA'
        assert self.owner_name(game, 'A VEN') == 'ITALY'
        assert self.owner_name(game, 'A TYR') == 'ITALY'

    def test_6_d_2(self):
        """ 6.D.2. TEST CASE, A MOVE CUTS SUPPORT ON HOLD
            The most simple support on hold cut.
            Austria: F Adriatic Sea Supports A Trieste - Venice
            Austria: A Trieste - Venice
            Austria: A Vienna - Tyrolia
            Italy: A Venice Hold
            Italy: A Tyrolia Supports A Venice
            The support of Tyrolia is cut by the army in Vienna. That means that the army in Venice is dislodged by the
            army from Trieste.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'AUSTRIA', ['F ADR', 'A TRI', 'A VIE'])
        self.set_units(game, 'ITALY', ['A VEN', 'A TYR'])
        self.set_orders(game, 'AUSTRIA', ['F ADR S A TRI - VEN', 'A TRI - VEN', 'A VIE - TYR'])
        self.set_orders(game, 'ITALY', ['A VEN H', 'A TYR S A VEN'])
        self.process(game)
        assert self.check_results(game, 'F ADR', OK)
        assert self.check_results(game, 'A TRI', OK)
        assert self.check_results(game, 'A VIE', BOUNCE)
        assert self.check_results(game, 'A VEN', DISLODGED)
        assert self.check_results(game, 'A TYR', CUT)
        assert check_dislodged(game, 'A VEN', 'A TRI')
        assert self.owner_name(game, 'F ADR') == 'AUSTRIA'
        assert self.owner_name(game, 'A TRI') is None
        assert self.owner_name(game, 'A VIE') == 'AUSTRIA'
        assert self.owner_name(game, 'A VEN') == 'AUSTRIA'
        assert self.owner_name(game, 'A TYR') == 'ITALY'

    def test_6_d_3(self):
        """ 6.D.3. TEST CASE, A MOVE CUTS SUPPORT ON MOVE
            The most simple support on move cut.
            Austria: F Adriatic Sea Supports A Trieste - Venice
            Austria: A Trieste - Venice
            Italy: A Venice Hold
            Italy: F Ionian Sea - Adriatic Sea
            The support of the fleet in the Adriatic Sea is cut. That means that the army in Venice will not be
            dislodged and the army in Trieste stays in Trieste.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'AUSTRIA', ['F ADR', 'A TRI'])
        self.set_units(game, 'ITALY', ['A VEN', 'F ION'])
        self.set_orders(game, 'AUSTRIA', ['F ADR S A TRI - VEN', 'A TRI - VEN'])
        self.set_orders(game, 'ITALY', ['A VEN H', 'F ION - ADR'])
        self.process(game)
        assert self.check_results(game, 'F ADR', CUT)
        assert self.check_results(game, 'A TRI', BOUNCE)
        assert self.check_results(game, 'A VEN', OK)
        assert self.check_results(game, 'F ION', BOUNCE)
        assert self.owner_name(game, 'F ADR') == 'AUSTRIA'
        assert self.owner_name(game, 'A TRI') == 'AUSTRIA'
        assert self.owner_name(game, 'A VEN') == 'ITALY'
        assert self.owner_name(game, 'F ION') == 'ITALY'

    def test_6_d_4(self):
        """ 6.D.4. TEST CASE, SUPPORT TO HOLD ON UNIT SUPPORTING A HOLD ALLOWED
            A unit that is supporting a hold, can receive a hold support.
            Germany: A Berlin Supports F Kiel
            Germany: F Kiel Supports A Berlin
            Russia: F Baltic Sea Supports A Prussia - Berlin
            Russia: A Prussia - Berlin
            The Russian move from Prussia to Berlin fails.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'GERMANY', ['A BER', 'F KIE'])
        self.set_units(game, 'RUSSIA', ['F BAL', 'A PRU'])
        self.set_orders(game, 'GERMANY', ['A BER S F KIE', 'F KIE S A BER'])
        self.set_orders(game, 'RUSSIA', ['F BAL S A PRU - BER', 'A PRU - BER'])
        self.process(game)
        assert self.check_results(game, 'A BER', CUT)
        assert self.check_results(game, 'F KIE', OK)
        assert self.check_results(game, 'F BAL', OK)
        assert self.check_results(game, 'A PRU', BOUNCE)
        assert self.owner_name(game, 'A BER') == 'GERMANY'
        assert self.owner_name(game, 'F KIE') == 'GERMANY'
        assert self.owner_name(game, 'F BAL') == 'RUSSIA'
        assert self.owner_name(game, 'A PRU') == 'RUSSIA'

    def test_6_d_5(self):
        """ 6.D.5. TEST CASE, SUPPORT TO HOLD ON UNIT SUPPORTING A MOVE ALLOWED
            A unit that is supporting a move, can receive a hold support.
            Germany: A Berlin Supports A Munich - Silesia
            Germany: F Kiel Supports A Berlin
            Germany: A Munich - Silesia
            Russia: F Baltic Sea Supports A Prussia - Berlin
            Russia: A Prussia - Berlin
            The Russian move from Prussia to Berlin fails.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'GERMANY', ['A BER', 'F KIE', 'A MUN'])
        self.set_units(game, 'RUSSIA', ['F BAL', 'A PRU'])
        self.set_orders(game, 'GERMANY', ['A BER S A MUN - SIL', 'F KIE S A BER', 'A MUN - SIL'])
        self.set_orders(game, 'RUSSIA', ['F BAL S A PRU - BER', 'A PRU - BER'])
        self.process(game)
        assert self.check_results(game, 'A BER', CUT)
        assert self.check_results(game, 'F KIE', OK)
        assert self.check_results(game, 'A MUN', OK)
        assert self.check_results(game, 'F BAL', OK)
        assert self.check_results(game, 'A PRU', BOUNCE)
        assert self.owner_name(game, 'A BER') == 'GERMANY'
        assert self.owner_name(game, 'F KIE') == 'GERMANY'
        assert self.owner_name(game, 'A MUN') is None
        assert self.owner_name(game, 'F BAL') == 'RUSSIA'
        assert self.owner_name(game, 'A PRU') == 'RUSSIA'
        assert self.owner_name(game, 'A SIL') == 'GERMANY'

    def test_6_d_6(self):
        """ 6.D.6. TEST CASE, SUPPORT TO HOLD ON CONVOYING UNIT ALLOWED
            A unit that is convoying, can receive a hold support.
            Germany: A Berlin - Sweden
            Germany: F Baltic Sea Convoys A Berlin - Sweden
            Germany: F Prussia Supports F Baltic Sea
            Russia: F Livonia - Baltic Sea
            Russia: F Gulf of Bothnia Supports F Livonia - Baltic Sea
            The Russian move from Livonia to the Baltic Sea fails. The convoy from Berlin to Sweden succeeds.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'GERMANY', ['A BER', 'F BAL', 'F PRU'])
        self.set_units(game, 'RUSSIA', ['F LVN', 'F BOT'])
        self.set_orders(game, 'GERMANY', ['A BER - SWE', 'F BAL C A BER - SWE', 'F PRU S F BAL'])
        self.set_orders(game, 'RUSSIA', ['F LVN - BAL', 'F BOT S F LVN - BAL'])
        self.process(game)
        assert self.check_results(game, 'A BER', OK)
        assert self.check_results(game, 'F BAL', OK)
        assert self.check_results(game, 'F PRU', OK)
        assert self.check_results(game, 'F LVN', BOUNCE)
        assert self.check_results(game, 'F BOT', OK)
        assert self.owner_name(game, 'A BER') is None
        assert self.owner_name(game, 'F BAL') == 'GERMANY'
        assert self.owner_name(game, 'F PRU') == 'GERMANY'
        assert self.owner_name(game, 'F LVN') == 'RUSSIA'
        assert self.owner_name(game, 'F BOT') == 'RUSSIA'
        assert self.owner_name(game, 'A SWE') == 'GERMANY'

    def test_6_d_7(self):
        """ 6.D.7. TEST CASE, SUPPORT TO HOLD ON MOVING UNIT NOT ALLOWED
            A unit that is moving, can not receive a hold support for the situation that the move fails.
            Germany: F Baltic Sea - Sweden
            Germany: F Prussia Supports F Baltic Sea
            Russia: F Livonia - Baltic Sea
            Russia: F Gulf of Bothnia Supports F Livonia - Baltic Sea
            Russia: A Finland - Sweden
            The support of the fleet in Prussia fails. The fleet in Baltic Sea will bounce on the Russian army
            in Finland and will be dislodged by the Russian fleet from Livonia when it returns to the Baltic Sea.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'GERMANY', ['F BAL', 'F PRU'])
        self.set_units(game, 'RUSSIA', ['F LVN', 'F BOT', 'A FIN'])
        self.set_orders(game, 'GERMANY', ['F BAL - SWE', 'F PRU S F BAL'])
        self.set_orders(game, 'RUSSIA', ['F LVN - BAL', 'F BOT S F LVN - BAL', 'A FIN - SWE'])
        self.process(game)
        assert self.check_results(game, 'F BAL', BOUNCE)
        assert self.check_results(game, 'F BAL', DISLODGED)
        assert self.check_results(game, 'F PRU', VOID)
        assert self.check_results(game, 'F LVN', OK)
        assert self.check_results(game, 'F BOT', OK)
        assert self.check_results(game, 'A FIN', BOUNCE)
        assert check_dislodged(game, 'F BAL', 'F LVN')
        assert self.owner_name(game, 'F BAL') == 'RUSSIA'
        assert self.owner_name(game, 'F PRU') == 'GERMANY'
        assert self.owner_name(game, 'F LVN') is None
        assert self.owner_name(game, 'F BOT') == 'RUSSIA'
        assert self.owner_name(game, 'A FIN') == 'RUSSIA'
        assert self.owner_name(game, 'A SWE') is None

    def test_6_d_8(self):
        """ 6.D.8. TEST CASE, FAILED CONVOY CAN NOT RECEIVE HOLD SUPPORT
            If a convoy fails because of disruption of the convoy or when the right convoy orders are not given,
            then the army to be convoyed can not receive support in hold, since it still tried to move.
            Austria: F Ionian Sea Hold
            Austria: A Serbia Supports A Albania - Greece
            Austria: A Albania - Greece
            Turkey: A Greece - Naples
            Turkey: A Bulgaria Supports A Greece
            There was a possible convoy from Greece to Naples, before the orders were made public (via the Ionian Sea).
            This means that the order of Greece to Naples should never be treated as illegal order and be changed in a
            hold order able to receive hold support (see also issue VI.A). Therefore, the support in Bulgaria fails and
            the army in Greece is dislodged by the army in Albania.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'AUSTRIA', ['F ION', 'A SER', 'A ALB'])
        self.set_units(game, 'TURKEY', ['A GRE', 'A BUL'])
        self.set_orders(game, 'AUSTRIA', ['F ION H', 'A SER S A ALB - GRE', 'A ALB - GRE'])
        self.set_orders(game, 'TURKEY', ['A GRE - NAP', 'A BUL S A GRE'])
        self.process(game)
        assert self.check_results(game, 'F ION', OK)
        assert self.check_results(game, 'A SER', OK)
        assert self.check_results(game, 'A ALB', OK)
        assert self.check_results(game, 'A GRE', DISLODGED)
        assert self.check_results(game, 'A BUL', VOID)
        assert check_dislodged(game, 'A GRE', 'A ALB')
        assert self.owner_name(game, 'F ION') == 'AUSTRIA'
        assert self.owner_name(game, 'A SER') == 'AUSTRIA'
        assert self.owner_name(game, 'A ALB') is None
        assert self.owner_name(game, 'A GRE') == 'AUSTRIA'
        assert self.owner_name(game, 'A BUL') == 'TURKEY'

    def test_6_d_9(self):
        """ 6.D.9. TEST CASE, SUPPORT TO MOVE ON HOLDING UNIT NOT ALLOWED
            A unit that is holding can not receive a support in moving.
            Italy: A Venice - Trieste
            Italy: A Tyrolia Supports A Venice - Trieste
            Austria: A Albania Supports A Trieste - Serbia
            Austria: A Trieste Hold
            The support of the army in Albania fails and the army in Trieste is dislodged by the army from Venice.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ITALY', ['A VEN', 'A TYR'])
        self.set_units(game, 'AUSTRIA', ['A ALB', 'A TRI'])
        self.set_orders(game, 'ITALY', ['A VEN - TRI', 'A TYR S A VEN - TRI'])
        self.set_orders(game, 'AUSTRIA', ['A ALB S A TRI - SER', 'A TRI H'])
        self.process(game)
        assert self.check_results(game, 'A VEN', OK)
        assert self.check_results(game, 'A TYR', OK)
        assert self.check_results(game, 'A ALB', VOID)
        assert self.check_results(game, 'A TRI', DISLODGED)
        assert check_dislodged(game, 'A TRI', 'A VEN')
        assert self.owner_name(game, 'A VEN') is None
        assert self.owner_name(game, 'A TYR') == 'ITALY'
        assert self.owner_name(game, 'A ALB') == 'AUSTRIA'
        assert self.owner_name(game, 'A TRI') == 'ITALY'

    def test_6_d_10(self):
        """ 6.D.10. TEST CASE, SELF DISLODGMENT PROHIBITED
            A unit may not dislodge a unit of the same great power.
            Germany: A Berlin Hold
            Germany: F Kiel - Berlin
            Germany: A Munich Supports F Kiel - Berlin
            Move to Berlin fails.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'GERMANY', ['A BER', 'F KIE', 'A MUN'])
        self.set_orders(game, 'GERMANY', ['A BER H', 'F KIE - BER', 'A MUN S F KIE - BER'])
        self.process(game)
        assert self.check_results(game, 'A BER', OK)
        assert self.check_results(game, 'F KIE', BOUNCE)
        assert self.check_results(game, 'A MUN', VOID)
        assert self.owner_name(game, 'A BER') == 'GERMANY'
        assert self.owner_name(game, 'F KIE') == 'GERMANY'
        assert self.owner_name(game, 'A MUN') == 'GERMANY'

    def test_6_d_11(self):
        """ 6.D.11. TEST CASE, NO SELF DISLODGMENT OF RETURNING UNIT
            Idem.
            Germany: A Berlin - Prussia
            Germany: F Kiel - Berlin
            Germany: A Munich Supports F Kiel - Berlin
            Russia: A Warsaw - Prussia
            Army in Berlin bounces, but is not dislodged by own unit.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'GERMANY', ['A BER', 'F KIE', 'A MUN'])
        self.set_units(game, 'RUSSIA', 'A WAR')
        self.set_orders(game, 'GERMANY', ['A BER - PRU', 'F KIE - BER', 'A MUN S F KIE - BER'])
        self.set_orders(game, 'RUSSIA', ['A WAR - PRU'])
        self.process(game)
        assert self.check_results(game, 'A BER', BOUNCE)
        assert self.check_results(game, 'F KIE', BOUNCE)
        assert self.check_results(game, 'A MUN', VOID)
        assert self.check_results(game, 'A WAR', BOUNCE)
        assert self.owner_name(game, 'A BER') == 'GERMANY'
        assert self.owner_name(game, 'F KIE') == 'GERMANY'
        assert self.owner_name(game, 'A MUN') == 'GERMANY'
        assert self.owner_name(game, 'A WAR') == 'RUSSIA'

    def test_6_d_12(self):
        """ 6.D.12. TEST CASE, SUPPORTING A FOREIGN UNIT TO DISLODGE OWN UNIT PROHIBITED
            You may not help another power in dislodging your own unit.
            Austria: F Trieste Hold
            Austria: A Vienna Supports A Venice - Trieste
            Italy: A Venice - Trieste
            No dislodgment of fleet in Trieste.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'AUSTRIA', ['F TRI', 'A VIE'])
        self.set_units(game, 'ITALY', ['A VEN'])
        self.set_orders(game, 'AUSTRIA', ['F TRI H', 'A VIE S A VEN - TRI'])
        self.set_orders(game, 'ITALY', 'A VEN - TRI')
        self.process(game)
        assert self.check_results(game, 'F TRI', OK)
        assert self.check_results(game, 'A VIE', VOID)
        assert self.check_results(game, 'A VEN', BOUNCE)
        assert self.owner_name(game, 'F TRI') == 'AUSTRIA'
        assert self.owner_name(game, 'A VIE') == 'AUSTRIA'
        assert self.owner_name(game, 'A VEN') == 'ITALY'

    def test_6_d_13(self):
        """ 6.D.13. TEST CASE, SUPPORTING A FOREIGN UNIT TO DISLODGE A RETURNING OWN UNIT PROHIBITED
            Idem.
            Austria: F Trieste - Adriatic Sea
            Austria: A Vienna Supports A Venice - Trieste
            Italy: A Venice - Trieste
            Italy: F Apulia - Adriatic Sea
            No dislodgment of fleet in Trieste.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'AUSTRIA', ['F TRI', 'A VIE'])
        self.set_units(game, 'ITALY', ['A VEN', 'F APU'])
        self.set_orders(game, 'AUSTRIA', ['F TRI - ADR', 'A VIE S A VEN - TRI'])
        self.set_orders(game, 'ITALY', ['A VEN - TRI', 'F APU - ADR'])
        self.process(game)
        assert self.check_results(game, 'F TRI', BOUNCE)
        assert self.check_results(game, 'A VIE', VOID)
        assert self.check_results(game, 'A VEN', BOUNCE)
        assert self.check_results(game, 'F APU', BOUNCE)
        assert self.owner_name(game, 'F TRI') == 'AUSTRIA'
        assert self.owner_name(game, 'A VIE') == 'AUSTRIA'
        assert self.owner_name(game, 'A VEN') == 'ITALY'
        assert self.owner_name(game, 'F APU') == 'ITALY'

    def test_6_d_14(self):
        """  6.D.14. TEST CASE, SUPPORTING A FOREIGN UNIT IS NOT ENOUGH TO PREVENT DISLODGEMENT
            If a foreign unit has enough support to dislodge your unit, you may not prevent that dislodgement by
            supporting the attack.
            Austria: F Trieste Hold
            Austria: A Vienna Supports A Venice - Trieste
            Italy: A Venice - Trieste
            Italy: A Tyrolia Supports A Venice - Trieste
            Italy: F Adriatic Sea Supports A Venice - Trieste
            The fleet in Trieste is dislodged.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'AUSTRIA', ['F TRI', 'A VIE'])
        self.set_units(game, 'ITALY', ['A VEN', 'A TYR', 'F ADR'])
        self.set_orders(game, 'AUSTRIA', ['F TRI H', 'A VIE S A VEN - TRI'])
        self.set_orders(game, 'ITALY', ['A VEN - TRI', 'A TUR S A VEN - TRI', 'F ADR S A VEN - TRI'])
        self.process(game)
        assert self.check_results(game, 'F TRI', DISLODGED)
        assert self.check_results(game, 'A VIE', VOID)
        assert self.check_results(game, 'A VEN', OK)
        assert self.check_results(game, 'A TYR', OK)
        assert self.check_results(game, 'F ADR', OK)
        assert check_dislodged(game, 'F TRI', 'A VEN')
        assert self.owner_name(game, 'A TRI') == 'ITALY'
        assert self.owner_name(game, 'A VIE') == 'AUSTRIA'
        assert self.owner_name(game, 'A VEN') is None
        assert self.owner_name(game, 'A TYR') == 'ITALY'
        assert self.owner_name(game, 'F ADR') == 'ITALY'

    def test_6_d_15(self):
        """ 6.D.15. TEST CASE, DEFENDER CAN NOT CUT SUPPORT FOR ATTACK ON ITSELF
            A unit that is attacked by a supported unit can not prevent dislodgement by guessing which of the units
            will do the support.
            Russia: F Constantinople Supports F Black Sea - Ankara
            Russia: F Black Sea - Ankara
            Turkey: F Ankara - Constantinople
            The support of Constantinople is not cut and the fleet in Ankara is dislodged by the fleet in the Black Sea.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'RUSSIA', ['F CON', 'F BLA'])
        self.set_units(game, 'TURKEY', ['F ANK'])
        self.set_orders(game, 'RUSSIA', ['F CON S F BLA - ANK', 'F BLA - ANK'])
        self.set_orders(game, 'TURKEY', ['F ANK - CON'])
        self.process(game)
        assert self.check_results(game, 'F CON', OK)
        assert self.check_results(game, 'F BLA', OK)
        assert self.check_results(game, 'F ANK', BOUNCE)
        assert self.check_results(game, 'F ANK', DISLODGED)
        assert check_dislodged(game, 'F ANK', 'F BLA')
        assert self.owner_name(game, 'F CON') == 'RUSSIA'
        assert self.owner_name(game, 'F BLA') is None
        assert self.owner_name(game, 'F ANK') == 'RUSSIA'

    def test_6_d_16(self):
        """ 6.D.16. TEST CASE, CONVOYING A UNIT DISLODGING A UNIT OF SAME POWER IS ALLOWED
            It is allowed to convoy a foreign unit that dislodges your own unit is allowed.
            England: A London Hold
            England: F North Sea Convoys A Belgium - London
            France: F English Channel Supports A Belgium - London
            France: A Belgium - London
            The English army in London is dislodged by the French army coming from Belgium.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['A LON', 'F NTH'])
        self.set_units(game, 'FRANCE', ['F ENG', 'A BEL'])
        self.set_orders(game, 'ENGLAND', ['A LON H', 'F NTH C A BEL - LON'])
        self.set_orders(game, 'FRANCE', ['F ENG S A BEL - LON', 'A BEL - LON'])
        self.process(game)
        assert self.check_results(game, 'A LON', DISLODGED)
        assert self.check_results(game, 'F NTH', OK)
        assert self.check_results(game, 'F ENG', OK)
        assert self.check_results(game, 'A BEL', OK)
        assert check_dislodged(game, 'A LON', 'A BEL')
        assert self.owner_name(game, 'A LON') == 'FRANCE'
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'F ENG') == 'FRANCE'
        assert self.owner_name(game, 'A BEL') is None

    def test_6_d_17(self):
        """ 6.D.17. TEST CASE, DISLODGEMENT CUTS SUPPORTS
            The famous dislodge rule.
            Russia: F Constantinople Supports F Black Sea - Ankara
            Russia: F Black Sea - Ankara
            Turkey: F Ankara - Constantinople
            Turkey: A Smyrna Supports F Ankara - Constantinople
            Turkey: A Armenia - Ankara
            The Russian fleet in Constantinople is dislodged. This cuts the support to from Black Sea to Ankara.
            Black Sea will bounce with the army from Armenia.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'RUSSIA', ['F CON', 'F BLA'])
        self.set_units(game, 'TURKEY', ['F ANK', 'A SMY', 'A ARM'])
        self.set_orders(game, 'RUSSIA', ['F CON S F BLA - ANK', 'F BLA - ANK'])
        self.set_orders(game, 'TURKEY', ['F ANK - CON', 'A SMY S F ANK - CON', 'A ARM - ANK'])
        self.process(game)
        assert self.check_results(game, 'F CON', DISLODGED)
        assert self.check_results(game, 'F CON', CUT)
        assert self.check_results(game, 'F BLA', BOUNCE)
        assert self.check_results(game, 'F ANK', OK)
        assert self.check_results(game, 'A SMY', OK)
        assert self.check_results(game, 'A ARM', BOUNCE)
        assert check_dislodged(game, 'F CON', 'F ANK')
        assert self.owner_name(game, 'F CON') == 'TURKEY'
        assert self.owner_name(game, 'F BLA') == 'RUSSIA'
        assert self.owner_name(game, 'F ANK') is None
        assert self.owner_name(game, 'A SMY') == 'TURKEY'
        assert self.owner_name(game, 'A ARM') == 'TURKEY'

    def test_6_d_18(self):
        """ 6.D.18. TEST CASE, A SURVIVING UNIT WILL SUSTAIN SUPPORT
            Idem. But now with an additional hold that prevents dislodgement.
            Russia: F Constantinople Supports F Black Sea - Ankara
            Russia: F Black Sea - Ankara
            Russia: A Bulgaria Supports F Constantinople
            Turkey: F Ankara - Constantinople
            Turkey: A Smyrna Supports F Ankara - Constantinople
            Turkey: A Armenia - Ankara
            The Russian fleet in the Black Sea will dislodge the Turkish fleet in Ankara.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'RUSSIA', ['F CON', 'F BLA', 'A BUL'])
        self.set_units(game, 'TURKEY', ['F ANK', 'A SMY', 'A ARM'])
        self.set_orders(game, 'RUSSIA', ['F CON S F BLA - ANK', 'F BLA - ANK', 'A BUL S F CON'])
        self.set_orders(game, 'TURKEY', ['F ANK - CON', 'A SMY S F ANK - CON', 'A ARM - ANK'])
        self.process(game)
        assert self.check_results(game, 'F CON', OK)
        assert self.check_results(game, 'F BLA', OK)
        assert self.check_results(game, 'A BUL', OK)
        assert self.check_results(game, 'F ANK', DISLODGED)
        assert self.check_results(game, 'A SMY', OK)
        assert self.check_results(game, 'A ARM', BOUNCE)
        assert check_dislodged(game, 'F ANK', 'F BLA')
        assert self.owner_name(game, 'F CON') == 'RUSSIA'
        assert self.owner_name(game, 'F BLA') is None
        assert self.owner_name(game, 'A BUL') == 'RUSSIA'
        assert self.owner_name(game, 'F ANK') == 'RUSSIA'
        assert self.owner_name(game, 'A SMY') == 'TURKEY'
        assert self.owner_name(game, 'A ARM') == 'TURKEY'

    def test_6_d_19(self):
        """ 6.D.19. TEST CASE, EVEN WHEN SURVIVING IS IN ALTERNATIVE WAY
            Now, the dislodgement is prevented because the supports comes from a Russian army:
            Russia: F Constantinople Supports F Black Sea - Ankara
            Russia: F Black Sea - Ankara
            Russia: A Smyrna Supports F Ankara - Constantinople
            Turkey: F Ankara - Constantinople
            The Russian fleet in Constantinople is not dislodged, because one of the support is of Russian origin.
            The support from Black Sea to Ankara will sustain and the fleet in Ankara will be dislodged.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'RUSSIA', ['F CON', 'F BLA', 'A SMY'])
        self.set_units(game, 'TURKEY', ['F ANK'])
        self.set_orders(game, 'RUSSIA', ['F CON S F BLA - ANK', 'F BLA - ANK', 'A SMY S F ANK - CON'])
        self.set_orders(game, 'TURKEY', 'F ANK - CON')
        self.process(game)
        assert self.check_results(game, 'F CON', OK)
        assert self.check_results(game, 'F BLA', OK)
        assert self.check_results(game, 'A SMY', VOID)
        assert self.check_results(game, 'F ANK', DISLODGED)
        assert check_dislodged(game, 'F ANK', 'F BLA')
        assert self.owner_name(game, 'F CON') == 'RUSSIA'
        assert self.owner_name(game, 'F BLA') is None
        assert self.owner_name(game, 'A SMY') == 'RUSSIA'
        assert self.owner_name(game, 'F ANK') == 'RUSSIA'

    def test_6_d_20(self):
        """ 6.D.20. TEST CASE, UNIT CAN NOT CUT SUPPORT OF ITS OWN COUNTRY
            Although this is not mentioned in all rulebooks, it is generally accepted that when a unit attacks
            another unit of the same Great Power, it will not cut support.
            England: F London Supports F North Sea - English Channel
            England: F North Sea - English Channel
            England: A Yorkshire - London
            France: F English Channel Hold
            The army in York does not cut support. This means that the fleet in the English Channel is dislodged by the
            fleet in the North Sea.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F LON', 'F NTH', 'A YOR'])
        self.set_units(game, 'FRANCE', 'F ENG')
        self.set_orders(game, 'ENGLAND', ['F LON S F NTH - ENG', 'F NTH - ENG', 'A YOR - LON'])
        self.set_orders(game, 'FRANCE', 'F ENG H')
        self.process(game)
        assert self.check_results(game, 'F LON', OK)
        assert self.check_results(game, 'F NTH', OK)
        assert self.check_results(game, 'A YOR', BOUNCE)
        assert self.check_results(game, 'F ENG', DISLODGED)
        assert check_dislodged(game, 'F ENG', 'F NTH')
        assert self.owner_name(game, 'F LON') == 'ENGLAND'
        assert self.owner_name(game, 'F NTH') is None
        assert self.owner_name(game, 'A YOR') == 'ENGLAND'
        assert self.owner_name(game, 'F ENG') == 'ENGLAND'

    def test_6_d_21(self):
        """ 6.D.21. TEST CASE, DISLODGING DOES NOT CANCEL A SUPPORT CUT
            Sometimes there is the question whether a dislodged moving unit does not cut support (similar to the
            dislodge rule). This is not the case.
            Austria: F Trieste Hold
            Italy: A Venice - Trieste
            Italy: A Tyrolia Supports A Venice - Trieste
            Germany: A Munich - Tyrolia
            Russia: A Silesia - Munich
            Russia: A Berlin Supports A Silesia - Munich
            Although the German army is dislodged, it still cuts the Italian support. That means that the Austrian
            Fleet is not dislodged.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'AUSTRIA', ['F TRI'])
        self.set_units(game, 'ITALY', ['A VEN', 'A TYR'])
        self.set_units(game, 'GERMANY', 'A MUN')
        self.set_units(game, 'RUSSIA', ['A SIL', 'A BER'])
        self.set_orders(game, 'AUSTRIA', 'F TRI H')
        self.set_orders(game, 'ITALY', ['A VEN - TRI', 'A TYR S A VEN - TRI'])
        self.set_orders(game, 'GERMANY', 'A MUN - TYR')
        self.set_orders(game, 'RUSSIA', ['A SIL - MUN', 'A BER S A SIL - MUN'])
        self.process(game)
        assert self.check_results(game, 'F TRI', OK)
        assert self.check_results(game, 'A VEN', BOUNCE)
        assert self.check_results(game, 'A TYR', CUT)
        assert self.check_results(game, 'A MUN', DISLODGED)
        assert self.check_results(game, 'A SIL', OK)
        assert self.check_results(game, 'A BER', OK)
        assert check_dislodged(game, 'A MUN', 'A SIL')
        assert self.owner_name(game, 'F TRI') == 'AUSTRIA'
        assert self.owner_name(game, 'A VEN') == 'ITALY'
        assert self.owner_name(game, 'A TYR') == 'ITALY'
        assert self.owner_name(game, 'A MUN') == 'RUSSIA'
        assert self.owner_name(game, 'A SIL') is None
        assert self.owner_name(game, 'A BER') == 'RUSSIA'

    def test_6_d_22(self):
        """ 6.D.22. TEST CASE, IMPOSSIBLE FLEET MOVE CAN NOT BE SUPPORTED
            If a fleet tries moves to a land area it seems pointless to support the fleet, since the move will fail
            anyway. However, in such case, the support is also invalid for defense purposes.
            Germany: F Kiel - Munich
            Germany: A Burgundy Supports F Kiel - Munich
            Russia: A Munich - Kiel
            Russia: A Berlin Supports A Munich - Kiel
            The German move from Kiel to Munich is illegal (fleets can not go to Munich). Therefore, the support from
            Burgundy fails and the Russian army in Munich will dislodge the fleet in Kiel. Note that the failing of the
            support is not explicitly mentioned in the rulebooks (the DPTG is more clear about this point). If you take
            the rulebooks very literally, you might conclude that the fleet in Munich is not dislodged, but this is an
            incorrect interpretation.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'GERMANY', ['F KIE', 'A BUR'])
        self.set_units(game, 'RUSSIA', ['A MUN', 'A BER'])
        self.set_orders(game, 'GERMANY', ['F KIE - MUN', 'A BUR S F KIE - MUN'])
        self.set_orders(game, 'RUSSIA', ['A MUN - KIE', 'A BER S A MUN - KIE'])
        self.process(game)
        assert self.check_results(game, 'F KIE', VOID)
        assert self.check_results(game, 'F KIE', DISLODGED)
        assert self.check_results(game, 'A BUR', VOID)
        assert self.check_results(game, 'A MUN', OK)
        assert self.check_results(game, 'A BER', OK)
        assert check_dislodged(game, 'F KIE', 'A MUN')
        assert self.owner_name(game, 'A KIE') == 'RUSSIA'
        assert self.owner_name(game, 'A BUR') == 'GERMANY'
        assert self.owner_name(game, 'A MUN') is None
        assert self.owner_name(game, 'A BER') == 'RUSSIA'

    def test_6_d_23(self):
        """ 6.D.23. TEST CASE, IMPOSSIBLE COAST MOVE CAN NOT BE SUPPORTED
            Comparable with the previous test case, but now the fleet move is impossible for coastal reasons.
            Italy: F Gulf of Lyon - Spain(sc)
            Italy: F Western Mediterranean Supports F Gulf of Lyon - Spain(sc)
            France: F Spain(nc) - Gulf of Lyon
            France: F Marseilles Supports F Spain(nc) - Gulf of Lyon
            The French move from Spain North Coast to Gulf of Lyon is illegal (wrong coast). Therefore, the support
            from Marseilles fails and the fleet in Spain is dislodged.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ITALY', ['F LYO', 'F WES'])
        self.set_units(game, 'FRANCE', ['F SPA/NC', 'F MAR'])
        self.set_orders(game, 'ITALY', ['F LYO - SPA/SC', 'F WES S F LYO - SPA/SC'])
        self.set_orders(game, 'FRANCE', ['F SPA/NC - LYO', 'F MAR S F SPA/NC - LYO'])
        self.process(game)
        assert self.check_results(game, 'F LYO', OK)
        assert self.check_results(game, 'F WES', OK)
        assert self.check_results(game, 'F SPA/NC', VOID)
        assert self.check_results(game, 'F SPA/NC', DISLODGED)
        assert self.check_results(game, 'F MAR', VOID)
        assert check_dislodged(game, 'F SPA/NC', 'F LYO')
        assert self.owner_name(game, 'F LYO') is None
        assert self.owner_name(game, 'F WES') == 'ITALY'
        assert self.owner_name(game, 'F SPA/NC') is None
        assert self.owner_name(game, 'F SPA/SC') == 'ITALY'
        assert self.owner_name(game, 'F MAR') == 'FRANCE'

    def test_6_d_24(self):
        """ 6.D.24. TEST CASE, IMPOSSIBLE ARMY MOVE CAN NOT BE SUPPORTED
            Comparable with the previous test case, but now an army tries to move into sea and the support is used in a
            beleaguered garrison.
            France: A Marseilles - Gulf of Lyon
            France: F Spain(sc) Supports A Marseilles - Gulf of Lyon
            Italy: F Gulf of Lyon Hold
            Turkey: F Tyrrhenian Sea Supports F Western Mediterranean - Gulf of Lyon
            Turkey: F Western Mediterranean - Gulf of Lyon
            The French move from Marseilles to Gulf of Lyon is illegal (an army can not go to sea). Therefore,
            the support from Spain fails and there is no beleaguered garrison. The fleet in the Gulf of Lyon is
            dislodged by the Turkish fleet in the Western Mediterranean.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'FRANCE', ['A MAR', 'F SPA/SC'])
        self.set_units(game, 'ITALY', ['F LYO'])
        self.set_units(game, 'TURKEY', ['F TYS', 'F WES'])
        self.set_orders(game, 'FRANCE', ['A MAR - LYO', 'F SPA/SC S A MAR - LYO'])
        self.set_orders(game, 'ITALY', ['F LYO H'])
        self.set_orders(game, 'TURKEY', ['F TYS S F WES - LYO', 'F WES - LYO'])
        self.process(game)
        assert self.check_results(game, 'A MAR', VOID)
        assert self.check_results(game, 'F SPA/SC', VOID)
        assert self.check_results(game, 'F LYO', DISLODGED)
        assert self.check_results(game, 'F TYS', OK)
        assert self.check_results(game, 'F WES', OK)
        assert check_dislodged(game, 'F LYO', 'F WES')
        assert self.owner_name(game, 'A MAR') == 'FRANCE'
        assert self.owner_name(game, 'F SPA/SC') == 'FRANCE'
        assert self.owner_name(game, 'F LYO') == 'TURKEY'
        assert self.owner_name(game, 'F TYS') == 'TURKEY'
        assert self.owner_name(game, 'F WES') is None

    def test_6_d_25(self):
        """ 6.D.25. TEST CASE, FAILING HOLD SUPPORT CAN BE SUPPORTED
            If an adjudicator fails on one of the previous three test cases, then the bug should be removed with care.
            A failing move can not be supported, but a failing hold support, because of some preconditions (unmatching
            order) can still be supported.
            Germany: A Berlin Supports A Prussia
            Germany: F Kiel Supports A Berlin
            Russia: F Baltic Sea Supports A Prussia - Berlin
            Russia: A Prussia - Berlin
            Although the support of Berlin on Prussia fails (because of unmatching orders), the support of Kiel on
            Berlin is still valid. So, Berlin will not be dislodged.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'GERMANY', ['A BER', 'F KIE'])
        self.set_units(game, 'RUSSIA', ['F BAL', 'A PRU'])
        self.set_orders(game, 'GERMANY', ['A BER S A PRU', 'F KIE S A BER'])
        self.set_orders(game, 'RUSSIA', ['F BAL S A PRU - BER', 'A PRU - BER'])
        self.process(game)
        assert self.check_results(game, 'A BER', VOID)
        assert self.check_results(game, 'F KIE', OK)
        assert self.check_results(game, 'F BAL', OK)
        assert self.check_results(game, 'A PRU', BOUNCE)
        assert self.owner_name(game, 'A BER') == 'GERMANY'
        assert self.owner_name(game, 'F KIE') == 'GERMANY'
        assert self.owner_name(game, 'F BAL') == 'RUSSIA'
        assert self.owner_name(game, 'A PRU') == 'RUSSIA'

    def test_6_d_26(self):
        """ 6.D.26. TEST CASE, FAILING MOVE SUPPORT CAN BE SUPPORTED
            Similar as the previous test case, but now with an unmatched support to move.
            Germany: A Berlin Supports A Prussia - Silesia
            Germany: F Kiel Supports A Berlin
            Russia: F Baltic Sea Supports A Prussia - Berlin
            Russia: A Prussia - Berlin
            Again, Berlin will not be dislodged.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'GERMANY', ['A BER', 'F KIE'])
        self.set_units(game, 'RUSSIA', ['F BAL', 'A PRU'])
        self.set_orders(game, 'GERMANY', ['A BER S A PRU - SIL', 'F KIE S A BER'])
        self.set_orders(game, 'RUSSIA', ['F BAL S A PRU - BER', 'A PRU - BER'])
        self.process(game)
        assert self.check_results(game, 'A BER', VOID)
        assert self.check_results(game, 'F KIE', OK)
        assert self.check_results(game, 'F BAL', OK)
        assert self.check_results(game, 'A PRU', BOUNCE)
        assert self.owner_name(game, 'A BER') == 'GERMANY'
        assert self.owner_name(game, 'F KIE') == 'GERMANY'
        assert self.owner_name(game, 'F BAL') == 'RUSSIA'
        assert self.owner_name(game, 'A PRU') == 'RUSSIA'

    def test_6_d_27(self):
        """ 6.D.27. TEST CASE, FAILING CONVOY CAN BE SUPPORTED
            Similar as the previous test case, but now with an unmatched convoy.
            England: F Sweden - Baltic Sea
            England: F Denmark Supports F Sweden - Baltic Sea
            Germany: A Berlin Hold
            Russia: F Baltic Sea Convoys A Berlin - Livonia
            Russia: F Prussia Supports F Baltic Sea
            The convoy order in the Baltic Sea is unmatched and fails. However, the support of Prussia on the Baltic Sea
            is still valid and the fleet in the Baltic Sea is not dislodged.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F SWE', 'F DEN'])
        self.set_units(game, 'GERMANY', 'A BER')
        self.set_units(game, 'RUSSIA', ['F BAL', 'F PRU'])
        self.set_orders(game, 'ENGLAND', ['F SWE - BAL', 'F DEN S F SWE - BAL'])
        self.set_orders(game, 'GERMANY', 'A BER H')
        self.set_orders(game, 'RUSSIA', ['F BAL C A BER - LVN', 'F PRU S F BAL'])
        self.process(game)
        assert self.check_results(game, 'F SWE', BOUNCE)
        assert self.check_results(game, 'F DEN', OK)
        assert self.check_results(game, 'A BER', OK)
        assert self.check_results(game, 'F BAL', VOID)
        assert self.check_results(game, 'F PRU', OK)
        assert self.owner_name(game, 'F SWE') == 'ENGLAND'
        assert self.owner_name(game, 'F DEN') == 'ENGLAND'
        assert self.owner_name(game, 'A BER') == 'GERMANY'
        assert self.owner_name(game, 'F BAL') == 'RUSSIA'
        assert self.owner_name(game, 'F PRU') == 'RUSSIA'

    def test_6_d_28(self):
        """ 6.D.28. TEST CASE, IMPOSSIBLE MOVE AND SUPPORT
            If a move is impossible then it can be treated as "illegal", which makes a hold support possible.
            Austria: A Budapest Supports F Rumania
            Russia: F Rumania - Holland
            Turkey: F Black Sea - Rumania
            Turkey: A Bulgaria Supports F Black Sea - Rumania
            The move of the Russian fleet is impossible. But the question is, whether it is "illegal" (see issue 4.E.1).
            If the move is "illegal" it must be ignored and that makes the hold support of the army in Budapest valid
            and the fleet in Rumania will not be dislodged.
            I prefer that the move is "illegal", which means that the fleet in the Black Sea does not dislodge the
            supported Russian fleet.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'AUSTRIA', ['A BUD'])
        self.set_units(game, 'RUSSIA', 'F RUM')
        self.set_units(game, 'TURKEY', ['F BLA', 'A BUL'])
        self.set_orders(game, 'AUSTRIA', 'A BUD S F RUM')
        self.set_orders(game, 'RUSSIA', 'F RUM - HOL')
        self.set_orders(game, 'TURKEY', ['F BLA - RUM', 'A BUL S F BLA - RUM'])
        self.process(game)
        assert self.check_results(game, 'A BUD', OK)
        assert self.check_results(game, 'F RUM', VOID)
        assert self.check_results(game, 'F BLA', BOUNCE)
        assert self.check_results(game, 'A BUL', OK)
        assert self.owner_name(game, 'A BUD') == 'AUSTRIA'
        assert self.owner_name(game, 'F RUM') == 'RUSSIA'
        assert self.owner_name(game, 'F BLA') == 'TURKEY'
        assert self.owner_name(game, 'A BUL') == 'TURKEY'

    def test_6_d_29(self):
        """ 6.D.29. TEST CASE, MOVE TO IMPOSSIBLE COAST AND SUPPORT
            Similar to the previous test case, but now the move can be "illegal" because of the wrong coast.
            Austria: A Budapest Supports F Rumania
            Russia: F Rumania - Bulgaria(sc)
            Turkey: F Black Sea - Rumania
            Turkey: A Bulgaria Supports F Black Sea - Rumania
            Again the move of the Russian fleet is impossible. However, some people might correct the coast
            (see issue 4.B.3). If the coast is not corrected, again the question is whether it is "illegal" (see
            issue 4.E.1). If the move is "illegal" it must be ignored and that makes the hold support of the army in
            Budapest valid and the fleet in Rumania will not be dislodged.
            I prefer that unambiguous orders are not changed and that the move is "illegal". That means that the fleet
            in the Black Sea does not dislodge the supported Russian fleet.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'AUSTRIA', 'A BUD')
        self.set_units(game, 'RUSSIA', 'F RUM')
        self.set_units(game, 'TURKEY', ['F BLA', 'A BUL'])
        self.set_orders(game, 'AUSTRIA', 'A BUD S F RUM')
        self.set_orders(game, 'RUSSIA', 'F RUM - BUL/SC')
        self.set_orders(game, 'TURKEY', ['F BLA - RUM', 'A BUL S F BLA - RUM'])
        self.process(game)
        assert self.check_results(game, 'A BUD', OK)
        assert self.check_results(game, 'F RUM', VOID)
        assert self.check_results(game, 'F BLA', BOUNCE)
        assert self.check_results(game, 'A BUL', OK)
        assert self.owner_name(game, 'A BUD') == 'AUSTRIA'
        assert self.owner_name(game, 'F RUM') == 'RUSSIA'
        assert self.owner_name(game, 'F BLA') == 'TURKEY'
        assert self.owner_name(game, 'A BUL') == 'TURKEY'

    def test_6_d_30(self):
        """ 6.D.30. TEST CASE, MOVE WITHOUT COAST AND SUPPORT
            Similar to the previous test case, but now the move can be "illegal" because of missing coast.
            Italy: F Aegean Sea Supports F Constantinople
            Russia: F Constantinople - Bulgaria
            Turkey: F Black Sea - Constantinople
            Turkey: A Bulgaria Supports F Black Sea - Constantinople
            Again the order to the Russian fleet is with problems, because it does not specify the coast, while both
            coasts of Bulgaria are possible. If no default coast is taken (see issue 4.B.1), then also here it must be
            decided whether the order is "illegal" (see issue 4.E.1). If the move is "illegal" it must be ignored and
            that makes the hold support of the fleet in the Aegean Sea valid and the Russian fleet will not be
            dislodged. I don't like default coasts and I prefer that the move is "illegal". That means that the fleet
            in the Black Sea does not dislodge the supported Russian fleet.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ITALY', 'F AEG')
        self.set_units(game, 'RUSSIA', 'F CON')
        self.set_units(game, 'TURKEY', ['F BLA', 'A BUL'])
        self.set_orders(game, 'ITALY', ['F AEG S F CON'])
        self.set_orders(game, 'RUSSIA', ['F CON - BUL'])
        self.set_orders(game, 'TURKEY', ['F BLA - CON', 'A BUL S F BLA - CON'])
        self.process(game)
        assert self.check_results(game, 'F AEG', OK)
        assert self.check_results(game, 'F CON', VOID)
        assert self.check_results(game, 'F BLA', BOUNCE)
        assert self.check_results(game, 'A BUL', OK)
        assert self.owner_name(game, 'F AEG') == 'ITALY'
        assert self.owner_name(game, 'F CON') == 'RUSSIA'
        assert self.owner_name(game, 'F BLA') == 'TURKEY'
        assert self.owner_name(game, 'A BUL') == 'TURKEY'

    def test_6_d_31(self):
        """ 6.D.31. TEST CASE, A TRICKY IMPOSSIBLE SUPPORT
            A support order can be impossible for complex reasons.
            Austria: A Rumania - Armenia
            Turkey: F Black Sea Supports A Rumania - Armenia
            Although the army in Rumania can move to Armenia and the fleet in the Black Sea can also go to Armenia,
            the support is still not possible. The reason is that the only possible convoy is through the Black Sea and
            a fleet can not convoy and support at the same time.
            This is relevant for computer programs that show only the possible orders. In the list of possible orders,
            the support as given to the fleet in the Black Sea, should not be listed. Furthermore, if the fleet in the
            Black Sea gets a second order, then this may fail, because of double orders (although it can also be ruled
            differently, see issue 4.D.3). However, when the support order is considered "illegal" (see issue 4.E.1),
            then this impossible support must be ignored and the second order must be carried out.
            I prefer that impossible orders are "illegal" and ignored. If there would be a second order for the fleet
            in the Black Sea, that order should be carried out.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'AUSTRIA', 'A RUM')
        self.set_units(game, 'TURKEY', 'F BLA')
        self.set_orders(game, 'AUSTRIA', ['A RUM - ARM'])
        self.set_orders(game, 'TURKEY', ['F BLA S A RUM - ARM'])
        self.process(game)
        assert self.check_results(game, 'A RUM', NO_CONVOY)
        assert self.check_results(game, 'F BLA', VOID)
        assert self.owner_name(game, 'A RUM') == 'AUSTRIA'
        assert self.owner_name(game, 'F BLA') == 'TURKEY'

    def test_6_d_32(self):
        """ 6.D.32. TEST CASE, A MISSING FLEET
            The previous test cases contained an order that was impossible even when some other pieces on the board
            where changed. In this test case, the order is impossible, but only for that situation.
            England: F Edinburgh Supports A Liverpool - Yorkshire
            England: A Liverpool - Yorkshire
            France: F London Supports A Yorkshire
            Germany: A Yorkshire - Holland
            The German order to Yorkshire can not be executed, because there is no fleet in the North Sea. In other
            situations (where there is a fleet in the North Sea), the exact same order would be possible. It should be
            determined whether this is "illegal" (see issue 4.E.1) or not. If it is illegal, then the order should be
            ignored and the support of the French fleet in London succeeds. This means that the army in Yorkshire is
            not dislodged.
            I prefer that impossible orders, even if it is only impossible for the current situation, are "illegal" and
            ignored. The army in Yorkshire is not dislodged.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F EDI', 'A LVP'])
        self.set_units(game, 'FRANCE', 'F LON')
        self.set_units(game, 'GERMANY', 'A YOR')
        self.set_orders(game, 'ENGLAND', ['F EDI S A LVP - YOR', 'A LVP - YOR'])
        self.set_orders(game, 'FRANCE', ['F LON S A YOR'])
        self.set_orders(game, 'GERMANY', ['A YOR - HOL'])
        self.process(game)
        assert self.check_results(game, 'F EDI', OK)
        assert self.check_results(game, 'A LVP', BOUNCE)
        assert self.check_results(game, 'F LON', OK)
        assert self.check_results(game, 'A YOR', VOID)
        assert self.owner_name(game, 'F EDI') == 'ENGLAND'
        assert self.owner_name(game, 'A LVP') == 'ENGLAND'
        assert self.owner_name(game, 'F LON') == 'FRANCE'
        assert self.owner_name(game, 'A YOR') == 'GERMANY'

    def test_6_d_33(self):
        """ 6.D.33. TEST CASE, UNWANTED SUPPORT ALLOWED
            A self stand-off can be broken by an unwanted support.
            Austria: A Serbia - Budapest
            Austria: A Vienna - Budapest
            Russia: A Galicia Supports A Serbia - Budapest
            Turkey: A Bulgaria - Serbia
            Due to the Russian support, the army in Serbia advances to Budapest. This enables Turkey to capture
            Serbia with the army in Bulgaria.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'AUSTRIA', ['A SER', 'A VIE'])
        self.set_units(game, 'RUSSIA', 'A GAL')
        self.set_units(game, 'TURKEY', 'A BUL')
        self.set_orders(game, 'AUSTRIA', ['A SER - BUD', 'A VIE - BUD'])
        self.set_orders(game, 'RUSSIA', 'A GAL S A SER - BUD')
        self.set_orders(game, 'TURKEY', 'A BUL - SER')
        self.process(game)
        assert self.check_results(game, 'A SER', OK)
        assert self.check_results(game, 'A VIE', BOUNCE)
        assert self.check_results(game, 'A GAL', OK)
        assert self.check_results(game, 'A BUL', OK)
        assert self.owner_name(game, 'A SER') == 'TURKEY'
        assert self.owner_name(game, 'A VIE') == 'AUSTRIA'
        assert self.owner_name(game, 'A GAL') == 'RUSSIA'
        assert self.owner_name(game, 'A BUL') is None
        assert self.owner_name(game, 'A BUD') == 'AUSTRIA'

    def test_6_d_34(self):
        """ 6.D.34. TEST CASE, SUPPORT TARGETING OWN AREA NOT ALLOWED
            Support targeting the area where the supporting unit is standing, is illegal.
            Germany: A Berlin - Prussia
            Germany: A Silesia Supports A Berlin - Prussia
            Germany: F Baltic Sea Supports A Berlin - Prussia
            Italy: A Prussia Supports Livonia - Prussia
            Russia: A Warsaw Supports A Livonia - Prussia
            Russia: A Livonia - Prussia
            Russia and Italy wanted to get rid of the Italian army in Prussia (to build an Italian fleet somewhere
            else). However, they didn't want a possible German attack on Prussia to succeed. They invented this odd
            order of Italy. It was intended that the attack of the army in Livonia would have strength three, so it
            would be capable to prevent the possible German attack to succeed. However, the order of Italy is illegal,
            because a unit may only support to an area where the unit can go by itself. A unit can't go to the area it
            is already standing, so the Italian order is illegal and the German move from Berlin succeeds. Even if it
            would be legal, the German move from Berlin would still succeed, because the support of Prussia is cut by
            Livonia and Berlin.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'GERMANY', ['A BER', 'A SIL', 'F BAL'])
        self.set_units(game, 'ITALY', 'A PRU')
        self.set_units(game, 'RUSSIA', ['A WAR', 'A LVN'])
        self.set_orders(game, 'GERMANY', ['A BER - PRU', 'A SIL S A BER - PRU', 'F BAL S A BER - PRU'])
        self.set_orders(game, 'ITALY', ['A PRU S LVN - PRU'])
        self.set_orders(game, 'RUSSIA', ['A WAR S A LVN - PRU', 'A LVN - PRU'])
        self.process(game)
        assert self.check_results(game, 'A BER', OK)
        assert self.check_results(game, 'A SIL', OK)
        assert self.check_results(game, 'F BAL', OK)
        assert self.check_results(game, 'A PRU', VOID)
        assert self.check_results(game, 'A PRU', DISLODGED)
        assert self.check_results(game, 'A WAR', OK)
        assert self.check_results(game, 'A LVN', BOUNCE)
        assert check_dislodged(game, 'A PRU', 'A BER')
        assert self.owner_name(game, 'A BER') is None
        assert self.owner_name(game, 'A SIL') == 'GERMANY'
        assert self.owner_name(game, 'F BAL') == 'GERMANY'
        assert self.owner_name(game, 'A PRU') == 'GERMANY'
        assert self.owner_name(game, 'A WAR') == 'RUSSIA'
        assert self.owner_name(game, 'A LVN') == 'RUSSIA'

    # 6.E. TEST CASES, HEAD TO HEAD BATTLES AND BELEAGUERED GARRISON
    def test_6_e_1(self):
        """ 6.E.1. TEST CASE, DISLODGED UNIT HAS NO EFFECT ON ATTACKERS AREA
            An army can follow.
            Germany: A Berlin - Prussia
            Germany: F Kiel - Berlin
            Germany: A Silesia Supports A Berlin - Prussia
            Russia: A Prussia - Berlin
            The army in Kiel will move to Berlin.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'GERMANY', ['A BER', 'F KIE', 'A SIL'])
        self.set_units(game, 'RUSSIA', 'A PRU')
        self.set_orders(game, 'GERMANY', ['A BER - PRU', 'F KIE - BER', 'A SIL S A BER - PRU'])
        self.set_orders(game, 'RUSSIA', 'A PRU - BER')
        self.process(game)
        assert self.check_results(game, 'A BER', OK)
        assert self.check_results(game, 'F KIE', OK)
        assert self.check_results(game, 'A SIL', OK)
        assert self.check_results(game, 'A PRU', DISLODGED)
        assert self.check_results(game, 'A PRU', BOUNCE)
        assert check_dislodged(game, 'A PRU', 'A BER')
        assert self.owner_name(game, 'F BER') == 'GERMANY'
        assert self.owner_name(game, 'F KIE') is None
        assert self.owner_name(game, 'A SIL') == 'GERMANY'
        assert self.owner_name(game, 'A PRU') == 'GERMANY'

    def test_6_e_2(self):
        """ 6.E.2. TEST CASE, NO SELF DISLODGEMENT IN HEAD TO HEAD BATTLE
            Self dislodgement is not allowed. This also counts for head to head battles.
            Germany: A Berlin - Kiel
            Germany: F Kiel - Berlin
            Germany: A Munich Supports A Berlin - Kiel
            No unit will move.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'GERMANY', ['A BER', 'F KIE', 'A MUN'])
        self.set_orders(game, 'GERMANY', ['A BER - KIE', 'F KIE - BER', 'A MUN S A BER - KIE'])
        self.process(game)
        assert self.check_results(game, 'A BER', BOUNCE)
        assert self.check_results(game, 'F KIE', BOUNCE)
        assert self.check_results(game, 'A MUN', VOID)
        assert self.owner_name(game, 'A BER') == 'GERMANY'
        assert self.owner_name(game, 'F KIE') == 'GERMANY'
        assert self.owner_name(game, 'A MUN') == 'GERMANY'

    def test_6_e_3(self):
        """ 6.E.3. TEST CASE, NO HELP IN DISLODGING OWN UNIT
            To help a foreign power to dislodge own unit in head to head battle is not possible.
            Germany: A Berlin - Kiel
            Germany: A Munich Supports F Kiel - Berlin
            England: F Kiel - Berlin
            No unit will move.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'GERMANY', ['A BER', 'A MUN'])
        self.set_units(game, 'ENGLAND', 'F KIE')
        self.set_orders(game, 'GERMANY', ['A BER - KIE', 'A MUN S F KIE - BER'])
        self.set_orders(game, 'ENGLAND', 'F KIE - BER')
        self.process(game)
        assert self.check_results(game, 'A BER', BOUNCE)
        assert self.check_results(game, 'A MUN', VOID)
        assert self.check_results(game, 'F KIE', BOUNCE)
        assert self.owner_name(game, 'A BER') == 'GERMANY'
        assert self.owner_name(game, 'A MUN') == 'GERMANY'
        assert self.owner_name(game, 'F KIE') == 'ENGLAND'

    def test_6_e_4(self):
        """ 6.E.4. TEST CASE, NON-DISLODGED LOSER HAS STILL EFFECT
            If in an unbalanced head to head battle the loser is not dislodged, it has still effect on the area of
            the attacker.
            Germany: F Holland - North Sea
            Germany: F Helgoland Bight Supports F Holland - North Sea
            Germany: F Skagerrak Supports F Holland - North Sea
            France: F North Sea - Holland
            France: F Belgium Supports F North Sea - Holland
            England: F Edinburgh Supports F Norwegian Sea - North Sea
            England: F Yorkshire Supports F Norwegian Sea - North Sea
            England: F Norwegian Sea - North Sea
            Austria: A Kiel Supports A Ruhr - Holland
            Austria: A Ruhr - Holland
            The French fleet in the North Sea is not dislodged due to the beleaguered garrison. Therefore,
            the Austrian army in Ruhr will not move to Holland.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'GERMANY', ['F HOL', 'F HEL', 'F SKA'])
        self.set_units(game, 'FRANCE', ['F NTH', 'F BEL'])
        self.set_units(game, 'ENGLAND', ['F EDI', 'F YOR', 'F NWG'])
        self.set_units(game, 'AUSTRIA', ['A KIE', 'A RUH'])
        self.set_orders(game, 'GERMANY', ['F HOL - NTH', 'F HEL S F HOL - NTH', 'F SKA S F HOL - NTH'])
        self.set_orders(game, 'FRANCE', ['F NTH - HOL', 'F BEL S F NTH - HOL'])
        self.set_orders(game, 'ENGLAND', ['F EDI S F NWG - NTH', 'F YOR S F NWG - NTH', 'F NWG - NTH'])
        self.set_orders(game, 'AUSTRIA', ['A KIE S A RUH - HOL', 'A RUH - HOL'])
        self.process(game)
        assert self.check_results(game, 'F HOL', BOUNCE)
        assert self.check_results(game, 'F HEL', OK)
        assert self.check_results(game, 'F SKA', OK)
        assert self.check_results(game, 'F NTH', BOUNCE)
        assert self.check_results(game, 'F BEL', OK)
        assert self.check_results(game, 'F EDI', OK)
        assert self.check_results(game, 'F YOR', OK)
        assert self.check_results(game, 'F NWG', BOUNCE)
        assert self.check_results(game, 'A KIE', OK)
        assert self.check_results(game, 'A RUH', BOUNCE)
        assert self.owner_name(game, 'F HOL') == 'GERMANY'
        assert self.owner_name(game, 'F HEL') == 'GERMANY'
        assert self.owner_name(game, 'F SKA') == 'GERMANY'
        assert self.owner_name(game, 'F NTH') == 'FRANCE'
        assert self.owner_name(game, 'F BEL') == 'FRANCE'
        assert self.owner_name(game, 'F EDI') == 'ENGLAND'
        assert self.owner_name(game, 'F YOR') == 'ENGLAND'
        assert self.owner_name(game, 'F NWG') == 'ENGLAND'
        assert self.owner_name(game, 'A KIE') == 'AUSTRIA'
        assert self.owner_name(game, 'A RUH') == 'AUSTRIA'

    def test_6_e_5(self):
        """ 6.E.5. TEST CASE, LOSER DISLODGED BY ANOTHER ARMY HAS STILL EFFECT
            If in an unbalanced head to head battle the loser is dislodged by a unit not part of the head to head
            battle, the loser has still effect on the place of the winner of the head to head battle.
            Germany: F Holland - North Sea
            Germany: F Helgoland Bight Supports F Holland - North Sea
            Germany: F Skagerrak Supports F Holland - North Sea
            France: F North Sea - Holland
            France: F Belgium Supports F North Sea - Holland
            England: F Edinburgh Supports F Norwegian Sea - North Sea
            England: F Yorkshire Supports F Norwegian Sea - North Sea
            England: F Norwegian Sea - North Sea
            England: F London Supports F Norwegian Sea - North Sea
            Austria: A Kiel Supports A Ruhr - Holland
            Austria: A Ruhr - Holland
            The French fleet in the North Sea is dislodged but not by the German fleet in Holland. Therefore,
            the French fleet can still prevent that the Austrian army in Ruhr will move to Holland. So, the Austrian
            move in Ruhr fails and the German fleet in Holland is not dislodged.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'GERMANY', ['F HOL', 'F HEL', 'F SKA'])
        self.set_units(game, 'FRANCE', ['F NTH', 'F BEL'])
        self.set_units(game, 'ENGLAND', ['F EDI', 'F YOR', 'F NWG', 'F LON'])
        self.set_units(game, 'AUSTRIA', ['A KIE', 'A RUH'])
        self.set_orders(game, 'GERMANY', ['F HOL - NTH', 'F HEL S F HOL - NTH', 'F SKA S F HOL - NTH'])
        self.set_orders(game, 'FRANCE', ['F NTH - HOL', 'F BEL S F NTH - HOL'])
        self.set_orders(game, 'ENGLAND', ['F EDI S F NWG - NTH', 'F YOR S F NWG - NTH', 'F NWG - NTH',
                                          'F LON S F NWG - NTH'])
        self.set_orders(game, 'AUSTRIA', ['A KIE S A RUH - HOL', 'A RUH - HOL'])
        self.process(game)
        assert self.check_results(game, 'F HOL', BOUNCE)
        assert self.check_results(game, 'F HEL', OK)
        assert self.check_results(game, 'F SKA', OK)
        assert self.check_results(game, 'F NTH', DISLODGED)
        assert self.check_results(game, 'F NTH', BOUNCE)
        assert self.check_results(game, 'F BEL', OK)
        assert self.check_results(game, 'F EDI', OK)
        assert self.check_results(game, 'F YOR', OK)
        assert self.check_results(game, 'F NWG', OK)
        assert self.check_results(game, 'F LON', OK)
        assert self.check_results(game, 'A KIE', OK)
        assert self.check_results(game, 'A RUH', BOUNCE)
        assert check_dislodged(game, 'F NTH', 'F NWG')
        assert self.owner_name(game, 'F HOL') == 'GERMANY'
        assert self.owner_name(game, 'F HEL') == 'GERMANY'
        assert self.owner_name(game, 'F SKA') == 'GERMANY'
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'F BEL') == 'FRANCE'
        assert self.owner_name(game, 'F EDI') == 'ENGLAND'
        assert self.owner_name(game, 'F YOR') == 'ENGLAND'
        assert self.owner_name(game, 'F NWG') is None
        assert self.owner_name(game, 'F LON') == 'ENGLAND'
        assert self.owner_name(game, 'A KIE') == 'AUSTRIA'
        assert self.owner_name(game, 'A RUH') == 'AUSTRIA'

    def test_6_e_6(self):
        """ 6.E.6. TEST CASE, NOT DISLODGE BECAUSE OF OWN SUPPORT HAS STILL EFFECT
            If in an unbalanced head to head battle the loser is not dislodged because the winner had help of a unit
            of the loser, the loser has still effect on the area of the winner.
            Germany: F Holland - North Sea
            Germany: F Helgoland Bight Supports F Holland - North Sea
            France: F North Sea - Holland
            France: F Belgium Supports F North Sea - Holland
            France: F English Channel Supports F Holland - North Sea
            Austria: A Kiel Supports A Ruhr - Holland
            Austria: A Ruhr - Holland
            Although the German force from Holland to North Sea is one larger than the French force from North Sea
            to Holland,
            the French fleet in the North Sea is not dislodged, because one of the supports on the German movement is
            French.
            Therefore, the Austrian army in Ruhr will not move to Holland.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'GERMANY', ['F HOL', 'F HEL'])
        self.set_units(game, 'FRANCE', ['F NTH', 'F BEL', 'F ENG'])
        self.set_units(game, 'AUSTRIA', ['A KIE', 'A RUH'])
        self.set_orders(game, 'GERMANY', ['F HOL - NTH', 'F HEL S F HOL - NTH'])
        self.set_orders(game, 'FRANCE', ['F NTH - HOL', 'F BEL S F NTH - HOL', 'F ENG S F HOL - NTH'])
        self.set_orders(game, 'AUSTRIA', ['A KIE S A RUH - HOL', 'A RUH - HOL'])
        self.process(game)
        assert self.check_results(game, 'F HOL', BOUNCE)
        assert self.check_results(game, 'F HEL', OK)
        assert self.check_results(game, 'F NTH', BOUNCE)
        assert self.check_results(game, 'F BEL', OK)
        assert self.check_results(game, 'F ENG', VOID)
        assert self.check_results(game, 'A KIE', OK)
        assert self.check_results(game, 'A RUH', BOUNCE)
        assert self.owner_name(game, 'F HOL') == 'GERMANY'
        assert self.owner_name(game, 'F HEL') == 'GERMANY'
        assert self.owner_name(game, 'F NTH') == 'FRANCE'
        assert self.owner_name(game, 'F BEL') == 'FRANCE'
        assert self.owner_name(game, 'F ENG') == 'FRANCE'
        assert self.owner_name(game, 'A KIE') == 'AUSTRIA'
        assert self.owner_name(game, 'A RUH') == 'AUSTRIA'

    def test_6_e_7(self):
        """ 6.E.7. TEST CASE, NO SELF DISLODGEMENT WITH BELEAGUERED GARRISON
            An attempt to self dislodgement can be combined with a beleaguered garrison. Such self dislodgment is still
            not possible.
            England: F North Sea Hold
            England: F Yorkshire Supports F Norway - North Sea
            Germany: F Holland Supports F Helgoland Bight - North Sea
            Germany: F Helgoland Bight - North Sea
            Russia: F Skagerrak Supports F Norway - North Sea
            Russia: F Norway - North Sea
            Although the Russians beat the German attack (with the support of Yorkshire) and the two Russian fleets
            are enough to dislodge the fleet in the North Sea, the fleet in the North Sea is not dislodged, since it
            would not be dislodged if the English fleet in Yorkshire would not give support. According to the DPTG the
            fleet in the North Sea would be dislodged. The DPTG is incorrect in this case.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F NTH', 'F YOR'])
        self.set_units(game, 'GERMANY', ['F HOL', 'F HEL'])
        self.set_units(game, 'RUSSIA', ['F SKA', 'F NWY'])
        self.set_orders(game, 'ENGLAND', ['F NTH H', 'F YOR S F NWY - NTH'])
        self.set_orders(game, 'GERMANY', ['F HOL S F HEL - NTH', 'F HEL - NTH'])
        self.set_orders(game, 'RUSSIA', ['F SKA S F NWY - NTH', 'F NWY - NTH'])
        self.process(game)
        assert self.check_results(game, 'F NTH', OK)
        assert self.check_results(game, 'F YOR', VOID)
        assert self.check_results(game, 'F HOL', OK)
        assert self.check_results(game, 'F HEL', BOUNCE)
        assert self.check_results(game, 'F SKA', OK)
        assert self.check_results(game, 'F NWY', BOUNCE)
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'F YOR') == 'ENGLAND'
        assert self.owner_name(game, 'F HOL') == 'GERMANY'
        assert self.owner_name(game, 'F HEL') == 'GERMANY'
        assert self.owner_name(game, 'F SKA') == 'RUSSIA'
        assert self.owner_name(game, 'F NWY') == 'RUSSIA'

    def test_6_e_8(self):
        """ 6.E.8. TEST CASE, NO SELF DISLODGEMENT WITH BELEAGUERED GARRISON AND HEAD TO HEAD BATTLE
            Similar to the previous test case, but now the beleaguered fleet is also engaged in a head to head battle.
            England: F North Sea - Norway
            England: F Yorkshire Supports F Norway - North Sea
            Germany: F Holland Supports F Helgoland Bight - North Sea
            Germany: F Helgoland Bight - North Sea
            Russia: F Skagerrak Supports F Norway - North Sea
            Russia: F Norway - North Sea
            Again, none of the fleets move.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F NTH', 'F YOR'])
        self.set_units(game, 'GERMANY', ['F HOL', 'F HEL'])
        self.set_units(game, 'RUSSIA', ['F SKA', 'F NWY'])
        self.set_orders(game, 'ENGLAND', ['F NTH - NWY', 'F YOR S F NWY - NTH'])
        self.set_orders(game, 'GERMANY', ['F HOL S F HEL - NTH', 'F HEL - NTH'])
        self.set_orders(game, 'RUSSIA', ['F SKA S F NWY - NTH', 'F NWY - NTH'])
        self.process(game)
        assert self.check_results(game, 'F NTH', BOUNCE)
        assert self.check_results(game, 'F YOR', VOID)
        assert self.check_results(game, 'F HOL', OK)
        assert self.check_results(game, 'F HEL', BOUNCE)
        assert self.check_results(game, 'F SKA', OK)
        assert self.check_results(game, 'F NWY', BOUNCE)
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'F YOR') == 'ENGLAND'
        assert self.owner_name(game, 'F HOL') == 'GERMANY'
        assert self.owner_name(game, 'F HEL') == 'GERMANY'
        assert self.owner_name(game, 'F SKA') == 'RUSSIA'
        assert self.owner_name(game, 'F NWY') == 'RUSSIA'

    def test_6_e_9(self):
        """ 6.E.9. TEST CASE, ALMOST SELF DISLODGEMENT WITH BELEAGUERED GARRISON
            Similar to the previous test case, but now the beleaguered fleet is moving away.
            England: F North Sea - Norwegian Sea
            England: F Yorkshire Supports F Norway - North Sea
            Germany: F Holland Supports F Helgoland Bight - North Sea
            Germany: F Helgoland Bight - North Sea
            Russia: F Skagerrak Supports F Norway - North Sea
            Russia: F Norway - North Sea
            Both the fleet in the North Sea and the fleet in Norway move.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F NTH', 'F YOR'])
        self.set_units(game, 'GERMANY', ['F HOL', 'F HEL'])
        self.set_units(game, 'RUSSIA', ['F SKA', 'F NWY'])
        self.set_orders(game, 'ENGLAND', ['F NTH - NWG', 'F YOR S F NWY - NTH'])
        self.set_orders(game, 'GERMANY', ['F HOL S F HEL - NTH', 'F HEL - NTH'])
        self.set_orders(game, 'RUSSIA', ['F SKA S F NWY - NTH', 'F NWY - NTH'])
        self.process(game)
        assert self.check_results(game, 'F NTH', OK)
        assert self.check_results(game, 'F YOR', OK)
        assert self.check_results(game, 'F HOL', OK)
        assert self.check_results(game, 'F HEL', BOUNCE)
        assert self.check_results(game, 'F SKA', OK)
        assert self.check_results(game, 'F NWY', OK)
        assert self.owner_name(game, 'F NTH') == 'RUSSIA'
        assert self.owner_name(game, 'F YOR') == 'ENGLAND'
        assert self.owner_name(game, 'F HOL') == 'GERMANY'
        assert self.owner_name(game, 'F HEL') == 'GERMANY'
        assert self.owner_name(game, 'F SKA') == 'RUSSIA'
        assert self.owner_name(game, 'F NWY') is None
        assert self.owner_name(game, 'F NWG') == 'ENGLAND'

    def test_6_e_10(self):
        """ 6.E.10. TEST CASE, ALMOST CIRCULAR MOVEMENT WITH NO SELF DISLODGEMENT WITH BELEAGUERED GARRISON
            Similar to the previous test case, but now the beleaguered fleet is in circular movement with the weaker
            attacker. So, the circular movement fails.
            England: F North Sea - Denmark
            England: F Yorkshire Supports F Norway - North Sea
            Germany: F Holland Supports F Helgoland Bight - North Sea
            Germany: F Helgoland Bight - North Sea
            Germany: F Denmark - Helgoland Bight
            Russia: F Skagerrak Supports F Norway - North Sea
            Russia: F Norway - North Sea
            There is no movement of fleets.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F NTH', 'F YOR'])
        self.set_units(game, 'GERMANY', ['F HOL', 'F HEL', 'F DEN'])
        self.set_units(game, 'RUSSIA', ['F SKA', 'F NWY'])
        self.set_orders(game, 'ENGLAND', ['F NTH - DEN', 'F YOR S F NWY - NTH'])
        self.set_orders(game, 'GERMANY', ['F HOL S F HEL - NTH', 'F HEL - NTH', 'F DEN - HEL'])
        self.set_orders(game, 'RUSSIA', ['F SKA S F NWY - NTH', 'F NWY - NTH'])
        self.process(game)
        assert self.check_results(game, 'F NTH', BOUNCE)
        assert self.check_results(game, 'F YOR', VOID)
        assert self.check_results(game, 'F HOL', OK)
        assert self.check_results(game, 'F HEL', BOUNCE)
        assert self.check_results(game, 'F DEN', BOUNCE)
        assert self.check_results(game, 'F SKA', OK)
        assert self.check_results(game, 'F NWY', BOUNCE)
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'F YOR') == 'ENGLAND'
        assert self.owner_name(game, 'F HOL') == 'GERMANY'
        assert self.owner_name(game, 'F HEL') == 'GERMANY'
        assert self.owner_name(game, 'F DEN') == 'GERMANY'
        assert self.owner_name(game, 'F SKA') == 'RUSSIA'
        assert self.owner_name(game, 'F NWY') == 'RUSSIA'

    def test_6_e_11(self):
        """ 6.E.11. TEST CASE, NO SELF DISLODGEMENT WITH BELEAGUERED GARRISON, UNIT SWAP WITH ADJACENT CONVOYING AND
            TWO COASTS
            Similar to the previous test case, but now the beleaguered fleet is in a unit swap with the stronger
            attacker. So, the unit swap succeeds. To make the situation more complex, the swap is on an area with
            two coasts.
            France: A Spain - Portugal via Convoy
            France: F Mid-Atlantic Ocean Convoys A Spain - Portugal
            France: F Gulf of Lyon Supports F Portugal - Spain(nc)
            Germany: A Marseilles Supports A Gascony - Spain
            Germany: A Gascony - Spain
            Italy: F Portugal - Spain(nc)
            Italy: F Western Mediterranean Supports F Portugal - Spain(nc)
            The unit swap succeeds. Note that due to the success of the swap, there is no beleaguered garrison anymore.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'FRANCE', ['A SPA', 'F MAO', 'F LYO'])
        self.set_units(game, 'GERMANY', ['A MAR', 'A GAS'])
        self.set_units(game, 'ITALY', ['F POR', 'F WES'])
        self.set_orders(game, 'FRANCE', ['A SPA - POR VIA', 'F MAO C A SPA - POR', 'F LYO S F POR - SPA/NC'])
        self.set_orders(game, 'GERMANY', ['A MAR S A GAS - SPA', 'A GAS - SPA'])
        self.set_orders(game, 'ITALY', ['F POR - SPA/NC', 'F WES S F POR - SPA/NC'])
        self.process(game)
        assert self.check_results(game, 'A SPA', OK)
        assert self.check_results(game, 'F MAO', OK)
        assert self.check_results(game, 'F LYO', OK)
        assert self.check_results(game, 'A MAR', OK)
        assert self.check_results(game, 'A GAS', BOUNCE)
        assert self.check_results(game, 'F POR', OK)
        assert self.check_results(game, 'F WES', OK)
        assert self.owner_name(game, 'F SPA') == 'ITALY'
        assert self.owner_name(game, 'F SPA/NC') == 'ITALY'
        assert self.owner_name(game, 'F SPA/SC') is None
        assert self.owner_name(game, 'F MAO') == 'FRANCE'
        assert self.owner_name(game, 'F LYO') == 'FRANCE'
        assert self.owner_name(game, 'A MAR') == 'GERMANY'
        assert self.owner_name(game, 'A GAS') == 'GERMANY'
        assert self.owner_name(game, 'A POR') == 'FRANCE'
        assert self.owner_name(game, 'F WES') == 'ITALY'

    def test_6_e_12(self):
        """ 6.E.12. TEST CASE, SUPPORT ON ATTACK ON OWN UNIT CAN BE USED FOR OTHER MEANS
            A support on an attack on your own unit has still effect. It can prevent that another army will dislodge
            the unit.
            Austria: A Budapest - Rumania
            Austria: A Serbia Supports A Vienna - Budapest
            Italy: A Vienna - Budapest
            Russia: A Galicia - Budapest
            Russia: A Rumania Supports A Galicia - Budapest
            The support of Serbia on the Italian army prevents that the Russian army in Galicia will advance.
            No army will move.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'AUSTRIA', ['A BUD', 'A SER'])
        self.set_units(game, 'ITALY', ['A VIE'])
        self.set_units(game, 'RUSSIA', ['A GAL', 'A RUM'])
        self.set_orders(game, 'AUSTRIA', ['A BUD - RUM', 'A SER S A VIE - BUD'])
        self.set_orders(game, 'ITALY', 'A VIE - BUD')
        self.set_orders(game, 'RUSSIA', ['A GAL - BUD', 'A RUM S A GAL - BUD'])
        self.process(game)
        assert self.check_results(game, 'A BUD', BOUNCE)
        assert self.check_results(game, 'A SER', OK)
        assert self.check_results(game, 'A VIE', BOUNCE)
        assert self.check_results(game, 'A GAL', BOUNCE)
        assert self.check_results(game, 'A RUM', OK)
        assert self.owner_name(game, 'A BUD') == 'AUSTRIA'
        assert self.owner_name(game, 'A SER') == 'AUSTRIA'
        assert self.owner_name(game, 'A VIE') == 'ITALY'
        assert self.owner_name(game, 'A GAL') == 'RUSSIA'
        assert self.owner_name(game, 'A RUM') == 'RUSSIA'

    def test_6_e_13(self):
        """ 6.E.13. TEST CASE, THREE WAY BELEAGUERED GARRISON
            In a beleaguered garrison from three sides, the adjudicator may not let two attacks fail and then let the
            third succeed.
            England: F Edinburgh Supports F Yorkshire - North Sea
            England: F Yorkshire - North Sea
            France: F Belgium - North Sea
            France: F English Channel Supports F Belgium - North Sea
            Germany: F North Sea Hold
            Russia: F Norwegian Sea - North Sea
            Russia: F Norway Supports F Norwegian Sea - North Sea
            None of the fleets move. The German fleet in the North Sea is not dislodged.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F EDI', 'F YOR'])
        self.set_units(game, 'FRANCE', ['F BEL', 'F ENG'])
        self.set_units(game, 'GERMANY', 'F NTH')
        self.set_units(game, 'RUSSIA', ['F NWG', 'F NWY'])
        self.set_orders(game, 'ENGLAND', ['F EDI S F YOR - NTH', 'F YOR - NTH'])
        self.set_orders(game, 'FRANCE', ['F BEL - NTH', 'F ENG S F BEL - NTH'])
        self.set_orders(game, 'GERMANY', 'F NTH H')
        self.set_orders(game, 'RUSSIA', ['F NWG - NTH', 'F NWY S F NWG - NTH'])
        self.process(game)
        assert self.check_results(game, 'F EDI', OK)
        assert self.check_results(game, 'F YOR', BOUNCE)
        assert self.check_results(game, 'F BEL', BOUNCE)
        assert self.check_results(game, 'F ENG', OK)
        assert self.check_results(game, 'F NTH', OK)
        assert self.check_results(game, 'F NWG', BOUNCE)
        assert self.check_results(game, 'F NWY', OK)
        assert self.owner_name(game, 'F EDI') == 'ENGLAND'
        assert self.owner_name(game, 'F YOR') == 'ENGLAND'
        assert self.owner_name(game, 'F BEL') == 'FRANCE'
        assert self.owner_name(game, 'F ENG') == 'FRANCE'
        assert self.owner_name(game, 'F NTH') == 'GERMANY'
        assert self.owner_name(game, 'F NWG') == 'RUSSIA'
        assert self.owner_name(game, 'F NWY') == 'RUSSIA'

    def test_6_e_14(self):
        """ 6.E.14. TEST CASE, ILLEGAL HEAD TO HEAD BATTLE CAN STILL DEFEND
            If in a head to head battle, one of the units makes an illegal move, than that unit has still the
            possibility to defend against attacks with strength of one.
            England: A Liverpool - Edinburgh
            Russia: F Edinburgh - Liverpool
            The move of the Russian fleet is illegal, but can still prevent the English army to enter Edinburgh. So,
            none of the units move.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['A LVP'])
        self.set_units(game, 'RUSSIA', ['F EDI'])
        self.set_orders(game, 'ENGLAND', ['A LVP - EDI'])
        self.set_orders(game, 'RUSSIA', ['F EDI - LVP'])
        self.process(game)
        assert self.check_results(game, 'A LVP', BOUNCE)
        assert self.check_results(game, 'F EDI', VOID)
        assert self.owner_name(game, 'A LVP') == 'ENGLAND'
        assert self.owner_name(game, 'F EDI') == 'RUSSIA'

    def test_6_e_15(self):
        """ 6.E.15. TEST CASE, THE FRIENDLY HEAD TO HEAD BATTLE
            In this case both units in the head to head battle prevent that the other one is dislodged.
            England: F Holland Supports A Ruhr - Kiel
            England: A Ruhr - Kiel
            France: A Kiel - Berlin
            France: A Munich Supports A Kiel - Berlin
            France: A Silesia Supports A Kiel - Berlin
            Germany: A Berlin - Kiel
            Germany: F Denmark Supports A Berlin - Kiel
            Germany: F Helgoland Bight Supports A Berlin - Kiel
            Russia: F Baltic Sea Supports A Prussia - Berlin
            Russia: A Prussia - Berlin
            None of the moves succeeds. This case is especially difficult for sequence based adjudicators. They will
            start adjudicating the head to head battle and continue to adjudicate the attack on one of the units part
            of the head to head battle. In this self.process, one of the sides of the head to head battle might be
            cancelled out. This happens in the DPTG. If this is adjudicated according to the DPTG, the unit in Ruhr or
            in Prussia will advance (depending on the order the units are adjudicated). This is clearly a bug in the
            DPTG.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F HOL', 'A RUH'])
        self.set_units(game, 'FRANCE', ['A KIE', 'A MUN', 'A SIL'])
        self.set_units(game, 'GERMANY', ['A BER', 'F DEN', 'F HEL'])
        self.set_units(game, 'RUSSIA', ['F BAL', 'A PRU'])
        self.set_orders(game, 'ENGLAND', ['F HOL S A RUH - KIE', 'A RUH - KIE'])
        self.set_orders(game, 'FRANCE', ['A KIE - BER', 'A MUN S A KIE - BER', 'A SIL S A KIE - BER'])
        self.set_orders(game, 'GERMANY', ['A BER - KIE', 'F DEN S A BER - KIE', 'F HEL S A BER - KIE'])
        self.set_orders(game, 'RUSSIA', ['F BAL S A PRU - BER', 'A PRU - BER'])
        self.process(game)
        assert self.check_results(game, 'F HOL', OK)
        assert self.check_results(game, 'A RUH', BOUNCE)
        assert self.check_results(game, 'A KIE', BOUNCE)
        assert self.check_results(game, 'A MUN', OK)
        assert self.check_results(game, 'A SIL', OK)
        assert self.check_results(game, 'A BER', BOUNCE)
        assert self.check_results(game, 'F DEN', OK)
        assert self.check_results(game, 'F HEL', OK)
        assert self.check_results(game, 'F BAL', OK)
        assert self.check_results(game, 'A PRU', BOUNCE)
        assert self.owner_name(game, 'F HOL')
        assert self.owner_name(game, 'A RUH')
        assert self.owner_name(game, 'A KIE')
        assert self.owner_name(game, 'A MUN')
        assert self.owner_name(game, 'A SIL')
        assert self.owner_name(game, 'A BER')
        assert self.owner_name(game, 'F DEN')
        assert self.owner_name(game, 'F HEL')
        assert self.owner_name(game, 'F BAL')
        assert self.owner_name(game, 'A PRU')

    # 6.F. TEST CASES, CONVOYS
    def test_6_f_1(self):
        """ 6.F.1. TEST CASE, NO CONVOY IN COASTAL AREAS
            A fleet in a coastal area may not convoy.
            Turkey: A Greece - Sevastopol
            Turkey: F Aegean Sea Convoys A Greece - Sevastopol
            Turkey: F Constantinople Convoys A Greece - Sevastopol
            Turkey: F Black Sea Convoys A Greece - Sevastopol
            The convoy in Constantinople is not possible. So, the army in Greece will not move to Sevastopol.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'TURKEY', ['A GRE', 'F AEG', 'F CON', 'F BLA'])
        self.set_orders(game, 'TURKEY', ['A GRE - SEV', 'F AEG C A GRE - SEV', 'F CON C A GRE - SEV',
                                         'F BLA C A GRE - SEV'])
        self.process(game)
        # Note F CON is void, the other moves then are impossible (i.e. A GRE can't move by convoy to SEV)
        assert self.check_results(game, 'A GRE', VOID)
        assert self.check_results(game, 'F AEG', VOID)
        assert self.check_results(game, 'F CON', VOID)
        assert self.check_results(game, 'F BLA', VOID)
        assert self.owner_name(game, 'A GRE') == 'TURKEY'
        assert self.owner_name(game, 'F AEG') == 'TURKEY'
        assert self.owner_name(game, 'F CON') == 'TURKEY'
        assert self.owner_name(game, 'F BLA') == 'TURKEY'
        assert self.owner_name(game, 'A SEV') is None

    def test_6_f_2(self):
        """ 6.F.2. TEST CASE, AN ARMY BEING CONVOYED CAN BOUNCE AS NORMAL
            Armies being convoyed bounce on other units just as armies that are not being convoyed.
            England: F English Channel Convoys A London - Brest
            England: A London - Brest
            France: A Paris - Brest
            The English army in London bounces on the French army in Paris. Both units do not move.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F ENG', 'A LON'])
        self.set_units(game, 'FRANCE', 'A PAR')
        self.set_orders(game, 'ENGLAND', ['F ENG C A LON - BRE', 'A LON - BRE'])
        self.set_orders(game, 'FRANCE', 'A PAR - BRE')
        self.process(game)
        assert self.check_results(game, 'F ENG', OK)
        assert self.check_results(game, 'A LON', BOUNCE)
        assert self.check_results(game, 'A PAR', BOUNCE)
        assert self.owner_name(game, 'F ENG') == 'ENGLAND'
        assert self.owner_name(game, 'A LON') == 'ENGLAND'
        assert self.owner_name(game, 'A PAR') == 'FRANCE'

    def test_6_f_3(self):
        """ 6.F.3. TEST CASE, AN ARMY BEING CONVOYED CAN RECEIVE SUPPORT
            Armies being convoyed can receive support as in any other move.
            England: F English Channel Convoys A London - Brest
            England: A London - Brest
            England: F Mid-Atlantic Ocean Supports A London - Brest
            France: A Paris - Brest
            The army in London receives support and beats the army in Paris. This means that the army London will end
            in Brest and the French army in Paris stays in Paris.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F ENG', 'A LON', 'F MAO'])
        self.set_units(game, 'FRANCE', 'A PAR')
        self.set_orders(game, 'ENGLAND', ['F ENG C A LON - BRE', 'A LON - BRE', 'F MAO S A LON - BRE'])
        self.set_orders(game, 'FRANCE', 'A PAR - BRE')
        self.process(game)
        assert self.check_results(game, 'F ENG', OK)
        assert self.check_results(game, 'A LON', OK)
        assert self.check_results(game, 'F MAO', OK)
        assert self.check_results(game, 'A PAR', BOUNCE)
        assert self.owner_name(game, 'F ENG') == 'ENGLAND'
        assert self.owner_name(game, 'A BRE') == 'ENGLAND'
        assert self.owner_name(game, 'F MAO') == 'ENGLAND'
        assert self.owner_name(game, 'A LON') is None
        assert self.owner_name(game, 'A PAR') == 'FRANCE'

    def test_6_f_4(self):
        """ 6.F.4. TEST CASE, AN ATTACKED CONVOY IS NOT DISRUPTED
            A convoy can only be disrupted by dislodging the fleets. Attacking is not sufficient.
            England: F North Sea Convoys A London - Holland
            England: A London - Holland
            Germany: F Skagerrak - North Sea
            The army in London will successfully convoy and end in Holland.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F NTH', 'A LON'])
        self.set_units(game, 'GERMANY', 'F SKA')
        self.set_orders(game, 'ENGLAND', ['F NTH C A LON - HOL', 'A LON - HOL'])
        self.set_orders(game, 'GERMANY', 'F SKA - NTH')
        self.process(game)
        assert self.check_results(game, 'F NTH', OK)
        assert self.check_results(game, 'A LON', OK)
        assert self.check_results(game, 'F SKA', BOUNCE)
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'A LON') is None
        assert self.owner_name(game, 'F SKA') == 'GERMANY'
        assert self.owner_name(game, 'A HOL') == 'ENGLAND'

    def test_6_f_5(self):
        """ 6.F.5. TEST CASE, A BELEAGUERED CONVOY IS NOT DISRUPTED
            Even when a convoy is in a beleaguered garrison it is not disrupted.
            England: F North Sea Convoys A London - Holland
            England: A London - Holland
            France: F English Channel - North Sea
            France: F Belgium Supports F English Channel - North Sea
            Germany: F Skagerrak - North Sea
            Germany: F Denmark Supports F Skagerrak - North Sea
            The army in London will successfully convoy and end in Holland.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F NTH', 'A LON'])
        self.set_units(game, 'FRANCE', ['F ENG', 'F BEL'])
        self.set_units(game, 'GERMANY', ['F SKA', 'F DEN'])
        self.set_orders(game, 'ENGLAND', ['F NTH C A LON - HOL', 'A LON - HOL'])
        self.set_orders(game, 'FRANCE', ['F ENG - NTH', 'F BEL S F ENG - NTH'])
        self.set_orders(game, 'GERMANY', ['F SKA - NTH', 'F DEN S F SKA - NTH'])
        self.process(game)
        assert self.check_results(game, 'F NTH', OK)
        assert self.check_results(game, 'A LON', OK)
        assert self.check_results(game, 'F ENG', BOUNCE)
        assert self.check_results(game, 'F BEL', OK)
        assert self.check_results(game, 'F SKA', BOUNCE)
        assert self.check_results(game, 'F DEN', OK)
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'A LON') is None
        assert self.owner_name(game, 'F ENG') == 'FRANCE'
        assert self.owner_name(game, 'F BEL') == 'FRANCE'
        assert self.owner_name(game, 'F SKA') == 'GERMANY'
        assert self.owner_name(game, 'F DEN') == 'GERMANY'
        assert self.owner_name(game, 'A HOL') == 'ENGLAND'

    def test_6_f_6(self):
        """ 6.F.6. TEST CASE, DISLODGED CONVOY DOES NOT CUT SUPPORT
            When a fleet of a convoy is dislodged, the convoy is completely cancelled. So, no support is cut.
            England: F North Sea Convoys A London - Holland
            England: A London - Holland
            Germany: A Holland Supports A Belgium
            Germany: A Belgium Supports A Holland
            Germany: F Helgoland Bight Supports F Skagerrak - North Sea
            Germany: F Skagerrak - North Sea
            France: A Picardy - Belgium
            France: A Burgundy Supports A Picardy - Belgium
            The hold order of Holland on Belgium will sustain and Belgium will not be dislodged by the French in
            Picardy.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F NTH', 'A LON'])
        self.set_units(game, 'GERMANY', ['A HOL', 'A BEL', 'F HEL', 'F SKA'])
        self.set_units(game, 'FRANCE', ['A PIC', 'A BUR'])
        self.set_orders(game, 'ENGLAND', ['F NTH C A LON - HOL', 'A LON - HOL'])
        self.set_orders(game, 'GERMANY', ['A HOL S A BEL', 'A BEL S A HOL', 'F HEL S F SKA - NTH', 'F SKA - NTH'])
        self.set_orders(game, 'FRANCE', ['A PIC - BEL', 'A BUR S A PIC - BEL'])
        self.process(game)
        assert self.check_results(game, 'F NTH', DISLODGED)
        assert self.check_results(game, 'A LON', NO_CONVOY)
        assert self.check_results(game, 'A HOL', OK)
        assert self.check_results(game, 'A BEL', CUT)
        assert self.check_results(game, 'F HEL', OK)
        assert self.check_results(game, 'F SKA', OK)
        assert self.check_results(game, 'A PIC', BOUNCE)
        assert self.check_results(game, 'A BUR', OK)
        assert check_dislodged(game, 'F NTH', 'F SKA')
        assert self.owner_name(game, 'F NTH') == 'GERMANY'
        assert self.owner_name(game, 'A LON') == 'ENGLAND'
        assert self.owner_name(game, 'A HOL') == 'GERMANY'
        assert self.owner_name(game, 'A BEL') == 'GERMANY'
        assert self.owner_name(game, 'F HEL') == 'GERMANY'
        assert self.owner_name(game, 'F SKA') is None
        assert self.owner_name(game, 'A PIC') == 'FRANCE'
        assert self.owner_name(game, 'A BUR') == 'FRANCE'

    def test_6_f_7(self):
        """ 6.F.7. TEST CASE, DISLODGED CONVOY DOES NOT CAUSE CONTESTED AREA
            When a fleet of a convoy is dislodged, the landing area is not contested, so other units can retreat to
            that area.
            England: F North Sea Convoys A London - Holland
            England: A London - Holland
            Germany: F Helgoland Bight Supports F Skagerrak - North Sea
            Germany: F Skagerrak - North Sea
            The dislodged English fleet can retreat to Holland.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F NTH', 'A LON'])
        self.set_units(game, 'GERMANY', ['F HEL', 'F SKA'])

        # Movements phase
        self.set_orders(game, 'ENGLAND', ['F NTH C A LON - HOL', 'A LON - HOL'])
        self.set_orders(game, 'GERMANY', ['F HEL S F SKA - NTH', 'F SKA - NTH'])
        self.process(game)
        assert self.check_results(game, 'F NTH', DISLODGED)
        assert self.check_results(game, 'A LON', NO_CONVOY)
        assert self.check_results(game, 'F HEL', OK)
        assert self.check_results(game, 'F SKA', OK)
        assert check_dislodged(game, 'F NTH', 'F SKA')      # ENGLAND
        assert self.owner_name(game, 'F NTH') == 'GERMANY'
        assert self.owner_name(game, 'A LON') == 'ENGLAND'
        assert self.owner_name(game, 'F HEL') == 'GERMANY'
        assert self.owner_name(game, 'F SKA') is None
        assert self.owner_name(game, 'A HOL') is None

        # Retreats phase
        if game.phase_type == 'R':
            self.set_orders(game, 'ENGLAND', 'F NTH R HOL')
            self.process(game)
            assert self.check_results(game, 'F NTH', OK, phase='R')
        assert self.owner_name(game, 'F NTH') == 'GERMANY'
        assert self.owner_name(game, 'A LON') == 'ENGLAND'
        assert self.owner_name(game, 'F HEL') == 'GERMANY'
        assert self.owner_name(game, 'F SKA') is None
        assert self.owner_name(game, 'F HOL') == 'ENGLAND'

    def test_6_f_8(self):
        """ 6.F.8. TEST CASE, DISLODGED CONVOY DOES NOT CAUSE A BOUNCE
            When a fleet of a convoy is dislodged, then there will be no bounce in the landing area.
            England: F North Sea Convoys A London - Holland
            England: A London - Holland
            Germany: F Helgoland Bight Supports F Skagerrak - North Sea
            Germany: F Skagerrak - North Sea
            Germany: A Belgium - Holland
            The army in Belgium will not bounce and move to Holland.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F NTH', 'A LON'])
        self.set_units(game, 'GERMANY', ['F HEL', 'F SKA', 'A BEL'])
        self.set_orders(game, 'ENGLAND', ['F NTH C A LON - HOL', 'A LON - HOL'])
        self.set_orders(game, 'GERMANY', ['F HEL S F SKA - NTH', 'F SKA - NTH', 'A BEL - HOL'])
        self.process(game)
        assert self.check_results(game, 'F NTH', DISLODGED)
        assert self.check_results(game, 'A LON', NO_CONVOY)
        assert self.check_results(game, 'F HEL', OK)
        assert self.check_results(game, 'F SKA', OK)
        assert self.check_results(game, 'A BEL', OK)
        assert check_dislodged(game, 'F NTH', 'F SKA')
        assert self.owner_name(game, 'F NTH') == 'GERMANY'
        assert self.owner_name(game, 'A LON') == 'ENGLAND'
        assert self.owner_name(game, 'F HEL') == 'GERMANY'
        assert self.owner_name(game, 'F SKA') is None
        assert self.owner_name(game, 'A BEL') is None
        assert self.owner_name(game, 'A HOL') == 'GERMANY'

    def test_6_f_9(self):
        """ 6.F.9. TEST CASE, DISLODGE OF MULTI-ROUTE CONVOY
            When a fleet of a convoy with multiple routes is dislodged, the result depends on the rulebook that is used.
            England: F English Channel Convoys A London - Belgium
            England: F North Sea Convoys A London - Belgium
            England: A London - Belgium
            France: F Brest Supports F Mid-Atlantic Ocean - English Channel
            France: F Mid-Atlantic Ocean - English Channel
            The French fleet in Mid Atlantic Ocean will dislodge the convoying fleet in the English Channel. If the
            1971 rules are used (see issue 4.A.1), this will disrupt the convoy and the army will stay in London. When
            the 1982 or 2000 rulebook is used (which I prefer) the army can still go via the North Sea and the convoy
            succeeds and the London army will end in Belgium.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F ENG', 'F NTH', 'A LON'])
        self.set_units(game, 'FRANCE', ['F BRE', 'F MAO'])
        self.set_orders(game, 'ENGLAND', ['F ENG C A LON - BEL', 'F NTH C A LON - BEL', 'A LON - BEL'])
        self.set_orders(game, 'FRANCE', ['F BRE S F MAO - ENG', 'F MAO - ENG'])
        self.process(game)
        assert self.check_results(game, 'F ENG', DISLODGED)
        assert self.check_results(game, 'F NTH', OK)
        assert self.check_results(game, 'A LON', OK)
        assert self.check_results(game, 'F BRE', OK)
        assert self.check_results(game, 'F MAO', OK)
        assert check_dislodged(game, 'F ENG', 'F MAO')
        assert self.owner_name(game, 'F ENG') == 'FRANCE'
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'A LON') is None
        assert self.owner_name(game, 'F BRE') == 'FRANCE'
        assert self.owner_name(game, 'F MAO') is None
        assert self.owner_name(game, 'A BEL') == 'ENGLAND'

    def test_6_f_10(self):
        """ 6.F.10. TEST CASE, DISLODGE OF MULTI-ROUTE CONVOY WITH FOREIGN FLEET
            When the 1971 rulebook is used "unwanted" multi-route convoys are possible.
            England: F North Sea Convoys A London - Belgium
            England: A London - Belgium
            Germany: F English Channel Convoys A London - Belgium
            France: F Brest Supports F Mid-Atlantic Ocean - English Channel
            France: F Mid-Atlantic Ocean - English Channel
            If the 1982 or 2000 rulebook is used (which I prefer), it makes no difference that the convoying fleet in
            the English Channel is German. It will take the convoy via the North Sea anyway and the army in London will
            end in Belgium. However, when the 1971 rules are used, the German convoy is "unwanted". According to the
            DPTG the German fleet should be ignored in the English convoy, since there is a convoy path with only
            English fleets. That means that the convoy is not disrupted and the English army in London will end in
            Belgium. See also issue 4.A.1.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F NTH', 'A LON'])
        self.set_units(game, 'GERMANY', 'F ENG')
        self.set_units(game, 'FRANCE', ['F BRE', 'F MAO'])
        self.set_orders(game, 'ENGLAND', ['F NTH C A LON - BEL', 'A LON - BEL'])
        self.set_orders(game, 'GERMANY', ['F ENG C A LON - BEL'])
        self.set_orders(game, 'FRANCE', ['F BRE S F MAO - ENG', 'F MAO - ENG'])
        self.process(game)
        assert self.check_results(game, 'F NTH', OK)
        assert self.check_results(game, 'A LON', OK)
        assert self.check_results(game, 'F ENG', DISLODGED)
        assert self.check_results(game, 'F BRE', OK)
        assert self.check_results(game, 'F MAO', OK)
        assert check_dislodged(game, 'F ENG', 'F MAO')
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'A LON') is None
        assert self.owner_name(game, 'F ENG') == 'FRANCE'
        assert self.owner_name(game, 'F BRE') == 'FRANCE'
        assert self.owner_name(game, 'F MAO') is None
        assert self.owner_name(game, 'A BEL') == 'ENGLAND'

    def test_6_f_11(self):
        """ 6.F.11. TEST CASE, DISLODGE OF MULTI-ROUTE CONVOY WITH ONLY FOREIGN FLEETS
            When the 1971 rulebook is used, "unwanted" convoys can not be ignored in all cases.
            England: A London - Belgium
            Germany: F English Channel Convoys A London - Belgium
            Russia: F North Sea Convoys A London - Belgium
            France: F Brest Supports F Mid-Atlantic Ocean - English Channel
            France: F Mid-Atlantic Ocean - English Channel
            If the 1982 or 2000 rulebook is used (which I prefer), it makes no difference that the convoying fleets
            are not English. It will take the convoy via the North Sea anyway and the army in London will end in
            Belgium. However, when the 1971 rules are used, the situation is different. Since both the fleet in the
            English Channel as the fleet in North Sea are not English, it can not be concluded that the German fleet
            is "unwanted". Therefore, one of the routes of the convoy is disrupted and that means that the complete
            convoy is disrupted. The army in London will stay in London. See also issue 4.A.1.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['A LON'])
        self.set_units(game, 'GERMANY', ['F ENG'])
        self.set_units(game, 'RUSSIA', ['F NTH'])
        self.set_units(game, 'FRANCE', ['F BRE', 'F MAO'])
        self.set_orders(game, 'ENGLAND', 'A LON - BEL')
        self.set_orders(game, 'GERMANY', 'F ENG C A LON - BEL')
        self.set_orders(game, 'RUSSIA', 'F NTH C A LON - BEL')
        self.set_orders(game, 'FRANCE', ['F BRE S F MAO - ENG', 'F MAO - ENG'])
        self.process(game)
        assert self.check_results(game, 'A LON', OK)
        assert self.check_results(game, 'F ENG', DISLODGED)
        assert self.check_results(game, 'F NTH', OK)
        assert self.check_results(game, 'F BRE', OK)
        assert self.check_results(game, 'F MAO', OK)
        assert check_dislodged(game, 'F ENG', 'F MAO')
        assert self.owner_name(game, 'A LON') is None
        assert self.owner_name(game, 'F ENG') == 'FRANCE'
        assert self.owner_name(game, 'F NTH') == 'RUSSIA'
        assert self.owner_name(game, 'F BRE') == 'FRANCE'
        assert self.owner_name(game, 'F MAO') is None
        assert self.owner_name(game, 'A BEL') == 'ENGLAND'

    def test_6_f_12(self):
        """ 6.F.12. TEST CASE, DISLODGED CONVOYING FLEET NOT ON ROUTE
            When the rule is used that convoys are disrupted when one of the routes is disrupted (see issue 4.A.1),
            the convoy is not necessarily disrupted when one of the fleets ordered to convoy is dislodged.
            England: F English Channel Convoys A London - Belgium
            England: A London - Belgium
            England: F Irish Sea Convoys A London - Belgium
            France: F North Atlantic Ocean Supports F Mid-Atlantic Ocean - Irish Sea
            France: F Mid-Atlantic Ocean - Irish Sea
            Even when convoys are disrupted when one of the routes is disrupted (see issue 4.A.1), the convoy from
            London to Belgium will still succeed, since the dislodged fleet in the Irish Sea is not part of any route,
            although it can be reached from the starting point London.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F ENG', 'A LON', 'F IRI'])
        self.set_units(game, 'FRANCE', ['F NAO', 'F MAO'])
        self.set_orders(game, 'ENGLAND', ['F ENG C A LON - BEL', 'A LON - BEL', 'F IRI C A LON - BEL'])
        self.set_orders(game, 'FRANCE', ['F NAO S F MAO - IRI', 'F MAO - IRI'])
        self.process(game)
        assert self.check_results(game, 'F ENG', OK)
        assert self.check_results(game, 'A LON', OK)
        assert self.check_results(game, 'F IRI', DISLODGED)
        assert self.check_results(game, 'F NAO', OK)
        assert self.check_results(game, 'F MAO', OK)
        assert check_dislodged(game, 'F IRI', 'F MAO')
        assert self.owner_name(game, 'F ENG') == 'ENGLAND'
        assert self.owner_name(game, 'A LON') is None
        assert self.owner_name(game, 'F IRI') == 'FRANCE'
        assert self.owner_name(game, 'F NAO') == 'FRANCE'
        assert self.owner_name(game, 'F MAO') is None
        assert self.owner_name(game, 'A BEL') == 'ENGLAND'

    def test_6_f_13(self):
        """ 6.F.13. TEST CASE, THE UNWANTED ALTERNATIVE
            This situation is not difficult to adjudicate, but it shows that even if someone wants to convoy, the
            player might not want an alternative route for the convoy.
            England: A London - Belgium
            England: F North Sea Convoys A London - Belgium
            France: F English Channel Convoys A London - Belgium
            Germany: F Holland Supports F Denmark - North Sea
            Germany: F Denmark - North Sea
            If France and German are allies, England want to keep its army in London, to defend the island. An army
            in Belgium could easily be destroyed by an alliance of France and Germany. England tries to be friends with
            Germany, however France and Germany trick England.
            The convoy of the army in London succeeds and the fleet in Denmark dislodges the fleet in the North Sea.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['A LON', 'F NTH'])
        self.set_units(game, 'FRANCE', 'F ENG')
        self.set_units(game, 'GERMANY', ['F HOL', 'F DEN'])
        self.set_orders(game, 'ENGLAND', ['A LON - BEL', 'F NTH C A LON - BEL'])
        self.set_orders(game, 'FRANCE', 'F ENG C A LON - BEL')
        self.set_orders(game, 'GERMANY', ['F HOL S F DEN - NTH', 'F DEN - NTH'])
        self.process(game)
        assert self.check_results(game, 'A LON', OK)
        assert self.check_results(game, 'F NTH', DISLODGED)
        assert self.check_results(game, 'F ENG', OK)
        assert self.check_results(game, 'F HOL', OK)
        assert self.check_results(game, 'F DEN', OK)
        assert check_dislodged(game, 'F NTH', 'F DEN')
        assert self.owner_name(game, 'A LON') is None
        assert self.owner_name(game, 'F NTH') == 'GERMANY'
        assert self.owner_name(game, 'F ENG') == 'FRANCE'
        assert self.owner_name(game, 'F HOL') == 'GERMANY'
        assert self.owner_name(game, 'F DEN') is None
        assert self.owner_name(game, 'A BEL') == 'ENGLAND'

    def test_6_f_14(self):
        """ 6.F.14. TEST CASE, SIMPLE CONVOY PARADOX
            The most common paradox is when the attacked unit supports an attack on one of the convoying fleets.
            England: F London Supports F Wales - English Channel
            England: F Wales - English Channel
            France: A Brest - London
            France: F English Channel Convoys A Brest - London
            This situation depends on how paradoxes are handled (see issue (4.A.2). In case of the 'All Hold' rule
            (fully applied, not just as "backup" rule), both the movement of the English fleet in Wales as the France
            convoy in Brest are part of the paradox and fail. In all other rules of paradoxical convoys (including the
            Szykman rule which I prefer), the support of London is not cut. That means that the fleet in the English
            Channel is dislodged.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F LON', 'F WAL'])
        self.set_units(game, 'FRANCE', ['A BRE', 'F ENG'])
        self.set_orders(game, 'ENGLAND', ['F LON S F WAL - ENG', 'F WAL - ENG'])
        self.set_orders(game, 'FRANCE', ['A BRE - LON', 'F ENG C A BRE - LON'])
        self.process(game)
        assert self.check_results(game, 'F LON', OK)
        assert self.check_results(game, 'F WAL', OK)
        assert self.check_results(game, 'A BRE', NO_CONVOY)
        assert self.check_results(game, 'F ENG', DISLODGED)
        assert check_dislodged(game, 'F ENG', 'F WAL')
        assert self.owner_name(game, 'F LON') == 'ENGLAND'
        assert self.owner_name(game, 'F WAL') is None
        assert self.owner_name(game, 'A BRE') == 'FRANCE'
        assert self.owner_name(game, 'F ENG') == 'ENGLAND'

    def test_6_f_15(self):
        """ 6.F.15. TEST CASE, SIMPLE CONVOY PARADOX WITH ADDITIONAL CONVOY
            Paradox rules only apply on the paradox core.
            England: F London Supports F Wales - English Channel
            England: F Wales - English Channel
            France: A Brest - London
            France: F English Channel Convoys A Brest - London
            Italy: F Irish Sea Convoys A North Africa - Wales
            Italy: F Mid-Atlantic Ocean Convoys A North Africa - Wales
            Italy: A North Africa - Wales
            The Italian convoy is not part of the paradox core and should therefore succeed when the move of the
            fleet in Wales is successful. This is the case except when the 'All Hold' paradox rule is used (fully
            applied, not just as "backup" rule, see issue 4.A.2).
            I prefer the Szykman rule, so I prefer that both the fleet in Wales as the army in North Africa succeed in
            moving.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F LON', 'F WAL'])
        self.set_units(game, 'FRANCE', ['A BRE', 'F ENG'])
        self.set_units(game, 'ITALY', ['F IRI', 'F MAO', 'A NAF'])
        self.set_orders(game, 'ENGLAND', ['F LON S F WAL - ENG', 'F WAL - ENG'])
        self.set_orders(game, 'FRANCE', ['A BRE - LON', 'F ENG C A BRE - LON'])
        self.set_orders(game, 'ITALY', ['F IRI C A NAF - WAL', 'F MAO C A NAF - WAL', 'A NAF - WAL'])
        self.process(game)
        assert self.check_results(game, 'F LON', OK)
        assert self.check_results(game, 'F WAL', OK)
        assert self.check_results(game, 'A BRE', NO_CONVOY)
        assert self.check_results(game, 'F ENG', DISLODGED)
        assert self.check_results(game, 'F IRI', OK)
        assert self.check_results(game, 'F MAO', OK)
        assert self.check_results(game, 'A NAF', OK)
        assert check_dislodged(game, 'F ENG', 'F WAL')
        assert self.owner_name(game, 'F LON') == 'ENGLAND'
        assert self.owner_name(game, 'A WAL') == 'ITALY'
        assert self.owner_name(game, 'A BRE') == 'FRANCE'
        assert self.owner_name(game, 'F ENG') == 'ENGLAND'
        assert self.owner_name(game, 'F IRI') == 'ITALY'
        assert self.owner_name(game, 'F MAO') == 'ITALY'
        assert self.owner_name(game, 'A NAF') is None

    def test_6_f_16(self):
        """ 6.F.16. TEST CASE, PANDIN'S PARADOX
            In Pandin's paradox, the attacked unit protects the convoying fleet by a beleaguered garrison.
            England: F London Supports F Wales - English Channel
            England: F Wales - English Channel
            France: A Brest - London
            France: F English Channel Convoys A Brest - London
            Germany: F North Sea Supports F Belgium - English Channel
            Germany: F Belgium - English Channel
            In all the different rules for resolving convoy disruption paradoxes (see issue 4.A.2), the support
            of London is not cut. That means that the fleet in the English Channel is not dislodged and none of the
            units succeed to move.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F LON', 'F WAL'])
        self.set_units(game, 'FRANCE', ['A BRE', 'F ENG'])
        self.set_units(game, 'GERMANY', ['F NTH', 'F BEL'])
        self.set_orders(game, 'ENGLAND', ['F LON S F WAL - ENG', 'F WAL - ENG'])
        self.set_orders(game, 'FRANCE', ['A BRE - LON', 'F ENG C A BRE - LON'])
        self.set_orders(game, 'GERMANY', ['F NTH S F BEL - ENG', 'F BEL - ENG'])
        self.process(game)
        assert self.check_results(game, 'F LON', OK)
        assert self.check_results(game, 'F WAL', BOUNCE)
        assert self.check_results(game, 'A BRE', NO_CONVOY)
        assert self.check_results(game, 'F ENG', DISRUPTED)
        assert self.check_results(game, 'F NTH', OK)
        assert self.check_results(game, 'F BEL', BOUNCE)
        assert self.owner_name(game, 'F LON') == 'ENGLAND'
        assert self.owner_name(game, 'F WAL') == 'ENGLAND'
        assert self.owner_name(game, 'A BRE') == 'FRANCE'
        assert self.owner_name(game, 'F ENG') == 'FRANCE'
        assert self.owner_name(game, 'F NTH') == 'GERMANY'
        assert self.owner_name(game, 'F BEL') == 'GERMANY'

    def test_6_f_17(self):
        """ 6.F.17. TEST CASE, PANDIN'S EXTENDED PARADOX
            In Pandin's extended paradox, the attacked unit protects the convoying fleet by a beleaguered garrison and
            the attacked unit can dislodge the unit that gives the protection.
            England: F London Supports F Wales - English Channel
            England: F Wales - English Channel
            France: A Brest - London
            France: F English Channel Convoys A Brest - London
            France: F Yorkshire Supports A Brest - London
            Germany: F North Sea Supports F Belgium - English Channel
            Germany: F Belgium - English Channel
            When the 1971, 1982 or 2000 rule is used (see issue 4.A.2), the support of London is not cut. That means
            that the fleet in the English Channel is not dislodged. The convoy will succeed and dislodge the fleet in
            London. You may argue that this violates the dislodge rule, but the common interpretation is that the
            paradox convoy rules take precedence over the dislodge rule.
            If the Simon Szykman alternative is used (which I prefer), the convoy fails and the fleet in London and
            the English Channel are not dislodged. When the 'All Hold' (fully applied, not just as "backup" rule) or
            the DPTG rule is used, the result is the same as the Simon Szykman alternative. The involved moves (the
            move of the German fleet in Belgium and the convoying army in Brest) fail.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F LON', 'F WAL'])
        self.set_units(game, 'FRANCE', ['A BRE', 'F ENG', 'F YOR'])
        self.set_units(game, 'GERMANY', ['F NTH', 'F BEL'])
        self.set_orders(game, 'ENGLAND', ['F LON S F WAL - ENG', 'F WAL - ENG'])
        self.set_orders(game, 'FRANCE', ['A BRE - LON', 'F ENG C A BRE - LON', 'F YOR S A BRE - LON'])
        self.set_orders(game, 'GERMANY', ['F NTH S F BEL - ENG', 'F BEL - ENG'])
        self.process(game)
        assert self.check_results(game, 'F LON', OK)
        assert self.check_results(game, 'F WAL', BOUNCE)
        assert self.check_results(game, 'A BRE', NO_CONVOY)
        assert self.check_results(game, 'F ENG', DISRUPTED)
        assert self.check_results(game, 'F YOR', NO_CONVOY)
        assert self.check_results(game, 'F NTH', OK)
        assert self.check_results(game, 'F BEL', BOUNCE)
        assert self.owner_name(game, 'F LON') == 'ENGLAND'
        assert self.owner_name(game, 'F WAL') == 'ENGLAND'
        assert self.owner_name(game, 'A BRE') == 'FRANCE'
        assert self.owner_name(game, 'F ENG') == 'FRANCE'
        assert self.owner_name(game, 'F YOR') == 'FRANCE'
        assert self.owner_name(game, 'F NTH') == 'GERMANY'
        assert self.owner_name(game, 'F BEL') == 'GERMANY'

    def test_6_f_18(self):
        """ 6.F.18. TEST CASE, BETRAYAL PARADOX
            The betrayal paradox is comparable to Pandin's paradox, but now the attacked unit direct supports the
            convoying fleet. Of course, this will only happen when the player of the attacked unit is betrayed.
            England: F North Sea Convoys A London - Belgium
            England: A London - Belgium
            England: F English Channel Supports A London - Belgium
            France: F Belgium Supports F North Sea
            Germany: F Helgoland Bight Supports F Skagerrak - North Sea
            Germany: F Skagerrak - North Sea
            If the English convoy from London to Belgium is successful, then it cuts the France support necessary to
            hold the fleet in the North Sea (see issue 4.A.2).
            The 1971 and 2000 ruling do not give an answer on this.
            According to the 1982 ruling the French support on the North Sea will not be cut. So, the fleet in the
            North Sea will not be dislodged by the Germans and the army in London will dislodge the French army in
            Belgium.
            If the Szykman rule is followed (which I prefer), the move of the army in London will fail and will not cut
            support. That means that the fleet in the North Sea will not be dislodged. The 'All Hold' rule has the same
            result as the Szykman rule, but with a different reason. The move of the army in London and the move of the
            German fleet in Skagerrak will fail. Since a failing convoy does not result in a consistent resolution,
            the DPTG gives the same result as the 'All Hold' rule.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F NTH', 'A LON', 'F ENG'])
        self.set_units(game, 'FRANCE', ['F BEL'])
        self.set_units(game, 'GERMANY', ['F HEL', 'F SKA'])
        self.set_orders(game, 'ENGLAND', ['F NTH C A LON - BEL', 'A LON - BEL', 'F ENG S A LON - BEL'])
        self.set_orders(game, 'FRANCE', ['F BEL S F NTH'])
        self.set_orders(game, 'GERMANY', ['F HEL S F SKA - NTH', 'F SKA - NTH'])
        self.process(game)
        assert self.check_results(game, 'F NTH', DISRUPTED)
        assert self.check_results(game, 'A LON', NO_CONVOY)
        assert self.check_results(game, 'F ENG', NO_CONVOY)
        assert self.check_results(game, 'F BEL', OK)
        assert self.check_results(game, 'F HEL', OK)
        assert self.check_results(game, 'F SKA', BOUNCE)
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'A LON') == 'ENGLAND'
        assert self.owner_name(game, 'F ENG') == 'ENGLAND'
        assert self.owner_name(game, 'F BEL') == 'FRANCE'
        assert self.owner_name(game, 'F HEL') == 'GERMANY'
        assert self.owner_name(game, 'F SKA') == 'GERMANY'

    def test_6_f_19(self):
        """ 6.F.19. TEST CASE, MULTI-ROUTE CONVOY DISRUPTION PARADOX
            The situation becomes more complex when the convoy has alternative routes.
            France: A Tunis - Naples
            France: F Tyrrhenian Sea Convoys A Tunis - Naples
            France: F Ionian Sea Convoys A Tunis - Naples
            Italy: F Naples Supports F Rome - Tyrrhenian Sea
            Italy: F Rome - Tyrrhenian Sea
            Now, two issues play a role. The ruling about disruption of convoys (issue 4.A.1) and the issue how
            paradoxes are resolved (issue 4.A.2).
            If the 1971 rule is used about multi-route convoys (when one of the routes is disrupted, the convoy fails),
            this test case is just a simple paradox. For the 1971, 1982, 2000 and Szykman paradox rule, the support of
            the fleet in Naples is not cut and the fleet in Rome dislodges the fleet in the Tyrrhenian Sea. When the
            'All Hold' rule is used, both the convoy of the army in Tunis as the move of the fleet in Rome will fail.
            When the 1982 rule is used about multi-route convoy disruption, then convoys are disrupted when all routes
            are disrupted (this is the rule I prefer). With this rule, the situation becomes paradoxical. According to
            the 1971 and 1982 paradox rules, the support given by the fleet in Naples is not cut, that means that the
            fleet in the Tyrrhenian Sea is dislodged.
            According to the 2000 ruling the fleet in the Tyrrhenian Sea is not "necessary" for the convoy and the
            support of Naples is cut and the fleet in the Tyrrhenian Sea is not dislodged.
            If the Szykman rule is used (which I prefer), the 'All Hold' rule or the DPTG, then there is no paradoxical
            situation. The support of Naples is cut and the fleet in the Tyrrhenian Sea is not dislodged.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'FRANCE', ['A TUN', 'F TYS', 'F ION'])
        self.set_units(game, 'ITALY', ['F NAP', 'F ROM'])
        self.set_orders(game, 'FRANCE', ['A TUN - NAP', 'F TYS C A TUN - NAP', 'F ION C A TUN - NAP'])
        self.set_orders(game, 'ITALY', ['F NAP S F ROM - TYS', 'F ROM - TYS'])
        self.process(game)
        assert self.check_results(game, 'A TUN', BOUNCE)
        assert self.check_results(game, 'F TYS', OK)
        assert self.check_results(game, 'F ION', OK)
        assert self.check_results(game, 'F NAP', CUT)
        assert self.check_results(game, 'F ROM', BOUNCE)
        assert self.owner_name(game, 'A TUN') == 'FRANCE'
        assert self.owner_name(game, 'F TYS') == 'FRANCE'
        assert self.owner_name(game, 'F ION') == 'FRANCE'
        assert self.owner_name(game, 'F NAP') == 'ITALY'
        assert self.owner_name(game, 'F ROM') == 'ITALY'

    def test_6_f_20(self):
        """ 6.F.20. TEST CASE, UNWANTED MULTI-ROUTE CONVOY PARADOX
            The 1982 paradox rule allows some creative defense.
            France: A Tunis - Naples
            France: F Tyrrhenian Sea Convoys A Tunis - Naples
            Italy: F Naples Supports F Ionian Sea
            Italy: F Ionian Sea Convoys A Tunis - Naples
            Turkey: F Aegean Sea Supports F Eastern Mediterranean - Ionian Sea
            Turkey: F Eastern Mediterranean - Ionian Sea
            Again, two issues play a role. The ruling about disruption of multi-route convoys (issue 4.A.1) and the
            issue how paradoxes are resolved (issue 4.A.2).
            If the 1971 rule is used about multi-route convoys (when one of the routes is disrupted, the convoy fails),
            the Italian convoy order in the Ionian Sea is not part of the convoy, because it is a foreign unit
            (according to the DPTG).
            That means that the fleet in the Ionian Sea is not a 'convoying' fleet. In all rulings the support of
            Naples on the Ionian Sea is cut and the fleet in the Ionian Sea is dislodged by the Turkish fleet in the
            Eastern Mediterranean. When the 1982 rule is used about multi-route convoy disruption, then convoys are
            disrupted when all routes are disrupted (this is the rule I prefer). With this rule, the situation becomes
            paradoxical. According to the 1971 and 1982 paradox rules, the support given by the fleet in Naples is not
            cut, that means that the fleet in the Ionian Sea is not dislodged.
            According to the 2000 ruling the fleet in the Ionian Sea is not "necessary" and the support of Naples is
            cut and the fleet in the Ionian Sea is dislodged by the Turkish fleet in the Eastern Mediterranean.
            If the Szykman rule, the 'All Hold' rule or DPTG is used, then there is no paradoxical situation. The
            support of Naples is cut and the fleet in the Ionian Sea is dislodged by the Turkish fleet in the Eastern
            Mediterranean. As you can see, the 1982 rules allows the Italian player to save its fleet in the Ionian Sea
            with a trick. I do not consider this trick as normal tactical play. I prefer the Szykman rule as one of the
            rules that does not allow this trick. According to this rule the fleet in the Ionian Sea is dislodged.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'FRANCE', ['A TUN', 'F TYS'])
        self.set_units(game, 'ITALY', ['F NAP', 'F ION'])
        self.set_units(game, 'TURKEY', ['F AEG', 'F EAS'])
        self.set_orders(game, 'FRANCE', ['A TUN - NAP', 'F TYS C A TUN - NAP'])
        self.set_orders(game, 'ITALY', ['F NAP S F ION', 'F ION C A TUN - NAP'])
        self.set_orders(game, 'TURKEY', ['F AEG S F EAS - ION', 'F EAS - ION'])
        self.process(game)
        assert self.check_results(game, 'A TUN', BOUNCE)
        assert self.check_results(game, 'F TYS', OK)
        assert self.check_results(game, 'F NAP', CUT)
        assert self.check_results(game, 'F ION', DISLODGED)
        assert self.check_results(game, 'F AEG', OK)
        assert self.check_results(game, 'F EAS', OK)
        assert check_dislodged(game, 'F ION', 'F EAS')
        assert self.owner_name(game, 'A TUN') == 'FRANCE'
        assert self.owner_name(game, 'F TYS') == 'FRANCE'
        assert self.owner_name(game, 'F NAP') == 'ITALY'
        assert self.owner_name(game, 'F ION') == 'TURKEY'
        assert self.owner_name(game, 'F AEG') == 'TURKEY'
        assert self.owner_name(game, 'F EAS') is None

    def test_6_f_21(self):
        """ 6.F.21. TEST CASE, DAD'S ARMY CONVOY
            The 1982 paradox rule has as side effect that convoying armies do not cut support in some situations that
            are not paradoxical.
            Russia: A Edinburgh Supports A Norway - Clyde
            Russia: F Norwegian Sea Convoys A Norway - Clyde
            Russia: A Norway - Clyde
            France: F Irish Sea Supports F Mid-Atlantic Ocean - North Atlantic Ocean
            France: F Mid-Atlantic Ocean - North Atlantic Ocean
            England: A Liverpool - Clyde via Convoy
            England: F North Atlantic Ocean Convoys A Liverpool - Clyde
            England: F Clyde Supports F North Atlantic Ocean
            In all rulings, except the 1982 paradox ruling, the support of the fleet in Clyde on the North Atlantic
            Ocean is cut and the French fleet in the Mid-Atlantic Ocean will dislodge the fleet in the North Atlantic
            Ocean. This is the preferred way. However, in the 1982 paradox rule (see issue 4.A.2), the support of the
            fleet in Clyde is not cut. That means that the English fleet in the North Atlantic Ocean is not dislodged.
            As you can see, the 1982 rule allows England to save its fleet in the North Atlantic Ocean in a very
            strange way. Just the support of Clyde is insufficient (if there is no convoy, the support is cut). Only
            the convoy to the area occupied by own unit, can do the trick in this situation. The embarking of troops
            in the fleet deceives the enemy so much that it works as a magic cloak. The enemy is not able to dislodge
            the fleet in the North Atlantic Ocean any more. Of course, this will only work in comedies. I prefer the
            Szykman rule as one of the rules that does not allow this trick. According to this rule (and all other
            paradox rules), the fleet in the North Atlantic is just dislodged.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'RUSSIA', ['A EDI', 'F NWG', 'A NWY'])
        self.set_units(game, 'FRANCE', ['F IRI', 'F MAO'])
        self.set_units(game, 'ENGLAND', ['A LVP', 'F NAO', 'F CLY'])
        self.set_orders(game, 'RUSSIA', ['A EDI S A NWY - CLY', 'F NWG C A NWY - CLY', 'A NWY - CLY'])
        self.set_orders(game, 'FRANCE', ['F IRI S F MAO - NAO', 'F MAO - NAO'])
        self.set_orders(game, 'ENGLAND', ['A LVP - CLY VIA', 'F NAO C A LVP - CLY', 'F CLY S F NAO'])
        self.process(game)
        assert self.check_results(game, 'A EDI', OK)
        assert self.check_results(game, 'F NWG', OK)
        assert self.check_results(game, 'A NWY', OK)
        assert self.check_results(game, 'F IRI', OK)
        assert self.check_results(game, 'F MAO', OK)
        assert self.check_results(game, 'A LVP', NO_CONVOY)
        assert self.check_results(game, 'F NAO', DISLODGED)
        assert self.check_results(game, 'F CLY', CUT)
        assert self.check_results(game, 'F CLY', DISLODGED)
        assert check_dislodged(game, 'F NAO', 'F MAO')
        assert check_dislodged(game, 'F CLY', 'A NWY')
        assert self.owner_name(game, 'A EDI') == 'RUSSIA'
        assert self.owner_name(game, 'F NWG') == 'RUSSIA'
        assert self.owner_name(game, 'A NWY') is None
        assert self.owner_name(game, 'F IRI') == 'FRANCE'
        assert self.owner_name(game, 'F MAO') is None
        assert self.owner_name(game, 'A LVP') == 'ENGLAND'
        assert self.owner_name(game, 'F NAO') == 'FRANCE'
        assert self.owner_name(game, 'A CLY') == 'RUSSIA'

    def test_6_f_22(self):
        """ 6.F.22. TEST CASE, SECOND ORDER PARADOX WITH TWO RESOLUTIONS
            Two convoys are involved in a second order paradox.
            England: F Edinburgh - North Sea
            England: F London Supports F Edinburgh - North Sea
            France: A Brest - London
            France: F English Channel Convoys A Brest - London
            Germany: F Belgium Supports F Picardy - English Channel
            Germany: F Picardy - English Channel
            Russia: A Norway - Belgium
            Russia: F North Sea Convoys A Norway - Belgium
            Without any paradox rule, there are two consistent resolutions. The supports of the English fleet in London
            and the German fleet in Picardy are not cut. That means that the French fleet in the English Channel and
            the Russian fleet in the North Sea are dislodged, which makes it impossible to cut the support. The other
            resolution is that the supports of the English fleet in London the German fleet in Picardy are cut. In that
            case the French fleet in the English Channel and the Russian fleet in the North Sea will survive and will
            not be dislodged. This gives the possibility to cut the support.
            The 1971 paradox rule and the 2000 rule (see issue 4.A.2) do not have an answer on this.
            According to the 1982 rule, the supports are not cut which means that the French fleet in the English
            Channel and the Russian fleet in the North Sea are dislodged.
            The Szykman (which I prefer), has the same result as the 1982 rule. The supports are not cut, the convoying
            armies fail to move, the fleet in Picardy dislodges the fleet in English Channel and the fleet in Edinburgh
            dislodges the fleet in the North Sea.
            The DPTG rule has in this case the same result as the Szykman rule, because the failing of all convoys is a
            consistent resolution. So, the armies in Brest and Norway fail to move, while the fleets in Edinburgh and
            Picardy succeed to move. When the 'All Hold' rule is used, the movement of the armies in Brest and Norway
            as the fleets in Edinburgh and Picardy will fail.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F EDI', 'F LON'])
        self.set_units(game, 'FRANCE', ['A BRE', 'F ENG'])
        self.set_units(game, 'GERMANY', ['F BEL', 'F PIC'])
        self.set_units(game, 'RUSSIA', ['A NWY', 'F NTH'])
        self.set_orders(game, 'ENGLAND', ['F EDI - NTH', 'F LON S F EDI - NTH'])
        self.set_orders(game, 'FRANCE', ['A BRE - LON', 'F ENG C A BRE - LON'])
        self.set_orders(game, 'GERMANY', ['F BEL S F PIC - ENG', 'F PIC - ENG'])
        self.set_orders(game, 'RUSSIA', ['A NWY - BEL', 'F NTH C A NWY - BEL'])
        self.process(game)
        assert self.check_results(game, 'F EDI', OK)
        assert self.check_results(game, 'F LON', OK)
        assert self.check_results(game, 'A BRE', NO_CONVOY)
        assert self.check_results(game, 'F ENG', DISLODGED)
        assert self.check_results(game, 'F BEL', OK)
        assert self.check_results(game, 'F PIC', OK)
        assert self.check_results(game, 'A NWY', NO_CONVOY)
        assert self.check_results(game, 'F NTH', DISLODGED)
        assert check_dislodged(game, 'F ENG', 'F PIC')
        assert check_dislodged(game, 'F NTH', 'F EDI')
        assert self.owner_name(game, 'F EDI') is None
        assert self.owner_name(game, 'F LON') == 'ENGLAND'
        assert self.owner_name(game, 'A BRE') == 'FRANCE'
        assert self.owner_name(game, 'F ENG') == 'GERMANY'
        assert self.owner_name(game, 'F BEL') == 'GERMANY'
        assert self.owner_name(game, 'F PIC') is None
        assert self.owner_name(game, 'A NWY') == 'RUSSIA'
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'

    def test_6_f_23(self):
        """ 6.F.23. TEST CASE, SECOND ORDER PARADOX WITH TWO EXCLUSIVE CONVOYS
            In this paradox there are two consistent resolutions, but where the two convoys do not fail or succeed at
            the same time. This fact is important for the DPTG resolution.
            England: F Edinburgh - North Sea
            England: F Yorkshire Supports F Edinburgh - North Sea
            France: A Brest - London
            France: F English Channel Convoys A Brest - London
            Germany: F Belgium Supports F English Channel
            Germany: F London Supports F North Sea
            Italy: F Mid-Atlantic Ocean - English Channel
            Italy: F Irish Sea Supports F Mid-Atlantic Ocean - English Channel
            Russia: A Norway - Belgium
            Russia: F North Sea Convoys A Norway - Belgium
            Without any paradox rule, there are two consistent resolutions. In one resolution, the convoy in the
            English Channel is dislodged by the fleet in the Mid-Atlantic Ocean, while the convoy in the North Sea
            succeeds. In the other resolution, it is the other way around. The convoy in the North Sea is dislodged by
            the fleet in Edinburgh, while the convoy in the English Channel succeeds.
            The 1971 paradox rule and the 2000 rule (see issue 4.A.2) do not have an answer on this.
            According to the 1982 rule, the supports are not cut which means that the none of the units move.
            The Szykman (which I prefer), has the same result as the 1982 rule. The convoying armies fail to move and
            the supports are not cut. Because of the failure to cut the support, no fleet succeeds to move.
            When the 'All Hold' rule is used, the movement of the armies and the fleets all fail.
            Since there is no consistent resolution where all convoys fail, the DPTG rule has the same result as the
            'All Hold' rule. That means the movement of all units fail.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F EDI', 'F YOR'])
        self.set_units(game, 'FRANCE', ['A BRE', 'F ENG'])
        self.set_units(game, 'GERMANY', ['F BEL', 'F LON'])
        self.set_units(game, 'ITALY', ['F MAO', 'F IRI'])
        self.set_units(game, 'RUSSIA', ['A NWY', 'F NTH'])
        self.set_orders(game, 'ENGLAND', ['F EDI - NTH', 'F YOR S F EDI - NTH'])
        self.set_orders(game, 'FRANCE', ['A BRE - LON', 'F ENG C A BRE - LON'])
        self.set_orders(game, 'GERMANY', ['F BEL S F ENG', 'F LON S F NTH'])
        self.set_orders(game, 'ITALY', ['F MAO - ENG', 'F IRI S F MAO - ENG'])
        self.set_orders(game, 'RUSSIA', ['A NWY - BEL', 'F NTH C A NWY - BEL'])
        self.process(game)
        assert self.check_results(game, 'F EDI', BOUNCE)
        assert self.check_results(game, 'F YOR', OK)
        assert self.check_results(game, 'A BRE', NO_CONVOY)
        assert self.check_results(game, 'F ENG', DISRUPTED)
        assert self.check_results(game, 'F BEL', OK)
        assert self.check_results(game, 'F LON', OK)
        assert self.check_results(game, 'F MAO', BOUNCE)
        assert self.check_results(game, 'F IRI', OK)
        assert self.check_results(game, 'A NWY', NO_CONVOY)
        assert self.check_results(game, 'F NTH', DISRUPTED)
        assert self.owner_name(game, 'F EDI') == 'ENGLAND'
        assert self.owner_name(game, 'F YOR') == 'ENGLAND'
        assert self.owner_name(game, 'A BRE') == 'FRANCE'
        assert self.owner_name(game, 'F ENG') == 'FRANCE'
        assert self.owner_name(game, 'F BEL') == 'GERMANY'
        assert self.owner_name(game, 'F LON') == 'GERMANY'
        assert self.owner_name(game, 'F MAO') == 'ITALY'
        assert self.owner_name(game, 'F IRI') == 'ITALY'
        assert self.owner_name(game, 'A NWY') == 'RUSSIA'
        assert self.owner_name(game, 'F NTH') == 'RUSSIA'

    def test_6_f_24(self):
        """ 6.F.24. TEST CASE, SECOND ORDER PARADOX WITH NO RESOLUTION
            As first order paradoxes, second order paradoxes come in two flavors, with two resolutions or no resolution.
            England: F Edinburgh - North Sea
            England: F London Supports F Edinburgh - North Sea
            England: F Irish Sea - English Channel
            England: F Mid-Atlantic Ocean Supports F Irish Sea - English Channel
            France: A Brest - London
            France: F English Channel Convoys A Brest - London
            France: F Belgium Supports F English Channel
            Russia: A Norway - Belgium
            Russia: F North Sea Convoys A Norway - Belgium
            When no paradox rule is used, there is no consistent resolution. If the French support in Belgium is cut,
            the French fleet in the English Channel will be dislodged. That means that the support of London will not
            be cut and the fleet in Edinburgh will dislodge the Russian fleet in the North Sea. In this way the support
            in Belgium is not cut! But if the support in Belgium is not cut, the Russian fleet in the North Sea will
            not be dislodged and the army in Norway can cut the support in Belgium.
            The 1971 paradox rule and the 2000 rule (see issue 4.A.2) do not have an answer on this. According to the
            1982 rule, the supports are not cut which means that the French fleet in the English Channel will survive
            and but the Russian fleet in the North Sea is dislodged.
            If the Szykman alternative is used (which I prefer), the supports are not cut and the convoying armies fail
            to move, which has the same result as the 1982 rule in this case.
            When the 'All Hold' rule is used, the movement of the armies in Brest and Norway as the fleets in Edinburgh
            and the Irish Sea will fail. Since there is no consistent resolution where all convoys fail, the DPTG has
            in this case the same result as the 'All Hold' rule.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F EDI', 'F LON', 'F IRI', 'F MAO'])
        self.set_units(game, 'FRANCE', ['A BRE', 'F ENG', 'F BEL'])
        self.set_units(game, 'RUSSIA', ['A NWY', 'F NTH'])
        self.set_orders(game, 'ENGLAND', ['F EDI - NTH', 'F LON S F EDI - NTH', 'F IRI - ENG', 'F MAO S F IRI - ENG'])
        self.set_orders(game, 'FRANCE', ['A BRE - LON', 'F ENG C A BRE - LON', 'F BEL S F ENG'])
        self.set_orders(game, 'RUSSIA', ['A NWY - BEL', 'F NTH C A NWY - BEL'])
        self.process(game)
        assert self.check_results(game, 'F EDI', OK)
        assert self.check_results(game, 'F LON', OK)
        assert self.check_results(game, 'F IRI', BOUNCE)
        assert self.check_results(game, 'F MAO', OK)
        assert self.check_results(game, 'A BRE', NO_CONVOY)
        assert self.check_results(game, 'F ENG', DISRUPTED)
        assert self.check_results(game, 'F BEL', OK)
        assert self.check_results(game, 'A NWY', NO_CONVOY)
        assert self.check_results(game, 'F NTH', DISLODGED)
        assert check_dislodged(game, 'F NTH', 'F EDI')
        assert self.owner_name(game, 'F EDI') is None
        assert self.owner_name(game, 'F LON') == 'ENGLAND'
        assert self.owner_name(game, 'F IRI') == 'ENGLAND'
        assert self.owner_name(game, 'F MAO') == 'ENGLAND'
        assert self.owner_name(game, 'A BRE') == 'FRANCE'
        assert self.owner_name(game, 'F ENG') == 'FRANCE'
        assert self.owner_name(game, 'F BEL') == 'FRANCE'
        assert self.owner_name(game, 'A NWY') == 'RUSSIA'
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'

    # 6.G. TEST CASES, CONVOYING TO ADJACENT PLACES
    def test_6_g_1(self):
        """ 6.G.1. TEST CASE, TWO UNITS CAN SWAP PLACES BY CONVOY
            The only way to swap two units, is by convoy.
            England: A Norway - Sweden
            England: F Skagerrak Convoys A Norway - Sweden
            Russia: A Sweden - Norway
            In most interpretation of the rules, the units in Norway and Sweden will be swapped. However, if
            explicit adjacent convoying is used (see issue 4.A.3), then it is just a head to head battle.
            I prefer the 2000 rules, so the units are swapped.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['A NWY', 'F SKA'])
        self.set_units(game, 'RUSSIA', ['A SWE'])
        self.set_orders(game, 'ENGLAND', ['A NWY - SWE', 'F SKA C A NWY - SWE'])
        self.set_orders(game, 'RUSSIA', ['A SWE - NWY'])
        self.process(game)
        assert self.check_results(game, 'A NWY', OK)
        assert self.check_results(game, 'F SKA', OK)
        assert self.check_results(game, 'A SWE', OK)
        assert self.owner_name(game, 'A NWY') == 'RUSSIA'
        assert self.owner_name(game, 'F SKA') == 'ENGLAND'
        assert self.owner_name(game, 'A SWE') == 'ENGLAND'

    def test_6_g_2(self):
        """ 6.G.2. TEST CASE, KIDNAPPING AN ARMY
            Germany promised England to support to dislodge the Russian fleet in Sweden and it promised Russia to
            support to dislodge the English army in Norway. Instead, the joking German orders a convoy.
            England: A Norway - Sweden
            Russia: F Sweden - Norway
            Germany: F Skagerrak Convoys A Norway - Sweden
            See issue 4.A.3.
            When the 1982/2000 rulebook is used (which I prefer), England has no intent to swap and it is just a head
            to head battle were both units will fail to move. When explicit adjacent convoying is used (DPTG), the
            English move is not a convoy and again it just a head to head battle were both units will fail to move.
            In all other interpretations, the army in Norway will be convoyed and swap its place with the fleet in
            Sweden.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', 'A NWY')
        self.set_units(game, 'RUSSIA', 'F SWE')
        self.set_units(game, 'GERMANY', 'F SKA')
        self.set_orders(game, 'ENGLAND', 'A NWY - SWE')
        self.set_orders(game, 'RUSSIA', 'F SWE - NWY')
        self.set_orders(game, 'GERMANY', 'F SKA C A NWY - SWE')
        self.process(game)
        assert self.check_results(game, 'A NWY', BOUNCE)
        assert self.check_results(game, 'F SWE', BOUNCE)
        assert self.check_results(game, 'F SKA', NO_CONVOY)
        assert self.owner_name(game, 'A NWY') == 'ENGLAND'
        assert self.owner_name(game, 'F SWE') == 'RUSSIA'
        assert self.owner_name(game, 'F SKA') == 'GERMANY'

    def test_6_g_3(self):
        """ 6.G.3. TEST CASE, KIDNAPPING WITH A DISRUPTED CONVOY
            When kidnapping of armies is allowed, a move can be sabotaged by a fleet that is almost certainly dislodged.
            France: F Brest - English Channel
            France: A Picardy - Belgium
            France: A Burgundy Supports A Picardy - Belgium
            France: F Mid-Atlantic Ocean Supports F Brest - English Channel
            England: F English Channel Convoys A Picardy - Belgium
            See issue 4.A.3. If a convoy always takes precedence over a land route (choice a), the move from Picardy to
            Belgium fails. It tries to convoy and the convoy is disrupted.
            For choice b and c, there is no unit moving in opposite direction for the move of the army in Picardy.
            For this reason, the move for the army in Picardy is not by convoy and succeeds over land.
            When the 1982 or 2000 rules are used (choice d), then it is not the "intent" of the French army in Picardy
            to convoy. The move from Picardy to Belgium is just a successful move over land.
            When explicit adjacent convoying is used (DPTG, choice e), the order of the French army in Picardy is not
            a convoy order. So, it just ordered over land, and that move succeeds. This is an excellent example why
            the convoy route should not automatically have priority over the land route. It would just be annoying for
            the attacker and this situation is without fun. I prefer the 1982 rule with the 2000 clarification.
            According to these rules the move from Picardy succeeds.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'FRANCE', ['F BRE', 'A PIC', 'A BUR', 'F MAO'])
        self.set_units(game, 'ENGLAND', ['F ENG'])
        self.set_orders(game, 'FRANCE', ['F BRE - ENG', 'A PIC - BEL', 'A BUR S A PIC - BEL', 'F MAO S F BRE - ENG'])
        self.set_orders(game, 'ENGLAND', ['F ENG C A PIC - BEL'])
        self.process(game)
        assert self.check_results(game, 'F BRE', OK)
        assert self.check_results(game, 'A PIC', OK)
        assert self.check_results(game, 'A BUR', OK)
        assert self.check_results(game, 'F MAO', OK)
        assert self.check_results(game, 'F ENG', DISLODGED)
        assert self.check_results(game, 'F ENG', NO_CONVOY)
        assert check_dislodged(game, 'F ENG', 'F BRE')
        assert self.owner_name(game, 'F BRE') is None
        assert self.owner_name(game, 'A PIC') is None
        assert self.owner_name(game, 'A BUR') == 'FRANCE'
        assert self.owner_name(game, 'F MAO') == 'FRANCE'
        assert self.owner_name(game, 'F ENG') == 'FRANCE'
        assert self.owner_name(game, 'A BEL') == 'FRANCE'

    def test_6_g_4(self):
        """ 6.G.4. TEST CASE, KIDNAPPING WITH A DISRUPTED CONVOY AND OPPOSITE MOVE
            In the situation of the previous test case it was rather clear that the army didn't want to take the
            convoy. But what if there is an army moving in opposite direction?
            France: F Brest - English Channel
            France: A Picardy - Belgium
            France: A Burgundy Supports A Picardy - Belgium
            France: F Mid-Atlantic Ocean Supports F Brest - English Channel
            England: F English Channel Convoys A Picardy - Belgium
            England: A Belgium - Picardy
            See issue 4.A.3. If a convoy always takes precedence over a land route (choice a), the move from Picardy to
            Belgium fails. It tries to convoy and the convoy is disrupted.
            For choice b the convoy is also taken, because there is a unit in Belgium moving in opposite direction.
            This means that the convoy is disrupted and the move from Picardy to Belgium fails.
            For choice c the convoy is not taken. Although, the unit in Belgium is moving in opposite direction,
            the army will not take a disrupted convoy. So, the move from Picardy to Belgium succeeds.
            When the 1982 or 2000 rules are used (choice d), then it is not the "intent" of the French army in Picardy
            to convoy. The move from Picardy to Belgium is just a successful move over land.
            When explicit adjacent convoying is used (DPTG, choice e), the order of the French army in Picardy is not
            a convoy order. So, it just ordered over land, and that move succeeds.
            Again an excellent example why the convoy route should not automatically have priority over the land route.
            It would just be annoying for the attacker and this situation is without fun. I prefer the 1982 rule with
            the 2000 clarification. According to these rules the move from Picardy succeeds.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'FRANCE', ['F BRE', 'A PIC', 'A BUR', 'F MAO'])
        self.set_units(game, 'ENGLAND', ['F ENG', 'A BEL'])
        self.set_orders(game, 'FRANCE', ['F BRE - ENG', 'A PIC - BEL', 'A BUR S A PIC - BEL', 'F MAO S F BRE - ENG'])
        self.set_orders(game, 'ENGLAND', ['F ENG C A PIC - BEL', 'A BEL - PIC'])
        self.process(game)
        assert self.check_results(game, 'F BRE', OK)
        assert self.check_results(game, 'A PIC', OK)
        assert self.check_results(game, 'A BUR', OK)
        assert self.check_results(game, 'F MAO', OK)
        assert self.check_results(game, 'F ENG', DISLODGED)
        assert self.check_results(game, 'F ENG', NO_CONVOY)
        assert self.check_results(game, 'A BEL', DISLODGED)
        assert check_dislodged(game, 'F ENG', 'F BRE')
        assert check_dislodged(game, 'A BEL', 'A PIC')
        assert self.owner_name(game, 'F BRE') is None
        assert self.owner_name(game, 'A PIC') is None
        assert self.owner_name(game, 'A BUR') == 'FRANCE'
        assert self.owner_name(game, 'F MAO') == 'FRANCE'
        assert self.owner_name(game, 'F ENG') == 'FRANCE'
        assert self.owner_name(game, 'A BEL') == 'FRANCE'

    def test_6_g_5(self):
        """ 6.G.5. TEST CASE, SWAPPING WITH INTENT
            When one of the convoying fleets is of the same nationality of the convoyed army, the "intent" is to convoy.
            Italy: A Rome - Apulia
            Italy: F Tyrrhenian Sea Convoys A Apulia - Rome
            Turkey: A Apulia - Rome
            Turkey: F Ionian Sea Convoys A Apulia - Rome
            See issue 4.A.3. When the 1982/2000 rulebook is used (which I prefer), the convoy depends on the "intent".
            Since there is an own fleet in the convoy, the intent is to convoy and the armies in Rome and Apulia swap
            places. For choices a, b and c of the issue there is also a convoy and the same swap takes place.
            When explicit adjacent convoying is used (DPTG, choice e), then the Turkish army did not receive an order
            to move by convoy. So, it is just a head to head battle and both the army in Rome and Apulia will not move.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ITALY', ['A ROM', 'F TYS'])
        self.set_units(game, 'TURKEY', ['A APU', 'F ION'])
        self.set_orders(game, 'ITALY', ['A ROM - APU', 'F TYS C A APU - ROM'])
        self.set_orders(game, 'TURKEY', ['A APU - ROM', 'F ION C A APU - ROM'])
        self.process(game)
        assert self.check_results(game, 'A ROM', OK)
        assert self.check_results(game, 'F TYS', OK)
        assert self.check_results(game, 'A APU', OK)
        assert self.check_results(game, 'F ION', OK)
        assert self.owner_name(game, 'A ROM') == 'TURKEY'
        assert self.owner_name(game, 'F TYS') == 'ITALY'
        assert self.owner_name(game, 'A APU') == 'ITALY'
        assert self.owner_name(game, 'F ION') == 'TURKEY'

    def test_6_g_6(self):
        """ 6.G.6. TEST CASE, SWAPPING WITH UNINTENDED INTENT
            The intent is questionable.
            England: A Liverpool - Edinburgh
            England: F English Channel Convoys A Liverpool - Edinburgh
            Germany: A Edinburgh - Liverpool
            France: F Irish Sea Hold
            France: F North Sea Hold
            Russia: F Norwegian Sea Convoys A Liverpool - Edinburgh
            Russia: F North Atlantic Ocean Convoys A Liverpool - Edinburgh
            See issue 4.A.3.
            For choice a, b and c the English army in Liverpool will move by convoy and consequentially the two armies
            are swapped. For choice d, the 1982/2000 rulebook (which I prefer), the convoy depends on the "intent".
            England intended to convoy via the French fleets in the Irish Sea and the North Sea. However, the French
            did not order the convoy. The alternative route with the Russian fleets was unintended. The English fleet
            in the English Channel (with the convoy order) is not part of this alternative route with the Russian
            fleets. Since England still "intent" to convoy, the move from Liverpool to Edinburgh should be via convoy
            and the two armies are swapped. Although, you could argue that this is not really according to the
            clarification of the 2000 rulebook. When explicit adjacent convoying is used (DPTG, choice e), then the
            English army did not receive an order to move by convoy. So, it is just a head to head battle and both the
            army in Edinburgh and Liverpool will not move.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['A LVP', 'F ENG'])
        self.set_units(game, 'GERMANY', ['A EDI'])
        self.set_units(game, 'FRANCE', ['F IRI', 'F NTH'])
        self.set_units(game, 'RUSSIA', ['F NWG', 'F NAO'])
        self.set_orders(game, 'ENGLAND', ['A LVP - EDI', 'F ENG C A LVP - EDI'])
        self.set_orders(game, 'GERMANY', ['A EDI - LVP'])
        self.set_orders(game, 'FRANCE', ['F IRI H', 'F NTH H'])
        self.set_orders(game, 'RUSSIA', ['F NWG C A LVP - EDI', 'F NAO C A LVP - EDI'])
        self.process(game)
        assert self.check_results(game, 'A LVP', OK)
        assert self.check_results(game, 'F ENG', NO_CONVOY)
        assert self.check_results(game, 'A EDI', OK)
        assert self.check_results(game, 'F IRI', OK)
        assert self.check_results(game, 'F NTH', OK)
        assert self.check_results(game, 'F NWG', OK)
        assert self.check_results(game, 'F NAO', OK)
        assert self.owner_name(game, 'A LVP') == 'GERMANY'
        assert self.owner_name(game, 'F ENG') == 'ENGLAND'
        assert self.owner_name(game, 'A EDI') == 'ENGLAND'
        assert self.owner_name(game, 'F IRI') == 'FRANCE'
        assert self.owner_name(game, 'F NTH') == 'FRANCE'
        assert self.owner_name(game, 'F NWG') == 'RUSSIA'
        assert self.owner_name(game, 'F NAO') == 'RUSSIA'

    def test_6_g_7(self):
        """ 6.G.7. TEST CASE, SWAPPING WITH ILLEGAL INTENT
            Can the intent made clear with an impossible order?
            England: F Skagerrak Convoys A Sweden - Norway
            England: F Norway - Sweden
            Russia: A Sweden - Norway
            Russia: F Gulf of Bothnia Convoys A Sweden - Norway
            See issue 4.A.3 and 4.E.1.
            If for issue 4.A.3 choice a, b or c has been taken, then the army in Sweden moves by convoy and swaps
            places with the fleet in Norway.
            However, if for issue 4.A.3 the 1982/2000 has been chosen (choice d), then the "intent" is important.
            The question is whether the fleet in the Gulf of Bothnia can express the intent. If the order for this
            fleet is considered illegal (see issue 4.E.1), then this order must be ignored and there is no intent to
            swap. In that case none of the units move. If explicit convoying is used (DPTG, choice e of issue 4.A.3)
            then the army in Sweden will take the land route and none of the units move.
            I prefer the 1982/2000 rule and that any orders that can't be valid are illegal. So, the order of the fleet
            in the Gulf of Bothnia is ignored and can not show the intent. There is no convoy, so no unit will move.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F SKA', 'F NWY'])
        self.set_units(game, 'RUSSIA', ['A SWE', 'F BOT'])
        self.set_orders(game, 'ENGLAND', ['F SKA C A SWE - NWY', 'F NWY - SWE'])
        self.set_orders(game, 'RUSSIA', ['A SWE - NWY', 'F BOT C A SWE - NWY'])
        self.process(game)
        assert self.check_results(game, 'F SKA', NO_CONVOY)
        assert self.check_results(game, 'F NWY', BOUNCE)
        assert self.check_results(game, 'A SWE', BOUNCE)
        assert self.check_results(game, 'F BOT', VOID)
        assert self.owner_name(game, 'F SKA') == 'ENGLAND'
        assert self.owner_name(game, 'F NWY') == 'ENGLAND'
        assert self.owner_name(game, 'A SWE') == 'RUSSIA'
        assert self.owner_name(game, 'F BOT') == 'RUSSIA'

    def test_6_g_8(self):
        """ 6.G.8. TEST CASE, EXPLICIT CONVOY THAT ISN'T THERE
            What to do when a unit is explicitly ordered to move via convoy and the convoy is not there?
            France: A Belgium - Holland via Convoy
            England: F North Sea - Helgoland Bight
            England: A Holland - Kiel
            The French army in Belgium intended to move convoyed with the English fleet in the North Sea. But the
            English changed their plans.
            See issue 4.A.3.
            If choice a, b or c has been taken, then the 'via Convoy' directive has no meaning and the army in Belgium
            will move to Holland. If the 1982/2000 rulebook is used (choice d, which I prefer), the "via Convoy" has
            meaning, but only when there is both a land route and a convoy route. Since there is no convoy the
            "via Convoy" directive should be ignored. And the move from Belgium to Holland succeeds.
            If explicit adjacent convoying is used (DPTG, choice e), then the unit can only go by convoy. Since there
            is no convoy, the move from Belgium to Holland fails.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'FRANCE', ['A BEL'])
        self.set_units(game, 'ENGLAND', ['F NTH', 'A HOL'])
        self.set_orders(game, 'FRANCE', ['A BEL - HOL VIA'])
        self.set_orders(game, 'ENGLAND', ['F NTH - HEL', 'A HOL - KIE'])
        self.process(game)
        assert self.check_results(game, 'A BEL', OK)
        assert self.check_results(game, 'F NTH', OK)
        assert self.check_results(game, 'A HOL', OK)
        assert self.owner_name(game, 'A BEL') is None
        assert self.owner_name(game, 'F NTH') is None
        assert self.owner_name(game, 'A HOL') == 'FRANCE'
        assert self.owner_name(game, 'F HEL') == 'ENGLAND'
        assert self.owner_name(game, 'A KIE') == 'ENGLAND'

    def test_6_g_9(self):
        """ 6.G.9. TEST CASE, SWAPPED OR DISLODGED?
            The 1982 rulebook says that whether the move is over land or via convoy depends on the "intent" as shown
            by the totality of the orders written by the player governing the army (see issue 4.A.3). In this test
            case the English army in Norway will end in all cases in Sweden. But whether it is convoyed or not has
            effect on the Russian army. In case of convoy the Russian army ends in Norway and in case of a land route
            the Russian army is dislodged.
            England: A Norway - Sweden
            England: F Skagerrak Convoys A Norway - Sweden
            England: F Finland Supports A Norway - Sweden
            Russia: A Sweden - Norway
            See issue 4.A.3.
            For choice a, b and c the move of the army in Norway is by convoy and the armies in Norway and Sweden are
            swapped. If the 1982 rulebook is used with the clarification of the 2000 rulebook (choice d, which I
            prefer), the intent of the English player is to convoy, since it ordered the fleet in Skagerrak to convoy.
            Therefore, the armies in Norway and Sweden are swapped. When explicit adjacent convoying is used (DTPG,
            choice e), then the unit in Norway did not receive an order to move by convoy and the land route should be
            considered. The Russian army in Sweden is dislodged.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['A NWY', 'F SKA', 'F FIN'])
        self.set_units(game, 'RUSSIA', ['A SWE'])
        self.set_orders(game, 'ENGLAND', ['A NWY - SWE', 'F SKA C A NWY - SWE', 'F FIN S A NWY - SWE'])
        self.set_orders(game, 'RUSSIA', ['A SWE - NWY'])
        self.process(game)
        assert self.check_results(game, 'A NWY', OK)
        assert self.check_results(game, 'F SKA', OK)
        assert self.check_results(game, 'F FIN', OK)
        assert self.check_results(game, 'A SWE', OK)
        assert self.owner_name(game, 'A NWY') == 'RUSSIA'
        assert self.owner_name(game, 'F SKA') == 'ENGLAND'
        assert self.owner_name(game, 'F FIN') == 'ENGLAND'
        assert self.owner_name(game, 'A SWE') == 'ENGLAND'

    def test_6_g_10(self):
        """ 6.G.10. TEST CASE, SWAPPED OR AN HEAD TO HEAD BATTLE?
            Can a dislodged unit have effect on the attackers area, when the attacker moved by convoy?
            England: A Norway - Sweden via Convoy
            England: F Denmark Supports A Norway - Sweden
            England: F Finland Supports A Norway - Sweden
            Germany: F Skagerrak Convoys A Norway - Sweden
            Russia: A Sweden - Norway
            Russia: F Barents Sea Supports A Sweden - Norway
            France: F Norwegian Sea - Norway
            France: F North Sea Supports F Norwegian Sea - Norway
            Since England ordered the army in Norway to move explicitly via convoy and the army in Sweden is moving
            in opposite direction, only the convoyed route should be considered regardless of the rulebook used. It
            is clear that the army in Norway will dislodge the Russian army in Sweden. Since the strength of three is
            in all cases the strongest force. The army in Sweden will not advance to Norway, because it can not beat
            the force in the Norwegian Sea. It will be dislodged by the army from Norway.
            The more interesting question is whether French fleet in the Norwegian Sea is bounced by the Russian army
            from Sweden. This depends on the interpretation of issue 4.A.7. If the rulebook is taken literally
            (choice a), then a dislodged unit can not bounce a unit in the area where the attacker came from. This
            would mean that the move of the fleet in the Norwegian Sea succeeds However, if choice b is taken
            (which I prefer), then a bounce is still possible, when there is no head to head battle. So, the fleet in
            the Norwegian Sea will fail to move.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['A NWY', 'F DEN', 'F FIN'])
        self.set_units(game, 'GERMANY', ['F SKA'])
        self.set_units(game, 'RUSSIA', ['A SWE', 'F BAR'])
        self.set_units(game, 'FRANCE', ['F NWG', 'F NTH'])
        self.set_orders(game, 'ENGLAND', ['A NWY - SWE VIA', 'F DEN S A NWY - SWE', 'F FIN S A NWY - SWE'])
        self.set_orders(game, 'GERMANY', ['F SKA C A NWY - SWE'])
        self.set_orders(game, 'RUSSIA', ['A SWE - NWY', 'F BAR S A SWE - NWY'])
        self.set_orders(game, 'FRANCE', ['F NWG - NWY', 'F NTH S F NWG - NWY'])
        self.process(game)
        assert self.check_results(game, 'A NWY', OK)
        assert self.check_results(game, 'F DEN', OK)
        assert self.check_results(game, 'F FIN', OK)
        assert self.check_results(game, 'F SKA', OK)
        assert self.check_results(game, 'A SWE', BOUNCE)
        assert self.check_results(game, 'A SWE', DISLODGED)
        assert self.check_results(game, 'F BAR', OK)
        assert self.check_results(game, 'F NWG', BOUNCE)
        assert self.check_results(game, 'F NTH', OK)
        assert check_dislodged(game, 'A SWE', 'A NWY')
        assert self.owner_name(game, 'A NWY') is None
        assert self.owner_name(game, 'F DEN') == 'ENGLAND'
        assert self.owner_name(game, 'F FIN') == 'ENGLAND'
        assert self.owner_name(game, 'F SKA') == 'GERMANY'
        assert self.owner_name(game, 'A SWE') == 'ENGLAND'
        assert self.owner_name(game, 'F BAR') == 'RUSSIA'
        assert self.owner_name(game, 'F NWG') == 'FRANCE'
        assert self.owner_name(game, 'F NTH') == 'FRANCE'

    def test_6_g_11(self):
        """ 6.G.11. TEST CASE, A CONVOY TO AN ADJACENT PLACE WITH A PARADOX
            In this case the convoy route is available when the land route is chosen and the convoy route is not
            available when the convoy route is chosen.
            England: F Norway Supports F North Sea - Skagerrak
            England: F North Sea - Skagerrak
            Russia: A Sweden - Norway
            Russia: F Skagerrak Convoys A Sweden - Norway
            Russia: F Barents Sea Supports A Sweden - Norway
            See issue 4.A.2 and 4.A.3.
            If for issue 4.A.3, choice b, c or e has been taken, then the move from Sweden to Norway is not a
            convoy and the English fleet in Norway is dislodged and the fleet in Skagerrak will not be dislodged.
            If choice a or d (1982/2000 rule) has been taken for issue 4.A.3, then the move from Sweden to Norway
            must be treated as a convoy. At that moment the situation becomes paradoxical. When the 'All Hold' rule is
            used, both the army in Sweden as the fleet in the North Sea will not advance. In all other paradox rules
            the English fleet in the North Sea will dislodge the Russian fleet in Skagerrak and the army in Sweden will
            not advance.
            I prefer the 1982 rule with the 2000 rulebook clarification concerning the convoy to adjacent places and
            I prefer the Szykman rule for paradox resolving. That means that according to these preferences the fleet
            in the North Sea will dislodge the Russian fleet in Skagerrak and the army in Sweden will not advance.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F NWY', 'F NTH'])
        self.set_units(game, 'RUSSIA', ['A SWE', 'F SKA', 'F BAR'])
        self.set_orders(game, 'ENGLAND', ['F NWY S F NTH - SKA', 'F NTH - SKA'])
        self.set_orders(game, 'RUSSIA', ['A SWE - NWY', 'F SKA C A SWE - NWY', 'F BAR S A SWE - NWY'])
        self.process(game)
        assert self.check_results(game, 'F NWY', OK)
        assert self.check_results(game, 'F NTH', OK)
        assert self.check_results(game, 'A SWE', NO_CONVOY)
        assert self.check_results(game, 'F SKA', DISLODGED)
        assert self.check_results(game, 'F BAR', NO_CONVOY)
        assert check_dislodged(game, 'F SKA', 'F NTH')
        assert self.owner_name(game, 'F NWY') == 'ENGLAND'
        assert self.owner_name(game, 'F NTH') is None
        assert self.owner_name(game, 'A SWE') == 'RUSSIA'
        assert self.owner_name(game, 'F SKA') == 'ENGLAND'
        assert self.owner_name(game, 'F BAR') == 'RUSSIA'

    def test_6_g_12(self):
        """ 6.G.12. TEST CASE, SWAPPING TWO UNITS WITH TWO CONVOYS
            Of course, two armies can also swap by when they are both convoyed.
            England: A Liverpool - Edinburgh via Convoy
            England: F North Atlantic Ocean Convoys A Liverpool - Edinburgh
            England: F Norwegian Sea Convoys A Liverpool - Edinburgh
            Germany: A Edinburgh - Liverpool via Convoy
            Germany: F North Sea Convoys A Edinburgh - Liverpool
            Germany: F English Channel Convoys A Edinburgh - Liverpool
            Germany: F Irish Sea Convoys A Edinburgh - Liverpool
            The armies in Liverpool and Edinburgh are swapped.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['A LVP', 'F NAO', 'F NWG'])
        self.set_units(game, 'GERMANY', ['A EDI', 'F NTH', 'F ENG', 'F IRI'])
        self.set_orders(game, 'ENGLAND', ['A LVP - EDI VIA', 'F NAO C A LVP - EDI', 'F NWG C A LVP - EDI'])
        self.set_orders(game, 'GERMANY', ['A EDI - LVP VIA', 'F NTH C A EDI - LVP', 'F ENG C A EDI - LVP',
                                          'F IRI C A EDI - LVP'])
        self.process(game)
        assert self.check_results(game, 'A LVP', OK)
        assert self.check_results(game, 'F NAO', OK)
        assert self.check_results(game, 'F NWG', OK)
        assert self.check_results(game, 'A EDI', OK)
        assert self.check_results(game, 'F NTH', OK)
        assert self.check_results(game, 'F ENG', OK)
        assert self.check_results(game, 'F IRI', OK)
        assert self.owner_name(game, 'A LVP') == 'GERMANY'
        assert self.owner_name(game, 'F NAO') == 'ENGLAND'
        assert self.owner_name(game, 'F NWG') == 'ENGLAND'
        assert self.owner_name(game, 'A EDI') == 'ENGLAND'
        assert self.owner_name(game, 'F NTH') == 'GERMANY'
        assert self.owner_name(game, 'F ENG') == 'GERMANY'
        assert self.owner_name(game, 'F IRI') == 'GERMANY'

    def test_6_g_13(self):
        """ 6.G.13. TEST CASE, SUPPORT CUT ON ATTACK ON ITSELF VIA CONVOY
            If a unit is attacked by a supported unit, it is not possible to prevent dislodgement by trying to cut
            the support. But what, if a move is attempted via a convoy?
            Austria: F Adriatic Sea Convoys A Trieste - Venice
            Austria: A Trieste - Venice via Convoy
            Italy: A Venice Supports F Albania - Trieste
            Italy: F Albania - Trieste
            First it should be mentioned that if for issue 4.A.3 choice b or c is taken, then the move from Trieste
            to Venice is just a move over land, because the army in Venice is not moving in opposite direction. In that
            case, the support of Venice will not be cut as normal.
            In any other choice for issue 4.A.3, it should be decided whether the Austrian attack is considered to be
            coming from Trieste or from the Adriatic Sea. If it comes from Trieste, the support in Venice is not cut
            and the army in Trieste is dislodged by the fleet in Albania. If the Austrian attack is considered to be
            coming from the Adriatic Sea, then the support is cut and the army in Trieste will not be dislodged. See
            also issue 4.A.4. First of all, I prefer the 1982/2000 rules for adjacent convoying. This means that I
            prefer the move from Trieste uses the convoy. Furthermore, I think that the two Italian units are still
            stronger than the army in Trieste. Therefore, I prefer that the support in Venice is not cut and that the
            army in Trieste is dislodged by the fleet in Albania.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'AUSTRIA', ['F ADR', 'A TRI'])
        self.set_units(game, 'ITALY', ['A VEN', 'F ALB'])
        self.set_orders(game, 'AUSTRIA', ['F ADR C A TRI - VEN', 'A TRI - VEN VIA'])
        self.set_orders(game, 'ITALY', ['A VEN S F ALB - TRI', 'F ALB - TRI'])
        self.process(game)
        assert self.check_results(game, 'F ADR', OK)
        assert self.check_results(game, 'A TRI', DISLODGED)
        assert self.check_results(game, 'A TRI', BOUNCE)
        assert self.check_results(game, 'A VEN', OK)
        assert self.check_results(game, 'F ALB', OK)
        assert check_dislodged(game, 'A TRI', 'F ALB')
        assert self.owner_name(game, 'F ADR') == 'AUSTRIA'
        assert self.owner_name(game, 'F TRI') == 'ITALY'
        assert self.owner_name(game, 'A VEN') == 'ITALY'
        assert self.owner_name(game, 'F ALB') is None

    def test_6_g_14(self):
        """ 6.G.14. TEST CASE, BOUNCE BY CONVOY TO ADJACENT PLACE
            Similar to test case 6.G.10, but now the other unit is taking the convoy.
            England: A Norway - Sweden
            England: F Denmark Supports A Norway - Sweden
            England: F Finland Supports A Norway - Sweden
            France: F Norwegian Sea - Norway
            France: F North Sea Supports F Norwegian Sea - Norway
            Germany: F Skagerrak Convoys A Sweden - Norway
            Russia: A Sweden - Norway via Convoy
            Russia: F Barents Sea Supports A Sweden - Norway
            Again the army in Sweden is bounced by the fleet in the Norwegian Sea. The army in Norway will move to
            Sweden and dislodge the Russian army.
            The final destination of the fleet in the Norwegian Sea depends on how issue 4.A.7 is resolved. If
            choice a is taken, then the fleet advances to Norway, but if choice b is taken (which I prefer) the fleet
            bounces and stays in the Norwegian Sea.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['A NWY', 'F DEN', 'F FIN'])
        self.set_units(game, 'FRANCE', ['F NWG', 'F NTH'])
        self.set_units(game, 'GERMANY', ['F SKA'])
        self.set_units(game, 'RUSSIA', ['A SWE', 'F BAR'])
        self.set_orders(game, 'ENGLAND', ['A NWY - SWE', 'F DEN S A NWY - SWE', 'F FIN S A NWY - SWE'])
        self.set_orders(game, 'FRANCE', ['F NWG - NWY', 'F NTH S F NWG - NWY'])
        self.set_orders(game, 'GERMANY', ['F SKA C A SWE - NWY'])
        self.set_orders(game, 'RUSSIA', ['A SWE - NWY VIA', 'F BAR S A SWE - NWY'])
        self.process(game)
        assert self.check_results(game, 'A NWY', OK)
        assert self.check_results(game, 'F DEN', OK)
        assert self.check_results(game, 'F FIN', OK)
        assert self.check_results(game, 'F NWG', BOUNCE)
        assert self.check_results(game, 'F NTH', OK)
        assert self.check_results(game, 'F SKA', OK)
        assert self.check_results(game, 'A SWE', DISLODGED)
        assert self.check_results(game, 'A SWE', BOUNCE)
        assert self.check_results(game, 'F BAR', OK)
        assert check_dislodged(game, 'A SWE', 'A NWY')
        assert self.owner_name(game, 'A NWY') is None
        assert self.owner_name(game, 'F DEN') == 'ENGLAND'
        assert self.owner_name(game, 'F FIN') == 'ENGLAND'
        assert self.owner_name(game, 'F NWG') == 'FRANCE'
        assert self.owner_name(game, 'F NTH') == 'FRANCE'
        assert self.owner_name(game, 'F SKA') == 'GERMANY'
        assert self.owner_name(game, 'A SWE') == 'ENGLAND'
        assert self.owner_name(game, 'F BAR') == 'RUSSIA'

    def test_6_g_15(self):
        """ 6.G.15. TEST CASE, BOUNCE AND DISLODGE WITH DOUBLE CONVOY
            Similar to test case 6.G.10, but now both units use a convoy and without some support.
            England: F North Sea Convoys A London - Belgium
            England: A Holland Supports A London - Belgium
            England: A Yorkshire - London
            England: A London - Belgium via Convoy
            France: F English Channel Convoys A Belgium - London
            France: A Belgium - London via Convoy
            The French army in Belgium is bounced by the army from Yorkshire. The army in London move to Belgium,
            dislodging the unit there.
            The final destination of the army in the Yorkshire depends on how issue 4.A.7 is resolved. If choice a is
            taken, then the army advances to London, but if choice b is taken (which I prefer) the army bounces and
            stays in Yorkshire.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F NTH', 'A HOL', 'A YOR', 'A LON'])
        self.set_units(game, 'FRANCE', ['F ENG', 'A BEL'])
        self.set_orders(game, 'ENGLAND', ['F NTH C A LON - BEL',
                                          'A HOL S A LON - BEL',
                                          'A YOR - LON',
                                          'A LON - BEL VIA'])
        self.set_orders(game, 'FRANCE', ['F ENG C A BEL - LON', 'A BEL - LON VIA'])
        self.process(game)
        assert self.check_results(game, 'F NTH', OK)
        assert self.check_results(game, 'A HOL', OK)
        assert self.check_results(game, 'A YOR', BOUNCE)
        assert self.check_results(game, 'A LON', OK)
        assert self.check_results(game, 'F ENG', OK)
        assert self.check_results(game, 'A BEL', BOUNCE)
        assert self.check_results(game, 'A BEL', DISLODGED)
        assert check_dislodged(game, 'A BEL', 'A LON')
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'A HOL') == 'ENGLAND'
        assert self.owner_name(game, 'A YOR') == 'ENGLAND'
        assert self.owner_name(game, 'A LON') is None
        assert self.owner_name(game, 'F ENG') == 'FRANCE'
        assert self.owner_name(game, 'A BEL') == 'ENGLAND'

    def test_6_g_16(self):
        """ 6.G.16. TEST CASE, THE TWO UNIT IN ONE AREA BUG, MOVING BY CONVOY
            If the adjudicator is not correctly implemented, this may lead to a resolution where two units end up in
            the same area.
            England: A Norway - Sweden
            England: A Denmark Supports A Norway - Sweden
            England: F Baltic Sea Supports A Norway - Sweden
            England: F North Sea - Norway
            Russia: A Sweden - Norway via Convoy
            Russia: F Skagerrak Convoys A Sweden - Norway
            Russia: F Norwegian Sea Supports A Sweden - Norway
            See decision details 5.B.6. If the 'PREVENT STRENGTH' is incorrectly implemented, due to the fact that it
            does not take into account that the 'PREVENT STRENGTH' is only zero when the unit is engaged in a head to
            head battle, then this goes wrong in this test case. The 'PREVENT STRENGTH' of Sweden would be zero,
            because the opposing unit in Norway successfully moves. Since, this strength would be zero, the fleet in
            the North Sea would move to Norway. However, although the 'PREVENT STRENGTH' is zero, the army in Sweden
            would also move to Norway. So, the final result would contain two units that successfully moved to Norway.
            Of course, this is incorrect. Norway will indeed successfully move to Sweden while the army in Sweden ends
            in Norway, because it is stronger then the fleet in the North Sea. This fleet will stay in the North Sea.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['A NWY', 'A DEN', 'F BAL', 'F NTH'])
        self.set_units(game, 'RUSSIA', ['A SWE', 'F SKA', 'F NWG'])
        self.set_orders(game, 'ENGLAND', ['A NWY - SWE', 'A DEN S A NWY - SWE', 'F BAL S A NWY - SWE', 'F NTH - NWY'])
        self.set_orders(game, 'RUSSIA', ['A SWE - NWY VIA', 'F SKA C A SWE - NWY', 'F NWG S A SWE - NWY'])
        self.process(game)
        assert self.check_results(game, 'A NWY', OK)
        assert self.check_results(game, 'A DEN', OK)
        assert self.check_results(game, 'F BAL', OK)
        assert self.check_results(game, 'F NTH', BOUNCE)
        assert self.check_results(game, 'A SWE', OK)
        assert self.check_results(game, 'F SKA', OK)
        assert self.check_results(game, 'F NWG', OK)
        assert self.owner_name(game, 'A NWY') == 'RUSSIA'
        assert self.owner_name(game, 'A DEN') == 'ENGLAND'
        assert self.owner_name(game, 'F BAL') == 'ENGLAND'
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'A SWE') == 'ENGLAND'
        assert self.owner_name(game, 'F SKA') == 'RUSSIA'
        assert self.owner_name(game, 'F NWG') == 'RUSSIA'

    def test_6_g_17(self):
        """ 6.G.17. TEST CASE, THE TWO UNIT IN ONE AREA BUG, MOVING OVER LAND
            Similar to the previous test case, but now the other unit moves by convoy.
            England: A Norway - Sweden via Convoy
            England: A Denmark Supports A Norway - Sweden
            England: F Baltic Sea Supports A Norway - Sweden
            England: F Skagerrak Convoys A Norway - Sweden
            England: F North Sea - Norway
            Russia: A Sweden - Norway
            Russia: F Norwegian Sea Supports A Sweden - Norway
            Sweden and Norway are swapped, while the fleet in the North Sea will bounce.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['A NWY', 'A DEN', 'F BAL', 'F SKA', 'F NTH'])
        self.set_units(game, 'RUSSIA', ['A SWE', 'F NWG'])
        self.set_orders(game, 'ENGLAND', ['A NWY - SWE VIA',
                                          'A DEN S A NWY - SWE',
                                          'F BAL S A NWY - SWE',
                                          'F SKA C A NWY - SWE',
                                          'F NTH - NWY'])
        self.set_orders(game, 'RUSSIA', ['A SWE - NWY', 'F NWG S A SWE - NWY'])
        self.process(game)
        assert self.check_results(game, 'A NWY', OK)
        assert self.check_results(game, 'A DEN', OK)
        assert self.check_results(game, 'F BAL', OK)
        assert self.check_results(game, 'F SKA', OK)
        assert self.check_results(game, 'F NTH', BOUNCE)
        assert self.check_results(game, 'A SWE', OK)
        assert self.check_results(game, 'F NWG', OK)
        assert self.owner_name(game, 'A NWY') == 'RUSSIA'
        assert self.owner_name(game, 'A DEN') == 'ENGLAND'
        assert self.owner_name(game, 'F BAL') == 'ENGLAND'
        assert self.owner_name(game, 'F SKA') == 'ENGLAND'
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'A SWE') == 'ENGLAND'
        assert self.owner_name(game, 'F NWG') == 'RUSSIA'

    def test_6_g_18(self):
        """ 6.G.18. TEST CASE, THE TWO UNIT IN ONE AREA BUG, WITH DOUBLE CONVOY
            Similar to the previous test case, but now both units move by convoy.
            England: F North Sea Convoys A London - Belgium
            England: A Holland Supports A London - Belgium
            England: A Yorkshire - London
            England: A London - Belgium
            England: A Ruhr Supports A London - Belgium
            France: F English Channel Convoys A Belgium - London
            France: A Belgium - London
            France: A Wales Supports A Belgium - London
            Belgium and London are swapped, while the army in Yorkshire fails to move to London.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F NTH', 'A HOL', 'A YOR', 'A LON', 'A RUH'])
        self.set_units(game, 'FRANCE', ['F ENG', 'A BEL', 'A WAL'])
        self.set_orders(game, 'ENGLAND', ['F NTH C A LON - BEL',
                                          'A HOL S A LON - BEL',
                                          'A YOR - LON',
                                          'A LON - BEL',
                                          'A RUH S A LON - BEL'])
        self.set_orders(game, 'FRANCE', ['F ENG C A BEL - LON', 'A BEL - LON', 'A WAL S A BEL - LON'])
        self.process(game)
        assert self.check_results(game, 'F NTH', OK)
        assert self.check_results(game, 'A HOL', OK)
        assert self.check_results(game, 'A YOR', BOUNCE)
        assert self.check_results(game, 'A LON', OK)
        assert self.check_results(game, 'A RUH', OK)
        assert self.check_results(game, 'F ENG', OK)
        assert self.check_results(game, 'A BEL', OK)
        assert self.check_results(game, 'A WAL', OK)
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'A HOL') == 'ENGLAND'
        assert self.owner_name(game, 'A YOR') == 'ENGLAND'
        assert self.owner_name(game, 'A LON') == 'FRANCE'
        assert self.owner_name(game, 'A RUH') == 'ENGLAND'
        assert self.owner_name(game, 'F ENG') == 'FRANCE'
        assert self.owner_name(game, 'A BEL') == 'ENGLAND'
        assert self.owner_name(game, 'A WAL') == 'FRANCE'

    # 6.H. TEST CASES, RETREATING
    def test_6_h_1(self):
        """ 6.H.1. TEST CASE, NO SUPPORTS DURING RETREAT
            Supports are not allowed in the retreat phase.
            Austria: F Trieste Hold
            Austria: A Serbia Hold
            Turkey: F Greece Hold
            Italy: A Venice Supports A Tyrolia - Trieste
            Italy: A Tyrolia - Trieste
            Italy: F Ionian Sea - Greece
            Italy: F Aegean Sea Supports F Ionian Sea - Greece
            The fleet in Trieste and the fleet in Greece are dislodged. If the retreat orders are as follows:
            Austria: F Trieste - Albania
            Austria: A Serbia Supports F Trieste - Albania
            Turkey: F Greece - Albania
            The Austrian support order is illegal. Both dislodged fleets are disbanded.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'AUSTRIA', ['F TRI', 'A SER'])
        self.set_units(game, 'TURKEY', ['F GRE'])
        self.set_units(game, 'ITALY', ['A VEN', 'A TYR', 'F ION', 'F AEG'])

        # Movement phase
        self.set_orders(game, 'AUSTRIA', ['F TRI H', 'A SER H'])
        self.set_orders(game, 'TURKEY', ['F GRE H'])
        self.set_orders(game, 'ITALY', ['A VEN S A TYR - TRI', 'A TYR - TRI', 'F ION - GRE', 'F AEG S F ION - GRE'])
        self.process(game)
        assert self.check_results(game, 'F TRI', DISLODGED)
        assert self.check_results(game, 'A SER', OK)
        assert self.check_results(game, 'F GRE', DISLODGED)
        assert self.check_results(game, 'A VEN', OK)
        assert self.check_results(game, 'A TYR', OK)
        assert self.check_results(game, 'F ION', OK)
        assert self.check_results(game, 'F AEG', OK)
        assert check_dislodged(game, 'F TRI', 'A TYR')      # AUSTRIA
        assert check_dislodged(game, 'F GRE', 'F ION')      # TURKEY
        assert self.owner_name(game, 'A TRI') == 'ITALY'
        assert self.owner_name(game, 'A SER') == 'AUSTRIA'
        assert self.owner_name(game, 'F GRE') == 'ITALY'
        assert self.owner_name(game, 'A VEN') == 'ITALY'
        assert self.owner_name(game, 'A TYR') is None
        assert self.owner_name(game, 'F ION') is None
        assert self.owner_name(game, 'F AEG') == 'ITALY'

        # Retreats Phase
        if game.phase_type == 'R':
            self.set_orders(game, 'AUSTRIA', ['F TRI R ALB', 'A SER S F TRI - ALB'])
            self.set_orders(game, 'TURKEY', ['F GRE R ALB'])
            self.process(game)
            assert self.check_results(game, 'F TRI', BOUNCE, phase='R')
            assert self.check_results(game, 'F TRI', DISBAND, phase='R')
            assert self.check_results(game, 'A SER', VOID, phase='R')
            assert self.check_results(game, 'F GRE', BOUNCE, phase='R')
            assert self.check_results(game, 'F GRE', DISBAND, phase='R')
        assert not check_dislodged(game, 'F TRI', '')     # AUSTRIA
        assert not check_dislodged(game, 'F GRE', '')     # TURKEY
        assert self.owner_name(game, 'A TRI') == 'ITALY'
        assert self.owner_name(game, 'A SER') == 'AUSTRIA'
        assert self.owner_name(game, 'F GRE') == 'ITALY'
        assert self.owner_name(game, 'A VEN') == 'ITALY'
        assert self.owner_name(game, 'A TYR') is None
        assert self.owner_name(game, 'F ION') is None
        assert self.owner_name(game, 'F AEG') == 'ITALY'
        assert self.owner_name(game, 'F ALB') is None

    def test_6_h_2(self):
        """ 6.H.2. TEST CASE, NO SUPPORTS FROM RETREATING UNIT
            Even a retreating unit can not give support.
            England: A Liverpool - Edinburgh
            England: F Yorkshire Supports A Liverpool - Edinburgh
            England: F Norway Hold
            Germany: A Kiel Supports A Ruhr - Holland
            Germany: A Ruhr - Holland
            Russia: F Edinburgh Hold
            Russia: A Sweden Supports A Finland - Norway
            Russia: A Finland - Norway
            Russia: F Holland Hold
            The English fleet in Norway and the Russian fleets in Edinburgh and Holland are dislodged. If the
            following retreat orders are given:
            England: F Norway - North Sea
            Russia: F Edinburgh - North Sea
            Russia: F Holland Supports F Edinburgh - North Sea
            Although the fleet in Holland may receive an order, it may not support (it is disbanded).
            The English fleet in Norway and the Russian fleet in Edinburgh bounce and are disbanded.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['A LVP', 'F YOR', 'F NWY'])
        self.set_units(game, 'GERMANY', ['A KIE', 'A RUH'])
        self.set_units(game, 'RUSSIA', ['F EDI', 'A SWE', 'A FIN', 'F HOL'])

        # Movements Phase
        self.set_orders(game, 'ENGLAND', ['A LVP - EDI', 'F YOR S A LVP - EDI', 'F NWY H'])
        self.set_orders(game, 'GERMANY', ['A KIE S A RUH - HOL', 'A RUH - HOL'])
        self.set_orders(game, 'RUSSIA', ['F EDI H', 'A SWE S A FIN - NWY', 'A FIN - NWY', 'F HOL H'])
        self.process(game)
        assert self.check_results(game, 'A LVP', OK)
        assert self.check_results(game, 'F YOR', OK)
        assert self.check_results(game, 'F NWY', DISLODGED)
        assert self.check_results(game, 'A KIE', OK)
        assert self.check_results(game, 'A RUH', OK)
        assert self.check_results(game, 'F EDI', DISLODGED)
        assert self.check_results(game, 'A SWE', OK)
        assert self.check_results(game, 'A FIN', OK)
        assert self.check_results(game, 'F HOL', DISLODGED)
        assert check_dislodged(game, 'F NWY', 'A FIN')      # ENGLAND
        assert check_dislodged(game, 'F EDI', 'A LVP')      # RUSSIA
        assert check_dislodged(game, 'F HOL', 'A RUH')      # RUSSIA
        assert self.owner_name(game, 'A LVP') is None
        assert self.owner_name(game, 'F YOR') == 'ENGLAND'
        assert self.owner_name(game, 'A NWY') == 'RUSSIA'
        assert self.owner_name(game, 'A KIE') == 'GERMANY'
        assert self.owner_name(game, 'A RUH') is None
        assert self.owner_name(game, 'A EDI') == 'ENGLAND'
        assert self.owner_name(game, 'A SWE') == 'RUSSIA'
        assert self.owner_name(game, 'A FIN') is None
        assert self.owner_name(game, 'A HOL') == 'GERMANY'

        # Retreats phase
        if game.phase_type == 'R':
            self.set_orders(game, 'ENGLAND', ['F NWY R NTH'])
            self.set_orders(game, 'RUSSIA', ['F EDI R NTH', 'F HOL S F EDI - NTH'])
            self.process(game)
            assert self.check_results(game, 'F NWY', BOUNCE, phase='R')
            assert self.check_results(game, 'F NWY', DISBAND, phase='R')
            assert self.check_results(game, 'F EDI', BOUNCE, phase='R')
            assert self.check_results(game, 'F EDI', DISBAND, phase='R')
            assert self.check_results(game, 'F HOL', VOID, phase='R')
            assert self.check_results(game, 'F EDI', DISBAND, phase='R')
        assert not check_dislodged(game, 'F NWY', '')      # ENGLAND
        assert not check_dislodged(game, 'F EDI', '')      # RUSSIA
        assert not check_dislodged(game, 'F HOL', '')      # RUSSIA
        assert self.owner_name(game, 'A LVP') is None
        assert self.owner_name(game, 'F YOR') == 'ENGLAND'
        assert self.owner_name(game, 'A NWY') == 'RUSSIA'
        assert self.owner_name(game, 'A KIE') == 'GERMANY'
        assert self.owner_name(game, 'A RUH') is None
        assert self.owner_name(game, 'A EDI') == 'ENGLAND'
        assert self.owner_name(game, 'A SWE') == 'RUSSIA'
        assert self.owner_name(game, 'A FIN') is None
        assert self.owner_name(game, 'A HOL') == 'GERMANY'
        assert self.owner_name(game, 'F NTH') is None

    def test_6_h_3(self):
        """ 6.H.3. TEST CASE, NO CONVOY DURING RETREAT
            Convoys during retreat are not allowed.
            England: F North Sea Hold
            England: A Holland Hold
            Germany: F Kiel Supports A Ruhr - Holland
            Germany: A Ruhr - Holland
            The English army in Holland is dislodged. If England orders the following in retreat:
            England: A Holland - Yorkshire
            England: F North Sea Convoys A Holland - Yorkshire
            The convoy order is illegal. The army in Holland is disbanded.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F NTH', 'A HOL'])
        self.set_units(game, 'GERMANY', ['F KIE', 'A RUH'])

        # Movements phase
        self.set_orders(game, 'ENGLAND', ['F NTH H', 'A HOL H'])
        self.set_orders(game, 'GERMANY', ['F KIE S A RUH - HOL', 'A RUH - HOL'])
        self.process(game)
        assert self.check_results(game, 'F NTH', OK)
        assert self.check_results(game, 'A HOL', DISLODGED)
        assert self.check_results(game, 'F KIE', OK)
        assert self.check_results(game, 'A RUH', OK)
        assert check_dislodged(game, 'A HOL', 'A RUH')      # ENGLAND
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'A HOL') == 'GERMANY'
        assert self.owner_name(game, 'F KIE') == 'GERMANY'
        assert self.owner_name(game, 'A RUH') is None

        # Retreats phase
        if game.phase_type == 'R':
            self.set_orders(game, 'ENGLAND', ['A HOL R YOR', 'F NTH C A HOL - YOR'])
            self.process(game)
            assert self.check_results(game, 'F NTH', VOID, phase='R')
            assert self.check_results(game, 'A HOL', VOID, phase='R')
            assert self.check_results(game, 'A HOL', DISBAND, phase='R')
        assert not check_dislodged(game, 'A HOL', '')     # ENGLAND
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'A HOL') == 'GERMANY'
        assert self.owner_name(game, 'F KIE') == 'GERMANY'
        assert self.owner_name(game, 'A RUH') is None
        assert self.owner_name(game, 'A YOR') is None

    def test_6_h_4(self):
        """ 6.H.4. TEST CASE, NO OTHER MOVES DURING RETREAT
            Of course you may not do any other move during a retreat. But look if the adjudicator checks for it.
            England: F North Sea Hold
            England: A Holland Hold
            Germany: F Kiel Supports A Ruhr - Holland
            Germany: A Ruhr - Holland
            The English army in Holland is dislodged. If England orders the following in retreat:
            England: A Holland - Belgium
            England: F North Sea - Norwegian Sea
            The fleet in the North Sea is not dislodge, so the move is illegal.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F NTH', 'A HOL'])
        self.set_units(game, 'GERMANY', ['F KIE', 'A RUH'])

        # Movements phase
        self.set_orders(game, 'ENGLAND', ['F NTH H', 'A HOL H'])
        self.set_orders(game, 'GERMANY', ['F KIE S A RUH - HOL', 'A RUH - HOL'])
        self.process(game)
        assert self.check_results(game, 'F NTH', OK)
        assert self.check_results(game, 'A HOL', DISLODGED)
        assert self.check_results(game, 'F KIE', OK)
        assert self.check_results(game, 'A RUH', OK)
        assert check_dislodged(game, 'A HOL', 'A RUH')      # ENGLAND
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'A HOL') == 'GERMANY'
        assert self.owner_name(game, 'F KIE') == 'GERMANY'
        assert self.owner_name(game, 'A RUH') is None

        # Retreats phase
        if game.phase_type == 'R':
            self.set_orders(game, 'ENGLAND', ['A HOL R BEL', 'F NTH R NWG'])
            self.process(game)
            assert self.check_results(game, 'F NTH', VOID, phase='R')
            assert self.check_results(game, 'A HOL', OK, phase='R')
        assert not check_dislodged(game, 'A HOL', '')     # ENGLAND
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'A HOL') == 'GERMANY'
        assert self.owner_name(game, 'F KIE') == 'GERMANY'
        assert self.owner_name(game, 'A RUH') is None
        assert self.owner_name(game, 'A BEL') == 'ENGLAND'

    def test_6_h_5(self):
        """ 6.H.5. TEST CASE, A UNIT MAY NOT RETREAT TO THE AREA FROM WHICH IT IS ATTACKED
            Well, that would be of course stupid. Still, the adjudicator must be tested on this.
            Russia: F Constantinople Supports F Black Sea - Ankara
            Russia: F Black Sea - Ankara
            Turkey: F Ankara Hold
            Fleet in Ankara is dislodged and may not retreat to Black Sea.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'RUSSIA', ['F CON', 'F BLA'])
        self.set_units(game, 'TURKEY', 'F ANK')

        # Movements phase
        self.set_orders(game, 'RUSSIA', ['F CON S F BLA - ANK', 'F BLA - ANK'])
        self.set_orders(game, 'TURKEY', 'F ANK H')
        self.process(game)
        assert self.check_results(game, 'F CON', OK)
        assert self.check_results(game, 'F BLA', OK)
        assert self.check_results(game, 'F ANK', DISLODGED)
        assert check_dislodged(game, 'F ANK', 'F BLA')      # TURKEY
        assert self.owner_name(game, 'F CON') == 'RUSSIA'
        assert self.owner_name(game, 'F BLA') is None
        assert self.owner_name(game, 'F ANK') == 'RUSSIA'

        # Retreats Phase
        if game.phase_type == 'R':
            self.set_orders(game, 'TURKEY', ['F ANK R BLA'])
            self.process(game)
            assert self.check_results(game, 'F ANK', VOID, phase='R')
            assert self.check_results(game, 'F ANK', DISBAND, phase='R')
        assert not check_dislodged(game, 'F ANK', 'F BLA')  # TURKEY
        assert self.owner_name(game, 'F CON') == 'RUSSIA'
        assert self.owner_name(game, 'F BLA') is None
        assert self.owner_name(game, 'F ANK') == 'RUSSIA'

    def test_6_h_6(self):
        """ 6.H.6. TEST CASE, UNIT MAY NOT RETREAT TO A CONTESTED AREA
            Stand off prevents retreat to the area.
            Austria: A Budapest Supports A Trieste - Vienna
            Austria: A Trieste - Vienna
            Germany: A Munich - Bohemia
            Germany: A Silesia - Bohemia
            Italy: A Vienna Hold
            The Italian army in Vienna is dislodged. It may not retreat to Bohemia.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'AUSTRIA', ['A BUD', 'A TRI'])
        self.set_units(game, 'GERMANY', ['A MUN', 'A SIL'])
        self.set_units(game, 'ITALY', ['A VIE'])

        # Movements phase
        self.set_orders(game, 'AUSTRIA', ['A BUD S A TRI - VIE', 'A TRI - VIE'])
        self.set_orders(game, 'GERMANY', ['A MUN - BOH', 'A SIL - BOH'])
        self.set_orders(game, 'ITALY', ['A VIE H'])
        self.process(game)
        assert self.check_results(game, 'A BUD', OK)
        assert self.check_results(game, 'A TRI', OK)
        assert self.check_results(game, 'A MUN', BOUNCE)
        assert self.check_results(game, 'A SIL', BOUNCE)
        assert self.check_results(game, 'A VIE', DISLODGED)
        assert check_dislodged(game, 'A VIE', 'A TRI')      # ITALY
        assert self.owner_name(game, 'A BUD') == 'AUSTRIA'
        assert self.owner_name(game, 'A TRI') is None
        assert self.owner_name(game, 'A MUN') == 'GERMANY'
        assert self.owner_name(game, 'A SIL') == 'GERMANY'
        assert self.owner_name(game, 'A VIE') == 'AUSTRIA'
        assert self.owner_name(game, 'A BOH') is None

        # Retreats phase
        if game.phase_type == 'R':
            self.set_orders(game, 'ITALY', ['A VIE R BOH'])
            self.process(game)
            assert self.check_results(game, 'A VIE', VOID, phase='R')
            assert self.check_results(game, 'A VIE', DISBAND, phase='R')
        assert not check_dislodged(game, 'A VIE', '')  # ITALY
        assert self.owner_name(game, 'A BUD') == 'AUSTRIA'
        assert self.owner_name(game, 'A TRI') is None
        assert self.owner_name(game, 'A MUN') == 'GERMANY'
        assert self.owner_name(game, 'A SIL') == 'GERMANY'
        assert self.owner_name(game, 'A VIE') == 'AUSTRIA'
        assert self.owner_name(game, 'A BOH') is None

    def test_6_h_7(self):
        """ 6.H.7. TEST CASE, MULTIPLE RETREAT TO SAME AREA WILL DISBAND UNITS
            There can only be one unit in an area.
            Austria: A Budapest Supports A Trieste - Vienna
            Austria: A Trieste - Vienna
            Germany: A Munich Supports A Silesia - Bohemia
            Germany: A Silesia - Bohemia
            Italy: A Vienna Hold
            Italy: A Bohemia Hold
            If Italy orders the following for retreat:
            Italy: A Bohemia - Tyrolia
            Italy: A Vienna - Tyrolia
            Both armies will be disbanded.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'AUSTRIA', ['A BUD', 'A TRI'])
        self.set_units(game, 'GERMANY', ['A MUN', 'A SIL'])
        self.set_units(game, 'ITALY', ['A VIE', 'A BOH'])

        # Movements phase
        self.set_orders(game, 'AUSTRIA', ['A BUD S A TRI - VIE', 'A TRI - VIE'])
        self.set_orders(game, 'GERMANY', ['A MUN S A SIL - BOH', 'A SIL - BOH'])
        self.set_orders(game, 'ITALY', ['A VIE H', 'A BOH H'])
        self.process(game)
        assert self.check_results(game, 'A BUD', OK)
        assert self.check_results(game, 'A TRI', OK)
        assert self.check_results(game, 'A MUN', OK)
        assert self.check_results(game, 'A SIL', OK)
        assert self.check_results(game, 'A VIE', DISLODGED)
        assert self.check_results(game, 'A BOH', DISLODGED)
        assert check_dislodged(game, 'A VIE', 'A TRI')      # ITALY
        assert check_dislodged(game, 'A BOH', 'A SIL')      # ITALY
        assert self.owner_name(game, 'A BUD') == 'AUSTRIA'
        assert self.owner_name(game, 'A TRI') is None
        assert self.owner_name(game, 'A MUN') == 'GERMANY'
        assert self.owner_name(game, 'A SIL') is None
        assert self.owner_name(game, 'A VIE') == 'AUSTRIA'
        assert self.owner_name(game, 'A BOH') == 'GERMANY'

        # Retreats phase
        if game.phase_type == 'R':
            self.set_orders(game, 'ITALY', ['A VIE R TYR', 'A BOH R TYR'])
            self.process(game)
            assert self.check_results(game, 'A VIE', BOUNCE, phase='R')
            assert self.check_results(game, 'A VIE', DISBAND, phase='R')
            assert self.check_results(game, 'A BOH', BOUNCE, phase='R')
            assert self.check_results(game, 'A BOH', DISBAND, phase='R')
        assert not check_dislodged(game, 'A VIE', '')      # ITALY
        assert not check_dislodged(game, 'A BOH', '')      # ITALY
        assert self.owner_name(game, 'A BUD') == 'AUSTRIA'
        assert self.owner_name(game, 'A TRI') is None
        assert self.owner_name(game, 'A MUN') == 'GERMANY'
        assert self.owner_name(game, 'A SIL') is None
        assert self.owner_name(game, 'A VIE') == 'AUSTRIA'
        assert self.owner_name(game, 'A BOH') == 'GERMANY'
        assert self.owner_name(game, 'A TYR') is None

    def test_6_h_8(self):
        """ 6.H.8. TEST CASE, TRIPLE RETREAT TO SAME AREA WILL DISBAND UNITS
            When three units retreat to the same area, then all three units are disbanded.
            England: A Liverpool - Edinburgh
            England: F Yorkshire Supports A Liverpool - Edinburgh
            England: F Norway Hold
            Germany: A Kiel Supports A Ruhr - Holland
            Germany: A Ruhr - Holland
            Russia: F Edinburgh Hold
            Russia: A Sweden Supports A Finland - Norway
            Russia: A Finland - Norway
            Russia: F Holland Hold
            The fleets in Norway, Edinburgh and Holland are dislodged. If the following retreat orders are given:
            England: F Norway - North Sea
            Russia: F Edinburgh - North Sea
            Russia: F Holland - North Sea
            All three units are disbanded.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['A LVP', 'F YOR', 'F NWY'])
        self.set_units(game, 'GERMANY', ['A KIE', 'A RUH'])
        self.set_units(game, 'RUSSIA', ['F EDI', 'A SWE', 'A FIN', 'F HOL'])

        # Movements phase
        self.set_orders(game, 'ENGLAND', ['A LVP - EDI', 'F YOR S A LVP - EDI', 'F NWY H'])
        self.set_orders(game, 'GERMANY', ['A KIE S A RUH - HOL', 'A RUH - HOL'])
        self.set_orders(game, 'RUSSIA', ['F EDI H', 'A SWE S A FIN - NWY', 'A FIN - NWY', 'F HOL H'])
        self.process(game)
        assert self.check_results(game, 'A LVP', OK)
        assert self.check_results(game, 'F YOR', OK)
        assert self.check_results(game, 'F NWY', DISLODGED)
        assert self.check_results(game, 'A KIE', OK)
        assert self.check_results(game, 'A RUH', OK)
        assert self.check_results(game, 'F EDI', DISLODGED)
        assert self.check_results(game, 'A SWE', OK)
        assert self.check_results(game, 'A FIN', OK)
        assert self.check_results(game, 'F HOL', DISLODGED)
        assert check_dislodged(game, 'F NWY', 'A FIN')      # ENGLAND
        assert check_dislodged(game, 'F EDI', 'A LVP')      # RUSSIA
        assert check_dislodged(game, 'F HOL', 'A RUH')      # RUSSIA
        assert self.owner_name(game, 'A LVP') is None
        assert self.owner_name(game, 'F YOR') == 'ENGLAND'
        assert self.owner_name(game, 'A NWY') == 'RUSSIA'
        assert self.owner_name(game, 'A KIE') == 'GERMANY'
        assert self.owner_name(game, 'A RUH') is None
        assert self.owner_name(game, 'A EDI') == 'ENGLAND'
        assert self.owner_name(game, 'A SWE') == 'RUSSIA'
        assert self.owner_name(game, 'A FIN') is None
        assert self.owner_name(game, 'A HOL') == 'GERMANY'

        # Retreats phase
        if game.phase_type == 'R':
            self.set_orders(game, 'ENGLAND', ['F NWY R NTH'])
            self.set_orders(game, 'RUSSIA', ['F EDI R NTH', 'F HOL R NTH'])
            self.process(game)
            assert self.check_results(game, 'F NWY', BOUNCE, phase='R')
            assert self.check_results(game, 'F NWY', DISBAND, phase='R')
            assert self.check_results(game, 'F EDI', BOUNCE, phase='R')
            assert self.check_results(game, 'F EDI', DISBAND, phase='R')
            assert self.check_results(game, 'F HOL', BOUNCE, phase='R')
            assert self.check_results(game, 'F HOL', DISBAND, phase='R')
        assert not check_dislodged(game, 'F NWY', '')      # ENGLAND
        assert not check_dislodged(game, 'F EDI', '')      # RUSSIA
        assert not check_dislodged(game, 'F HOL', '')      # RUSSIA
        assert self.owner_name(game, 'A LVP') is None
        assert self.owner_name(game, 'F YOR') == 'ENGLAND'
        assert self.owner_name(game, 'A NWY') == 'RUSSIA'
        assert self.owner_name(game, 'A KIE') == 'GERMANY'
        assert self.owner_name(game, 'A RUH') is None
        assert self.owner_name(game, 'A EDI') == 'ENGLAND'
        assert self.owner_name(game, 'A SWE') == 'RUSSIA'
        assert self.owner_name(game, 'A FIN') is None
        assert self.owner_name(game, 'A HOL') == 'GERMANY'
        assert self.owner_name(game, 'F NTH') is None

    def test_6_h_9(self):
        """ 6.H.9. TEST CASE, DISLODGED UNIT WILL NOT MAKE ATTACKERS AREA CONTESTED
            An army can follow.
            England: F Helgoland Bight - Kiel
            England: F Denmark Supports F Helgoland Bight - Kiel
            Germany: A Berlin - Prussia
            Germany: F Kiel Hold
            Germany: A Silesia Supports A Berlin - Prussia
            Russia: A Prussia - Berlin
            The fleet in Kiel can retreat to Berlin.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F HEL', 'F DEN'])
        self.set_units(game, 'GERMANY', ['A BER', 'F KIE', 'A SIL'])
        self.set_units(game, 'RUSSIA', ['A PRU'])

        # Movements phase
        self.set_orders(game, 'ENGLAND', ['F HEL - KIE', 'F DEN S F HEL - KIE'])
        self.set_orders(game, 'GERMANY', ['A BER - PRU', 'F KIE H', 'A SIL S A BER - PRU'])
        self.set_orders(game, 'RUSSIA', ['A PRU - BER'])
        self.process(game)
        assert self.check_results(game, 'F HEL', OK)
        assert self.check_results(game, 'F DEN', OK)
        assert self.check_results(game, 'A BER', OK)
        assert self.check_results(game, 'F KIE', DISLODGED)
        assert self.check_results(game, 'A SIL', OK)
        assert self.check_results(game, 'A PRU', DISLODGED)
        assert check_dislodged(game, 'F KIE', 'F HEL')      # GERMANY
        assert check_dislodged(game, 'A PRU', 'A BER')      # RUSSIA
        assert self.owner_name(game, 'F HEL') is None
        assert self.owner_name(game, 'F DEN') == 'ENGLAND'
        assert self.owner_name(game, 'A BER') is None
        assert self.owner_name(game, 'F KIE') == 'ENGLAND'
        assert self.owner_name(game, 'A SIL') == 'GERMANY'
        assert self.owner_name(game, 'A PRU') == 'GERMANY'

        # Retreats phase
        if game.phase_type == 'R':
            self.set_orders(game, 'GERMANY', 'F KIE R BER')
            self.process(game)
            assert self.check_results(game, 'F KIE', OK, phase='R')
            assert self.check_results(game, 'A PRU', DISBAND, phase='R')
        assert not check_dislodged(game, 'F KIE', '')      # GERMANY
        assert not check_dislodged(game, 'A PRU', '')      # RUSSIA
        assert self.owner_name(game, 'F HEL') is None
        assert self.owner_name(game, 'F DEN') == 'ENGLAND'
        assert self.owner_name(game, 'F BER') == 'GERMANY'
        assert self.owner_name(game, 'F KIE') == 'ENGLAND'
        assert self.owner_name(game, 'A SIL') == 'GERMANY'
        assert self.owner_name(game, 'A PRU') == 'GERMANY'

    def test_6_h_10(self):
        """ 6.H.10. TEST CASE, NOT RETREATING TO ATTACKER DOES NOT MEAN CONTESTED
            An army can not retreat to the place of the attacker. The easiest way to program that, is to mark that
            place as "contested". However, this is not correct. Another army may retreat to that place.
            England: A Kiel Hold
            Germany: A Berlin - Kiel
            Germany: A Munich Supports A Berlin - Kiel
            Germany: A Prussia Hold
            Russia: A Warsaw - Prussia
            Russia: A Silesia Supports A Warsaw - Prussia
            The armies in Kiel and Prussia are dislodged. The English army in Kiel can not retreat to Berlin, but
            the army in Prussia can retreat to Berlin. Suppose the following retreat orders are given:
            England: A Kiel - Berlin
            Germany: A Prussia - Berlin
            The English retreat to Berlin is illegal and fails (the unit is disbanded). The German retreat to Berlin is
            successful and does not bounce on the English unit.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['A KIE'])
        self.set_units(game, 'GERMANY', ['A BER', 'A MUN', 'A PRU'])
        self.set_units(game, 'RUSSIA', ['A WAR', 'A SIL'])

        # Movements phase
        self.set_orders(game, 'ENGLAND', ['A KIE H'])
        self.set_orders(game, 'GERMANY', ['A BER - KIE', 'A MUN S A BER - KIE', 'A PRU H'])
        self.set_orders(game, 'RUSSIA', ['A WAR - PRU', 'A SIL S A WAR - PRU'])
        self.process(game)
        assert self.check_results(game, 'A KIE', DISLODGED)
        assert self.check_results(game, 'A BER', OK)
        assert self.check_results(game, 'A MUN', OK)
        assert self.check_results(game, 'A PRU', DISLODGED)
        assert self.check_results(game, 'A WAR', OK)
        assert self.check_results(game, 'A SIL', OK)
        assert check_dislodged(game, 'A KIE', 'A BER')      # ENGLAND
        assert check_dislodged(game, 'A PRU', 'A WAR')      # GERMANY
        assert self.owner_name(game, 'A KIE') == 'GERMANY'
        assert self.owner_name(game, 'A BER') is None
        assert self.owner_name(game, 'A MUN') == 'GERMANY'
        assert self.owner_name(game, 'A PRU') == 'RUSSIA'
        assert self.owner_name(game, 'A WAR') is None
        assert self.owner_name(game, 'A SIL') == 'RUSSIA'

        # Retreats phase
        if game.phase_type == 'R':
            self.set_orders(game, 'ENGLAND', ['A KIE R BER'])
            self.set_orders(game, 'GERMANY', ['A PRU R BER'])
            self.process(game)
            assert self.check_results(game, 'A KIE', VOID, phase='R')
            assert self.check_results(game, 'A PRU', OK, phase='R')
        assert not check_dislodged(game, 'A KIE', '')      # ENGLAND
        assert not check_dislodged(game, 'A PRU', '')      # GERMANY
        assert self.owner_name(game, 'A KIE') == 'GERMANY'
        assert self.owner_name(game, 'A BER') == 'GERMANY'
        assert self.owner_name(game, 'A MUN') == 'GERMANY'
        assert self.owner_name(game, 'A PRU') == 'RUSSIA'
        assert self.owner_name(game, 'A WAR') is None
        assert self.owner_name(game, 'A SIL') == 'RUSSIA'

    def test_6_h_11(self):
        """ 6.H.11. TEST CASE, RETREAT WHEN DISLODGED BY ADJACENT CONVOY
            If a unit is dislodged by an army via convoy, the question arises whether the dislodged army can retreat
            to the original place of the convoyed army. This is only relevant in case the convoy was to an adjacent
            place.
            France: A Gascony - Marseilles via Convoy
            France: A Burgundy Supports A Gascony - Marseilles
            France: F Mid-Atlantic Ocean Convoys A Gascony - Marseilles
            France: F Western Mediterranean Convoys A Gascony - Marseilles
            France: F Gulf of Lyon Convoys A Gascony - Marseilles
            Italy: A Marseilles Hold
            If for issue 4.A.3 choice b or c has been taken, then the army in Gascony will not move with the use of
            the convoy, because the army in Marseilles does not move in opposite direction. This immediately means that
            the army in Marseilles may not move to Gascony when it dislodged by the army there.
            For all other choices of issue 4.A.3, the army in Gascony takes a convoy and does not pass the border of
            Gascony with Marseilles (it went a complete different direction). Now, the result depends on which rule
            is used for retreating (see issue 4.A.5).
            I prefer the 1982/2000 rule for convoying to adjacent places. This means that the move of Gascony happened
            by convoy. Furthermore, I prefer that the army in Marseilles may retreat to Gascony.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'FRANCE', ['A GAS', 'A BUR', 'F MAO', 'F WES', 'F LYO'])
        self.set_units(game, 'ITALY', ['A MAR'])

        # Movements phase
        self.set_orders(game, 'FRANCE', ['A GAS - MAR VIA', 'A BUR S A GAS - MAR', 'F MAO C A GAS - MAR',
                                         'F WES C A GAS - MAR', 'F LYO C A GAS - MAR'])
        self.set_orders(game, 'ITALY', ['A MAR H'])
        self.process(game)
        assert self.check_results(game, 'A GAS', OK)
        assert self.check_results(game, 'A BUR', OK)
        assert self.check_results(game, 'F MAO', OK)
        assert self.check_results(game, 'F WES', OK)
        assert self.check_results(game, 'F LYO', OK)
        assert self.check_results(game, 'A MAR', DISLODGED)
        assert check_dislodged(game, 'A MAR', 'A GAS')      # ITALY
        assert self.owner_name(game, 'A GAS') is None
        assert self.owner_name(game, 'A BUR') == 'FRANCE'
        assert self.owner_name(game, 'F MAO') == 'FRANCE'
        assert self.owner_name(game, 'F WES') == 'FRANCE'
        assert self.owner_name(game, 'F LYO') == 'FRANCE'
        assert self.owner_name(game, 'A MAR') == 'FRANCE'

        # Retreats phase
        if game.phase_type == 'R':
            self.set_orders(game, 'ITALY', ['A MAR R GAS'])
            self.process(game)
            assert self.check_results(game, 'A MAR', OK, phase='R')
        assert not check_dislodged(game, 'A MAR', '')  # ITALY
        assert self.owner_name(game, 'A GAS') == 'ITALY'
        assert self.owner_name(game, 'A BUR') == 'FRANCE'
        assert self.owner_name(game, 'F MAO') == 'FRANCE'
        assert self.owner_name(game, 'F WES') == 'FRANCE'
        assert self.owner_name(game, 'F LYO') == 'FRANCE'
        assert self.owner_name(game, 'A MAR') == 'FRANCE'

    def test_6_h_12(self):
        """ 6.H.12. TEST CASE, RETREAT WHEN DISLODGED BY ADJACENT CONVOY WHILE TRYING TO DO THE SAME
            The previous test case can be made more extra ordinary, when both armies tried to move by convoy.
            England: A Liverpool - Edinburgh via Convoy
            England: F Irish Sea Convoys A Liverpool - Edinburgh
            England: F English Channel Convoys A Liverpool - Edinburgh
            England: F North Sea Convoys A Liverpool - Edinburgh
            France: F Brest - English Channel
            France: F Mid-Atlantic Ocean Supports F Brest - English Channel
            Russia: A Edinburgh - Liverpool via Convoy
            Russia: F Norwegian Sea Convoys A Edinburgh - Liverpool
            Russia: F North Atlantic Ocean Convoys A Edinburgh - Liverpool
            Russia: A Clyde Supports A Edinburgh - Liverpool
            If for issue 4.A.3 choice c has been taken, then the army in Liverpool will not try to move by convoy,
            because the convoy is disrupted. This has as consequence that army will just advance to Edinburgh by using
            the land route. For all other choices of issue 4.A.3, both the army in Liverpool as in Edinburgh will try
            to move by convoy. The army in Edinburgh will succeed. The army in Liverpool will fail, because of the
            disrupted convoy. It is dislodged by the army of Edinburgh. Now, the question is whether the army in
            Liverpool may retreat to Edinburgh. The result depends on which rule is used for retreating (see issue
            4.A.5). I prefer the 1982/2000 rule for convoying to adjacent places. This means that the army in Liverpool
            tries the disrupted convoy. Furthermore, I prefer that the army in Liverpool may retreat to Edinburgh.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['A LVP', 'F IRI', 'F ENG', 'F NTH'])
        self.set_units(game, 'FRANCE', ['F BRE', 'F MAO'])
        self.set_units(game, 'RUSSIA', ['A EDI', 'F NWG', 'F NAO', 'A CLY'])

        # Movements phase
        self.set_orders(game, 'ENGLAND', ['A LVP - EDI VIA',
                                          'F IRI C A LVP - EDI',
                                          'F ENG C A LVP - EDI',
                                          'F NTH C A LVP - EDI'])
        self.set_orders(game, 'FRANCE', ['F BRE - ENG', 'F MAO S F BRE - ENG'])
        self.set_orders(game, 'RUSSIA', ['A EDI - LVP VIA',
                                         'F NWG C A EDI - LVP',
                                         'F NAO C A EDI - LVP',
                                         'A CLY S A EDI - LVP'])
        self.process(game)
        assert self.check_results(game, 'A LVP', DISLODGED)
        assert self.check_results(game, 'F IRI', NO_CONVOY)
        assert self.check_results(game, 'F ENG', DISLODGED)
        assert self.check_results(game, 'F NTH', NO_CONVOY)
        assert self.check_results(game, 'F BRE', OK)
        assert self.check_results(game, 'F MAO', OK)
        assert self.check_results(game, 'A EDI', OK)
        assert self.check_results(game, 'F NWG', OK)
        assert self.check_results(game, 'F NAO', OK)
        assert self.check_results(game, 'A CLY', OK)
        assert check_dislodged(game, 'F ENG', 'F BRE')  # ENGLAND
        assert check_dislodged(game, 'A LVP', 'A EDI')  # ENGLAND
        assert self.owner_name(game, 'A LVP') == 'RUSSIA'
        assert self.owner_name(game, 'F IRI') == 'ENGLAND'
        assert self.owner_name(game, 'F ENG') == 'FRANCE'
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'F BRE') is None
        assert self.owner_name(game, 'F MAO') == 'FRANCE'
        assert self.owner_name(game, 'A EDI') is None
        assert self.owner_name(game, 'F NWG') == 'RUSSIA'
        assert self.owner_name(game, 'F NAO') == 'RUSSIA'
        assert self.owner_name(game, 'A CLY') == 'RUSSIA'

        # Retreats phase
        if game.phase_type == 'R':
            self.set_orders(game, 'ENGLAND', ['A LVP R EDI', 'F ENG D'])
            self.process(game)
            assert self.check_results(game, 'A LVP', OK, phase='R')
            assert self.check_results(game, 'F ENG', DISBAND, phase='R')
        assert not check_dislodged(game, 'A LVP', '')      # ENGLAND
        assert not check_dislodged(game, 'F ENG', '')      # ENGLAND
        assert self.owner_name(game, 'A LVP') == 'RUSSIA'
        assert self.owner_name(game, 'F IRI') == 'ENGLAND'
        assert self.owner_name(game, 'F ENG') == 'FRANCE'
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'F BRE') is None
        assert self.owner_name(game, 'F MAO') == 'FRANCE'
        assert self.owner_name(game, 'A EDI') == 'ENGLAND'
        assert self.owner_name(game, 'F NWG') == 'RUSSIA'
        assert self.owner_name(game, 'F NAO') == 'RUSSIA'
        assert self.owner_name(game, 'A CLY') == 'RUSSIA'

    def test_6_h_13(self):
        """ 6.H.13. TEST CASE, NO RETREAT WITH CONVOY IN MAIN PHASE
            The places where a unit may retreat to, must be calculated during the main phase. Care should be taken
            that a convoy ordered in the main phase can not be used in the retreat phase.
            England: A Picardy Hold
            England: F English Channel Convoys A Picardy - London
            France: A Paris - Picardy
            France: A Brest Supports A Paris - Picardy
            The dislodged army in Picardy can not retreat to London.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['A PIC', 'F ENG'])
        self.set_units(game, 'FRANCE', ['A PAR', 'A BRE'])

        # Movements phase
        self.set_orders(game, 'ENGLAND', ['A PIC H', 'F ENG C A PIC - LON'])
        self.set_orders(game, 'FRANCE', ['A PAR - PIC', 'A BRE S A PAR - PIC'])
        self.process(game)
        assert self.check_results(game, 'A PIC', DISLODGED)
        assert self.check_results(game, 'F ENG', VOID)
        assert self.check_results(game, 'A PAR', OK)
        assert self.check_results(game, 'A BRE', OK)
        assert check_dislodged(game, 'A PIC', 'A PAR')      # ENGLAND
        assert self.owner_name(game, 'A PIC') == 'FRANCE'
        assert self.owner_name(game, 'F ENG') == 'ENGLAND'
        assert self.owner_name(game, 'A PAR') is None
        assert self.owner_name(game, 'A BRE') == 'FRANCE'
        assert self.owner_name(game, 'A LON') is None

        # Retreats phase
        if game.phase_type == 'R':
            self.set_orders(game, 'ENGLAND', 'A PIC R LON')
            self.process(game)
            assert self.check_results(game, 'A PIC', VOID, phase='R')
            assert self.check_results(game, 'A PIC', DISBAND, phase='R')
        assert not check_dislodged(game, 'A PIC', '')  # ENGLAND
        assert self.owner_name(game, 'A PIC') == 'FRANCE'
        assert self.owner_name(game, 'F ENG') == 'ENGLAND'
        assert self.owner_name(game, 'A PAR') is None
        assert self.owner_name(game, 'A BRE') == 'FRANCE'
        assert self.owner_name(game, 'A LON') is None

    def test_6_h_14(self):
        """ 6.H.14. TEST CASE, NO RETREAT WITH SUPPORT IN MAIN PHASE
            Comparable to the previous test case, a support given in the main phase can not be used in the retreat
            phase.
            England: A Picardy Hold
            England: F English Channel Supports A Picardy - Belgium
            France: A Paris - Picardy
            France: A Brest Supports A Paris - Picardy
            France: A Burgundy Hold
            Germany: A Munich Supports A Marseilles - Burgundy
            Germany: A Marseilles - Burgundy
            After the main phase the following retreat orders are given:
            England: A Picardy - Belgium
            France: A Burgundy - Belgium
            Both the army in Picardy and Burgundy are disbanded.
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['A PIC', 'F ENG'])
        self.set_units(game, 'FRANCE', ['A PAR', 'A BRE', 'A BUR'])
        self.set_units(game, 'GERMANY', ['A MUN', 'A MAR'])

        # Movements phase
        self.set_orders(game, 'ENGLAND', ['A PIC H', 'F ENG S A PIC - BEL'])
        self.set_orders(game, 'FRANCE', ['A PAR - PIC', 'A BRE S A PAR - PIC', 'A BUR H'])
        self.set_orders(game, 'GERMANY', ['A MUN S A MAR - BUR', 'A MAR - BUR'])
        self.process(game)
        assert self.check_results(game, 'A PIC', DISLODGED)
        assert self.check_results(game, 'F ENG', VOID)
        assert self.check_results(game, 'A PAR', OK)
        assert self.check_results(game, 'A BRE', OK)
        assert self.check_results(game, 'A BUR', DISLODGED)
        assert self.check_results(game, 'A MUN', OK)
        assert self.check_results(game, 'A MAR', OK)
        assert check_dislodged(game, 'A PIC', 'A PAR')      # ENGLAND
        assert check_dislodged(game, 'A BUR', 'A MAR')      # FRANCE
        assert self.owner_name(game, 'A PIC') == 'FRANCE'
        assert self.owner_name(game, 'F ENG') == 'ENGLAND'
        assert self.owner_name(game, 'A PAR') is None
        assert self.owner_name(game, 'A BRE') == 'FRANCE'
        assert self.owner_name(game, 'A BUR') == 'GERMANY'
        assert self.owner_name(game, 'A MUN') == 'GERMANY'
        assert self.owner_name(game, 'A MAR') is None

        # Retreats phase
        if game.phase_type == 'R':
            self.set_orders(game, 'ENGLAND', ['A PIC R BEL'])
            self.set_orders(game, 'FRANCE', ['A BUR R BEL'])
            self.process(game)
            assert self.check_results(game, 'A PIC', BOUNCE, phase='R')
            assert self.check_results(game, 'A PIC', DISBAND, phase='R')
            assert self.check_results(game, 'A BUR', BOUNCE, phase='R')
            assert self.check_results(game, 'A BUR', DISBAND, phase='R')
        assert not check_dislodged(game, 'A PIC', '')      # ENGLAND
        assert not check_dislodged(game, 'A BUR', '')      # FRANCE
        assert self.owner_name(game, 'A PIC') == 'FRANCE'
        assert self.owner_name(game, 'F ENG') == 'ENGLAND'
        assert self.owner_name(game, 'A PAR') is None
        assert self.owner_name(game, 'A BRE') == 'FRANCE'
        assert self.owner_name(game, 'A BUR') == 'GERMANY'
        assert self.owner_name(game, 'A MUN') == 'GERMANY'
        assert self.owner_name(game, 'A MAR') is None

    def test_6_h_15(self):
        """ 6.H.15. TEST CASE, NO COASTAL CRAWL IN RETREAT
            You can not go to the other coast from where the attacker came from.
            England: F Portugal Hold
            France: F Spain(sc) - Portugal
            France: F Mid-Atlantic Ocean Supports F Spain(sc) - Portugal
            The English fleet in Portugal is destroyed and can not retreat to Spain(nc).
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'ENGLAND', ['F POR'])
        self.set_units(game, 'FRANCE', ['F SPA/SC', 'F MAO'])

        # Movements phase
        self.set_orders(game, 'ENGLAND', ['F POR H'])
        self.set_orders(game, 'FRANCE', ['F SPA/SC - POR', 'F MAO S F SPA/SC - POR'])
        self.process(game)
        assert self.check_results(game, 'F POR', DISLODGED)
        assert self.check_results(game, 'F SPA/SC', OK)
        assert self.check_results(game, 'F MAO', OK)
        assert check_dislodged(game, 'F POR', 'F SPA/SC')       # ENGLAND
        assert self.owner_name(game, 'F POR') == 'FRANCE'
        assert self.owner_name(game, 'F SPA') is None
        assert self.owner_name(game, 'F SPA/NC') is None
        assert self.owner_name(game, 'F SPA/SC') is None
        assert self.owner_name(game, 'F MAO') == 'FRANCE'

        # Retreats phase
        if game.phase_type == 'R':
            self.set_orders(game, 'ENGLAND', 'F POR R SPA/NC')
            self.process(game)
            assert self.check_results(game, 'F POR', VOID, phase='R')
            assert self.check_results(game, 'F POR', DISBAND, phase='R')
        assert not check_dislodged(game, 'F POR', '')  # ENGLAND
        assert self.owner_name(game, 'F POR') == 'FRANCE'
        assert self.owner_name(game, 'F SPA') is None
        assert self.owner_name(game, 'F SPA/NC') is None
        assert self.owner_name(game, 'F SPA/SC') is None
        assert self.owner_name(game, 'F MAO') == 'FRANCE'

    def test_6_h_16(self):
        """ 6.H.16. TEST CASE, CONTESTED FOR BOTH COASTS
            If a coast is contested, the other is not available for retreat.
            France: F Mid-Atlantic Ocean - Spain(nc)
            France: F Gascony - Spain(nc)
            France: F Western Mediterranean Hold
            Italy: F Tunis Supports F Tyrrhenian Sea - Western Mediterranean
            Italy: F Tyrrhenian Sea - Western Mediterranean
            The French fleet in the Western Mediterranean can not retreat to Spain(sc).
        """
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'FRANCE', ['F MAO', 'F GAS', 'F WES'])
        self.set_units(game, 'ITALY', ['F TUN', 'F TYS'])

        # Movements phase
        self.set_orders(game, 'FRANCE', ['F MAO - SPA/NC', 'F GAS - SPA/NC', 'F WES H'])
        self.set_orders(game, 'ITALY', ['F TUN S F TYS - WES', 'F TYS - WES'])
        self.process(game)
        assert self.check_results(game, 'F MAO', BOUNCE)
        assert self.check_results(game, 'F GAS', BOUNCE)
        assert self.check_results(game, 'F WES', DISLODGED)
        assert self.check_results(game, 'F TUN', OK)
        assert self.check_results(game, 'F TYS', OK)
        assert check_dislodged(game, 'F WES', 'F TYS')      # FRANCE
        assert self.owner_name(game, 'F MAO') == 'FRANCE'
        assert self.owner_name(game, 'F GAS') == 'FRANCE'
        assert self.owner_name(game, 'F WES') == 'ITALY'
        assert self.owner_name(game, 'F TUN') == 'ITALY'
        assert self.owner_name(game, 'F TYS') is None
        assert self.owner_name(game, 'F SPA') is None
        assert self.owner_name(game, 'F SPA/NC') is None
        assert self.owner_name(game, 'F SPA/SC') is None

        # Retreats phase
        if game.phase_type == 'R':
            self.set_orders(game, 'FRANCE', 'F WES R SPA/SC')
            self.process(game)
            assert self.check_results(game, 'F WES', VOID, phase='R')
            assert self.check_results(game, 'F WES', DISBAND, phase='R')
        assert not check_dislodged(game, 'F WES', '')      # FRANCE
        assert self.owner_name(game, 'F MAO') == 'FRANCE'
        assert self.owner_name(game, 'F GAS') == 'FRANCE'
        assert self.owner_name(game, 'F WES') == 'ITALY'
        assert self.owner_name(game, 'F TUN') == 'ITALY'
        assert self.owner_name(game, 'F TYS') is None
        assert self.owner_name(game, 'F SPA') is None
        assert self.owner_name(game, 'F SPA/NC') is None
        assert self.owner_name(game, 'F SPA/SC') is None

    # 6.I. TEST CASES, BUILDING
    def test_6_i_1(self):
        """ 6.I.1. TEST CASE, TOO MANY BUILD ORDERS
            Check how program reacts when someone orders too many builds.
            Germany may build one:
            Germany: Build A Warsaw
            Germany: Build A Kiel
            Germany: Build A Munich
            Program should not build all three, but handle it in an other way. See issue 4.D.4.
            I prefer that the build orders are just handled one by one until all allowed units are build. According
            to this preference, the build in Warsaw fails, the build in Kiel succeeds and the build in Munich fails.
        """
        game = self.create_game()
        self.clear_units(game)
        self.clear_centers(game)
        self.set_centers(game, 'GERMANY', ['KIE', 'MUN', 'WAR'])
        self.set_units(game, 'GERMANY', ['F NAO', 'F MAO'])
        self.move_to_phase(game, 'W1901A')
        if game.phase_type == 'A':
            self.set_orders(game, 'GERMANY', ['A WAR B', 'A KIE B', 'A MUN B'])
            self.process(game)
            assert self.check_results(game, 'A WAR', [VOID], phase='A')
            assert self.check_results(game, 'A KIE', [OK], phase='A')
            assert self.check_results(game, 'A MUN', [VOID], phase='A')
        assert self.owner_name(game, 'A WAR') is None
        assert self.owner_name(game, 'A KIE') == 'GERMANY'
        assert self.owner_name(game, 'A MUN') is None

    def test_6_i_2(self):
        """ 6.I.2. TEST CASE, FLEETS CAN NOT BE BUILD IN LAND AREAS
            Physical this is possible, but it is still not allowed.
            Russia has one build and Moscow is empty.
            Russia: Build F Moscow
            See issue 4.C.4. Some game masters will change the order and build an army in Moscow.
            I prefer that the build fails.
        """
        game = self.create_game()
        self.clear_units(game)
        self.clear_centers(game)
        self.set_centers(game, 'RUSSIA', 'MOS')
        self.move_to_phase(game, 'W1901A')
        if game.phase_type == 'A':
            self.set_orders(game, 'RUSSIA', ['F MOS B'])
            self.process(game)
            assert self.check_results(game, 'F MOS', [VOID], phase='A')
        assert self.owner_name(game, 'F MOS') is None

    def test_6_i_3(self):
        """ 6.I.3. TEST CASE, SUPPLY CENTER MUST BE EMPTY FOR BUILDING
            You can't have two units in a sector. So, you can't build when there is a unit in the supply center.
            Germany may build a unit but has an army in Berlin. Germany orders the following:
            Germany: Build A Berlin
            Build fails.
        """
        game = self.create_game()
        self.clear_units(game)
        self.clear_centers(game)
        self.set_centers(game, 'GERMANY', ['MUN', 'BER'])
        self.set_units(game, 'GERMANY', ['A BER'])
        self.move_to_phase(game, 'W1901A')
        if game.phase_type == 'A':
            self.set_orders(game, 'GERMANY', ['A BER B'])
            self.process(game)
            assert self.check_results(game, 'A BER', [VOID], phase='A')
        assert self.owner_name(game, 'A BER') == 'GERMANY'

    def test_6_i_4(self):
        """ 6.I.4. TEST CASE, BOTH COASTS MUST BE EMPTY FOR BUILDING
            If a sector is occupied on one coast, the other coast can not be used for building.
            Russia may build a unit and has a fleet in St Petersburg(sc). Russia orders the following:
            Russia: Build A St Petersburg(nc)
            Build fails.
        """
        game = self.create_game()
        self.clear_units(game)
        self.clear_centers(game)
        self.set_centers(game, 'RUSSIA', ['STP', 'MOS'])
        self.set_units(game, 'RUSSIA', ['F STP/SC'])
        self.move_to_phase(game, 'W1901A')
        if game.phase_type == 'A':
            self.set_orders(game, 'RUSSIA', ['F STP/NC B'])
            self.process(game)
            assert self.check_results(game, 'F STP/NC', [VOID], phase='A')
        assert self.owner_name(game, 'F STP') == 'RUSSIA'
        assert self.owner_name(game, 'F STP/NC') is None
        assert self.owner_name(game, 'F STP/SC') == 'RUSSIA'

    def test_6_i_5(self):
        """ 6.I.5. TEST CASE, BUILDING IN HOME SUPPLY CENTER THAT IS NOT OWNED
            Building a unit is only allowed when supply center is a home supply center and is owned. If not owned,
            build fails.
            Russia captured Berlin in Fall. Left Berlin. Germany can not build in Berlin.
            Germany: Build A Berlin
            Build fails.
        """
        game = self.create_game()
        self.clear_units(game)
        self.clear_centers(game)
        self.set_centers(game, 'GERMANY', 'MUN')
        self.set_centers(game, 'RUSSIA', 'BER')
        self.move_to_phase(game, 'W1901A')
        if game.phase_type == 'A':
            self.set_orders(game, 'GERMANY', ['A BER B'])
            self.process(game)
            assert self.check_results(game, 'A BER', [VOID], phase='A')
        assert self.owner_name(game, 'A BER') is None

    def test_6_i_6(self):
        """ 6.I.6. TEST CASE, BUILDING IN OWNED SUPPLY CENTER THAT IS NOT A HOME SUPPLY CENTER
            Building a unit is only allowed when supply center is a home supply center and is owned. If it is not
            a home supply center, the build fails.
            Germany owns Warsaw, Warsaw is empty and Germany may build one unit.
            Germany:
            Build A Warsaw
            Build fails.
        """
        game = self.create_game()
        self.clear_units(game)
        self.clear_centers(game)
        self.set_centers(game, 'GERMANY', ['MUN', 'WAR'])
        self.set_units(game, 'GERMANY', 'A MUN')
        self.move_to_phase(game, 'W1901A')
        if game.phase_type == 'A':
            self.set_orders(game, 'GERMANY', ['A WAR B'])
            self.process(game)
            assert self.check_results(game, 'A WAR', [VOID], phase='A')
        assert self.owner_name(game, 'A WAR') is None

    def test_6_i_7(self):
        """ 6.I.7. TEST CASE, ONLY ONE BUILD IN A HOME SUPPLY CENTER
            If you may build two units, you can still only build one in a supply center.
            Russia owns Moscow, Moscow is empty and Russia may build two units.
            Russia: Build A Moscow
            Russia: Build A Moscow
            The second build should fail.
        """
        game = self.create_game()
        self.clear_units(game)
        self.clear_centers(game)
        self.set_centers(game, 'RUSSIA', ['STP', 'MOS'])
        self.move_to_phase(game, 'W1901A')
        if game.phase_type == 'A':
            self.set_orders(game, 'RUSSIA', ['A MOS B', 'A MOS B'])
            self.process(game)
            assert self.check_results(game, 'A MOS', [VOID, OK], phase='A')
        assert self.owner_name(game, 'A MOS') == 'RUSSIA'

    # 6.J. TEST CASES, CIVIL DISORDER AND DISBANDS
    def test_6_j_1(self):
        """ 6.J.1. TEST CASE, TOO MANY REMOVE ORDERS
            Check how program reacts when someone orders too disbands.
            France has to disband one and has an army in Paris and Picardy.
            France: Remove F Gulf of Lyon
            France: Remove A Picardy
            France: Remove A Paris
            Program should not disband both Paris and Picardy, but should handle it in a different way. See also
            issue 4.D.6. I prefer that the disband orders are handled one by one. According to the preference, the
            removal of the fleet in the Gulf of Lyon fails (no fleet), the removal of the army in Picardy succeeds and
            the removal of the army in Paris fails (too many disbands).
        """
        game = self.create_game()
        self.clear_units(game)
        self.clear_centers(game)
        self.set_centers(game, 'FRANCE', 'PAR')
        self.set_units(game, 'FRANCE', ['A PIC', 'A PAR'])
        self.move_to_phase(game, 'W1901A')
        if game.phase_type == 'A':
            self.set_orders(game, 'FRANCE', ['F LYO D', 'A PIC D', 'A PAR D'])
            self.process(game)
            assert self.check_results(game, 'F LYO', [VOID], phase='A')
            assert self.check_results(game, 'A PIC', [OK], phase='A')
            assert self.check_results(game, 'A PAR', [VOID], phase='A')
        assert self.owner_name(game, 'F LYO') is None
        assert self.owner_name(game, 'A PIC') is None
        assert self.owner_name(game, 'A PAR') == 'FRANCE'

    def test_6_j_2(self):
        """ 6.J.2. TEST CASE, REMOVING THE SAME UNIT TWICE
            If you have to remove two units, you can always try to trick the computer by removing the same unit twice.
            France has to disband two and has an army in Paris.
            France: Remove A Paris
            France: Remove A Paris
            Program should remove army in Paris and remove another unit by using the civil disorder rules.
        """
        game = self.create_game()
        self.clear_units(game)
        self.clear_centers(game)
        self.set_centers(game, 'FRANCE', 'PAR')
        self.set_units(game, 'FRANCE', ['A PIC', 'A PAR', 'F NAO'])
        self.move_to_phase(game, 'W1901A')
        self.set_orders(game, 'FRANCE', ['A PAR D', 'A PAR D'])
        self.process(game)
        assert self.check_results(game, 'A PAR', [VOID, OK], phase='A')
        assert self.owner_name(game, 'A PAR') is None
        assert self.owner_name(game, 'A PIC') is None or self.owner_name(game, 'F NAO') is None

    def test_6_j_3(self):
        """ 6.J.3. TEST CASE, CIVIL DISORDER TWO ARMIES WITH DIFFERENT DISTANCE
            When a player forgets to disband a unit, the civil disorder rules must be applied. When two armies
            have different distance from the home supply centers, then the army with the greatest distance has to
            be removed.
            Russia has to remove one.
            Russia has armies in Livonia and Sweden.
            Russia does not order a disband.
            The army in Sweden is removed.
        """
        game = self.create_game()
        self.clear_units(game)
        self.clear_centers(game)
        self.set_centers(game, 'RUSSIA', 'SWE')
        self.set_units(game, 'RUSSIA', ['A LVN', 'A SWE'])
        self.move_to_phase(game, 'W1901A')
        self.process(game)
        assert self.owner_name(game, 'A LVN') == 'RUSSIA'
        assert self.owner_name(game, 'A SWE') is None

    def test_6_j_4(self):
        """ 6.J.4. TEST CASE, CIVIL DISORDER TWO ARMIES WITH EQUAL DISTANCE
            If two armies have equal distance from the home supply centers, then alphabetical order is used.
            Russia has to remove one.
            Russia has armies in Livonia and Ukraine.
            Russia does not order a disband.
            Both armies have distance one. The Livonia army is removed, because it appears first in alphabetical order.
        """
        game = self.create_game()
        self.clear_units(game)
        self.clear_centers(game)
        self.set_centers(game, 'RUSSIA', 'STP')
        self.set_units(game, 'RUSSIA', ['A LIV', 'A UKR'])
        self.move_to_phase(game, 'W1901A')
        self.process(game)
        assert self.owner_name(game, 'A LIV') is None
        assert self.owner_name(game, 'A UKR') == 'RUSSIA'

    def test_6_j_5(self):
        """ 6.J.5 TEST CASE, CIVIL DISORDER TWO FLEETS WITH DIFFERENT DISTANCE
            If two fleets have different distance from the home supply centers, then the fleet with the greatest
            distance has to be removed. Note that fleets can not go over land.
            Russia has to remove one.
            Russia has fleets in Skagerrak and Berlin.
            Russia does not order a disband.
            The distance of the fleet in Berlin is three (the fleet can not go to Warsaw), the fleet in Skaggerrak
            has distance two (via Norway). So, the fleet in Berlin has to be removed.
        """
        game = self.create_game()
        self.clear_units(game)
        self.clear_centers(game)
        self.set_centers(game, 'RUSSIA', 'BER')
        self.set_units(game, 'RUSSIA', ['F SKA', 'F BER'])
        self.move_to_phase(game, 'W1901A')
        self.process(game)
        assert self.owner_name(game, 'F SKA') == 'RUSSIA'
        assert self.owner_name(game, 'F BER') is None

    def test_6_j_6(self):
        """ 6.J.6. TEST CASE, CIVIL DISORDER TWO FLEETS WITH EQUAL DISTANCE
            Alphabetical order is used, when two fleets have equal distance to the home supply centers.
            Russia has to remove one.
            Russia has fleets in Berlin and Helgoland Bight.
            Russia does not order a disband.
            The distances of both fleets to one of the home supply centers is three. The fleet in the Berlin is
            removed, because it appears first in alphabetical order. This also tests whether fleets can not go over
            land. If they could go over land, the distance of Berlin would be two (going to Warsaw) and the fleet in
            the Helgoland Bight would have incorrectly be removed.
        """
        game = self.create_game()
        self.clear_units(game)
        self.clear_centers(game)
        self.set_centers(game, 'RUSSIA', 'BER')
        self.set_units(game, 'RUSSIA', ['F BER', 'F HEL'])
        self.move_to_phase(game, 'W1901A')
        self.process(game)
        assert self.owner_name(game, 'F BER') is None
        assert self.owner_name(game, 'F HEL') == 'RUSSIA'

    def test_6_j_7(self):
        """ 6.J.7. TEST CASE, CIVIL DISORDER TWO FLEETS AND ARMY WITH EQUAL DISTANCE
            In removal, the fleet has precedence over an army. In this case there are two fleets, to make the test
            more complex.
            Russia has to remove one.
            Russia has an army in Bohemia, a fleet in Skagerrak and a fleet in the North Sea.
            Russia does not order a disband.
            The distances of the army and the fleets to one of the home supply centers are two. The fleets take
            precedence above the army (although the army is alphabetical first). The fleet in the North Sea is
            alphabetical first, compared to Skagerrak and has to be removed.
        """
        game = self.create_game()
        self.clear_units(game)
        self.clear_centers(game)
        self.set_centers(game, 'RUSSIA', ['STP', 'MOS'])
        self.set_units(game, 'RUSSIA', ['A BOH', 'F SKA', 'F NTH'])
        self.move_to_phase(game, 'W1901A')
        self.process(game)
        assert self.owner_name(game, 'A BOH') == 'RUSSIA'
        assert self.owner_name(game, 'F SKA') == 'RUSSIA'
        assert self.owner_name(game, 'F NTH') is None

    def test_6_j_8(self):
        """ 6.J.8. TEST CASE, CIVIL DISORDER A FLEET WITH SHORTER DISTANCE THEN THE ARMY
            If the fleet has a shorter distance than the army, the army is removed.
            Russia has to remove one.
            Russia has an army in Tyrolia and a fleet in the Baltic Sea.
            Russia does not order a disband.
            The distances of the army to Warsaw is three while the distance of the fleet is two. So, the army
            is removed.
        """
        game = self.create_game()
        self.clear_units(game)
        self.clear_centers(game)
        self.set_centers(game, 'RUSSIA', 'STP')
        self.set_units(game, 'RUSSIA', ['A TYR', 'F BAL'])
        self.move_to_phase(game, 'W1901A')
        self.process(game)
        assert self.owner_name(game, 'A TYR') is None
        assert self.owner_name(game, 'F BAL') == 'RUSSIA'

    def test_6_j_9(self):
        """ 6.J.9. TEST CASE, CIVIL DISORDER MUST BE COUNTED FROM BOTH COASTS
            Distance must be calculated from both coasts.

            a)
            Russia has to remove one.
            Russia has an army in Tyrolia and a fleet in the Baltic Sea.
            Russia does not order a disband.
            The distance of the fleet to St Petersburg(nc) is three but to St Petersburg(sc) is two. So, the army
            in Tyrolia must be removed.

            b)
            Russia has to remove one.
            Russia has an army in Tyrolia and a fleet in Skagerrak.
            Russia does not order a disband.
            The distance of the fleet to St Petersburg(sc) is three but to St Petersburg(nc) is two. So, the army
            in Tyrolia must be removed.
        """
        # a)
        game = self.create_game()
        self.clear_units(game)
        self.clear_centers(game)
        self.set_centers(game, 'RUSSIA', 'STP')
        self.set_units(game, 'RUSSIA', ['A TYR', 'F BAL'])
        self.move_to_phase(game, 'W1901A')
        self.process(game)
        assert self.owner_name(game, 'A TYR') is None
        assert self.owner_name(game, 'F BAL') == 'RUSSIA'

        # b)
        game = self.create_game()
        self.clear_units(game)
        self.clear_centers(game)
        self.set_centers(game, 'RUSSIA', 'STP')
        self.set_units(game, 'RUSSIA', ['A TYR', 'F SKA'])
        self.move_to_phase(game, 'W1901A')
        self.process(game)
        assert self.owner_name(game, 'A TYR') is None
        assert self.owner_name(game, 'F SKA') == 'RUSSIA'

    def test_6_j_10(self):
        """ 6.J.10. TEST CASE, CIVIL DISORDER COUNTING CONVOYING DISTANCE
            For armies the distance must be calculated by taking land areas, coastal areas as sea areas.
            Italy has to remove one.
            Italy has a fleet in the Ionian Sea and armies in Greece and Silesia.
            Italy does not order a disband.
            The distance from Greece to one of the Italian home supply center is three over land. However, using
            a convoy the distance is one or two (depending how you count, see issue 4.D.8). Anyway, the army in
            Silesia has to be removed.
        """
        game = self.create_game()
        self.clear_units(game)
        self.clear_centers(game)
        self.set_centers(game, 'ITALY', ['GRE', 'NAP'])
        self.set_units(game, 'ITALY', ['F ION', 'A GRE', 'A SIL'])
        self.move_to_phase(game, 'W1901A')
        self.process(game)
        assert self.owner_name(game, 'F ION') == 'ITALY'
        assert self.owner_name(game, 'A GRE') == 'ITALY'
        assert self.owner_name(game, 'A SIL') is None

    def test_6_j_11(self):
        """ 6.J.11. TEST CASE, CIVIL DISORDER COUNTING DISTANCE WITHOUT CONVOYING FLEET
            If there is no convoying fleet the result depends on the interpretation of the rules.
            Italy has to remove one.
            Italy has armies in Greece and Silesia.
            Italy does not order a disband.
            The distance from Greece to one of the Italian home supply centers is one, two or three (depending how
            you count, see issue 4.D.8).
            I prefer that sea areas just add one to the distance. According to this preference, the distance is two
            and the army in Silesia has to be removed.
        """
        game = self.create_game()
        self.clear_units(game)
        self.clear_centers(game)
        self.set_centers(game, 'ITALY', 'GRE')
        self.set_units(game, 'ITALY', ['A GRE', 'A SIL'])
        self.move_to_phase(game, 'W1901A')
        self.process(game)
        assert self.owner_name(game, 'A GRE') == 'ITALY'
        assert self.owner_name(game, 'A SIL') is None

    # 6.K. TEST CASES - CUSTOM TESTS
    def test_6_k_1(self):
        """ 6.K.1. TEST CASE, CIVIL DISORDER WITH SOME ORDERS.
            When a power has to disband multiple units, but does not disband all its units, the civil disorder rule
            should automatically disband units that have not already been disbanded.

            England has to remove two.
            England has 7 units (armies in Ruhr, Holland, Edinburg and fleets in North Sea, Botnia, St. Petersburg/NC,
            and Irish Sea).
            England has 5 centers (Edinburg, London, Holland, Sweden and St. Petersburg)
            England disband the fleet at Botnia Sea.

            The civil disorder rule would automatically disband Botnia Sea, but since this unit is already disbanded
            it needs to select the next unit which is St. Petersburg/NC.
        """
        game = self.create_game()
        self.clear_units(game)
        self.clear_centers(game)
        self.set_centers(game, 'ENGLAND', ['EDI', 'LON', 'HOL', 'SWE', 'STP'])
        self.set_units(game, 'ENGLAND', ['A RUH', 'F NTH', 'F BOT', 'A HOL', 'F STP/NC', 'F IRI', 'A EDI'])
        self.move_to_phase(game, 'W1901A')
        self.set_orders(game, 'ENGLAND', ['F BOT D'])
        self.process(game)
        assert self.owner_name(game, 'A RUH') == 'ENGLAND'
        assert self.owner_name(game, 'F NTH') == 'ENGLAND'
        assert self.owner_name(game, 'A HOL') == 'ENGLAND'
        assert self.owner_name(game, 'F IRI') == 'ENGLAND'
        assert self.owner_name(game, 'A EDI') == 'ENGLAND'
        assert self.owner_name(game, 'F BOT') is None
        assert self.owner_name(game, 'F STP/NC') is None

    def test_6_k_2(self):
        """ 6.K.2. TEST CASE, SUPPORT OF A FAILED CONVOYING FLEET
            The engine is supposed to not allow the support of an army moving via a convoy if the convoy fails. This
            rule tests that a support of a fleet convoying is still valid even if the convoy fails.

            France has 4 units (Fleets in Mid-Atlantic, Irish Sea, Western Mediterranean, and army in Brest)
            England has 2 units (Fleets in North Atlantic, and English Channel).
            France: The army in Brest wants to move via convoy to Clyde.
            France: The fleet in Mid-Atlantic convoys the army in Brest to Clyde.
            France: The fleet in Irish Sea convoys the army in Brest to Clyde.
            France: The fleet in Western Mediterranean supports the fleet in Mid-Atlantic.
            England: The fleet in North Atlantic attacks the fleet in Mid-Atlantic.
            England: The fleet in English Channel supports the attack of North Atlantic to Mid-Atlantic.

            The convoy fails because they are no valid path, but the support from Western Mediterranean is still valid
            and the attack from North Atlantic should bounce.
        """
        game = self.create_game()
        self.clear_units(game)
        self.clear_centers(game)
        self.set_units(game, 'FRANCE', ['F MAO', 'F IRI', 'A BRE', 'F WES'])
        self.set_units(game, 'ENGLAND', ['F NAO', 'F ENG'])
        self.set_orders(game, 'FRANCE', ['F MAO C A BRE - CLY', 'F IRI C A BRE - CLY', 'A BRE - CLY VIA',
                                         'F WES S F MAO'])
        self.set_orders(game, 'ENGLAND', ['F NAO - MAO', 'F ENG S F NAO - MAO'])
        self.process(game)
        assert self.check_results(game, 'F MAO', NO_CONVOY)
        assert self.check_results(game, 'F IRI', NO_CONVOY)
        assert self.check_results(game, 'A BRE', NO_CONVOY)
        assert self.check_results(game, 'F WES', OK)
        assert self.check_results(game, 'F NAO', BOUNCE)
        assert self.check_results(game, 'F ENG', OK)
        assert self.owner_name(game, 'F MAO') == 'FRANCE'
        assert self.owner_name(game, 'F IRI') == 'FRANCE'
        assert self.owner_name(game, 'A BRE') == 'FRANCE'
        assert self.owner_name(game, 'F WES') == 'FRANCE'
        assert self.owner_name(game, 'A CLY') is None
        assert self.owner_name(game, 'F NAO') == 'ENGLAND'
        assert self.owner_name(game, 'F ENG') == 'ENGLAND'

def check_dislodged(game, unit, dislodger):
    """ Checks if a unit has been dislodged """
    if not game:
        return False
    if unit not in game.dislodged:
        return False
    return game.dislodged[unit] == ''.join(dislodger.split()[1:])[:3]
