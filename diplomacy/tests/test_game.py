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
""" Test_game
    - Contains tests for the game object
"""
from copy import deepcopy
from diplomacy.engine.game import Game
from diplomacy.utils.order_results import BOUNCE

def test_is_game_done():
    """ Tests if the game is done """
    game = Game()
    assert not game.is_game_done
    game.phase = 'COMPLETED'
    assert game.is_game_done

def test_create_game():
    """ Test - Creates a game """
    game = Game()
    assert not game.error

def test_get_units():
    """ Tests - get units """
    game = Game()
    game.clear_units()
    game.set_units('FRANCE', ['A PAR', 'A MAR'])
    game.set_units('ENGLAND', ['A PAR', 'A LON'])
    units = game.get_units()
    assert units['AUSTRIA'] == []
    assert units['ENGLAND'] == ['A PAR', 'A LON']
    assert units['FRANCE'] == ['A MAR']
    assert units['GERMANY'] == []
    assert units['ITALY'] == []
    assert units['RUSSIA'] == []
    assert units['TURKEY'] == []

    assert game.get_units('AUSTRIA') == []
    assert game.get_units('ENGLAND') == ['A PAR', 'A LON']
    assert game.get_units('FRANCE') == ['A MAR']
    assert game.get_units('GERMANY') == []
    assert game.get_units('ITALY') == []
    assert game.get_units('RUSSIA') == []
    assert game.get_units('TURKEY') == []

    # Making sure we got a copy, and not a direct game reference
    game.set_units('FRANCE', ['F MAR'])
    units_2 = game.get_units()
    assert units['FRANCE'] == ['A MAR']
    assert units_2['FRANCE'] == ['F MAR']

def test_get_centers():
    """ Test - get centers """
    game = Game()
    centers = game.get_centers()
    assert centers['AUSTRIA'] == ['BUD', 'TRI', 'VIE']
    assert centers['ENGLAND'] == ['EDI', 'LON', 'LVP']
    assert centers['FRANCE'] == ['BRE', 'MAR', 'PAR']
    assert centers['GERMANY'] == ['BER', 'KIE', 'MUN']
    assert centers['ITALY'] == ['NAP', 'ROM', 'VEN']
    assert centers['RUSSIA'] == ['MOS', 'SEV', 'STP', 'WAR']
    assert centers['TURKEY'] == ['ANK', 'CON', 'SMY']

    assert game.get_centers('AUSTRIA') == ['BUD', 'TRI', 'VIE']
    assert game.get_centers('ENGLAND') == ['EDI', 'LON', 'LVP']
    assert game.get_centers('FRANCE') == ['BRE', 'MAR', 'PAR']
    assert game.get_centers('GERMANY') == ['BER', 'KIE', 'MUN']
    assert game.get_centers('ITALY') == ['NAP', 'ROM', 'VEN']
    assert game.get_centers('RUSSIA') == ['MOS', 'SEV', 'STP', 'WAR']
    assert game.get_centers('TURKEY') == ['ANK', 'CON', 'SMY']

    # Making sure we got a copy, and not a direct game reference
    austria = game.get_power('AUSTRIA')
    austria.centers.remove('BUD')
    centers_2 = game.get_centers()
    assert centers['AUSTRIA'] == ['BUD', 'TRI', 'VIE']
    assert centers_2['AUSTRIA'] == ['TRI', 'VIE']

