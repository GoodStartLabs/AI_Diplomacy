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
from diplomacy.daide import requests, tokens
from diplomacy.daide.requests import RequestBuilder
from diplomacy.daide.utils import str_to_bytes

def test_nme_001():
    """ Tests the NME request """
    daide_str = 'NME ( A l b e r t ) ( v 6 . 0 . 1 )'
    expected_str = 'NME (Albert) (v6.0.1)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.NME), 'Expected a NME request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.client_name == 'Albert'
    assert request.client_version == 'v6.0.1'

def test_nme_002():
    """ Tests the NME request """
    daide_str = 'NME ( J o h n D o e ) ( v 1 . 2 )'
    expected_str = 'NME (JohnDoe) (v1.2)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.NME), 'Expected a NME request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.client_name == 'JohnDoe'
    assert request.client_version == 'v1.2'

def test_obs():
    """ Test the OBS request """
    daide_str = 'OBS'
    expected_str = 'OBS'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.OBS), 'Expected a OBS request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str

def test_iam():
    """ Test the IAM request """
    daide_str = 'IAM ( FRA ) ( #1234 )'
    expected_str = 'IAM (FRA) (1234)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.IAM), 'Expected a IAM request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.power_name == 'FRANCE'
    assert request.passcode == '1234'

def test_hlo():
    """ Test the HLO request """
    daide_str = 'HLO'
    expected_str = 'HLO'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.HLO), 'Expected a HLO request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str

def test_map():
    """ Test the MAP request """
    daide_str = 'MAP'
    expected_str = 'MAP'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.MAP), 'Expected a MAP request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str

def test_mdf():
    """ Test the MDF request """
    daide_str = 'MDF'
    expected_str = 'MDF'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.MDF), 'Expected a MDF request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str

def test_sco():
    """ Test the SCO request """
    daide_str = 'SCO'
    expected_str = 'SCO'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SCO), 'Expected a SCO request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str

def test_now():
    """ Test the NOW request """
    daide_str = 'NOW'
    expected_str = 'NOW'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.NOW), 'Expected a NOW request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str

def test_hst_spr():
    """ Tests the HST request """
    daide_str = 'HST ( SPR #1901 )'
    expected_str = 'HST (SPR 1901)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.HST), 'Expected a HST request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == 'S1901M'

def test_sub_spr_hold():
    """ Tests the SUB request """
    daide_str = 'SUB ( SPR #1901 ) ( ( ENG AMY LVP ) HLD )'
    expected_str = 'SUB (SPR 1901) ((ENG AMY LVP) HLD)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == 'S1901M'
    assert request.power_name == 'ENGLAND'
    assert request.orders == ['A LVP H']

def test_sub_sum_hold():
    """ Tests the SUB request """
    daide_str = 'SUB ( SUM #1902 ) ( ( ENG AMY LVP ) HLD )'
    expected_str = 'SUB (SUM 1902) ((ENG AMY LVP) HLD)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == 'S1902R'
    assert request.power_name == 'ENGLAND'
    assert request.orders == ['A LVP H']

def test_sub_fal_hold():
    """ Tests the SUB request """
    daide_str = 'SUB ( FAL #1903 ) ( ( ENG AMY LVP ) HLD )'
    expected_str = 'SUB (FAL 1903) ((ENG AMY LVP) HLD)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == 'F1903M'
    assert request.power_name == 'ENGLAND'
    assert request.orders == ['A LVP H']

def test_sub_aut_hold():
    """ Tests the SUB request """
    daide_str = 'SUB ( AUT #1904 ) ( ( ENG AMY LVP ) HLD )'
    expected_str = 'SUB (AUT 1904) ((ENG AMY LVP) HLD)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == 'F1904R'
    assert request.power_name == 'ENGLAND'
    assert request.orders == ['A LVP H']

def test_sub_win_hold():
    """ Tests the SUB request """
    daide_str = 'SUB ( WIN #1905 ) ( ( ENG AMY LVP ) HLD )'
    expected_str = 'SUB (WIN 1905) ((ENG AMY LVP) HLD)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == 'W1905A'
    assert request.power_name == 'ENGLAND'
    assert request.orders == ['A LVP H']

