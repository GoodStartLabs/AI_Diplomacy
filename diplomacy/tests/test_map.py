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
""" Tests cases for Map
    - Contains the test cases for the map object
"""
from copy import deepcopy
from diplomacy.engine.map import Map

def test_init():
    """ Creates a map"""
    Map()

def test_str():
    """ Tests map.__str__ """
    this_map = deepcopy(Map())
    assert str(this_map) == this_map.name

def test_add_homes():
    """ Tests map.add_homes """
    this_map = deepcopy(Map())
    this_map.add_homes('FRANCE', 'BRE MAR PAR'.split(), reinit=1)
    assert this_map.homes['FRANCE'] == ['BRE', 'MAR', 'PAR']
    this_map.add_homes('FRANCE', [], reinit=1)
    assert this_map.homes['FRANCE'] == []

def test_drop():
    """ Tests map.drop """
    this_map = deepcopy(Map())
    this_map.drop('STP')
    assert not [loc for loc in list(this_map.locs) if loc.upper().startswith('STP')]
    assert not [loc_name for (loc_name, loc) in list(this_map.loc_name.items()) if loc.startswith('STP')]
    assert not [alias for (alias, value) in list(this_map.aliases.items()) if value.startswith('STP')]
    assert not [homes for homes in list(this_map.homes.values()) if 'STP' in homes]
    assert not [units for units in list(this_map.units.values()) for unit in units if unit[2:5] == 'STP'[:3]]
    assert not [center for center in list(this_map.scs) if center.upper().startswith('STP')]
    assert not [p_name for (p_name, scs) in this_map.centers.items() for center in scs if center.startswith('STP')]
    assert not [loc for loc, abuts in list(this_map.loc_abut.items()) for there in abuts
                if loc.startswith('STP') or there.startswith('STP')]
    assert not [loc for loc in list(this_map.loc_type.keys()) if loc.startswith('STP')]

def test_compact():
    """ Tests map.compact """
    this_map = deepcopy(Map())
    # Power name at top of string is removed by Map.compact().
    assert this_map.compact('England: Fleet Western Mediterranean -> Tyrrhenian Sea. (*bounce*)') \
           == ['F', 'WES', 'TYS', '|']

def test_norm_power():
    """ Tests map.norm_power """
    this_map = deepcopy(Map())
    assert this_map.norm_power('abc def. ghi/jkl!-ABC|~ (Hello)') == 'ABCDEFGHI/JKL!ABC|~(HELLO)'

def test_norm():
    """ Tests map.norm """
    this_map = deepcopy(Map())
    assert this_map.norm('abc def. ghi/jkl!-ABC|~ (Hello)') == 'ABC DEF GHI /JKL ! ABC | ~ ( HELLO )'

def test_vet():
    """ Tests map.vet """
    this_map = deepcopy(Map())
    assert this_map.vet(['A B']) == [('A B', 0)]
    assert this_map.vet(['SPAIN/NC']) == [('SPAIN/NC', 1)]
    assert this_map.vet(['SPANISH']) == [('SPANISH', 1)]
    assert this_map.vet(['A']) == [('A', 2)]
    assert this_map.vet(['F']) == [('F', 2)]
    assert this_map.vet(['POR']) == [('POR', 3)]
    assert this_map.vet(['SPA']) == [('SPA', 3)]
    assert this_map.vet(['SPA/NC']) == [('SPA/NC', 4)]
    assert this_map.vet(['S']) == [('S', 5)]
    assert this_map.vet(['C']) == [('C', 5)]
    assert this_map.vet(['H']) == [('H', 5)]
    assert this_map.vet(['-']) == [('-', 6)]
    assert this_map.vet(['=']) == [('=', 6)]
    assert this_map.vet(['_']) == [('_', 6)]
    assert this_map.vet(['|']) == [('|', 7)]
    assert this_map.vet(['?']) == [('?', 7)]
    assert this_map.vet(['~']) == [('~', 7)]
    assert this_map.vet(['ZZZ'], strict=0) == [('ZZZ', 3)]
    assert this_map.vet(['ZZZ'], strict=1) == [('ZZZ', -3)]

def test_area_type():
    """ Tests map.area_type """
    this_map = deepcopy(Map())
    assert this_map.area_type('ADR') == 'WATER'
    assert this_map.area_type('ALB') == 'COAST'
    assert this_map.area_type('BUL/EC') == 'COAST'
    assert this_map.area_type('BUR') == 'LAND'
    assert this_map.area_type('SWI') == 'SHUT'

def test_default_coast():
    """ Tests map.default_coast """
    this_map = deepcopy(Map())
    assert this_map.default_coast(['F', 'GRE', '-', 'BUL']) == ['F', 'GRE', '-', 'BUL/SC']
    assert this_map.default_coast(['F', 'MAO', '-', 'SPA']) == ['F', 'MAO', '-', 'SPA']
    assert this_map.default_coast(['F', 'FIN', '-', 'STP']) == ['F', 'FIN', '-', 'STP/SC']
    assert this_map.default_coast(['F', 'NAO', '-', 'MAO']) == ['F', 'NAO', '-', 'MAO']