def test_get_orders():
    """ Test - get orders """
    check_sorted = lambda list_1, list_2: sorted(list_1) == sorted(list_2)
    game = Game()

    # Movement phase
    game.set_orders('FRANCE', ['A PAR H', 'A MAR - BUR'])
    game.set_orders('ENGLAND', ['LON H'])
    orders = game.get_orders()
    assert check_sorted(orders['AUSTRIA'], [])
    assert check_sorted(orders['ENGLAND'], ['F LON H'])
    assert check_sorted(orders['FRANCE'], ['A PAR H', 'A MAR - BUR'])
    assert check_sorted(orders['GERMANY'], [])
    assert check_sorted(orders['ITALY'], [])
    assert check_sorted(orders['RUSSIA'], [])
    assert check_sorted(orders['TURKEY'], [])

    assert check_sorted(game.get_orders('AUSTRIA'), [])
    assert check_sorted(game.get_orders('ENGLAND'), ['F LON H'])
    assert check_sorted(game.get_orders('FRANCE'), ['A PAR H', 'A MAR - BUR'])
    assert check_sorted(game.get_orders('GERMANY'), [])
    assert check_sorted(game.get_orders('ITALY'), [])
    assert check_sorted(game.get_orders('RUSSIA'), [])
    assert check_sorted(game.get_orders('TURKEY'), [])

    # Making sure we got a copy, and not a direct game reference
    france = game.get_power('FRANCE')
    del france.orders['A PAR']
    orders_2 = game.get_orders()
    assert check_sorted(orders['FRANCE'], ['A PAR H', 'A MAR - BUR'])
    assert check_sorted(orders_2['FRANCE'], ['A MAR - BUR'])

    # Moving to W1901A
    game.clear_units('FRANCE')
    game.set_centers('FRANCE', 'SPA')
    game.process()
    game.process()
    assert game.get_current_phase() == 'W1901A'

    # Adjustment phase
    game.set_orders('FRANCE', ['A MAR B', 'F MAR B'])
    game.set_orders('AUSTRIA', 'A PAR H')
    orders = game.get_orders()
    assert check_sorted(orders['AUSTRIA'], [])
    assert check_sorted(orders['ENGLAND'], [])
    assert check_sorted(orders['FRANCE'], ['A MAR B'])
    assert check_sorted(orders['GERMANY'], [])
    assert check_sorted(orders['ITALY'], [])
    assert check_sorted(orders['RUSSIA'], [])
    assert check_sorted(orders['TURKEY'], [])

    assert check_sorted(game.get_orders('AUSTRIA'), [])
    assert check_sorted(game.get_orders('ENGLAND'), [])
    assert check_sorted(game.get_orders('FRANCE'), ['A MAR B'])
    assert check_sorted(game.get_orders('GERMANY'), [])
    assert check_sorted(game.get_orders('ITALY'), [])
    assert check_sorted(game.get_orders('RUSSIA'), [])
    assert check_sorted(game.get_orders('TURKEY'), [])

def test_get_orders_no_check():
    """ Test - get orders NO_CHECK """
    check_sorted = lambda list_1, list_2: sorted(list_1) == sorted(list_2)
    game = Game()
    game.add_rule('NO_CHECK')

    # Movement phase
    game.set_orders('FRANCE', ['A PAR H', 'A MAR - BUR'])
    game.set_orders('ENGLAND', ['LON H'])
    orders = game.get_orders()
    assert check_sorted(orders['AUSTRIA'], [])
    assert check_sorted(orders['ENGLAND'], ['LON H'])                       # Should not be fixed
    assert check_sorted(orders['FRANCE'], ['A PAR H', 'A MAR - BUR'])
    assert check_sorted(orders['GERMANY'], [])
    assert check_sorted(orders['ITALY'], [])
    assert check_sorted(orders['RUSSIA'], [])
    assert check_sorted(orders['TURKEY'], [])

    assert check_sorted(game.get_orders('AUSTRIA'), [])
    assert check_sorted(game.get_orders('ENGLAND'), ['LON H'])              # Should not be fixed
    assert check_sorted(game.get_orders('FRANCE'), ['A PAR H', 'A MAR - BUR'])
    assert check_sorted(game.get_orders('GERMANY'), [])
    assert check_sorted(game.get_orders('ITALY'), [])
    assert check_sorted(game.get_orders('RUSSIA'), [])
    assert check_sorted(game.get_orders('TURKEY'), [])

    # Making sure we got a copy, and not a direct game reference
    france = game.get_power('FRANCE')
    france.orders = {order_ix: order_value for order_ix, order_value in france.orders.items()
                     if not order_value.startswith('A PAR')}
    orders_2 = game.get_orders()
    assert check_sorted(orders['FRANCE'], ['A PAR H', 'A MAR - BUR'])
    assert check_sorted(orders_2['FRANCE'], ['A MAR - BUR'])

    # Moving to W1901A
    game.clear_units('FRANCE')
    game.set_centers('FRANCE', 'SPA')
    game.process()
    game.process()
    assert game.get_current_phase() == 'W1901A'

    # Adjustment phase
    game.set_orders('FRANCE', ['A MAR B', 'F MAR B'])
    game.set_orders('AUSTRIA', 'A PAR H')
    orders = game.get_orders()
    assert check_sorted(orders['AUSTRIA'], [])                  # 'A PAR H' is VOID
    assert check_sorted(orders['ENGLAND'], [])
    assert check_sorted(orders['FRANCE'], ['A MAR B'])          # 'F MAR B' is VOID
    assert check_sorted(orders['GERMANY'], [])
    assert check_sorted(orders['ITALY'], [])
    assert check_sorted(orders['RUSSIA'], [])
    assert check_sorted(orders['TURKEY'], [])

    assert check_sorted(game.get_orders('AUSTRIA'), [])
    assert check_sorted(game.get_orders('ENGLAND'), [])
    assert check_sorted(game.get_orders('FRANCE'), ['A MAR B'])
    assert check_sorted(game.get_orders('GERMANY'), [])
    assert check_sorted(game.get_orders('ITALY'), [])
    assert check_sorted(game.get_orders('RUSSIA'), [])
    assert check_sorted(game.get_orders('TURKEY'), [])