def test_sub_austria_hold():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( AUS AMY LVP ) HLD )'
    expected_str = 'SUB ((AUS AMY LVP) HLD)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'AUSTRIA'
    assert request.orders == ['A LVP H']

def test_sub_english_hold():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( ENG AMY LVP ) HLD )'
    expected_str = 'SUB ((ENG AMY LVP) HLD)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'ENGLAND'
    assert request.orders == ['A LVP H']

def test_sub_france_hold():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( FRA AMY LVP ) HLD )'
    expected_str = 'SUB ((FRA AMY LVP) HLD)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'FRANCE'
    assert request.orders == ['A LVP H']

def test_sub_germany_hold():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( GER AMY LVP ) HLD )'
    expected_str = 'SUB ((GER AMY LVP) HLD)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'GERMANY'
    assert request.orders == ['A LVP H']

def test_sub_italy_hold():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( ITA AMY LVP ) HLD )'
    expected_str = 'SUB ((ITA AMY LVP) HLD)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'ITALY'
    assert request.orders == ['A LVP H']

def test_sub_russia_hold():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( RUS AMY LVP ) HLD )'
    expected_str = 'SUB ((RUS AMY LVP) HLD)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'RUSSIA'
    assert request.orders == ['A LVP H']

def test_sub_turkey_hold():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( TUR AMY LVP ) HLD )'
    expected_str = 'SUB ((TUR AMY LVP) HLD)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'TURKEY'
    assert request.orders == ['A LVP H']

def test_sub_fleet_hold():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( ENG FLT LVP ) HLD )'
    expected_str = 'SUB ((ENG FLT LVP) HLD)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'ENGLAND'
    assert request.orders == ['F LVP H']

def test_sub_eng_ech_hold():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( FRA FLT ECH ) HLD )'
    expected_str = 'SUB ((FRA FLT ECH) HLD)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'FRANCE'
    assert request.orders == ['F ENG H']

def test_sub_gob_bot_hold():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( FRA FLT GOB ) HLD )'
    expected_str = 'SUB ((FRA FLT GOB) HLD)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'FRANCE'
    assert request.orders == ['F BOT H']

def test_sub_gol_lyo_hold():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( FRA FLT GOL ) HLD )'
    expected_str = 'SUB ((FRA FLT GOL) HLD)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'FRANCE'
    assert request.orders == ['F LYO H']

def test_sub_move():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( ENG FLT LON ) MTO NTH )'
    expected_str = 'SUB ((ENG FLT LON) MTO NTH)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'ENGLAND'
    assert request.orders == ['F LON - NTH']

def test_sub_move_coast():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( ENG FLT BAR ) MTO ( STP NCS ) )'
    expected_str = 'SUB ((ENG FLT BAR) MTO (STP NCS))'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'ENGLAND'
    assert request.orders == ['F BAR - STP/NC']

def test_sub_support_hold_001():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( ENG FLT EDI ) SUP ( ENG FLT LON ) )'
    expected_str = 'SUB ((ENG FLT EDI) SUP (ENG FLT LON))'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'ENGLAND'
    assert request.orders == ['F EDI S F LON']

def test_sub_support_hold_002():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( ENG FLT NWY ) SUP ( ENG FLT BAR ) )'
    expected_str = 'SUB ((ENG FLT NWY) SUP (ENG FLT BAR))'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'ENGLAND'
    assert request.orders == ['F NWY S F BAR']

def test_sub_support_hold_003():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( ENG FLT NWG ) SUP ( ENG AMY YOR ) )'
    expected_str = 'SUB ((ENG FLT NWG) SUP (ENG AMY YOR))'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'ENGLAND'
    assert request.orders == ['F NWG S A YOR']

def test_sub_support_move_001():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( ENG FLT EDI ) SUP ( ENG FLT LON ) MTO NTH )'
    expected_str = 'SUB ((ENG FLT EDI) SUP (ENG FLT LON) MTO NTH)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'ENGLAND'
    assert request.orders == ['F EDI S F LON - NTH']

