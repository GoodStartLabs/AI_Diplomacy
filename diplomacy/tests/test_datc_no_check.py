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
""" DATC Test Cases (Using rule NO_CHECK)
    - Contains the diplomacy adjudication test cases (without order validation)
"""
from diplomacy.engine.game import Game
from diplomacy.tests.test_datc import TestDATC as RootDATC
from diplomacy.utils.order_results import OK, VOID

# -----------------
# DATC TEST CASES (Without order validation)
# -----------------
class TestDATCNoCheck(RootDATC):
    """ DATC test cases"""

    @staticmethod
    def create_game():
        """ Creates a game object"""
        game = Game()
        game.add_rule('NO_CHECK')
        return game

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

        # >>>>>>>>>>>>>>>>>>>>>>>>
        # For NO_CHECK, we expect to find the unit in game.orderable_units
        # But we require that the order is marked as 'void'
        # As opposed to a regular game, where an invalid order is dropped
        # <<<<<<<<<<<<<<<<<<<<<<<<
        # Invalid order
        if value == VOID:
            if VOID in result.get(unit, []):
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