def test_abuts():
    """ Tests map.abuts """
    this_map = deepcopy(Map())
    assert this_map.abuts('A', 'POR', 'S', 'SPA/NC') == 1
    assert this_map.abuts('A', 'POR', 'C', 'SPA/NC') == 0
    assert this_map.abuts('A', 'MUN', 'S', 'SWI') == 0
    assert this_map.abuts('?', 'YOR', 'S', 'LVP') == 1
    assert this_map.abuts('F', 'YOR', 'S', 'LVP') == 0
    assert this_map.abuts('A', 'YOR', 'S', 'LVP') == 1
    assert this_map.abuts('F', 'BOT', 'S', 'STP') == 1
    assert this_map.abuts('F', 'BOT', 'S', 'MOS') == 0
    assert this_map.abuts('F', 'VEN', 'S', 'TUS') == 0
    assert this_map.abuts('A', 'POR', 'C', 'MAO') == 1

def test_is_valid_unit():
    """ Tests maps.is_valid_unit """
    # ADR = WATER
    # ALB = COAST
    # BUL/EC = COAST
    # BUR = LAND
    # SWI = SHUT
    this_map = deepcopy(Map())
    assert this_map.is_valid_unit('A ADR', no_coast_ok=0, shut_ok=0) == 0
    assert this_map.is_valid_unit('A ALB', no_coast_ok=0, shut_ok=0) == 1
    assert this_map.is_valid_unit('A BUL', no_coast_ok=0, shut_ok=0) == 1
    assert this_map.is_valid_unit('A BUL/EC', no_coast_ok=0, shut_ok=0) == 0
    assert this_map.is_valid_unit('A BUR', no_coast_ok=0, shut_ok=0) == 1
    assert this_map.is_valid_unit('A SWI', no_coast_ok=0, shut_ok=0) == 0
    assert this_map.is_valid_unit('F ADR', no_coast_ok=0, shut_ok=0) == 1
    assert this_map.is_valid_unit('F ALB', no_coast_ok=0, shut_ok=0) == 1
    assert this_map.is_valid_unit('F BUL', no_coast_ok=0, shut_ok=0) == 0
    assert this_map.is_valid_unit('F BUL/EC', no_coast_ok=0, shut_ok=0) == 1
    assert this_map.is_valid_unit('F BUR', no_coast_ok=0, shut_ok=0) == 0
    assert this_map.is_valid_unit('F SWI', no_coast_ok=0, shut_ok=0) == 0
    assert this_map.is_valid_unit('F ADR', no_coast_ok=1, shut_ok=0) == 1
    assert this_map.is_valid_unit('F ALB', no_coast_ok=1, shut_ok=0) == 1
    assert this_map.is_valid_unit('F BUL', no_coast_ok=1, shut_ok=0) == 1
    assert this_map.is_valid_unit('F BUL/EC', no_coast_ok=1, shut_ok=0) == 1
    assert this_map.is_valid_unit('F BUR', no_coast_ok=1, shut_ok=0) == 0
    assert this_map.is_valid_unit('F SWI', no_coast_ok=1, shut_ok=0) == 0
    assert this_map.is_valid_unit('? ADR', no_coast_ok=0, shut_ok=0) == 1
    assert this_map.is_valid_unit('? ALB', no_coast_ok=0, shut_ok=0) == 1
    assert this_map.is_valid_unit('? BUL', no_coast_ok=0, shut_ok=0) == 1
    assert this_map.is_valid_unit('? BUL/EC', no_coast_ok=0, shut_ok=0) == 1
    assert this_map.is_valid_unit('? BUR', no_coast_ok=0, shut_ok=0) == 1
    assert this_map.is_valid_unit('? SWI', no_coast_ok=0, shut_ok=0) == 0
    assert this_map.is_valid_unit('A SWI', no_coast_ok=0, shut_ok=1) == 1
    assert this_map.is_valid_unit('F SWI', no_coast_ok=0, shut_ok=1) == 1
    assert this_map.is_valid_unit('? SWI', no_coast_ok=0, shut_ok=1) == 1

def test_abut_list():
    """ Tests map.abut_list """
    this_map = deepcopy(Map())
    this_map.loc_abut['---'] = ['ABC', 'DEF', 'GHI']
    this_map.loc_abut['aaa'] = ['LOW', 'HIG', 'MAY']
    assert this_map.abut_list('---') == ['ABC', 'DEF', 'GHI']
    assert this_map.abut_list('AAA') == ['LOW', 'HIG', 'MAY']
    assert this_map.abut_list('LVP') == ['CLY', 'edi', 'IRI', 'NAO', 'WAL', 'yor']