def test_sub_support_move_002():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( ENG FLT NWY ) SUP ( ENG FLT BAR ) MTO STP )'
    expected_str = 'SUB ((ENG FLT NWY) SUP (ENG FLT BAR) MTO STP)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'ENGLAND'
    assert request.orders == ['F NWY S F BAR - STP']

def test_sub_support_move_003():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( ENG FLT NWG ) SUP ( ENG AMY YOR ) MTO NWY )'
    expected_str = 'SUB ((ENG FLT NWG) SUP (ENG AMY YOR) MTO NWY)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'ENGLAND'
    assert request.orders == ['F NWG S A YOR - NWY']

def test_sub_move_via_001():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( ITA AMY TUN ) CTO SYR VIA ( ION EAS ) )'
    expected_str = 'SUB ((ITA AMY TUN) CTO SYR VIA (ION EAS))'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'ITALY'
    assert request.orders == ['A TUN - SYR VIA']

def test_sub_move_via_002():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( ENG AMY YOR ) CTO NWY VIA ( NTH ) )'
    expected_str = 'SUB ((ENG AMY YOR) CTO NWY VIA (NTH))'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'ENGLAND'
    assert request.orders == ['A YOR - NWY VIA']

def test_sub_convoy_001():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( ITA FLT ION ) CVY ( ITA AMY TUN ) CTO SYR )'
    expected_str = 'SUB ((ITA FLT ION) CVY (ITA AMY TUN) CTO SYR)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'ITALY'
    assert request.orders == ['F ION C A TUN - SYR']

def test_sub_convoy_002():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( ITA FLT EAS ) CVY ( ITA AMY TUN ) CTO SYR )'
    expected_str = 'SUB ((ITA FLT EAS) CVY (ITA AMY TUN) CTO SYR)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'ITALY'
    assert request.orders == ['F EAS C A TUN - SYR']

def test_sub_convoy_003():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( ENG FLT NTH ) CVY ( ENG AMY YOR ) CTO STP )'
    expected_str = 'SUB ((ENG FLT NTH) CVY (ENG AMY YOR) CTO STP)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'ENGLAND'
    assert request.orders == ['F NTH C A YOR - STP']

def test_sub_retreat():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( ENG FLT LON ) RTO NTH )'
    expected_str = 'SUB ((ENG FLT LON) RTO NTH)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'ENGLAND'
    assert request.orders == ['F LON R NTH']

def test_sub_retreat_coast():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( ENG FLT LON ) RTO ( STP NCS ) )'
    expected_str = 'SUB ((ENG FLT LON) RTO (STP NCS))'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'ENGLAND'
    assert request.orders == ['F LON R STP/NC']

def test_sub_disband():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( RUS FLT GOB ) DSB )'
    expected_str = 'SUB ((RUS FLT GOB) DSB)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'RUSSIA'
    assert request.orders == ['F BOT D']

def test_sub_build():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( ITA FLT NAP ) BLD )'
    expected_str = 'SUB ((ITA FLT NAP) BLD)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'ITALY'
    assert request.orders == ['F NAP B']

def test_sub_remove():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( RUS FLT GOB ) REM )'
    expected_str = 'SUB ((RUS FLT GOB) REM)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'RUSSIA'
    assert request.orders == ['F BOT D']

def test_sub_waive():
    """ Tests the SUB request """
    daide_str = 'SUB ( ENG WVE )'
    expected_str = 'SUB (ENG WVE)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'ENGLAND'
    assert request.orders == ['WAIVE']

def test_sub_multi_001():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( ENG AMY LVP ) HLD ) ' \
                '( ( ENG FLT LON ) MTO NTH ) ' \
                '( ( ENG FLT EDI ) SUP ( ENG FLT LON ) MTO NTH )'
    expected_str = 'SUB ((ENG AMY LVP) HLD) ' \
                   '((ENG FLT LON) MTO NTH) ' \
                   '((ENG FLT EDI) SUP (ENG FLT LON) MTO NTH)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'ENGLAND'
    assert request.orders == ['A LVP H', 'F LON - NTH', 'F EDI S F LON - NTH']

