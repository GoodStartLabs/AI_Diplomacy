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
""" Tests for request objects """
from diplomacy import Game
from diplomacy.daide import responses
from diplomacy.daide.utils import str_to_bytes
import diplomacy.utils.errors as err
from diplomacy.utils.order_results import OK, BOUNCE, DISLODGED

def test_map():
    """ Tests the MAP response """
    daide_str = 'MAP ( s t a n d a r d )'
    response = responses.MAP('standard')
    assert isinstance(response, responses.MAP), 'Expected a MAP response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_hlo():
    """ Tests the HLO response """
    daide_str = 'HLO ( FRA ) ( #1234 ) ( ( LVL #0 ) ( MTL #1200 ) ( RTL #1200 ) ( BTL #1200 ) ( AOA ) )'
    response = responses.HLO('FRANCE', 1234, 0, 1200, ['NO_CHECK'])
    assert isinstance(response, responses.HLO), 'Expected a HLO response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_hlo_no_deadline():
    """ Tests the HLO response """
    daide_str = 'HLO ( FRA ) ( #1234 ) ( ( LVL #0 ) ( AOA ) )'
    response = responses.HLO('FRANCE', 1234, 0, 0, ['NO_CHECK'])
    assert isinstance(response, responses.HLO), 'Expected a HLO response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_sco():
    """ Tests the SCO response """
    daide_str = 'SCO ( AUS BUD TRI VIE ) ( ENG EDI LON LVP ) ( FRA BRE MAR PAR ) ' \
                '( GER BER KIE MUN ) ( ITA NAP ROM VEN ) ( RUS MOS SEV STP WAR ) ' \
                '( TUR ANK CON SMY ) ( UNO BEL BUL DEN GRE HOL NWY POR RUM SER SPA SWE TUN )'
    game = Game(map_name='standard')
    power_centers = {power.name: power.centers for power in game.powers.values()}
    response = responses.SCO(power_centers, map_name='standard')
    assert isinstance(response, responses.SCO), 'Expected a SCO response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_now():
    """ Tests the NOW response """
    daide_str = 'NOW ( SPR #1901 ) ( AUS AMY BUD ) ( AUS AMY VIE ) ( AUS FLT TRI ) ( ENG FLT EDI )' \
                ' ( ENG FLT LON ) ( ENG AMY LVP ) ( FRA FLT BRE ) ( FRA AMY MAR ) ( FRA AMY PAR )' \
                ' ( GER FLT KIE ) ( GER AMY BER ) ( GER AMY MUN ) ( ITA FLT NAP ) ( ITA AMY ROM )' \
                ' ( ITA AMY VEN ) ( RUS AMY WAR ) ( RUS AMY MOS ) ( RUS FLT SEV )' \
                ' ( RUS FLT ( STP SCS ) ) ( TUR FLT ANK ) ( TUR AMY CON ) ( TUR AMY SMY )'
    game = Game(map_name='standard')
    phase_name = game.get_current_phase()
    units = {power.name: power.units for power in game.powers.values()}
    retreats = {power.name: power.retreats for power in game.powers.values()}
    response = responses.NOW(phase_name=phase_name, powers_units=units, powers_retreats=retreats)
    assert isinstance(response, responses.NOW), 'Expected a NOW response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_thx_001():
    """ Tests the THX response """
    daide_str = 'THX ( ( ENG FLT NWG ) SUP ( ENG AMY YOR ) MTO NWY ) ( MBV )'
    order_daide_str = '( ( ENG FLT NWG ) SUP ( ENG AMY YOR ) MTO NWY )'
    response = responses.THX(order_bytes=str_to_bytes(order_daide_str), results=[])
    assert isinstance(response, responses.THX), 'Expected a THX response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_thx_002():
    """ Tests the THX response """
    daide_str = 'THX ( ( ENG FLT NWG ) SUP ( ENG AMY YOR ) MTO NWY ) ( NYU )'
    order_daide_str = '( ( ENG FLT NWG ) SUP ( ENG AMY YOR ) MTO NWY )'
    response = responses.THX(order_bytes=str_to_bytes(order_daide_str),
                             results=[error.code for error in [err.GAME_ORDER_TO_FOREIGN_UNIT % 'A MAR']])
    assert isinstance(response, responses.THX), 'Expected a THX response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_thx_003():
    """ Tests the THX response """
    daide_str = 'THX ( ( ENG FLT NWG ) SUP ( ENG AMY YOR ) MTO NWY ) ( MBV )'
    order_daide_str = '( ( ENG FLT NWG ) SUP ( ENG AMY YOR ) MTO NWY )'
    response = responses.THX(order_bytes=str_to_bytes(order_daide_str),
                             results=[error.code for error in [OK, err.MAP_LEAST_TWO_POWERS]])
    assert isinstance(response, responses.THX), 'Expected a THX response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_mis_001():
    """ Tests the MIS response """
    daide_str = 'MIS ( FRA FLT BRE ) ( FRA AMY MAR ) ( FRA AMY PAR )'
    game = Game(map_name='standard')
    phase_name = 'S1901M'
    power = game.get_power('FRANCE')
    response = responses.MIS(phase_name=phase_name, power=power)
    assert isinstance(response, responses.MIS), 'Expected a MIS response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_mis_002():
    """ Tests the MIS response """
    daide_str = 'MIS ( TUR FLT ANK MRT ( ARM ) ) ' \
                '( TUR FLT CON MRT ( BLA SMY ( BUL ECS ) ( BUL SCS ) ) ) ' \
                '( TUR AMY SMY MRT ( SYR ) )'
    game = Game(map_name='standard')
    phase_name = 'S1901R'
    power = game.get_power('TURKEY')
    power.units = ['F ANK', 'F CON', 'A SMY']
    power.retreats['F ANK'] = ['ARM']
    power.retreats['F CON'] = ['BLA', 'SMY', 'BUL/EC', 'BUL/SC']
    power.retreats['A SMY'] = ['SYR']
    response = responses.MIS(phase_name=phase_name, power=power)
    assert isinstance(response, responses.MIS), 'Expected a MIS response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_mis_003():
    """ Tests the MIS response """
    daide_str = 'MIS ( #0 )'
    game = Game(map_name='standard')
    phase_name = 'W1901A'
    power = game.get_power('FRANCE')
    response = responses.MIS(phase_name=phase_name, power=power)
    assert isinstance(response, responses.MIS), 'Expected a MIS response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_mis_004():
    """ Tests the MIS response """
    daide_str = 'MIS ( #1 )'
    game = Game(map_name='standard')
    phase_name = 'W1901A'
    power = game.get_power('FRANCE')
    power.centers = power.centers[:-1]
    response = responses.MIS(phase_name=phase_name, power=power)
    assert isinstance(response, responses.MIS), 'Expected a MIS response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_mis_005():
    """ Tests the MIS response """
    daide_str = 'MIS ( #-1 )'
    game = Game(map_name='standard')
    phase_name = 'W1901A'
    power = game.get_power('FRANCE')
    power.units = power.units[:-1]
    response = responses.MIS(phase_name=phase_name, power=power)
    assert isinstance(response, responses.MIS), 'Expected a MIS response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_mis_006():
    """ Tests the MIS response """
    daide_str = 'MIS ( #1 )'
    game = Game(map_name='standard')
    phase_name = 'W1901A'
    power = game.get_power('FRANCE')
    power.units = power.units + ['F LON']
    response = responses.MIS(phase_name=phase_name, power=power)
    assert isinstance(response, responses.MIS), 'Expected a MIS response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_mis_007():
    """ Tests the MIS response """
    daide_str = 'MIS ( FRA FLT BRE ) ( FRA AMY MAR )'
    game = Game(map_name='standard')
    game.set_orders('FRANCE', ['A PAR - BUR'])
    phase_name = 'S1901M'
    power = game.get_power('FRANCE')
    response = responses.MIS(phase_name=phase_name, power=power)
    assert isinstance(response, responses.MIS), 'Expected a MIS response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_mis_008():
    """ Tests the MIS response """
    daide_str = 'MIS ( FRA FLT BRE ) ( FRA AMY MAR )'
    game = Game(map_name='standard')
    game.add_rule('NO_CHECK')
    game.set_orders('FRANCE', ['A PAR - BUR'])
    phase_name = 'S1901M'
    power = game.get_power('FRANCE')
    response = responses.MIS(phase_name=phase_name, power=power)
    assert isinstance(response, responses.MIS), 'Expected a MIS response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_mis_009():
    """ Tests the MIS response """
    daide_str = 'MIS ( FRA FLT BRE ) ( FRA AMY MAR )'
    game = Game(map_name='standard')
    phase_name = 'S1901M'
    power = game.get_power('FRANCE')
    power.orders['REORDER 1'] = 'A PAR - BUR'
    response = responses.MIS(phase_name=phase_name, power=power)
    assert isinstance(response, responses.MIS), 'Expected a MIS response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_mis_010():
    """ Tests the MIS response """
    daide_str = 'MIS ( FRA FLT BRE ) ( FRA AMY MAR )'
    game = Game(map_name='standard')
    phase_name = 'S1901M'
    power = game.get_power('FRANCE')
    power.orders['INVALID'] = 'A PAR - BUR'
    response = responses.MIS(phase_name=phase_name, power=power)
    assert isinstance(response, responses.MIS), 'Expected a MIS response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_mis_011():
    """ Tests the MIS response """
    daide_str = 'MIS ( #0 )'
    game = Game(map_name='standard')
    phase_name = 'W1901A'
    power = game.get_power('FRANCE')
    power.centers += ['LON']
    response = responses.MIS(phase_name=phase_name, power=power)
    assert isinstance(response, responses.MIS), 'Expected a MIS response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_mis_012():
    """ Tests the MIS response """
    daide_str = 'MIS ( #-1 )'
    game = Game(map_name='standard')
    phase_name = 'W1901A'
    power = game.get_power('FRANCE')
    power.centers += ['LON']
    power.units = power.units[:2]
    response = responses.MIS(phase_name=phase_name, power=power)
    assert isinstance(response, responses.MIS), 'Expected a MIS response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_ord_001():
    """ Tests the ORD response """
    daide_str = 'ORD ( SPR #1901 ) ( ( ENG FLT NWG ) SUP ( ENG AMY YOR ) MTO NWY ) ( SUC )'
    order_daide_str = '( ENG FLT NWG ) SUP ( ENG AMY YOR ) MTO NWY'
    game = Game(map_name='standard')
    phase_name = game.map.phase_abbr(game.phase)
    response = responses.ORD(phase_name=phase_name, order_bytes=str_to_bytes(order_daide_str), results=[])
    assert isinstance(response, responses.ORD), 'Expected a ORD response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_ord_002():
    """ Tests the ORD response """
    daide_str = 'ORD ( SPR #1901 ) ( ( ENG FLT NWG ) SUP ( ENG AMY YOR ) MTO NWY ) ( NSO )'
    order_daide_str = '( ENG FLT NWG ) SUP ( ENG AMY YOR ) MTO NWY'
    game = Game(map_name='standard')
    phase_name = game.map.phase_abbr(game.phase)
    response = responses.ORD(phase_name=phase_name, order_bytes=str_to_bytes(order_daide_str),
                             results=[BOUNCE.code])
    assert isinstance(response, responses.ORD), 'Expected a ORD response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_ord_003():
    """ Tests the ORD response """
    daide_str = 'ORD ( SPR #1901 ) ( ( ENG FLT NWG ) SUP ( ENG AMY YOR ) MTO NWY ) ( NSO )'
    order_daide_str = '( ENG FLT NWG ) SUP ( ENG AMY YOR ) MTO NWY'
    game = Game(map_name='standard')
    phase_name = game.map.phase_abbr(game.phase)
    response = responses.ORD(phase_name=phase_name, order_bytes=str_to_bytes(order_daide_str),
                             results=[DISLODGED])
    assert isinstance(response, responses.ORD), 'Expected a ORD response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_ord_004():
    """ Tests the ORD response """
    daide_str = 'ORD ( SPR #1901 ) ( ( ENG FLT NWG ) SUP ( ENG AMY YOR ) MTO NWY ) ( NSO )'
    order_daide_str = '( ENG FLT NWG ) SUP ( ENG AMY YOR ) MTO NWY'
    game = Game(map_name='standard')
    phase_name = game.map.phase_abbr(game.phase)
    response = responses.ORD(phase_name=phase_name, order_bytes=str_to_bytes(order_daide_str),
                             results=[BOUNCE.code, DISLODGED])
    assert isinstance(response, responses.ORD), 'Expected a ORD response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_tme():
    """ Tests the TME response """
    daide_str = 'TME ( #60 )'
    response = responses.TME(seconds=60)
    assert isinstance(response, responses.TME), 'Expected a TME response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_yes():
    """ Tests the YES response """
    daide_str = 'YES ( TME ( #60 ) )'
    request_daide_str = 'TME ( #60 )'
    response = responses.YES(request_bytes=str_to_bytes(request_daide_str))
    assert isinstance(response, responses.YES), 'Expected a YES response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_rej():
    """ Tests the REJ response """
    daide_str = 'REJ ( TME ( #60 ) )'
    request_daide_str = 'TME ( #60 )'
    response = responses.REJ(request_bytes=str_to_bytes(request_daide_str))
    assert isinstance(response, responses.REJ), 'Expected a REJ response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_not():
    """ Tests the NOT response """
    daide_str = 'NOT ( CCD ( FRA ) )'
    response_daide_str = 'CCD ( FRA )'
    response = responses.NOT(response_bytes=str_to_bytes(response_daide_str))
    assert isinstance(response, responses.NOT), 'Expected a NOT response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_ccd():
    """ Tests the CCD response """
    daide_str = 'CCD ( AUS )'
    response = responses.CCD(power_name='AUSTRIA')
    assert isinstance(response, responses.CCD), 'Expected a CCD response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_out():
    """ Tests the OUT response """
    daide_str = 'OUT ( AUS )'
    response = responses.OUT(power_name='AUSTRIA')
    assert isinstance(response, responses.OUT), 'Expected a OUT response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_prn():
    """ Tests the PRN response """
    daide_str = 'PRN ( SUB ( ( ENG AMY LVP ) HLD ) ' \
                '( ( ENG FLT LON ) MTO NTH ) ' \
                '( ( ENG FLT EDI ) SUP ( ENG FLT LON ) MTO NTH )'
    request_daide_str = 'SUB ( ( ENG AMY LVP ) HLD ) ' \
                        '( ( ENG FLT LON ) MTO NTH ) ' \
                        '( ( ENG FLT EDI ) SUP ( ENG FLT LON ) MTO NTH'
    response = responses.PRN(request_bytes=str_to_bytes(request_daide_str))
    assert isinstance(response, responses.PRN), 'Expected a PRN response'
    assert bytes(response) == str_to_bytes(daide_str)

def test_huh():
    """ Tests the HUH response """
    daide_str = 'HUH ( ERR )'
    response = responses.HUH(b'', 0)
    assert isinstance(response, responses.HUH), 'Expected a HUH response'
    assert bytes(response) == str_to_bytes(daide_str)
