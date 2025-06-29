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
""" DATC Test Cases (No Expansion)
    - Contains the diplomacy adjudication test cases (without order expansion)
"""
from diplomacy.tests.test_datc import TestDATC as RootDATC
from diplomacy.utils.order_results import OK, BOUNCE, VOID

# -----------------
# DATC TEST CASES (Without order expansion)
# -----------------
class TestDATCNoExpand(RootDATC):
    """ DATC test cases"""

    @staticmethod
    def set_orders(game, power_name, orders):
        """ Submit orders """
        game.set_orders(power_name, orders, expand=False)

    def test_6_b_2(self):
        """ 6.B.2. TEST CASE, MOVING WITH UNSPECIFIED COAST WHEN COAST IS NOT NECESSARY
            There is only one coast possible in this case:
            France: F Gascony - Spain
            Since the North Coast is the only coast that can be reached, it seems logical that
            the a move is attempted to the north coast of Spain. Some adjudicators require that a coast
            is also specified in this case and will decide that the move fails or take a default coast (see 4.B.2).
            I prefer that an attempt is made to the only possible coast, the north coast of Spain.
        """
        # Expected to failed

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
        game = self.create_game()
        self.clear_units(game)
        self.set_units(game, 'FRANCE', ['F POR', 'F MAO'])
        self.set_units(game, 'ITALY', ['F LYO', 'F WES'])
        self.set_orders(game, 'FRANCE', ['F POR S F MAO - SPA/NC', 'F MAO - SPA/SC'])
        self.set_orders(game, 'ITALY', ['F LYO S F WES - SPA/SC', 'F WES - SPA/SC'])
        self.process(game)
        assert self.check_results(game, 'F POR', VOID)
        assert self.check_results(game, 'F MAO', BOUNCE)
        assert self.check_results(game, 'F LYO', OK)
        assert self.check_results(game, 'F WES', OK)
        assert self.owner_name(game, 'F POR') == 'FRANCE'
        assert self.owner_name(game, 'F MAO') == 'FRANCE'
        assert self.owner_name(game, 'F SPA') == 'ITALY'
        assert self.owner_name(game, 'F SPA/NC') is None
        assert self.owner_name(game, 'F SPA/SC') == 'ITALY'
        assert self.owner_name(game, 'F LYO') == 'ITALY'
        assert self.owner_name(game, 'F WES') is None

    def test_6_b_10(self):
        """ 6.B.10. TEST CASE, UNIT ORDERED WITH WRONG COAST
            A player might specify the wrong coast for the ordered unit.
            France has a fleet on the south coast of Spain and orders:
            France: F Spain(nc) - Gulf of Lyon
            If only perfect orders are accepted, then the move will fail, but since the coast for the ordered unit
            has no purpose, it might also be ignored (see issue 4.B.5).
            I prefer that a move will be attempted.
        """
        # Expected to fail

    def test_6_b_12(self):
        """ 6.B.12. TEST CASE, ARMY MOVEMENT WITH COASTAL SPECIFICATION
            For armies the coasts are irrelevant:
            France: A Gascony - Spain(nc)
            If only perfect orders are accepted, then the move will fail. But it is also possible that coasts are
            ignored in this case and a move will be attempted (see issue 4.B.6).
            I prefer that a move will be attempted.
        """
        # Expected to fail