def test_sub_multi_002():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( ENG FLT BAR ) MTO ( STP NCS ) ) ' \
                '( ( ITA FLT NWY ) SUP ( ENG FLT BAR ) MTO STP )'
    expected_str = 'SUB ((ENG FLT BAR) MTO (STP NCS)) ' \
                   '((ITA FLT NWY) SUP (ENG FLT BAR) MTO STP)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'ENGLAND'
    assert request.orders == ['F BAR - STP/NC', 'F NWY S F BAR - STP']

def test_sub_multi_003():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( ITA AMY TUN ) CTO SYR VIA ( ION EAS ) ) ' \
                '( ( ITA FLT ION ) CVY ( ITA AMY TUN ) CTO SYR ) ' \
                '( ( ITA FLT EAS ) CVY ( ITA AMY TUN ) CTO SYR )'
    expected_str = 'SUB ((ITA AMY TUN) CTO SYR VIA (ION EAS)) ' \
                   '((ITA FLT ION) CVY (ITA AMY TUN) CTO SYR) ' \
                   '((ITA FLT EAS) CVY (ITA AMY TUN) CTO SYR)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'ITALY'
    assert request.orders == ['A TUN - SYR VIA', 'F ION C A TUN - SYR', 'F EAS C A TUN - SYR']

def test_sub_multi_004():
    """ Tests the SUB request """
    daide_str = 'SUB ( ( ENG AMY YOR ) CTO NWY VIA ( NTH ) ) ' \
                '( ( ENG FLT NTH ) CVY ( ENG AMY YOR ) CTO NWY ) ' \
                '( ( ENG FLT NWG ) SUP ( ENG AMY YOR ) MTO NWY )'
    expected_str = 'SUB ((ENG AMY YOR) CTO NWY VIA (NTH)) ' \
                   '((ENG FLT NTH) CVY (ENG AMY YOR) CTO NWY) ' \
                   '((ENG FLT NWG) SUP (ENG AMY YOR) MTO NWY)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SUB), 'Expected a SUB request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.power_name == 'ENGLAND'
    assert request.orders == ['A YOR - NWY VIA', 'F NTH C A YOR - NWY', 'F NWG S A YOR - NWY']

def test_mis():
    """ Test the MIS request """
    daide_str = 'MIS'
    expected_str = 'MIS'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.MIS), 'Expected a MIS request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str

def test_gof():
    """ Test the GOF request """
    daide_str = 'GOF'
    expected_str = 'GOF'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.GOF), 'Expected a GOF request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str

def test_tme():
    """ Tests the TME request """
    daide_str = 'TME'
    expected_str = 'TME'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.TME), 'Expected a TME request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.seconds is None

def test_tme_sec():
    """ Tests the TME request """
    daide_str = 'TME ( #60 )'
    expected_str = 'TME (60)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.TME), 'Expected a TME request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.seconds == 60

def test_drw_001():
    """ Test the DRW request """
    daide_str = 'DRW'
    expected_str = 'DRW'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.DRW), 'Expected a DRW request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.powers == []

def test_drw_002():
    """ Test the DRW request """
    daide_str = 'DRW ( FRA ENG ITA )'
    expected_str = 'DRW (FRA ENG ITA)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.DRW), 'Expected a DRW request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.powers == ['FRANCE', 'ENGLAND', 'ITALY']

def test_snd_001():
    """ Tests the SND request """
    daide_str = 'SND ( FRA ENG ) ( PRP ( PCE ( FRA ENG GER ) ) )'
    expected_str = 'SND (FRA ENG) (PRP (PCE (FRA ENG GER)))'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SND), 'Expected a SND request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.powers == ['FRANCE', 'ENGLAND']
    assert request.message_bytes == str_to_bytes('PRP ( PCE ( FRA ENG GER ) )')

def test_snd_002():
    """ Tests the SND request """
    daide_str = 'SND ( SPR #1901 ) ( FRA ENG ) ( PRP ( PCE ( FRA ENG GER ) ) )'
    expected_str = 'SND (SPR 1901) (FRA ENG) (PRP (PCE (FRA ENG GER)))'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SND), 'Expected a SND request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == 'S1901M'
    assert request.powers == ['FRANCE', 'ENGLAND']
    assert request.message_bytes == str_to_bytes('PRP ( PCE ( FRA ENG GER ) )')

