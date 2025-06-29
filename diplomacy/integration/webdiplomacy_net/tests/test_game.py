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
from diplomacy.integration.webdiplomacy_net.game import turn_to_phase, unit_dict_to_str, center_dict_to_str, \
    order_dict_to_str

# ------------------------------------
# ---- Tests for turn_to_phase ----
# ------------------------------------
def test_phase_s1901m():
    """ Tests S1901M """
    phase = turn_to_phase(0, 'Diplomacy')
    assert phase == 'S1901M'

def test_phase_s1901r():
    """ Tests S1901R """
    phase = turn_to_phase(0, 'Retreats')
    assert phase == 'S1901R'

def test_phase_f1901m():
    """ Tests F1901M """
    phase = turn_to_phase(1, 'Diplomacy')
    assert phase == 'F1901M'

def test_phase_f1901r():
    """ Tests F1901R """
    phase = turn_to_phase(1, 'Retreats')
    assert phase == 'F1901R'

def test_phase_w1901a():
    """ Tests W1901A """
    phase = turn_to_phase(1, 'Builds')
    assert phase == 'W1901A'

def test_phase_s1902m():
    """ Tests S1902M """
    phase = turn_to_phase(2, 'Diplomacy')
    assert phase == 'S1902M'


# ------------------------------------
# ---- Tests for unit_dict_to_str ----
# ------------------------------------
def test_army_france():
    """ Tests Army France """
    unit_dict = {'unitType': 'Army', 'terrID': 47, 'countryID': 2, 'retreating': 'No'}
    power_name, unit = unit_dict_to_str(unit_dict)
    assert power_name == 'FRANCE'
    assert unit == 'A PAR'

def test_dis_fleet_england():
    """ Tests Dislodged Fleet England """
    unit_dict = {'unitType': 'Fleet', 'terrID': 6, 'countryID': 1, 'retreating': 'Yes'}
    power_name, unit = unit_dict_to_str(unit_dict)
    assert power_name == 'ENGLAND'
    assert unit == '*F LON'

def test_invalid_unit():
    """ Tests invalid unit """
    unit_dict = {'unitType': 'Fleet', 'terrID': 99, 'countryID': 0, 'retreating': 'No'}
    power_name, unit = unit_dict_to_str(unit_dict)
    assert power_name == ''
    assert unit == ''


# --------------------------------------
# ---- Tests for center_dict_to_str ----
# --------------------------------------
def test_center_dict():
    """ Tests parsing centers """
    power_name, center = center_dict_to_str({'countryID': 1, 'terrID': 6}, map_id=1)
    assert power_name == 'ENGLAND'
    assert center == 'LON'

    power_name, center = center_dict_to_str({'countryID': 2, 'terrID': 47}, map_id=1)
    assert power_name == 'FRANCE'
    assert center == 'PAR'


# -------------------------------------
# ---- Tests for order_dict_to_str ----
# -------------------------------------
def test_s1901m_hold():
    """ Tests hold in S1901M """
    order_dict = {'turn': 0,
                  'phase': 'Diplomacy',
                  'countryID': 2,
                  'terrID': 6,
                  'unitType': 'Army',
                  'type': 'Hold',
                  'toTerrID': '',
                  'fromTerrID': '',
                  'viaConvoy': ''}
    power_name, order = order_dict_to_str(order_dict, phase='Diplomacy')
    assert power_name == 'FRANCE'
    assert order == 'A LON H'

def test_s1901r_disband():
    """ Tests disband in S1901R """
    order_dict = {'turn': 0,
                  'phase': 'Retreats',
                  'countryID': 1,
                  'terrID': 6,
                  'unitType': 'Fleet',
                  'type': 'Disband',
                  'toTerrID': '',
                  'fromTerrID': '',
                  'viaConvoy': ''}
    power_name, order = order_dict_to_str(order_dict, phase='Retreats')
    assert power_name == 'ENGLAND'
    assert order == 'F LON D'

def test_f1901m_move():
    """ Tests move in F1901M """
    order_dict = {'turn': 1,
                  'phase': 'Diplomacy',
                  'countryID': 2,
                  'terrID': 6,
                  'unitType': 'Army',
                  'type': 'Move',
                  'toTerrID': 47,
                  'fromTerrID': '',
                  'viaConvoy': 'Yes'}
    power_name, order = order_dict_to_str(order_dict, phase='Diplomacy')
    assert power_name == 'FRANCE'
    assert order == 'A LON - PAR VIA'

def test_f1901r_retreat():
    """ Tests retreat in F1901R """
    order_dict = {'turn': 1,
                  'phase': 'Retreats',
                  'countryID': 3,
                  'terrID': 6,
                  'unitType': 'Army',
                  'type': 'Retreat',
                  'toTerrID': 47,
                  'fromTerrID': '',
                  'viaConvoy': ''}
    power_name, order = order_dict_to_str(order_dict, phase='Retreats')
    assert power_name == 'ITALY'
    assert order == 'A LON R PAR'

def test_w1901a_build():
    """ Tests build army in W1901A """
    order_dict = {'turn': 1,
                  'phase': 'Builds',
                  'countryID': 2,
                  'terrID': 6,
                  'unitType': 'Army',
                  'type': 'Build Army',
                  'toTerrID': 6,
                  'fromTerrID': '',
                  'viaConvoy': ''}
    power_name, order = order_dict_to_str(order_dict, phase='Builds')
    assert power_name == 'FRANCE'
    assert order == 'A LON B'

def test_s1902m_hold():
    """ Tests hold in S1902M """
    order_dict = {'turn': 2,
                  'phase': 'Diplomacy',
                  'countryID': 2,
                  'terrID': 6,
                  'unitType': 'Army',
                  'type': 'Hold',
                  'toTerrID': '',
                  'fromTerrID': '',
                  'viaConvoy': ''}
    power_name, order = order_dict_to_str(order_dict, phase='Diplomacy')
    assert power_name == 'FRANCE'
    assert order == 'A LON H'
