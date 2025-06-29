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
""" Test order conversion. """
from diplomacy.integration.webdiplomacy_net.orders import Order

def compare_dicts(dict_1, dict_2):
    """ Checks if two dictionaries are equal """
    keys_1 = set(dict_1.keys()) - {'convoyPath'}
    keys_2 = set(dict_2.keys()) - {'convoyPath'}
    if keys_1 != keys_2:
        return False
    for key in keys_1:
        if dict_1[key] != dict_2[key]:
            return False
    return True

def test_hold_army_001():
    """ Tests hold army """
    raw_order = 'A PAR H'
    order_str = 'A PAR H'
    order_dict = {'terrID': 47,
                  'unitType': 'Army',
                  'type': 'Hold',
                  'toTerrID': '',
                  'fromTerrID': '',
                  'viaConvoy': ''}
    order_from_string = Order(raw_order)
    order_from_dict = Order(order_dict)

    # Validating
    assert order_from_string.to_string() == order_str
    assert compare_dicts(order_from_string.to_dict(), order_dict)
    assert order_from_dict.to_string() == order_str
    assert compare_dicts(order_from_dict.to_dict(), order_dict)

def test_hold_army_002():
    """ Tests hold army """
    raw_order = 'A ABC H'
    order_str = ''
    order_dict = {}
    order_from_string = Order(raw_order)
    order_from_dict = Order(order_dict)

    # Validating
    assert order_from_string.to_string() == order_str
    assert compare_dicts(order_from_string.to_dict(), order_dict)
    assert order_from_dict.to_string() == order_str
    assert compare_dicts(order_from_dict.to_dict(), order_dict)

def test_hold_fleet_001():
    """ Tests hold fleet """
    raw_order = 'F LON H'
    order_str = 'F LON H'
    order_dict = {'terrID': 6,
                  'unitType': 'Fleet',
                  'type': 'Hold',
                  'toTerrID': '',
                  'fromTerrID': '',
                  'viaConvoy': ''}
    order_from_string = Order(raw_order)
    order_from_dict = Order(order_dict)

    # Validating
    assert order_from_string.to_string() == order_str
    assert compare_dicts(order_from_string.to_dict(), order_dict)
    assert order_from_dict.to_string() == order_str
    assert compare_dicts(order_from_dict.to_dict(), order_dict)

def test_move_army_001():
    """ Tests move army """
    raw_order = 'A YOR - LON'
    order_str = 'A YOR - LON'
    order_dict = {'terrID': 4,
                  'unitType': 'Army',
                  'type': 'Move',
                  'toTerrID': 6,
                  'fromTerrID': '',
                  'viaConvoy': 'No'}
    order_from_string = Order(raw_order)
    order_from_dict = Order(order_dict)

    # Validating
    assert order_from_string.to_string() == order_str
    assert compare_dicts(order_from_string.to_dict(), order_dict)
    assert order_from_dict.to_string() == order_str
    assert compare_dicts(order_from_dict.to_dict(), order_dict)

def test_move_army_002():
    """ Tests move army """
    raw_order = 'A PAR - LON VIA'
    order_str = 'A PAR - LON VIA'
    order_dict = {'terrID': 47,
                  'unitType': 'Army',
                  'type': 'Move',
                  'toTerrID': 6,
                  'fromTerrID': '',
                  'viaConvoy': 'Yes'}
    order_from_string = Order(raw_order)
    order_from_dict = Order(order_dict)

    # Validating
    assert order_from_string.to_string() == order_str
    assert compare_dicts(order_from_string.to_dict(), order_dict)
    assert order_from_dict.to_string() == order_str
    assert compare_dicts(order_from_dict.to_dict(), order_dict)