def test_get_order_status():
    """ Tests - get order status """
    game = Game()
    game.clear_units()
    game.set_units('ITALY', 'A VEN')
    game.set_units('AUSTRIA', 'A VIE')
    game.set_orders('ITALY', 'A VEN - TYR')
    game.set_orders('AUSTRIA', 'A VIE - TYR')
    game.process()
    results = game.get_order_status()
    assert BOUNCE in results['ITALY']['A VEN']
    assert BOUNCE in results['AUSTRIA']['A VIE']
    assert BOUNCE in game.get_order_status(unit='A VEN')
    assert BOUNCE in game.get_order_status(unit='A VIE')
    assert BOUNCE in game.get_order_status('ITALY')['A VEN']
    assert BOUNCE in game.get_order_status('AUSTRIA')['A VIE']

def test_set_units():
    """ Test - Sets units """
    game = Game()
    game.clear_units()
    game.set_units('FRANCE', ['A PAR', 'A MAR', '*A GAS'], reset=False)
    game.set_units('ENGLAND', ['A PAR', 'A LON'])
    assert game.get_power('AUSTRIA').units == []
    assert game.get_power('ENGLAND').units == ['A PAR', 'A LON']
    assert game.get_power('FRANCE').units == ['A MAR']
    assert 'A GAS' in game.get_power('FRANCE').retreats
    assert game.get_power('GERMANY').units == []
    assert game.get_power('ITALY').units == []
    assert game.get_power('RUSSIA').units == []
    assert game.get_power('TURKEY').units == []

    # Adding F PIC to England without resetting
    game.set_units('ENGLAND', ['F PIC'], reset=False)
    assert game.get_power('ENGLAND').units == ['A PAR', 'A LON', 'F PIC']

    # Adding F PIC to England with resetting
    game.set_units('ENGLAND', ['F PIC'], reset=True)
    assert game.get_power('ENGLAND').units == ['F PIC']

    # Adding F PAR (Illegal unit) to England without resetting
    game.set_units('ENGLAND', ['F PAR'], reset=False)
    assert game.get_power('ENGLAND').units == ['F PIC']

def test_set_centers():
    """ Tests - Sets centers """
    game = Game()
    game.clear_centers()
    game.set_centers('FRANCE', ['PAR', 'MAR', 'GAS'])       # GAS is not a valid SC loc
    game.set_centers('ENGLAND', ['PAR', 'LON'])
    assert game.get_power('AUSTRIA').centers == []
    assert game.get_power('ENGLAND').centers == ['PAR', 'LON']
    assert game.get_power('FRANCE').centers == ['MAR']
    assert game.get_power('GERMANY').centers == []
    assert game.get_power('ITALY').centers == []
    assert game.get_power('RUSSIA').centers == []
    assert game.get_power('TURKEY').centers == []

    # Adding BUD to England without resetting
    game.set_centers('ENGLAND', 'BUD', reset=False)
    assert game.get_power('ENGLAND').centers == ['PAR', 'LON', 'BUD']

    # Adding BUD to England with resetting
    game.set_centers('ENGLAND', ['BUD'], reset=True)
    assert game.get_power('ENGLAND').centers == ['BUD']

    # Adding UKR to England (illegal SC)
    game.set_centers('ENGLAND', 'UKR', reset=False)
    assert game.get_power('ENGLAND').centers == ['BUD']