def test_snd_003():
    """ Tests the SND request """
    daide_str = 'SND ( FRA ENG ) ( CCL ( PRP ( PCE ( FRA ENG GER ) ) ) )'
    expected_str = 'SND (FRA ENG) (CCL (PRP (PCE (FRA ENG GER))))'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SND), 'Expected a SND request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.powers == ['FRANCE', 'ENGLAND']
    assert request.message_bytes == str_to_bytes('CCL ( PRP ( PCE ( FRA ENG GER ) ) )')

def test_snd_004():
    """ Tests the SND request """
    daide_str = 'SND ( FRA ENG ) ( FCT ( PCE ( FRA ENG GER ) ) )'
    expected_str = 'SND (FRA ENG) (FCT (PCE (FRA ENG GER)))'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SND), 'Expected a SND request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.powers == ['FRANCE', 'ENGLAND']
    assert request.message_bytes == str_to_bytes('FCT ( PCE ( FRA ENG GER ) )')

def test_snd_005():
    """ Tests the SND request """
    daide_str = 'SND ( FRA ENG ) ( TRY ( PRP PCE ALY VSS DRW SLO NOT YES REJ BWX ) )'
    expected_str = 'SND (FRA ENG) (TRY (PRP PCE ALY VSS DRW SLO NOT YES REJ BWX))'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SND), 'Expected a SND request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.powers == ['FRANCE', 'ENGLAND']
    assert request.message_bytes == str_to_bytes('TRY ( PRP PCE ALY VSS DRW SLO NOT YES REJ BWX )')

def test_snd_006():
    """ Tests the SND request """
    daide_str = 'SND ( FRA GER ) ( YES ( PRP ( ALY ( FRA ENG GER ) VSS ( ITA ) ) ) )'
    expected_str = 'SND (FRA GER) (YES (PRP (ALY (FRA ENG GER) VSS (ITA))))'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SND), 'Expected a SND request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.powers == ['FRANCE', 'GERMANY']
    assert request.message_bytes == str_to_bytes('YES ( PRP ( ALY ( FRA ENG GER ) VSS ( ITA ) ) )')

def test_snd_007():
    """ Tests the SND request """
    daide_str = 'SND ( FRA GER ) ( REJ ( PRP ( ALY ( FRA ENG GER ) VSS ( ITA ) ) ) )'
    expected_str = 'SND (FRA GER) (REJ (PRP (ALY (FRA ENG GER) VSS (ITA))))'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SND), 'Expected a SND request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.powers == ['FRANCE', 'GERMANY']
    assert request.message_bytes == str_to_bytes('REJ ( PRP ( ALY ( FRA ENG GER ) VSS ( ITA ) ) )')

def test_snd_008():
    """ Tests the SND request """
    daide_str = 'SND ( FRA GER ) ( BWX ( PRP ( ALY ( FRA ENG GER ) VSS ( ITA ) ) ) )'
    expected_str = 'SND (FRA GER) (BWX (PRP (ALY (FRA ENG GER) VSS (ITA))))'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SND), 'Expected a SND request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.powers == ['FRANCE', 'GERMANY']
    assert request.message_bytes == str_to_bytes('BWX ( PRP ( ALY ( FRA ENG GER ) VSS ( ITA ) ) )')

def test_snd_009():
    """ Tests the SND request """
    daide_str = 'SND ( FRA GER ) ( HUH ( ERR PRP ( ALY ( FRA ENG GER ) VSS ( ITA ) ) ) )'
    expected_str = 'SND (FRA GER) (HUH (ERR PRP (ALY (FRA ENG GER) VSS (ITA))))'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.SND), 'Expected a SND request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.phase == ''
    assert request.powers == ['FRANCE', 'GERMANY']
    assert request.message_bytes == str_to_bytes('HUH ( ERR PRP ( ALY ( FRA ENG GER ) VSS ( ITA ) ) )')

def test_not_sub():
    """ Tests the NOT request """
    daide_str = 'NOT ( SUB )'
    expected_str = 'NOT (SUB)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.NOT), 'Expected a NOT request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert isinstance(request.request, requests.SUB), 'Expected a SUB not request'