def test_move_fleet_001():
    """ Tests move fleet """
    raw_order = 'F BRE - MAO'
    order_str = 'F BRE - MAO'
    order_dict = {'terrID': 46,
                  'unitType': 'Fleet',
                  'type': 'Move',
                  'toTerrID': 61,
                  'fromTerrID': '',
                  'viaConvoy': 'No'}
    order_from_string = Order(raw_order)
    order_from_dict = Order(order_dict)

    # Validating
    assert order_from_string.to_string() == order_str
    assert compare_dicts(order_from_string.to_dict(), order_dict)
    assert order_from_dict.to_string() == order_str
    assert compare_dicts(order_from_dict.to_dict(), order_dict)

def test_support_hold_001():
    """ Tests for support hold """
    raw_order = 'A PAR S F BRE'
    order_str = 'A PAR S BRE'
    order_dict = {'terrID': 47,
                  'unitType': 'Army',
                  'type': 'Support hold',
                  'toTerrID': 46,
                  'fromTerrID': '',
                  'viaConvoy': ''}
    order_from_string = Order(raw_order)
    order_from_dict = Order(order_dict)

    # Validating
    assert order_from_string.to_string() == order_str
    assert compare_dicts(order_from_string.to_dict(), order_dict)
    assert order_from_dict.to_string() == order_str
    assert compare_dicts(order_from_dict.to_dict(), order_dict)

def test_support_hold_002():
    """ Tests for support hold """
    raw_order = 'F MAO S F BRE'
    order_str = 'F MAO S BRE'
    order_dict = {'terrID': 61,
                  'unitType': 'Fleet',
                  'type': 'Support hold',
                  'toTerrID': 46,
                  'fromTerrID': '',
                  'viaConvoy': ''}
    order_from_string = Order(raw_order)
    order_from_dict = Order(order_dict)

    # Validating
    assert order_from_string.to_string() == order_str
    assert compare_dicts(order_from_string.to_dict(), order_dict)
    assert order_from_dict.to_string() == order_str
    assert compare_dicts(order_from_dict.to_dict(), order_dict)

def test_support_move_001():
    """ Tests support move """
    raw_order = 'A PAR S F MAO - BRE'
    order_str = 'A PAR S MAO - BRE'
    order_dict = {'terrID': 47,
                  'unitType': 'Army',
                  'type': 'Support move',
                  'toTerrID': 46,
                  'fromTerrID': 61,
                  'viaConvoy': ''}
    order_from_string = Order(raw_order)
    order_from_dict = Order(order_dict)

    # Validating
    assert order_from_string.to_string() == order_str
    assert compare_dicts(order_from_string.to_dict(), order_dict)
    assert order_from_dict.to_string() == order_str
    assert compare_dicts(order_from_dict.to_dict(), order_dict)

def test_support_move_002():
    """ Tests support move """
    raw_order = 'F MAO S A PAR - BRE'
    order_str = 'F MAO S PAR - BRE'
    order_dict = {'terrID': 61,
                  'unitType': 'Fleet',
                  'type': 'Support move',
                  'toTerrID': 46,
                  'fromTerrID': 47,
                  'viaConvoy': ''}
    order_from_string = Order(raw_order)
    order_from_dict = Order(order_dict)

    # Validating
    assert order_from_string.to_string() == order_str
    assert compare_dicts(order_from_string.to_dict(), order_dict)
    assert order_from_dict.to_string() == order_str
    assert compare_dicts(order_from_dict.to_dict(), order_dict)

def test_convoy_001():
    """ Tests convoy """
    raw_order = 'F MAO C A PAR - LON'
    order_str = 'F MAO C A PAR - LON'
    order_dict = {'terrID': 61,
                  'unitType': 'Fleet',
                  'type': 'Convoy',
                  'toTerrID': 6,
                  'fromTerrID': 47,
                  'viaConvoy': ''}
    order_from_string = Order(raw_order)
    order_from_dict = Order(order_dict)

    # Validating
    assert order_from_string.to_string() == order_str
    assert compare_dicts(order_from_string.to_dict(), order_dict)
    assert order_from_dict.to_string() == order_str
    assert compare_dicts(order_from_dict.to_dict(), order_dict)