def test_set_orders():
    """ Test - Sets orders """
    game = Game()
    game.clear_units()
    game.set_units('ITALY', 'A VEN')
    game.set_units('AUSTRIA', 'A VIE')
    game.set_units('FRANCE', 'A PAR')
    game.set_orders('ITALY', 'A VEN - TYR')
    game.set_orders('AUSTRIA', 'A VIE - TYR')

    game.set_orders('FRANCE', ['', '', 'A PAR - GAS', '', '', ''])
    game.set_orders('RUSSIA', '')
    game.set_orders('GERMANY', [])
    assert game.get_orders('FRANCE') == ['A PAR - GAS']
    assert not game.get_orders('RUSSIA')
    assert not game.get_orders('GERMANY')

    game.process()
    results = game.get_order_status()
    assert BOUNCE in results['ITALY']['A VEN']
    assert BOUNCE in results['AUSTRIA']['A VIE']

def test_set_orders_replace():
    """ Test - Sets orders with replace=True """
    check_sorted = lambda list_1, list_2: sorted(list_1) == sorted(list_2)

    # Regular Movement Phase
    game = Game()
    game.clear_units()
    game.set_units('ITALY', ['A VEN', 'A PAR'])
    game.set_units('AUSTRIA', 'A VIE')
    game.set_orders('ITALY', ['A VEN - TYR', 'A PAR H'])
    game.set_orders('AUSTRIA', 'A VIE - TYR')
    game.set_orders('ITALY', 'A PAR - GAS')
    orders = game.get_orders()
    assert check_sorted(orders['ITALY'], ['A VEN - TYR', 'A PAR - GAS'])
    assert check_sorted(orders['AUSTRIA'], ['A VIE - TYR'])

    # NO_CHECK Movement Phase
    game = Game()
    game.add_rule('NO_CHECK')
    game.clear_units()
    game.set_units('ITALY', ['A VEN', 'A PAR'])
    game.set_units('AUSTRIA', 'A VIE')
    game.set_orders('ITALY', ['A VEN - TYR', 'A PAR H'])
    game.set_orders('AUSTRIA', 'A VIE - TYR')
    game.set_orders('ITALY', 'A PAR - GAS')
    orders = game.get_orders()
    assert check_sorted(orders['ITALY'], ['A VEN - TYR', 'A PAR - GAS'])
    assert check_sorted(orders['AUSTRIA'], ['A VIE - TYR'])

    # Regular Retreat Phase
    game = Game()
    game.clear_units()
    game.set_units('ITALY', ['A BRE', 'A PAR'])
    game.set_units('AUSTRIA', 'A GAS')
    game.set_orders('ITALY', ['A BRE - GAS', 'A PAR S A BRE - GAS'])
    game.set_orders('AUSTRIA', 'A GAS H')
    game.process()
    game.set_orders('AUSTRIA', 'A GAS R MAR')
    game.set_orders('AUSTRIA', 'A GAS R SPA')
    orders = game.get_orders()
    assert check_sorted(orders['AUSTRIA'], ['A GAS R SPA'])

    # NO_CHECK Retreat Phase
    game = Game()
    game.add_rule('NO_CHECK')
    game.clear_units()
    game.set_units('ITALY', ['A BRE', 'A PAR'])
    game.set_units('AUSTRIA', 'A GAS')
    game.set_orders('ITALY', ['A BRE - GAS', 'A PAR S A BRE - GAS'])
    game.set_orders('AUSTRIA', 'A GAS H')
    game.process()
    game.set_orders('AUSTRIA', 'A GAS R MAR')
    game.set_orders('AUSTRIA', 'A GAS R SPA')
    orders = game.get_orders()
    assert check_sorted(orders['AUSTRIA'], ['A GAS R SPA'])

    # Regular Adjustment Phase
    game = Game()
    game.clear_units()
    game.clear_centers()
    game.set_units('FRANCE', ['A BRE', 'A PAR'])
    game.set_units('AUSTRIA', 'A GAS')
    game.set_orders('FRANCE', 'A PAR - PIC')
    game.process()
    game.set_orders('FRANCE', ['A PIC - BEL', 'A BRE - PAR'])
    game.process()
    game.set_orders('FRANCE', 'A BRE B')
    game.set_orders('FRANCE', 'F BRE B')
    orders = game.get_orders()
    assert check_sorted(orders['FRANCE'], ['F BRE B'])

    # NO_CHECK Adjustment Phase
    game = Game()
    game.add_rule('NO_CHECK')
    game.clear_units()
    game.clear_centers()
    game.set_units('FRANCE', ['A BRE', 'A PAR'])
    game.set_units('AUSTRIA', 'A GAS')
    game.set_orders('FRANCE', 'A PAR - PIC')
    game.process()
    game.set_orders('FRANCE', ['A PIC - BEL', 'A BRE - PAR'])
    game.process()
    game.set_orders('FRANCE', 'A BRE B')
    game.set_orders('FRANCE', 'F BRE B')
    orders = game.get_orders()
    assert check_sorted(orders['FRANCE'], ['F BRE B'])