def test_not_sub_orders():
    """ Tests the NOT request """
    daide_str = 'NOT ( SUB ( ( ENG AMY YOR ) CTO NWY VIA ( NTH ) ) ' \
                '( ( ENG FLT NTH ) CVY ( ENG AMY YOR ) CTO NWY ) ' \
                '( ( ENG FLT NWG ) SUP ( ENG AMY YOR ) MTO NWY ) )'
    expected_str = 'NOT (SUB ((ENG AMY YOR) CTO NWY VIA (NTH)) ' \
                   '((ENG FLT NTH) CVY (ENG AMY YOR) CTO NWY) ' \
                   '((ENG FLT NWG) SUP (ENG AMY YOR) MTO NWY))'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.NOT), 'Expected a NOT request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert isinstance(request.request, requests.SUB), 'Expected a SUB not request'

def test_not_gof():
    """ Tests the NOT request """
    daide_str = 'NOT ( GOF )'
    expected_str = 'NOT (GOF)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.NOT), 'Expected a NOT request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert isinstance(request.request, requests.GOF), 'Expected a GOF not request'

def test_not_tme():
    """ Tests the NOT request """
    daide_str = 'NOT ( TME )'
    expected_str = 'NOT (TME)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.NOT), 'Expected a NOT request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert isinstance(request.request, requests.TME), 'Expected a TME not request'

def test_not_tme_sec():
    """ Tests the NOT request """
    daide_str = 'NOT ( TME ( #60 ) )'
    expected_str = 'NOT (TME (60))'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.NOT), 'Expected a NOT request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert isinstance(request.request, requests.TME), 'Expected a TME not request'

def test_not_drw():
    """ Tests the NOT request """
    daide_str = 'NOT ( DRW )'
    expected_str = 'NOT (DRW)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.NOT), 'Expected a NOT request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert isinstance(request.request, requests.DRW), 'Expected a DRW not request'

def test_yes():
    """ Tests the YES request """
    daide_str = 'YES ( MAP ( s t a n d a r d ) )'
    expected_str = 'YES (MAP (standard))'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.YES), 'Expected a YES request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert tokens.Token(from_bytes=request.response_bytes[:2]) == tokens.MAP

def test_rej():
    """ Tests the REJ request """
    daide_str = 'REJ ( SVE ( g a m e n a m e ) )'
    expected_str = 'REJ (SVE (gamename))'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.REJ), 'Expected a REJ request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert tokens.Token(from_bytes=request.response_bytes[:2]) == tokens.SVE

def test_prn_sub():
    """ Tests the PRN request """
    daide_str = 'PRN ( SUB ( ( ENG AMY LVP ) HLD ) ' \
                '( ( ENG FLT LON ) MTO NTH ) ' \
                '( ( ENG FLT EDI ) SUP ( ENG FLT LON ) MTO NTH )'
    request_message_daide_str = 'SUB ( ( ENG AMY LVP ) HLD ) ' \
                                '( ( ENG FLT LON ) MTO NTH ) ' \
                                '( ( ENG FLT EDI ) SUP ( ENG FLT LON ) MTO NTH'
    expected_str = 'PRN (SUB ((ENG AMY LVP) HLD) ' \
                   '((ENG FLT LON) MTO NTH) ' \
                   '((ENG FLT EDI) SUP (ENG FLT LON) MTO NTH)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.PRN), 'Expected a PRN request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.message_bytes == str_to_bytes(request_message_daide_str)

def test_huh_sub():
    """ Tests the HUH request """
    daide_str = 'HUH ( )'
    expected_str = 'HUH ()'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.HUH), 'Expected a HUH request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.message_bytes == b''

def test_adm():
    """ Tests the ADM request """
    daide_str = 'ADM ( I \' m  h a v i n g  c o n n e c t i o n  p r o b l e m s )'
    expected_str = 'ADM (I\'m having connection problems)'
    request = RequestBuilder.from_bytes(str_to_bytes(daide_str))
    assert isinstance(request, requests.ADM), 'Expected a ADM request'
    assert bytes(request) == str_to_bytes(daide_str)
    assert str(request) == expected_str
    assert request.adm_message == 'I\'m having connection problems'