def test_retreat_army_001():
    """ Tests retreat army """
    raw_order = 'A PAR R LON'
    order_str = 'A PAR R LON'
    order_dict = {'terrID': 47,
                  'unitType': 'Army',
                  'type': 'Retreat',
                  'toTerrID': 6,
                  'fromTerrID': '',
                  'viaConvoy': ''}
    order_from_string = Order(raw_order)
    order_from_dict = Order(order_dict)

    # Validating
    assert order_from_string.to_string() == order_str
    assert compare_dicts(order_from_string.to_dict(), order_dict)
    assert order_from_dict.to_string() == order_str
    assert compare_dicts(order_from_dict.to_dict(), order_dict)

def test_retreat_army_002():
    """ Tests retreat army """
    raw_order = 'A PAR - LON'
    order_str = 'A PAR R LON'
    order_dict = {'terrID': 47,
                  'unitType': 'Army',
                  'type': 'Retreat',
                  'toTerrID': 6,
                  'fromTerrID': '',
                  'viaConvoy': ''}
    order_from_string = Order(raw_order, phase_type='R')
    order_from_dict = Order(order_dict, phase_type='R')

    # Validating
    assert order_from_string.to_string() == order_str
    assert compare_dicts(order_from_string.to_dict(), order_dict)
    assert order_from_dict.to_string() == order_str
    assert compare_dicts(order_from_dict.to_dict(), order_dict)

def test_retreat_fleet_001():
    """ Tests retreat fleet """
    raw_order = 'F BRE R SPA/SC'
    order_str = 'F BRE R SPA/SC'
    order_dict = {'terrID': 46,
                  'unitType': 'Fleet',
                  'type': 'Retreat',
                  'toTerrID': 77,
                  'fromTerrID': '',
                  'viaConvoy': ''}
    order_from_string = Order(raw_order)
    order_from_dict = Order(order_dict)

    # Validating
    assert order_from_string.to_string() == order_str
    assert compare_dicts(order_from_string.to_dict(), order_dict)
    assert order_from_dict.to_string() == order_str
    assert compare_dicts(order_from_dict.to_dict(), order_dict)

def test_disband_army_001():
    """ Tests disband army """
    raw_order = 'A PAR D'
    order_str = 'A PAR D'
    order_dict = {'terrID': 47,
                  'unitType': 'Army',
                  'type': 'Disband',
                  'toTerrID': '',
                  'fromTerrID': '',
                  'viaConvoy': ''}
    order_from_string = Order(raw_order, phase_type='R')
    order_from_dict = Order(order_dict, phase_type='R')

    # Validating
    assert order_from_string.to_string() == order_str
    assert compare_dicts(order_from_string.to_dict(), order_dict)
    assert order_from_dict.to_string() == order_str
    assert compare_dicts(order_from_dict.to_dict(), order_dict)

def test_disband_fleet_001():
    """ Tests disband fleet """
    raw_order = 'F BRE D'
    order_str = 'F BRE D'
    order_dict = {'terrID': 46,
                  'unitType': 'Fleet',
                  'type': 'Disband',
                  'toTerrID': '',
                  'fromTerrID': '',
                  'viaConvoy': ''}
    order_from_string = Order(raw_order, phase_type='R')
    order_from_dict = Order(order_dict, phase_type='R')

    # Validating
    assert order_from_string.to_string() == order_str
    assert compare_dicts(order_from_string.to_dict(), order_dict)
    assert order_from_dict.to_string() == order_str
    assert compare_dicts(order_from_dict.to_dict(), order_dict)