def test_set_orders_no_replace():
    """ Test - Sets orders with replace=False """
    check_sorted = lambda list_1, list_2: sorted(list_1) == sorted(list_2)

    # Regular Movement Phase
    game = Game()
    game.clear_units()
    game.set_units('ITALY', ['A VEN', 'A PAR'])
    game.set_units('AUSTRIA', 'A VIE')
    game.set_orders('ITALY', ['A VEN - TYR', 'A PAR H'], replace=False)
    game.set_orders('AUSTRIA', 'A VIE - TYR', replace=False)
    game.set_orders('ITALY', 'A PAR - GAS', replace=False)
    orders = game.get_orders()
    assert check_sorted(orders['ITALY'], ['A VEN - TYR', 'A PAR H'])
    assert check_sorted(orders['AUSTRIA'], ['A VIE - TYR'])

    # NO_CHECK Movement Phase
    game = Game()
    game.add_rule('NO_CHECK')
    game.clear_units()
    game.set_units('ITALY', ['A VEN', 'A PAR'])
    game.set_units('AUSTRIA', 'A VIE')
    game.set_orders('ITALY', ['A VEN - TYR', 'A PAR H'], replace=False)
    game.set_orders('AUSTRIA', 'A VIE - TYR', replace=False)
    game.set_orders('ITALY', 'A PAR - GAS', replace=False)
    orders = game.get_orders()
    assert check_sorted(orders['ITALY'], ['A VEN - TYR', 'A PAR H', 'A PAR - GAS'])
    assert check_sorted(orders['AUSTRIA'], ['A VIE - TYR'])

    # Regular Retreat Phase
    game = Game()
    game.clear_units()
    game.set_units('ITALY', ['A BRE', 'A PAR'])
    game.set_units('AUSTRIA', 'A GAS')
    game.set_orders('ITALY', ['A BRE - GAS', 'A PAR S A BRE - GAS'], replace=False)
    game.set_orders('AUSTRIA', 'A GAS H', replace=False)
    game.process()
    game.set_orders('AUSTRIA', 'A GAS R MAR', replace=False)
    game.set_orders('AUSTRIA', 'A GAS R SPA', replace=False)
    orders = game.get_orders()
    assert check_sorted(orders['AUSTRIA'], ['A GAS R MAR'])

    # NO_CHECK Retreat Phase
    game = Game()
    game.add_rule('NO_CHECK')
    game.clear_units()
    game.set_units('ITALY', ['A BRE', 'A PAR'])
    game.set_units('AUSTRIA', 'A GAS')
    game.set_orders('ITALY', ['A BRE - GAS', 'A PAR S A BRE - GAS'], replace=False)
    game.set_orders('AUSTRIA', 'A GAS H', replace=False)
    game.process()
    game.set_orders('AUSTRIA', 'A GAS R MAR', replace=False)
    game.set_orders('AUSTRIA', 'A GAS R SPA', replace=False)
    orders = game.get_orders()
    assert check_sorted(orders['AUSTRIA'], ['A GAS R MAR'])

    # Regular Adjustment Phase
    game = Game()
    game.clear_units()
    game.clear_centers()
    game.set_units('FRANCE', ['A BRE', 'A PAR'])
    game.set_units('AUSTRIA', 'A GAS')
    game.set_orders('FRANCE', 'A PAR - PIC', replace=False)
    game.process()
    game.set_orders('FRANCE', ['A PIC - BEL', 'A BRE - PAR'], replace=False)
    game.process()
    game.set_orders('FRANCE', 'A BRE B', replace=False)
    game.set_orders('FRANCE', 'F BRE B', replace=False)
    orders = game.get_orders()
    assert check_sorted(orders['FRANCE'], ['A BRE B'])

    # NO_CHECK Adjustment Phase
    game = Game()
    game.add_rule('NO_CHECK')
    game.clear_units()
    game.clear_centers()
    game.set_units('FRANCE', ['A BRE', 'A PAR'])
    game.set_units('AUSTRIA', 'A GAS')
    game.set_orders('FRANCE', 'A PAR - PIC', replace=False)
    game.process()
    game.set_orders('FRANCE', ['A PIC - BEL', 'A BRE - PAR'], replace=False)
    game.process()
    game.set_orders('FRANCE', 'A BRE B', replace=False)
    game.set_orders('FRANCE', 'F BRE B', replace=False)
    orders = game.get_orders()
    assert check_sorted(orders['FRANCE'], ['A BRE B'])