def test_compare_phases():
    """ Tests map.compare_phases """
    this_map = deepcopy(Map())
    assert this_map.compare_phases('FORMING', 'S1901M') == -1
    assert this_map.compare_phases('COMPLETED', 'S1901M') == 1
    assert this_map.compare_phases('S1901M', 'FORMING') == 1
    assert this_map.compare_phases('S1901M', 'COMPLETED') == -1
    assert this_map.compare_phases('FORMING', 'COMPLETED') == -1
    assert this_map.compare_phases('COMPLETED', 'FORMING') == 1
    assert this_map.compare_phases('S1901M', 'S1902M') == -1
    assert this_map.compare_phases('S1902M', 'S1901M') == 1
    assert this_map.compare_phases('S1901M', 'F1901M') == -1
    assert this_map.compare_phases('F1901M', 'S1901M') == 1
    assert this_map.compare_phases('S1901?', 'S1901R') == 0
    assert this_map.compare_phases('F1901?', 'F1901R') == 0
    assert this_map.compare_phases('W1901?', 'W1901A') == 0

def test_find_next_phase():
    """ Tests map.find_next_phase """
    this_map = deepcopy(Map())
    assert this_map.find_next_phase('FORMING') == 'FORMING'
    assert this_map.find_next_phase('COMPLETED') == 'COMPLETED'
    assert this_map.find_next_phase('WINTER 1901 ADJUSTMENTS') == 'SPRING 1902 MOVEMENT'
    assert this_map.find_next_phase('FALL 1901 RETREATS', phase_type='M') == 'SPRING 1902 MOVEMENT'
    assert this_map.find_next_phase('SPRING 1902 RETREATS', phase_type='M', skip=1) == 'SPRING 1903 MOVEMENT'

def test_find_previous_phase():
    """ Tests map.find_previous_phase """
    this_map = deepcopy(Map())
    assert this_map.find_previous_phase('FORMING') == 'FORMING'
    assert this_map.find_previous_phase('COMPLETED') == 'COMPLETED'
    assert this_map.find_previous_phase('SPRING 1902 MOVEMENT') == 'WINTER 1901 ADJUSTMENTS'
    assert this_map.find_previous_phase('SPRING 1902 MOVEMENT', phase_type='R') == 'FALL 1901 RETREATS'
    assert this_map.find_previous_phase('SPRING 1903 MOVEMENT', phase_type='R', skip=1) == 'SPRING 1902 RETREATS'

def test_phase_abbr():
    """ Tests map.phase_abbr """
    this_map = deepcopy(Map())
    assert this_map.phase_abbr('SPRING 1901 MOVEMENT') == 'S1901M'
    assert this_map.phase_abbr('SPRING 1901 RETREATS') == 'S1901R'
    assert this_map.phase_abbr('FALL 1901 MOVEMENT') == 'F1901M'
    assert this_map.phase_abbr('FALL 1901 RETREATS') == 'F1901R'
    assert this_map.phase_abbr('WINTER 1901 ADJUSTMENTS') == 'W1901A'
    assert this_map.phase_abbr('spring 1901 movement') == 'S1901M'
    assert this_map.phase_abbr('spring 1901 retreats') == 'S1901R'
    assert this_map.phase_abbr('fall 1901 movement') == 'F1901M'
    assert this_map.phase_abbr('fall 1901 retreats') == 'F1901R'
    assert this_map.phase_abbr('winter 1901 adjustments') == 'W1901A'
    assert this_map.phase_abbr('COMPLETED') == 'COMPLETED'
    assert this_map.phase_abbr('FORMING') == 'FORMING'
    assert this_map.phase_abbr('Bad') == '?????'
    assert this_map.phase_abbr('Bad', default='Test') == 'Test'

def test_phase_long():
    """ Test map.phase_long """
    this_map = deepcopy(Map())
    assert this_map.phase_long('S1901M') == 'SPRING 1901 MOVEMENT'
    assert this_map.phase_long('S1901R') == 'SPRING 1901 RETREATS'
    assert this_map.phase_long('F1901M') == 'FALL 1901 MOVEMENT'
    assert this_map.phase_long('F1901R') == 'FALL 1901 RETREATS'
    assert this_map.phase_long('W1901A') == 'WINTER 1901 ADJUSTMENTS'
    assert this_map.phase_long('s1901m') == 'SPRING 1901 MOVEMENT'
    assert this_map.phase_long('s1901r') == 'SPRING 1901 RETREATS'
    assert this_map.phase_long('f1901m') == 'FALL 1901 MOVEMENT'
    assert this_map.phase_long('f1901r') == 'FALL 1901 RETREATS'
    assert this_map.phase_long('w1901a') == 'WINTER 1901 ADJUSTMENTS'
    assert this_map.phase_long('bad') == '?????'
    assert this_map.phase_long('bad', default='Test') == 'Test'