def test_disband_fleet_coast_001():
    """ Tests disband fleet (retreats phase) """
    raw_order = 'F SPA/NC D'
    order_str = 'F SPA/NC D'
    order_dict = {'terrID': 76,
                  'unitType': 'Fleet',
                  'type': 'Disband',
                  'toTerrID': '',
                  'fromTerrID': '',
                  'viaConvoy': ''}
    order_from_string = Order(raw_order, phase_type='R')
    order_from_dict = Order(order_dict, phase_type='R')

    # Validating
    assert order_from_string.to_string() == order_str
    assert compare_dicts(order_from_string.to_dict(), order_dict)
    assert order_from_dict.to_string() == order_str
    assert compare_dicts(order_from_dict.to_dict(), order_dict)

def test_disband_fleet_coast_002():
    """ Tests disband fleet (adjustment phase)"""
    raw_order = 'F SPA/NC D'
    order_str = 'F SPA D'
    order_dict = {'terrID': 8,
                  'unitType': 'Fleet',
                  'type': 'Destroy',
                  'toTerrID': 8,
                  'fromTerrID': '',
                  'viaConvoy': ''}
    order_from_string = Order(raw_order, phase_type='A')
    order_from_dict = Order(order_dict, phase_type='A')

    # Validating
    assert order_from_string.to_string() == order_str
    assert compare_dicts(order_from_string.to_dict(), order_dict)
    assert order_from_dict.to_string() == order_str
    assert compare_dicts(order_from_dict.to_dict(), order_dict)

def test_build_army_001():
    """ Tests build army """
    raw_order = 'A PAR B'
    order_str = 'A PAR B'
    order_dict = {'terrID': 47,
                  'unitType': 'Army',
                  'type': 'Build Army',
                  'toTerrID': 47,
                  'fromTerrID': '',
                  'viaConvoy': ''}
    order_from_string = Order(raw_order)
    order_from_dict = Order(order_dict)

    # Validating
    assert order_from_string.to_string() == order_str
    assert compare_dicts(order_from_string.to_dict(), order_dict)
    assert order_from_dict.to_string() == order_str
    assert compare_dicts(order_from_dict.to_dict(), order_dict)

def test_build_fleet_001():
    """ Tests build fleet """
    raw_order = 'F BRE B'
    order_str = 'F BRE B'
    order_dict = {'terrID': 46,
                  'unitType': 'Fleet',
                  'type': 'Build Fleet',
                  'toTerrID': 46,
                  'fromTerrID': '',
                  'viaConvoy': ''}
    order_from_string = Order(raw_order)
    order_from_dict = Order(order_dict)

    # Validating
    assert order_from_string.to_string() == order_str
    assert compare_dicts(order_from_string.to_dict(), order_dict)
    assert order_from_dict.to_string() == order_str
    assert compare_dicts(order_from_dict.to_dict(), order_dict)

def test_disband_army_002():
    """ Tests disband army """
    raw_order = 'A PAR D'
    order_str = 'A PAR D'
    order_dict = {'terrID': 47,
                  'unitType': 'Army',
                  'type': 'Destroy',
                  'toTerrID': 47,
                  'fromTerrID': '',
                  'viaConvoy': ''}
    order_from_string = Order(raw_order, phase_type='A')
    order_from_dict = Order(order_dict, phase_type='A')

    # Validating
    assert order_from_string.to_string() == order_str
    assert compare_dicts(order_from_string.to_dict(), order_dict)
    assert order_from_dict.to_string() == order_str
    assert compare_dicts(order_from_dict.to_dict(), order_dict)

def test_disband_fleet_002():
    """ Tests disband fleet """
    raw_order = 'F BRE D'
    order_str = 'F BRE D'
    order_dict = {'terrID': 46,
                  'unitType': 'Fleet',
                  'type': 'Destroy',
                  'toTerrID': 46,
                  'fromTerrID': '',
                  'viaConvoy': ''}
    order_from_string = Order(raw_order, phase_type='A')
    order_from_dict = Order(order_dict, phase_type='A')

    # Validating
    assert order_from_string.to_string() == order_str
    assert compare_dicts(order_from_string.to_dict(), order_dict)
    assert order_from_dict.to_string() == order_str
    assert compare_dicts(order_from_dict.to_dict(), order_dict)