def test_clear_units():
    """ Tests - Clear units """
    game = Game()
    game.clear_units()
    for power in game.powers.values():
        assert not power.units
    assert not game.error

def test_clear_centers():
    """ Tests - Clear centers """
    game = Game()
    game.clear_centers()
    for power in game.powers.values():
        assert not power.centers
    assert not game.error

def test_clear_orders():
    """ Test - Clear orders"""
    game = Game()
    game.clear_units()
    game.set_units('ITALY', 'A VEN')
    game.set_units('AUSTRIA', 'A VIE')
    game.set_orders('ITALY', 'A VEN - TYR')
    game.set_orders('AUSTRIA', 'A VIE - TYR')
    game.clear_orders()
    game.process()
    results = game.get_order_status()
    assert results['ITALY']['A VEN'] == []
    assert results['AUSTRIA']['A VIE'] == []

def test_get_current_phase():
    """ Tests - get current phase """
    game = Game()
    assert game.get_current_phase() == 'S1901M'

def test_set_current_phase():
    """ Tests - set current phase"""
    game = Game()
    power = game.get_power('FRANCE')
    power.units.remove('A PAR')
    game.set_current_phase('W1901A')
    game.clear_cache()
    assert game.get_current_phase() == 'W1901A'
    assert game.phase_type == 'A'
    assert 'A PAR B' in game.get_all_possible_orders()['PAR']

def test_process_game():
    """ Tests - Process game """
    game = Game()
    game.clear_units()
    game.set_units('ITALY', 'A VEN')
    game.set_units('AUSTRIA', 'A VIE')
    game.set_orders('ITALY', 'A VEN - TYR')
    game.set_orders('AUSTRIA', 'A VIE - TYR')
    game.process()
    results = game.get_order_status()
    assert BOUNCE in results['ITALY']['A VEN']
    assert BOUNCE in results['AUSTRIA']['A VIE']

def test_deepcopy():
    """ Tests - deepcopy """
    game = Game()
    game2 = deepcopy(game)
    assert game != game2
    assert game.get_hash() == game2.get_hash()

def test_automatic_draw():
    """ Tests - draw """
    game = Game()
    assert game.map.first_year == 1901

    # fast forward 99 years with no winter
    for year in range(1, 100):
        game.process()
        game.process()
        assert int(game.get_current_phase()[1:5]) == game.map.first_year + year
    assert game.is_game_done is False

    # forward 2000 year. after this year should draw
    game.process()
    game.process()
    assert game.is_game_done is True
    assert list(sorted(game.outcome)) == list(
        sorted(['W2000A', 'AUSTRIA', 'ENGLAND', 'FRANCE', 'GERMANY', 'ITALY', 'RUSSIA', 'TURKEY']))

def test_histories():
    """ Test order_history, state_history, message_history and messages. """
    from diplomacy.server.server_game import ServerGame
    from diplomacy.utils.sorted_dict import SortedDict
    from diplomacy.utils import strings
    game = ServerGame(status=strings.ACTIVE)
    assert game.solitaire
    assert not game.n_controls
    assert game.is_game_active

    assert isinstance(game.messages, SortedDict)
    assert isinstance(game.message_history, SortedDict)
    assert isinstance(game.order_history, SortedDict)
    assert isinstance(game.state_history, SortedDict)
    assert not game.messages
    assert not game.message_history
    assert not game.order_history
    assert not game.state_history
    game.new_system_message('FRANCE', 'Hello France!')
    game.new_system_message('GLOBAL', 'Hello World!')
    game.set_orders('FRANCE', ['A PAR H'])
    assert len(game.messages) == 2
    previous_phase = game.get_current_phase()
    game.process()
    current_phase = game.get_current_phase()
    assert previous_phase != current_phase, (previous_phase, current_phase)
    assert not game.messages
    assert len(game.message_history) == 1
    assert len(game.order_history) == 1
    assert len(game.state_history) == 1
    game.set_orders('AUSTRIA', ['A BUD - GAL'])
    game.set_orders('FRANCE', ['A PAR H'])
    game.new_system_message('GLOBAL', 'New world.')
    assert len(game.messages) == 1
    game.process()
    assert not game.messages
    assert len(game.message_history) == 2
    assert len(game.order_history) == 2
    assert len(game.state_history) == 2
    assert all((p1 == p2 == p3) for (p1, p2, p3) in zip(game.message_history.keys(),
                                                        game.order_history.keys(),
                                                        game.state_history.keys()))

    assert game.map.compare_phases(str(game.state_history.first_key()), str(game.state_history.last_key())) < 0

    messages_phase_1 = list(game.message_history.first_value().values())
    messages_phase_2 = list(game.message_history.last_value().values())
    orders_phase_1 = game.order_history.first_value()
    orders_phase_2 = game.order_history.last_value()
    assert len(messages_phase_1) == 2
    assert len(messages_phase_2) == 1
    assert messages_phase_1[0].message == 'Hello France!'
    assert messages_phase_1[1].message == 'Hello World!'
    assert messages_phase_2[0].message == 'New world.'
    assert orders_phase_1['FRANCE'] == ['A PAR H']
    assert orders_phase_2['FRANCE'] == ['A PAR H']
    assert orders_phase_2['AUSTRIA'] == ['A BUD - GAL']

    assert all('messages' not in state for state in game.state_history.values())

    game_to_json = game.to_dict()
    game_copy = ServerGame.from_dict(game_to_json)
    assert list(game.state_history.keys()) == list(game_copy.state_history.keys())
    assert list(game.message_history.keys()) == list(game_copy.message_history.keys())
    assert list(game.order_history.keys()) == list(game_copy.order_history.keys())
    # Check histories in game copy.
    messages_phase_1 = list(game_copy.message_history.first_value().values())
    messages_phase_2 = list(game_copy.message_history.last_value().values())
    orders_phase_1 = game_copy.order_history.first_value()
    orders_phase_2 = game_copy.order_history.last_value()
    assert len(messages_phase_1) == 2
    assert len(messages_phase_2) == 1
    assert messages_phase_1[0].message == 'Hello France!'
    assert messages_phase_1[1].message == 'Hello World!'
    assert messages_phase_2[0].message == 'New world.'
    assert orders_phase_1['FRANCE'] == ['A PAR H']
    assert orders_phase_2['FRANCE'] == ['A PAR H']
    assert orders_phase_2['AUSTRIA'] == ['A BUD - GAL']

def test_result_history():
    """ Test result history. """
    short_phase_name = 'S1901M'
    game = Game()
    game.set_orders('FRANCE', ['A PAR - BUR', 'A MAR - BUR'])
    assert game.current_short_phase == short_phase_name
    game.process()
    assert game.current_short_phase == 'F1901M'
    phase_data = game.get_phase_from_history(short_phase_name)
    assert BOUNCE in phase_data.results['A PAR']
    assert BOUNCE in phase_data.results['A MAR']

def test_unit_owner():
    """ Test Unit Owner Resolver making sure the cached results are correct """
    game = Game()
    print(game.get_units('RUSSIA'))

    assert game._unit_owner('F STP/SC', coast_required=1) is game.get_power('RUSSIA')                                   # pylint: disable=protected-access
    assert game._unit_owner('F STP/SC', coast_required=0) is game.get_power('RUSSIA')                                   # pylint: disable=protected-access

    assert game._unit_owner('F STP', coast_required=1) is None                                                          # pylint: disable=protected-access
    assert game._unit_owner('F STP', coast_required=0) is game.get_power('RUSSIA')                                      # pylint: disable=protected-access

    assert game._unit_owner('A WAR', coast_required=0) is game.get_power('RUSSIA')                                      # pylint: disable=protected-access
    assert game._unit_owner('A WAR', coast_required=1) is game.get_power('RUSSIA')                                      # pylint: disable=protected-access

    assert game._unit_owner('F SEV', coast_required=0) is game.get_power('RUSSIA')                                      # pylint: disable=protected-access
    assert game._unit_owner('F SEV', coast_required=1) is game.get_power('RUSSIA')                                      # pylint: disable=protected-access
